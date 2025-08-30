"""
Analysis Engine - Handles technical analysis and signal generation.
Follows Single Responsibility Principle by only handling analysis.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from domain.models import AnalysisResult, TradingSignal, Symbol
from application.scoring_service import ScoringService
from application.risk_service import RiskService
from adapters.exchange_okx_ccxt import OKXExchangeAdapter


class AnalysisEngine:
    """
    Analysis engine that generates trading signals through technical analysis.
    
    Responsibilities:
    - Run technical analysis on symbols
    - Generate trading signals
    - Coordinate with scoring service
    - Apply risk filters
    """
    
    def __init__(
        self,
        scoring_service: ScoringService,
        risk_service: RiskService,
        exchange_adapter: OKXExchangeAdapter,
        config: Dict[str, Any]
    ):
        self.scoring_service = scoring_service
        self.risk_service = risk_service
        self.exchange_adapter = exchange_adapter
        self.config = config
        
        # Analysis state
        self.last_analysis = {}
        self.analysis_interval = config.get('analysis_interval', 300)  # 5 minutes
        self.min_analysis_gap = config.get('min_analysis_gap', 60)    # 1 minute
        
        # Analysis settings
        self.timeframe = config.get('default_timeframe', '1h')
        self.ohlcv_limit = config.get('ohlcv_limit', 200)
        self.min_volume_usd = config.get('min_volume_usd', 1000)
        self.max_spread_percent = config.get('max_spread_percent', 0.5)
        
        logger.info("Analysis Engine initialized")
    
    async def analyze_symbols(self, symbols: List[str]) -> Dict[str, AnalysisResult]:
        """
        Analyze multiple symbols and generate trading signals.
        
        Args:
            symbols: List of symbols to analyze
            
        Returns:
            Dictionary mapping symbols to analysis results
        """
        results = {}
        successful_analyses = 0
        skipped_symbols = []
        
        logger.info(f"Starting analysis for {len(symbols)} symbols: {', '.join(symbols)}")
        
        for symbol in symbols:
            try:
                # Check if analysis is needed
                if not self._should_analyze_symbol(symbol):
                    skipped_symbols.append({
                        "symbol": symbol,
                        "reason": "Analysis too recent",
                        "last_analysis": self.last_analysis.get(symbol)
                    })
                    continue
                
                # Run analysis
                result = await self._analyze_single_symbol(symbol)
                if result:
                    results[symbol] = result
                    successful_analyses += 1
                    self.last_analysis[symbol] = datetime.now()
                
                # Small delay between symbols
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to analyze {symbol}: {e}")
                skipped_symbols.append({
                    "symbol": symbol,
                    "reason": f"Analysis failed: {str(e)}",
                    "error": str(e)
                })
        
        # Log results
        logger.info(f"Completed analysis for {len(symbols)} symbols: "
                   f"{successful_analyses} successful, {len(skipped_symbols)} skipped")
        
        # Log skipped symbols if any
        if skipped_symbols:
            await self._log_skipped_symbols(skipped_symbols)
        
        return results
    
    async def analyze_single_symbol(self, symbol: str) -> Optional[AnalysisResult]:
        """
        Analyze a single symbol and generate trading signal.
        
        Args:
            symbol: Symbol to analyze
            
        Returns:
            Analysis result with trading signal, or None if analysis fails
        """
        try:
            # Check if analysis is needed
            if not self._should_analyze_symbol(symbol):
                return None
            
            # Run analysis
            result = await self._analyze_single_symbol(symbol)
            if result:
                self.last_analysis[symbol] = datetime.now()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze {symbol}: {e}")
            return None
    
    async def _analyze_single_symbol(self, symbol: str) -> Optional[AnalysisResult]:
        """Internal method to analyze a single symbol."""
        try:
            # Get market data
            market_data = await self._get_market_data(symbol)
            if not market_data:
                return None
            
            # Validate market conditions
            if not self._validate_market_conditions(symbol, market_data):
                return None
            
            # Run scoring analysis
            scoring_result = await self.scoring_service.score_symbol(symbol, market_data)
            if not scoring_result:
                return None
            
            # Apply risk filters
            risk_assessment = await self.risk_service.assess_risk(
                symbol, 
                scoring_result.score, 
                scoring_result.signal_type,
                market_data
            )
            
            # Generate trading signal
            signal = self._generate_trading_signal(symbol, scoring_result, risk_assessment)
            if not signal:
                return None
            
            # Create analysis result
            result = AnalysisResult(
                symbol=symbol,
                timestamp=datetime.now(),
                signal=signal,
                scoring_result=scoring_result,
                risk_assessment=risk_assessment,
                market_data=market_data,
                analysis_metadata={
                    "timeframe": self.timeframe,
                    "ohlcv_limit": self.ohlcv_limit,
                    "analysis_duration": 0  # Will be calculated
                }
            )
            
            logger.info(f"Analysis completed for {symbol}: {signal.side} {signal.type} "
                       f"Score: {scoring_result.score:.2f} Risk: {risk_assessment.risk_level}")
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            return None
    
    async def _get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for analysis."""
        try:
            # Get OHLCV data
            ohlcv = await self.exchange_adapter.fetch_ohlcv(
                symbol, 
                self.timeframe, 
                limit=self.ohlcv_limit
            )
            
            if not ohlcv or len(ohlcv) < 50:  # Minimum data requirement
                logger.warning(f"Insufficient OHLCV data for {symbol}: {len(ohlcv) if ohlcv else 0} candles")
                return None
            
            # Get ticker information
            ticker = await self.exchange_adapter.get_ticker(symbol)
            if not ticker:
                logger.warning(f"Failed to get ticker for {symbol}")
                return None
            
            # Get instrument information
            instrument = await self.exchange_adapter.get_instrument(symbol)
            
            return {
                "ohlcv": ohlcv,
                "ticker": ticker,
                "instrument": instrument,
                "symbol": symbol,
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return None
    
    def _validate_market_conditions(self, symbol: str, market_data: Dict[str, Any]) -> bool:
        """Validate market conditions before analysis."""
        try:
            ticker = market_data.get("ticker", {})
            
            # Check volume
            volume_usd = ticker.get("quoteVolume", 0)
            if volume_usd < self.min_volume_usd:
                logger.debug(f"Volume too low for {symbol}: ${volume_usd:.2f} < ${self.min_volume_usd}")
                return False
            
            # Check spread
            bid = ticker.get("bid", 0)
            ask = ticker.get("ask", 0)
            if bid > 0 and ask > 0:
                spread_percent = ((ask - bid) / bid) * 100
                if spread_percent > self.max_spread_percent:
                    logger.debug(f"Spread too high for {symbol}: {spread_percent:.2f}% > {self.max_spread_percent}%")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Market validation failed for {symbol}: {e}")
            return False
    
    def _generate_trading_signal(
        self, 
        symbol: str, 
        scoring_result: Any, 
        risk_assessment: Any
    ) -> Optional[TradingSignal]:
        """Generate trading signal based on scoring and risk assessment."""
        try:
            # Check if signal should be generated
            if scoring_result.score < self.config.get('min_score', 0.5):
                return None
            
            if risk_assessment.risk_level == "high":
                return None
            
            # Determine signal type and side
            signal_type = "market"  # Default to market order
            side = "buy" if scoring_result.signal_type == "long" else "sell"
            
            # Create trading signal
            signal = TradingSignal(
                symbol=symbol,
                side=side,
                type=signal_type,
                score=scoring_result.score,
                confidence=scoring_result.confidence,
                rationale=scoring_result.rationale,
                risk_level=risk_assessment.risk_level,
                timestamp=datetime.now(),
                metadata={
                    "scoring_method": scoring_result.method,
                    "risk_factors": risk_assessment.risk_factors,
                    "analysis_engine": "AnalysisEngine"
                }
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Signal generation failed for {symbol}: {e}")
            return None
    
    def _should_analyze_symbol(self, symbol: str) -> bool:
        """Check if symbol should be analyzed."""
        now = datetime.now()
        last_analysis = self.last_analysis.get(symbol)
        
        if not last_analysis:
            return True
        
        time_since_last = (now - last_analysis).total_seconds()
        return time_since_last >= self.min_analysis_gap
    
    async def _log_skipped_symbols(self, skipped_symbols: List[Dict[str, Any]]):
        """Log information about skipped symbols."""
        if not skipped_symbols:
            return
        
        # Group by reason
        reason_groups = {}
        for skip in skipped_symbols:
            reason = skip["reason"]
            if reason not in reason_groups:
                reason_groups[reason] = []
            reason_groups[reason].append(skip["symbol"])
        
        # Log grouped information
        for reason, symbols in reason_groups.items():
            logger.info(f"Skipped {len(symbols)} symbols due to: {reason}")
            if len(symbols) <= 5:
                logger.info(f"Skipped symbols: {', '.join(symbols)}")
            else:
                logger.info(f"Skipped symbols: {', '.join(symbols[:5])}... and {len(symbols) - 5} more")
    
    def get_analysis_status(self, symbol: str) -> Dict[str, Any]:
        """Get analysis status for a symbol."""
        last_analysis = self.last_analysis.get(symbol)
        
        return {
            "symbol": symbol,
            "last_analysis": last_analysis,
            "time_since_last": (datetime.now() - last_analysis).total_seconds() if last_analysis else None,
            "analysis_interval": self.analysis_interval,
            "min_analysis_gap": self.min_analysis_gap,
            "should_analyze": self._should_analyze_symbol(symbol)
        }
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of analysis engine status."""
        now = datetime.now()
        symbols_ready = []
        symbols_waiting = []
        
        for symbol in self.last_analysis.keys():
            if self._should_analyze_symbol(symbol):
                symbols_ready.append(symbol)
            else:
                symbols_waiting.append(symbol)
        
        return {
            "total_symbols": len(self.last_analysis),
            "symbols_ready_for_analysis": symbols_ready,
            "symbols_waiting": symbols_waiting,
            "analysis_interval": self.analysis_interval,
            "min_analysis_gap": self.min_analysis_gap,
            "last_analysis_timestamp": max(self.last_analysis.values()) if self.last_analysis else None
        }
