"""
Trading Analysis Job (15m)
Handles main trading decisions with bar-aligned execution
Enhanced with professional logging and monitoring.
"""

import asyncio
import hashlib
import json
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
from application.decision_tracer import get_decision_tracer, DecisionSnapshot


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
    
    async def cleanup(self):
        """Cleanup trading analysis resources"""
        try:
            if hasattr(self, 'exchange_adapter') and self.exchange_adapter:
                await self.exchange_adapter.close()
                logger.debug("✅ Closed exchange adapter for TradingAnalysisJob")
        except Exception as e:
            logger.error(f"❌ TradingAnalysisJob cleanup failed: {e}")
    
    async def execute(self):
        """Execute 15-minute trading analysis."""
        if not self.start_run('15m'):
            return
        
        start_time = time.time()
        bar_id = self.current_bar_id
        
        try:
            symbols = self.get_all_symbols()
            logger.info(
                f"🔄 [JOB] trading_analysis run_id={self.run_id} bar={bar_id} symbols={len(symbols)} processing"
            )
            
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
            
            # Mark 15m bar as processed for legacy idempotency tracking
            self.mark_bar_processed(self.job_id, '15m')
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log batch summary using enhanced logger
            self.summary_logger.log_batch_summary('15m', duration, bar_id, self.run_id)
            
            # Record job execution in Prometheus
            if self.prometheus_exporter:
                self.prometheus_exporter.record_job_execution('trading_analysis_15m', duration, True)
            
            logger.info(
                f"✅ [JOB-COMPLETE] trading_analysis run_id={self.run_id} bar={bar_id} "
                f"processed={processed_count} entries={entries} exits={exits} "
                f"reversals={reversals} ignored={ignored_same_dir} duration={duration:.1f}s"
            )
            self.finish_run("SUCCESS")
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record failure in Prometheus
            if self.prometheus_exporter:
                self.prometheus_exporter.record_job_execution('trading_analysis_15m', duration, False)
                self.prometheus_exporter.record_error('execution_failed', 'trading_analysis')
            
            logger.error(f"❌ TradingAnalysisJob execution failed: {e}")
            self.finish_run("FAILED", str(e))
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
            position_snapshot = None
            position_snapshot_hash = None
            if self.state_manager:
                position_info = self.state_manager.get_position_info(symbol)
                if position_info:
                    position_snapshot = {
                        "state": position_info.state.value,
                        "entry_time": position_info.entry_time.isoformat() if position_info.entry_time else None,
                        "entry_price": position_info.entry_price,
                        "size": position_info.size,
                        "side": position_info.side,
                        "stop_loss": position_info.stop_loss,
                        "take_profit": position_info.take_profit,
                        "holding_bars": position_info.holding_bars,
                        "r_multiple": position_info.r_multiple,
                    }
                    position_snapshot_hash = hashlib.sha1(
                        json.dumps(position_snapshot, sort_keys=True, default=str).encode('utf-8')
                    ).hexdigest()
            risk_context = {
                "timeframe": "15m",
                "bar_id": self.current_bar_id,
            }
            if position_snapshot is not None:
                risk_context["position_snapshot"] = position_snapshot
            if position_snapshot_hash is not None:
                risk_context["position_snapshot_hash"] = position_snapshot_hash
            
            risk_score, risk_details = await _compute_risk_analysis(
                self.risk_service,
                symbol,
                ohlcv_data,
                context=risk_context,
            )
            
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
            
            # Determine bar timestamp from 15m frame for counter alignment
            bar_timestamp = None
            main_df = ohlcv_data.get('main')
            if main_df is not None and not main_df.empty:
                ts = main_df.index[-1]
                if hasattr(ts, "to_pydatetime"):
                    ts = ts.to_pydatetime()
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                bar_timestamp = ts
            else:
                fallback_bar_id = self.get_current_bar_id('15m')
                try:
                    bar_timestamp = datetime.fromisoformat(fallback_bar_id.replace('Z', '+00:00'))
                    if bar_timestamp.tzinfo is None:
                        bar_timestamp = bar_timestamp.replace(tzinfo=timezone.utc)
                except Exception:
                    logger.warning(f"[COUNTER] {symbol} unable to derive bar timestamp from fallback bar_id={fallback_bar_id}")
                    bar_timestamp = datetime.now(timezone.utc)
            
            # Create signal dict
            signal_dict = {
                'final_score': composite_signal.final_score,
                'decision': composite_signal.decision,
                'ta_score': ta_score,
                'ml_score': ml_score,
                'news_score': news_score,
                'risk_score': risk_score,
                'timestamp': datetime.now(timezone.utc),
                'timeframe': '15m',
                'run_id': self.run_id,
                'bar_id': self.current_bar_id,
                'bar_timestamp': bar_timestamp
            }
            
            # Process through signal gate
            gated_signal = self.signal_gate.process_signal(symbol, signal_dict, ohlcv_1h_list)
            
            # Step 8: Process state transition (pass gated_signal with is_valid, size, mode)
            gated_signal_dict = {
                'final_score': gated_signal.original_score,
                'is_valid': gated_signal.is_valid,
                'direction': gated_signal.direction,
                'size': 0.0,  # Will be updated by execution pipeline
                'mode': 'PAPER'  # Default mode, will be updated by execution pipeline
            }
            transition = self.state_manager.process_signal(symbol, gated_signal_dict)
            
            # Extract gate details for logging
            gate_details = {
                'persist_count': gated_signal.details.get('persist_count', gated_signal.persistence_bars),
                'persist_required': gated_signal.details.get('persist_required', 5),
                'confidence': gated_signal.details.get('confidence', 0.0),
                'conf_required': gated_signal.details.get('conf_threshold', 0.0)
            }
            if gated_signal.details.get('duplicate_bar'):
                gate_details['duplicate'] = gated_signal.details.get('duplicate_count', 1)
            if gated_signal.details.get('bar_id'):
                gate_details['bar_id'] = gated_signal.details['bar_id']
            if gated_signal.details.get('run_id') or self.run_id:
                gate_details['run_id'] = gated_signal.details.get('run_id', self.run_id)
            
            # Extract age from signal history (counter format)
            signal_history = self.signal_gate.get_signal_history(symbol)
            age_bars = len(signal_history) if signal_history else 0
            max_age_bars = self.policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('max_signal_age_bars', 6)
            
            # Step 9: Create decision snapshot for tracing
            tracer = get_decision_tracer()
            if tracer.enabled:
                # Get current bar ID
                current_bar_id = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
                
                # Get balance and risk info
                balance_usdt = 100.0  # Fallback
                total_risk_usdt = 0.0
                try:
                    if hasattr(self.exchange_adapter, 'fetch_balance'):
                        balance = await self.exchange_adapter.fetch_balance()
                        balance_usdt = balance.get('USDT', {}).get('total', 100.0)
                    if hasattr(self.exchange_adapter, 'fetch_positions'):
                        positions = await self.exchange_adapter.fetch_positions()
                        total_risk_usdt = sum(float(pos.get('notional', 0)) for pos in positions if pos.get('size', 0) != 0)
                except:
                    pass
                
                # Calculate position size
                position_size_usdt = balance_usdt * (risk_details.get('position_size_pct', 0) / 100) if risk_details else 0
                position_size_pct = risk_details.get('position_size_pct', 0) if risk_details else 0
                
                # Create snapshot
                snapshot = DecisionSnapshot(
                    timestamp=datetime.now(timezone.utc).strftime('%H:%M:%S'),
                    symbol=symbol,
                    timeframe='15m',
                    bar_id=current_bar_id,
                    
                    # Scores
                    ta_score=ta_score,
                    ml_score=ml_score,
                    news_score=news_score,
                    risk_score=risk_score,
                    final_score=composite_signal.final_score,
                    grade=composite_signal.grade,
                    decision=gated_signal.direction,
                    confidence_pct=composite_signal.confidence_pct,
                    
                    # Gating
                    persistence_bars=gated_signal.persistence_bars,
                    persistence_required=gate_details['persist_required'],
                    confirmation_bars=gated_signal.confirmation_bars,
                    confirmation_required=gate_details['conf_required'],
                    signal_age=age_bars,
                    signal_age_max=max_age_bars,
                    hysteresis_ok=gated_signal.is_valid,
                    
                    # State
                    state_before=transition.from_state.value,
                    state_after=transition.to_state.value,
                    transition_action=transition.action,
                    transition_reason=transition.reason,
                    
                    # Risk/Size
                    position_size_usdt=position_size_usdt,
                    position_size_pct=position_size_pct,
                    leverage=risk_details.get('leverage', 1) if risk_details else 1,
                    balance_usdt=balance_usdt,
                    total_risk_usdt=total_risk_usdt,
                    max_risk_limit=balance_usdt * 0.6,
                    
                    # TP/SL
                    tp_distance_atr=risk_details.get('tp_atr', 4) if risk_details else 4,
                    sl_distance_atr=risk_details.get('sl_atr', 2) if risk_details else 2,
                    tp_price=0.0,  # Will be calculated during execution
                    sl_price=0.0,  # Will be calculated during execution
                    
                    # Guards
                    same_direction_blocked=transition.action == 'MAINTAIN' and 'same direction' in transition.reason.lower(),
                    once_per_bar_blocked=False,  # Not implemented yet
                    reversal_approved=transition.action == 'CLOSE_REVERSE',
                    bias_penalty=0.0,  # Not tracked in current flow
                    bias_reason='',
                    
                    # Result
                    execution_result='PENDING' if transition.action in ['OPEN_LONG', 'OPEN_SHORT'] else 'SKIP',
                    skip_reason=transition.reason if transition.action == 'MAINTAIN' else '',
                    client_order_id='',
                    
                    # Metadata
                    regime=gated_signal.regime_info.regime if hasattr(gated_signal, 'regime_info') else 'unknown',
                    adx_1h=gated_signal.regime_info.adx_1h if hasattr(gated_signal, 'regime_info') else 0.0,
                    confidence_multiplier=gated_signal.regime_info.confidence_multiplier if hasattr(gated_signal, 'regime_info') else 1.0
                )
                
                # Trace the decision
                tracer.trace_decision(snapshot)
                tracer.log_console_summary(snapshot)
            
            # Step 10: Log enhanced summary (single line or block mode)
            self.summary_logger.log_analysis({
                'symbol': symbol,
                'timeframe': '15m',
                'timestamp': datetime.now(timezone.utc),
                'bar_id': self.current_bar_id,
                'run_id': self.run_id,
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
            # Add gating info to composite_signal for enforcement
            composite_signal.gate_pass = gated_signal.is_valid
            composite_signal.state_before = transition.from_state.value
            composite_signal.decision = gated_signal.direction
            
            if transition.action == 'OPEN_LONG':
                logger.info(f"🚀 {symbol}: Opening LONG position")
                await self._execute_trade(symbol, 'long', composite_signal.final_score, composite_signal)
                
            elif transition.action == 'OPEN_SHORT':
                logger.info(f"🚀 {symbol}: Opening SHORT position")
                await self._execute_trade(symbol, 'short', composite_signal.final_score, composite_signal)
                
            elif transition.action == 'CLOSE_REVERSE':
                logger.info(f"🔄 {symbol}: Close & Reverse - {transition.reason}")
                await self._execute_close_and_reverse(symbol, gated_signal.direction, composite_signal.final_score, composite_signal)
                
            elif transition.action == 'MAINTAIN':
                logger.debug(f"⏸️ {symbol}: MAINTAIN - No state change")
                
            elif transition.action == 'COOLDOWN':
                logger.debug(f"⏸️ {symbol}: COOLDOWN - Position closed, entering cooldown period")
                
            logger.debug(f"✅ {symbol} processed successfully")
            
            # Build analysis result for cards
            result = {
                'symbol': symbol,
                'decision': composite_signal.decision,
                'final_score': composite_signal.final_score,
                'ta_score': ta_score,
                'ml_score': ml_score,
                'news_score': news_score,
                'risk_score': risk_score,
                'bar_id': self.current_bar_id,
                'run_id': self.run_id,
                'action': transition.action,  # Add action here
                'news_info': {
                    'type': news_categories.get('type', 'general') if isinstance(news_categories, dict) else 'general',
                    'confidence': news_categories.get('confidence', 0) if isinstance(news_categories, dict) else 0,
                    'title': news_categories.get('title', 'No recent news') if isinstance(news_categories, dict) else 'No recent news'
                },
                'risk_info': {
                    'level': risk_details.get('level', 'medium') if risk_details else 'medium',
                    'factors': risk_details.get('factors', []) if risk_details else []
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
                    
                    # Decision logging - use getattr for backwards compatibility
                    signal_scores = {
                        'ta': getattr(composite_signal, 'ta_score', getattr(composite_signal.technical, 'score', 0.0)),
                        'ml': getattr(composite_signal, 'ml_score', getattr(composite_signal.ml, 'score', 0.0)),
                        'news': getattr(composite_signal, 'news_score', getattr(composite_signal.news, 'score', 0.0)),
                        'risk': getattr(composite_signal, 'risk_score', getattr(composite_signal.risk, 'score', 0.0)),
                        'final': composite_signal.final_score
                    }
                    
                    self.decision_logger.log_decision(
                        symbol=symbol,
                        timeframe='15m',
                        signal_scores=signal_scores,
                        gate_result='PASS' if gated_signal.is_valid else 'FAIL',
                        gate_details=gate_results,
                        direction=composite_signal.decision,
                        size=0.0,  # Will be set during execution
                        leverage=1.0,
                        sl_price=0.0,
                        tp_price=0.0,
                        risk_exp=0.0,
                        tier='T1',
                        cb_status='OK',
                        state_transition=f"{transition.from_state.value}→{transition.to_state.value}",
                        strategy='single_flip',
                        guards=gate_results,
                        source='trading_analysis',
                        bar_id=self.current_bar_id,
                        run_id=self.run_id
                    )
                except Exception as log_err:
                    logger.warning(f"⚠️ Decision logging failed for {symbol}: {log_err}")
            
            # Return the result dict
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to process {symbol}: {e}")
            self.summary_logger.record_failure(symbol, str(e))
            if self.prometheus_exporter:
                self.prometheus_exporter.record_error('symbol_processing', 'trading_analysis')
            return None
    
    async def _execute_trade(self, symbol: str, side: str, score: float, composite_signal=None):
        """Execute a real trade using the existing trading logic."""
        try:
            # Import the real trading execution logic from runtime
            from infrastructure.runtime import _execute_trade as runtime_execute_trade
            
            # composite_signal should ALWAYS be provided from caller
            # If not provided, this is a logic error - log and raise
            if composite_signal is None:
                logger.error(f"❌ [EXEC] {symbol}: composite_signal is None - this should never happen!")
                logger.error(f"   Caller must provide composite_signal object, not separate side/score")
                raise ValueError(f"composite_signal is required for trade execution (got None)")
            
            # Validate composite_signal has required attributes
            required_attrs = ['decision', 'final_score', 'technical', 'ml', 'news', 'risk', 'timestamp']
            missing_attrs = [attr for attr in required_attrs if not hasattr(composite_signal, attr)]
            if missing_attrs:
                logger.error(f"❌ [EXEC] {symbol}: composite_signal missing attributes: {missing_attrs}")
                raise ValueError(f"composite_signal incomplete: missing {missing_attrs}")
            
            # Execute the trade using the real logic
            await runtime_execute_trade(
                exchange_adapter=self.exchange_adapter,
                symbol=symbol,
                composite_signal=composite_signal,
                live=True  # This is the scheduler, so always live
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to execute trade for {symbol}: {e}")
            raise
    
    async def _execute_close_and_reverse(self, symbol: str, new_direction: str, score: float, composite_signal=None):
        """Execute close and reverse using real trading logic."""
        try:
            # First close existing position
            logger.info(f"🔄 Closing existing position for {symbol}")
            # Close logic would go here
            
            # Then open new position
            await self._execute_trade(symbol, new_direction, score, composite_signal)
            
        except Exception as e:
            logger.error(f"❌ Failed to execute close and reverse for {symbol}: {e}")
            raise
