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
from application.decision_tracer import get_decision_tracer, DecisionSnapshot

# Install alert history loguru sink to capture warnings/errors
try:
    from application.alert_history import install_loguru_sink
    install_loguru_sink()
except Exception:
    pass  # Silent fail - alert history is optional


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
            
            # Initialize state management - USE SINGLETON for consistent state
            from application.position_state_manager import get_state_manager
            self.state_manager = get_state_manager(self.policy)
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
            
            # Step 0: Sync position state with real exchange positions FIRST
            # This prevents duplicate position opening by ensuring state matches reality
            has_position = await self._sync_position_from_exchange(symbol)
            if has_position:
                logger.info(f"[SYNC] {symbol}: Real position exists, state synced")
            
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
            # NOTE: ml_score may be None for TA-only mode - finalize() will redistribute ML weight to TA
            
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
                'timestamp': datetime.now(timezone.utc),
                'bar_timestamp': datetime.now(timezone.utc)  # For signal gate bar deduplication
            }
            
            # Get real position info from state manager for hysteresis sync
            current_state = self.state_manager.get_position_state(symbol)
            position_info = None
            if current_state:
                # PositionState enum: READY, LONG_OPEN, SHORT_OPEN, COOLDOWN
                position_info = {
                    'has_position': current_state.value in ['LONG_OPEN', 'SHORT_OPEN'],
                    'side': 'long' if current_state.value == 'LONG_OPEN' else ('short' if current_state.value == 'SHORT_OPEN' else None)
                }
            
            # Process through signal gate with real position info
            gated_signal = self.signal_gate.process_signal(symbol, signal_dict, ohlcv_1h_list, position_info)
            
            # Record signal to history store for Telegram visualization
            try:
                from application.signal_history import record_signal
                record_signal(
                    symbol=symbol,
                    ta_score=ta_score if ta_score else 0.0,
                    ml_score=ml_score if ml_score else 0.0,
                    news_score=news_score if news_score else 50.0,
                    risk_score=risk_score if risk_score else 50.0,
                    final_score=gated_signal.original_score,
                    direction=gated_signal.direction,
                    gate_status='PASS' if gated_signal.is_valid else 'PENDING'
                )
            except Exception as e:
                logger.debug(f"Signal history recording failed: {e}")
            
            # Step 8: Process state transition (pass gated_signal with is_valid, size, mode)
            gated_signal_dict = {
                'final_score': gated_signal.original_score,
                'is_valid': gated_signal.is_valid,
                'direction': gated_signal.direction,
                'size': 0.0,  # Will be updated by execution pipeline
                'mode': 'PAPER'  # Default mode, will be updated by execution pipeline
            }
            transition = self.state_manager.process_signal(symbol, gated_signal_dict)
            
            # Extract gate details for logging (conf removed, simplified to persist only)
            gate_details = {
                'persist_count': gated_signal.persistence_bars,
                'persist_required': self.policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('persistence_bars', 2),
                'confidence': 0.0,  # Conf removed, not used anymore
                'conf_required': 0.0
            }
            
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
                    ml_score=ml_score if ml_score is not None else 0.0,  # Handle TA-only mode
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
                    'ml': ml_score if ml_score is not None else 0.0,
                    'news': news_score,
                    'risk': risk_score
                })
            
            # Step 10: Execute transition actions - REAL TRADING LOGIC
            # Add gating info to composite_signal for enforcement
            composite_signal.gate_pass = gated_signal.is_valid
            composite_signal.state_before = transition.from_state.value
            composite_signal.decision = gated_signal.direction
            
            # Log all actions for debugging
            logger.info(f"[ACTION] {symbol}: transition={transition.action} from={transition.from_state.value} to={transition.to_state.value}")
            
            # NOTE: Position sync at start of cycle already guarantees state correctness.
            # If transition.from_state was READY and action is OPEN_*, it's a legitimate new trade.
            # The sync_from_exchange at _process_symbol start ensures we don't open duplicates.
            
            if transition.action == 'OPEN_LONG':
                logger.info(f"🚀 {symbol}: Opening LONG position (from={transition.from_state.value})")
                await self._execute_trade(symbol, 'long', composite_signal.final_score, composite_signal, ohlcv_data)
                
            elif transition.action == 'OPEN_SHORT':
                logger.info(f"🚀 {symbol}: Opening SHORT position (from={transition.from_state.value})")
                await self._execute_trade(symbol, 'short', composite_signal.final_score, composite_signal, ohlcv_data)
                
            elif transition.action == 'CLOSE_REVERSE' or transition.action == 'REVERSE':
                logger.info(f"🔄 {symbol}: Close & Reverse - {transition.reason}")
                await self._execute_close_and_reverse(symbol, gated_signal.direction, composite_signal.final_score, composite_signal, ohlcv_data)
                
            elif transition.action == 'IGNORE':
                # Same direction signal - ignore to prevent duplicate position
                logger.info(f"🚫 {symbol}: IGNORE - {transition.reason}")
                
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
            
            # NOTE: decision_logger.log_decision is disabled to avoid duplicate logs
            # summary_logger.log_analysis already provides full analysis info (called at line 357)
            # If structured JSONL logging is needed, re-enable this block
            
            # Return the result dict
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to process {symbol}: {e}")
            self.summary_logger.record_failure(symbol, str(e))
            if self.prometheus_exporter:
                self.prometheus_exporter.record_error('symbol_processing', 'trading_analysis')
            return None
    
    async def _execute_trade(self, symbol: str, side: str, score: float, composite_signal=None, ohlcv_data: dict = None):
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
                live=True,  # This is the scheduler, so always live
                ohlcv_data=ohlcv_data  # Pass OHLCV for ATR-based TP/SL
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to execute trade for {symbol}: {e}")
            raise
    
    async def _execute_close_and_reverse(self, symbol: str, new_direction: str, score: float, composite_signal=None, ohlcv_data: dict = None):
        """Execute close and reverse using real trading logic."""
        try:
            # Step 1: Close existing position
            logger.info(f"🔄 [REVERSE] Step 1: Closing existing position for {symbol}")
            
            try:
                # Fetch current position
                if hasattr(self.exchange_adapter, 'fetch_positions'):
                    positions = await self.exchange_adapter.fetch_positions()
                else:
                    positions = await self.exchange_adapter.ccxt_client.fetch_positions()
                
                # Find position for this symbol
                for pos in positions:
                    pos_symbol_raw = pos.get('symbol', '')
                    info = pos.get('info', {})
                    pos_symbol_okx = info.get('instId', '')
                    pos_symbol_normalized = pos_symbol_raw.replace('/', '-').replace(':USDT', '-SWAP').replace(':USD', '-SWAP')
                    
                    symbol_matches = (
                        pos_symbol_raw == symbol or
                        pos_symbol_normalized == symbol or
                        pos_symbol_okx == symbol
                    )
                    
                    contracts = float(pos.get('contracts', 0) or 0)
                    if contracts == 0:
                        contracts = abs(float(pos.get('notional', 0) or 0))
                    if contracts == 0:
                        contracts = abs(float(info.get('pos', 0) or 0))
                    
                    if symbol_matches and contracts != 0:
                        # Found position - close it
                        side = pos.get('side', '').lower()
                        close_side = 'buy' if side == 'short' else 'sell'
                        
                        logger.info(f"🔄 [REVERSE] Closing {side.upper()} position: {contracts} contracts")
                        
                        # Create close order (reduce only)
                        close_result = await self.exchange_adapter.create_market_order(
                            symbol=symbol,
                            side=close_side,
                            amount=contracts,
                            params={'reduceOnly': True}
                        )
                        logger.info(f"✅ [REVERSE] Position closed: {close_result.get('id', 'N/A')}")
                        break
                else:
                    logger.warning(f"⚠️ [REVERSE] No position found to close for {symbol}")
                    
            except Exception as e:
                logger.error(f"❌ [REVERSE] Failed to close position: {e}")
                # Continue to open new position anyway
            
            # Step 2: Open new position
            logger.info(f"🔄 [REVERSE] Step 2: Opening {new_direction.upper()} position for {symbol}")
            await self._execute_trade(symbol, new_direction, score, composite_signal, ohlcv_data)
            
            logger.info(f"✅ [REVERSE] Complete: {symbol} now {new_direction.upper()}")
            
        except Exception as e:
            logger.error(f"❌ Failed to execute close and reverse for {symbol}: {e}")
            raise
    
    async def _sync_position_from_exchange(self, symbol: str) -> bool:
        """
        Fetch real positions from exchange and sync with state manager.
        
        This is called at the START of each analysis cycle to ensure
        the in-memory position state matches the real exchange state.
        This prevents duplicate position opening.
        
        Args:
            symbol: Trading symbol to check
            
        Returns:
            True if a real position exists, False otherwise
        """
        try:
            # Fetch all positions from exchange
            if hasattr(self.exchange_adapter, 'fetch_positions'):
                positions = await self.exchange_adapter.fetch_positions()
            elif hasattr(self.exchange_adapter, 'ccxt_client'):
                positions = await self.exchange_adapter.ccxt_client.fetch_positions()
            else:
                logger.warning(f"⚠️ Cannot fetch positions - adapter doesn't support it")
                return False
            
            # DEBUG: Log first position to see format
            if positions and len(positions) > 0:
                logger.debug(f"[SYNC-DEBUG] Sample position keys: {list(positions[0].keys())}")
            
            # Find position for this symbol
            for pos in positions:
                pos_symbol_raw = pos.get('symbol', '')
                
                # CRITICAL: Normalize CCXT symbol format to our format
                # CCXT returns: 'BTC/USDT:USDT' or 'BTC/USDT'
                # Our format: 'BTC-USDT-SWAP'
                # Also check info.instId which is OKX native format: 'BTC-USDT-SWAP'
                info = pos.get('info', {})
                pos_symbol_okx = info.get('instId', '')  # OKX native format
                
                # Normalize CCXT format to our format
                pos_symbol_normalized = pos_symbol_raw.replace('/', '-').replace(':USDT', '-SWAP').replace(':USD', '-SWAP')
                
                # Check both formats
                symbol_matches = (
                    pos_symbol_raw == symbol or  # Exact match
                    pos_symbol_normalized == symbol or  # Normalized CCXT -> OKX
                    pos_symbol_okx == symbol  # OKX native from info
                )
                
                # CCXT uses 'contracts' or 'notional' or 'info.pos'
                contracts = float(pos.get('contracts', 0) or 0)
                if contracts == 0:
                    # Try alternative field names from CCXT
                    contracts = abs(float(pos.get('notional', 0) or 0))
                if contracts == 0:
                    # Try info dict (raw exchange data)
                    contracts = abs(float(info.get('pos', 0) or 0))
                
                # DEBUG: Log all positions we're checking
                if contracts != 0:
                    logger.debug(f"[SYNC-CHECK] pos_raw={pos_symbol_raw} pos_okx={pos_symbol_okx} pos_norm={pos_symbol_normalized} target={symbol} match={symbol_matches} contracts={contracts}")
                
                if symbol_matches and contracts != 0:
                    # Real position exists - sync to state manager
                    side = pos.get('side', '').lower()  # 'long' or 'short'
                    
                    # CCXT uses 'entryPrice' or 'info.avgPx'
                    entry_price = float(pos.get('entryPrice', 0) or pos.get('avgPrice', 0) or 0)
                    if entry_price == 0:
                        entry_price = float(info.get('avgPx', 0) or info.get('entryPrice', 0) or 0)
                    
                    size = abs(contracts)
                    
                    logger.info(f"[SYNC] {symbol}: Found REAL {side.upper()} position, size={size:.4f}, entry=${entry_price:.2f}")
                    
                    self.state_manager.sync_from_exchange(
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        size=size
                    )
                    
                    # Verify sync worked
                    current_state = self.state_manager.get_position_state(symbol)
                    logger.info(f"[SYNC] {symbol}: State after sync = {current_state.value}")
                    
                    return True
            
            # No position found - sync as no position
            self.state_manager.sync_no_position(symbol)
            logger.debug(f"[SYNC] {symbol}: No real position found, state=READY")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to sync position for {symbol}: {e}")
            import traceback
            logger.debug(f"[SYNC-ERROR] {traceback.format_exc()}")
            return False
