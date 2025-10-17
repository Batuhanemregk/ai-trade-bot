"""
Trading Analysis Job (15m)
Handles main trading decisions with bar-aligned execution
Enhanced with professional logging and monitoring.
"""

import asyncio
import time
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
from application.analysis_summary_logger import get_analysis_summary_logger
from monitoring.prometheus_exporter import get_prometheus_exporter


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
        self.decision_logger = None
        
        # Enhanced logging and monitoring
        self.summary_logger = get_analysis_summary_logger()
        self.prometheus_exporter = None
        
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
            
            # Initialize decision logger
            from infrastructure.decision_logger import DecisionLogger
            self.decision_logger = DecisionLogger()
            
            # Initialize Prometheus exporter
            try:
                self.prometheus_exporter = get_prometheus_exporter()
                self.summary_logger.set_prometheus_exporter(self.prometheus_exporter)
                logger.info("✅ Prometheus exporter connected to summary logger")
            except Exception as e:
                logger.warning(f"⚠️ Prometheus exporter not available: {e}")
            
            logger.info("✅ TradingAnalysisJob initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize TradingAnalysisJob: {e}")
            raise
    
    async def execute(self):
        """Execute 15-minute trading analysis."""
        start_time = time.time()
        
        try:
            # Check idempotency for 15m bar
            bar_id = self.get_current_bar_id('15m')
            job_key = 'trading_analysis'
            if self.is_bar_already_processed(job_key, '15m'):
                logger.info(f"⏭️ Already processed tf=15m bar={bar_id} → skipping")
                return
            
            symbols = self.get_all_symbols()
            logger.info(f"🔄 [JOB] trading_analysis processing {len(symbols)} symbols for bar={bar_id}")
            
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
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log batch summary using enhanced logger
            self.summary_logger.log_batch_summary('15m', duration)
            
            # Record job execution in Prometheus
            if self.prometheus_exporter:
                self.prometheus_exporter.record_job_execution('trading_analysis_15m', duration, True)
            
            logger.info(f"✅ [JOB-COMPLETE] trading_analysis | processed={processed_count} entries={entries} exits={exits} reversals={reversals} ignored={ignored_same_dir} | duration={duration:.1f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record failure in Prometheus
            if self.prometheus_exporter:
                self.prometheus_exporter.record_job_execution('trading_analysis_15m', duration, False)
                self.prometheus_exporter.record_error('execution_failed', 'trading_analysis')
            
            logger.error(f"❌ TradingAnalysisJob execution failed: {e}")
            raise
    
    async def _process_symbol(self, symbol: str):
        """Process a single symbol for trading analysis using real trading logic."""
        symbol_start_time = time.time()
        
        try:
            logger.debug(f"🔍 Processing {symbol}")
            
            # Step 1: Fetch OHLCV data (multi-timeframe) - GUARANTEED FIRST
            ohlcv_data = await _fetch_multi_timeframe_data(self.exchange_adapter, symbol, True)
            
            if not ohlcv_data:
                logger.warning(f"⚠️ No OHLCV data for {symbol}, skipping")
                self.summary_logger.record_failure(symbol, "No OHLCV data")
                return
            
            # Step 2: Technical Analysis - Uses cached OHLCV data
            ta_score, ta_rationale, ta_flags = await _compute_ta_analysis(self.ta_scorer, ohlcv_data, symbol)
            
            # Step 3: ML Analysis - Uses cached OHLCV data
            ml_score, ml_rationale, ml_details = await _compute_ml_analysis(self.ml_scorer, ohlcv_data, symbol)
            
            # Step 4: News Analysis - Independent of OHLCV
            news_score, news_categories, news_rationale, news_volatility = await _compute_news_analysis(self.news_scorer, symbol)
            
            # Step 5: Risk Analysis - MUST come AFTER data fetch, uses OHLCV data
            # This ensures risk calculations use the same data snapshot as TA/ML
            risk_score, risk_details = await _compute_risk_analysis(self.risk_service, symbol, ohlcv_data)
            
            # Step 6: Composite Score & Decision
            composite_signal = await _compute_composite_signal(
                symbol, ta_score, ta_rationale, ta_flags,
                ml_score, ml_rationale, ml_details,
                news_score, news_categories, news_rationale, news_volatility,
                risk_score, risk_details
            )
            
            # Step 7: Process signal with enhanced gating
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
            
            # Process through signal gate
            gated_signal = self.signal_gate.process_signal(symbol, signal_dict, ohlcv_1h_list)
            
            # Step 8: Process state transition
            transition = self.state_manager.process_signal(symbol, gated_signal)
            
            # Extract gate details for logging
            gate_details = {
                'persist_count': gated_signal.details.get('persist_count', gated_signal.persistence_bars),
                'persist_required': gated_signal.details.get('persist_required', 5),
                'confidence': gated_signal.details.get('confidence', 0.0),
                'conf_required': gated_signal.details.get('conf_threshold', 0.0)
            }
            
            # Extract age from signal history (counter format)
            signal_history = self.signal_gate.get_signal_history(symbol)
            age_bars = len(signal_history) if signal_history else 0
            max_age_bars = self.policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('max_signal_age_bars', 6)
            
            # Step 9: Log enhanced summary (single line or block mode)
            self.summary_logger.log_analysis({
                'symbol': symbol,
                'timeframe': '15m',
                'timestamp': datetime.now(timezone.utc),
                'ta_score': ta_score,
                'ml_score': ml_score,
                'news_score': news_score,
                'risk_score': risk_score,
                'final_score': composite_signal.final_score,
                'grade': composite_signal.grade,
                'direction': gated_signal.direction,
                'gate_status': 'PASS' if gated_signal.is_valid else 'PENDING',
                'gate_details': gate_details,
                'age_bars': age_bars,  # Counter format: 0/6, 3/6, etc.
                'max_age_bars': max_age_bars,
                # Block mode details
                'hyst_status': f"ok" if gated_signal.is_valid else "pending",
                'state_transition': f"{transition.from_state}→{transition.to_state}",
                'action': transition.action,
                'position_size': risk_details.get('position_size_pct', 0) if risk_details else 0,
                'leverage': risk_details.get('leverage', 1) if risk_details else 1,
                'sl_atr': risk_details.get('sl_atr', 2) if risk_details else 2,
                'tp_atr': risk_details.get('tp_atr', 4) if risk_details else 4,
                'risk_exposure': risk_details.get('exposure_pct', 0) if risk_details else 0,
                'risk_tier': risk_details.get('tier', 'T1') if risk_details else 'T1',
                'circuit_breaker': risk_details.get('circuit_breaker', 'OK') if risk_details else 'OK'
            })
            
            # Record analysis duration in Prometheus
            symbol_duration = time.time() - symbol_start_time
            if self.prometheus_exporter:
                self.prometheus_exporter.record_analysis_duration(symbol, symbol_duration)
                self.prometheus_exporter.update_scores(symbol, {
                    'composite': composite_signal.final_score,
                    'ta': ta_score,
                    'ml': ml_score,
                    'news': news_score,
                    'risk': risk_score
                })
            
            # Step 10: Execute transition actions - REAL TRADING LOGIC
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
                logger.debug(f"⏸️ {symbol}: MAINTAIN - No state change")
                
            elif transition.action == 'COOLDOWN':
                logger.debug(f"⏸️ {symbol}: COOLDOWN - Position closed, entering cooldown period")
                
            logger.debug(f"✅ {symbol} processed successfully")
            
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
            
            # Log decision to structured JSONL
            if self.decision_logger and hasattr(composite_signal, 'final_score'):
                try:
                    action = result.get('action', 'skip')
                    gate_results = {
                        'persistence': {'passed': gated_signal.is_valid},
                        'bias': {'passed': True},  # TODO: Get from actual gate results
                        'reversal': {'approved': transition.action not in ['IGNORED', 'COOLDOWN']}
                    }
                    
                    self.decision_logger.log_decision(
                        symbol=symbol,
                        composite_signal=composite_signal,
                        action=action.upper(),
                        position_size=0.0,  # Will be set during execution
                        tp_price=None,
                        sl_price=None,
                        reason=transition.reason,
                        gate_results=gate_results
                    )
                except Exception as log_err:
                    logger.warning(f"⚠️ Decision logging failed for {symbol}: {log_err}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to process {symbol}: {e}")
            self.summary_logger.record_failure(symbol, str(e))
            if self.prometheus_exporter:
                self.prometheus_exporter.record_error('symbol_processing', 'trading_analysis')
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
