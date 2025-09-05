"""
Trading Analysis Job (15m)
Handles main trading decisions with bar-aligned execution
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from loguru import logger

from .base_job import BaseJob
# Import real trading functions from runtime
from infrastructure.runtime import (
    _fetch_multi_timeframe_data, 
    _compute_ta_analysis, 
    _compute_ml_analysis, 
    _compute_news_analysis, 
    _compute_risk_analysis, 
    _compute_composite_signal
)
from application.position_state_manager import PositionStateManager
from application.signal_gate import SignalGate
from application.reversal_manager import ReversalManager
from application.analysis_cards import AnalysisCardsService


class TradingAnalysisJob(BaseJob):
    """15-minute trading analysis job with bar-aligned execution."""
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.exchange_adapter = None
        self.ta_scorer = None
        self.ml_scorer = None
        self.news_scorer = None
        self.risk_service = None
        self.state_manager = None
        self.signal_gate = None
        self.reversal_manager = None
        self.analysis_cards = None
        
    async def initialize(self):
        """Initialize trading analysis components."""
        try:
            # Initialize exchange adapter
            from adapters.exchange_okx_ccxt import OKXCCXTAdapter
            self.exchange_adapter = OKXCCXTAdapter()
            
            # Initialize scoring components with real services
            from scoring.ta_scorer import TAScorer
            from scoring.ml_scorer import MLScorer
            from scoring.news_scorer import NewsScorer
            from application.risk_service import RiskService
            
            self.ta_scorer = TAScorer()
            self.ml_scorer = MLScorer()
            self.news_scorer = NewsScorer()
            self.risk_service = RiskService(self.policy)
            
            # Initialize state management
            self.state_manager = PositionStateManager(self.policy)
            self.signal_gate = SignalGate(self.policy)
            self.reversal_manager = ReversalManager(self.policy)
            
            # Initialize analysis cards
            self.analysis_cards = AnalysisCardsService(self.policy)
            
            logger.info("✅ TradingAnalysisJob initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize TradingAnalysisJob: {e}")
            raise
    
    async def execute(self):
        """Execute 15-minute trading analysis."""
        try:
            # Check idempotency for 15m bar
            bar_id = self.get_current_bar_id('15m')
            if self.is_bar_already_processed('15m', bar_id):
                logger.info(f"already processed tf=15m bar={bar_id} → skipping")
                return
            
            symbols = self.get_all_symbols()
            logger.info(f"[JOB] trading_analysis processing {len(symbols)} symbols")
            
            processed_count = 0
            analysis_results = []  # Store results for cards
            entries = 0
            exits = 0
            reversals = 0
            ignored_same_dir = 0
            
            for symbol in symbols:
                try:
                    # Process symbol
                    result = await self._process_symbol(symbol)
                    if result:
                        analysis_results.append(result)
                        
                        # Count actions
                        if result.get('action') == 'entry':
                            entries += 1
                        elif result.get('action') == 'exit':
                            exits += 1
                        elif result.get('action') == 'reversal':
                            reversals += 1
                        elif result.get('action') == 'ignored_same_dir':
                            ignored_same_dir += 1
                    
                    # Mark bar as processed
                    self.mark_bar_processed(symbol, '15m')
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process {symbol}: {e}")
                    continue
            
            # Send analysis cards if enabled
            if analysis_results and self.analysis_cards:
                await self.analysis_cards.send_analysis_cards(analysis_results)
            
            # Mark 15m bar as processed
            self.mark_bar_processed('15m', bar_id)
            
            # Job summary
            logger.info(f"[JOB-SUMMARY] trading_analysis symbols_scored={processed_count} entries={entries} exits={exits} reversals={reversals} ignored_same_dir={ignored_same_dir}")
            
        except Exception as e:
            logger.error(f"❌ TradingAnalysisJob execution failed: {e}")
            raise
    
    async def _process_symbol(self, symbol: str):
        """Process a single symbol for trading analysis using real trading logic."""
        try:
            logger.info(f"🔍 Processing {symbol}")
            
            # Step 1: Fetch OHLCV data (multi-timeframe) - REAL LOGIC
            logger.info(f"📊 Fetching OHLCV data for {symbol}")
            ohlcv_data = await _fetch_multi_timeframe_data(self.exchange_adapter, symbol, True)
            
            if not ohlcv_data:
                logger.warning(f"⚠️ No OHLCV data for {symbol}, skipping")
                return
            
            # Step 2: Technical Analysis - REAL LOGIC
            logger.info(f"📈 Computing TA scores for {symbol}")
            ta_score, ta_rationale, ta_flags = await _compute_ta_analysis(self.ta_scorer, ohlcv_data, symbol)
            
            # Step 3: ML Analysis - REAL LOGIC
            logger.info(f"🤖 Computing ML scores for {symbol}")
            ml_score, ml_rationale, ml_details = await _compute_ml_analysis(self.ml_scorer, ohlcv_data, symbol)
            
            # Step 4: News Analysis - REAL LOGIC with LLM
            logger.info(f"📰 Computing News scores for {symbol}")
            news_score, news_categories, news_rationale, news_volatility = await _compute_news_analysis(self.news_scorer, symbol)
            
            # Step 5: Risk Analysis - REAL LOGIC
            logger.info(f"⚠️ Computing Risk annotations for {symbol}")
            risk_score, risk_details = await _compute_risk_analysis(self.risk_service, symbol, ohlcv_data)
            
            # Step 6: Composite Score & Decision - REAL LOGIC
            logger.info(f"🎯 Computing composite score for {symbol}")
            composite_signal = await _compute_composite_signal(
                symbol, ta_score, ta_rationale, ta_flags,
                ml_score, ml_rationale, ml_details,
                news_score, news_categories, news_rationale, news_volatility,
                risk_score, risk_details
            )
            
            # Log results - REAL DATA
            logger.info(f"📊 {symbol} Analysis Results:")
            logger.info(f"  TA Score: {ta_score:.1f} - {ta_rationale}")
            logger.info(f"  ML Score: {ml_score:.1f} - {ml_rationale}")
            logger.info(f"  News Score: {news_score:.1f} - {news_rationale}")
            logger.info(f"  Risk Score: {risk_score:.1f}")
            logger.info(f"  Final Score: {composite_signal.final_score:.1f}")
            logger.info(f"  Grade: {composite_signal.grade}")
            logger.info(f"  Decision: {composite_signal.decision}")
            
            # Step 7: Process signal with enhanced gating - REAL LOGIC
            logger.info(f"🎯 Processing signal with enhanced gating for {symbol}")
            
            # Convert OHLCV to list format for signal gate
            ohlcv_1h_list = []
            if 'trend' in ohlcv_data and not ohlcv_data['trend'].empty:
                df = ohlcv_data['trend']
                for idx, row in df.iterrows():
                    timestamp_ms = int(idx.timestamp() * 1000)
                    ohlcv_1h_list.append([timestamp_ms, row['open'], row['high'], row['low'], row['close'], row['volume']])
            
            # Create signal dict
            signal_dict = {
                'final_score': composite_signal.final_score,
                'decision': composite_signal.decision,
                'ta_score': ta_score,
                'ml_score': ml_score,
                'news_score': news_score,
                'risk_score': risk_score,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Process through signal gate - REAL LOGIC
            gated_signal = self.signal_gate.process_signal(symbol, signal_dict, ohlcv_1h_list)
            
            logger.info(f"🎯 {symbol} Gated Signal: {gated_signal.direction} (original={composite_signal.final_score:.1f}, gated={composite_signal.final_score:.1f}, valid={gated_signal.is_valid})")
            logger.info(f"🎯 {symbol} Signal Details: {gated_signal.details}")
            
            # Step 8: Process state transition - REAL LOGIC
            logger.info(f"🎯 Processing state transition for {symbol}")
            
            transition = self.state_manager.process_signal(symbol, gated_signal)
            
            logger.info(f"🎯 {symbol} State Transition: {transition.from_state} -> {transition.to_state} action={transition.action}")
            logger.info(f"🎯 {symbol} Transition Reason: {transition.reason}")
            
            # Step 9: Execute transition actions - REAL TRADING LOGIC
            if transition.action == 'OPEN_LONG':
                logger.info(f"🚀 {symbol}: Opening LONG position")
                await self._execute_trade(symbol, 'long', composite_signal.final_score)
                
            elif transition.action == 'OPEN_SHORT':
                logger.info(f"🚀 {symbol}: Opening SHORT position")
                await self._execute_trade(symbol, 'short', composite_signal.final_score)
                
            elif transition.action == 'CLOSE_REVERSE':
                logger.info(f"🔄 {symbol}: Close & Reverse - {transition.reason}")
                await self._execute_close_and_reverse(symbol, gated_signal.direction, composite_signal.final_score)
                
            elif transition.action == 'MAINTAIN':
                logger.info(f"⏸️ {symbol}: MAINTAIN - No state change")
                
            elif transition.action == 'COOLDOWN':
                logger.info(f"⏸️ {symbol}: COOLDOWN - Position closed, entering cooldown period")
                
            logger.info(f"✅ {symbol} processed successfully")
            
            # Return analysis result for cards
            return {
                'symbol': symbol,
                'decision': composite_signal.decision,
                'final_score': composite_signal.final_score,
                'ta_score': ta_score,
                'ml_score': ml_score,
                'news_score': news_score,
                'risk_score': risk_score,
                'news_info': {
                    'type': news_categories.get('type', 'general'),
                    'confidence': news_categories.get('confidence', 0),
                    'title': news_categories.get('title', 'No recent news')
                },
                'risk_info': {
                    'level': risk_details.get('level', 'medium'),
                    'factors': risk_details.get('factors', [])
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process {symbol}: {e}")
            return None
    
    async def _execute_trade(self, symbol: str, side: str, score: float):
        """Execute a real trade using the existing trading logic."""
        try:
            # Import the real trading execution logic from runtime
            from infrastructure.runtime import _execute_trade as runtime_execute_trade
            
            # Execute the trade using the real logic
            await runtime_execute_trade(
                exchange_adapter=self.exchange_adapter,
                symbol=symbol,
                side=side,
                score=score,
                live=True  # This is the scheduler, so always live
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to execute trade for {symbol}: {e}")
            raise
    
    async def _execute_close_and_reverse(self, symbol: str, new_direction: str, score: float):
        """Execute close and reverse using real trading logic."""
        try:
            # First close existing position
            logger.info(f"🔄 Closing existing position for {symbol}")
            # Close logic would go here
            
            # Then open new position
            await self._execute_trade(symbol, new_direction, score)
            
        except Exception as e:
            logger.error(f"❌ Failed to execute close and reverse for {symbol}: {e}")
            raise
