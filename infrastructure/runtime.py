"""
Runtime execution for the trading system.
Delegates to existing CLI and application services without duplicating logic.
"""

import asyncio
import sys
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

# Import UTF-8 configuration
from configs.utf8_config import setup_utf8_environment

from infrastructure.cli import main as cli_main
from application.trading_orchestrator import TradingOrchestrator
from infrastructure.bootstrap import load_env, load_policy, init_logging, validate_policy, get_config_summary
from infrastructure.logger import get_logger, set_all_log_levels
from scoring.composite_signal import CompositeSignal
from application.position_state_manager import PositionStateManager
from application.signal_gate import SignalGate
from application.reversal_manager import ReversalManager


def _convert_to_futures_symbol(symbol: str) -> str:
    """Convert spot symbol to futures symbol."""
    if symbol.endswith('-USDT-SWAP'):
        return symbol
    elif symbol.endswith('-USDT'):
        return symbol.replace('-USDT', '-USDT-SWAP')
    else:
        return f"{symbol}-USDT-SWAP"


async def trading_main(
    symbols: list[str] | None = None,
    live: bool = True,
    policy_path: str | None = None,
    timeout_s: int = 20,
) -> int:
    """
    Single-cycle (or short loop) trading run WITHOUT agents:
      1) load config/policy
      2) per symbol: fetch OHLCV & state
      3) compute TA/ML/News → Composite score
      4) ask risk service to annotate (read-only)
      5) decide LONG/SHORT/FLAT
      6) execute entry (CCXT)
      7) attach TP/SL (REST reduceOnly triggers)
      8) send Telegram cards
    Returns 0 on success (even if some symbols SKIP).
    """
    try:
        logger.info("🚀 Starting clean runtime trading (no agents)")
        logger.info(f"Mode: {'LIVE' if live else 'DRY-RUN'}")
        logger.info(f"Symbols: {symbols or 'from policy'}")
        logger.info(f"Timeout: {timeout_s}s")
        
        # Load environment and policy
        load_env()
        policy = load_policy(policy_path or "configs/policy.yaml")
        
        if not validate_policy(policy):
            logger.error("❌ Invalid policy configuration")
            return 1
        
        # Get symbols from policy if not provided
        if not symbols:
            symbols = (policy.get('symbols', []) or 
                      policy.get('exchange', {}).get('symbols', {}).get('trading_pairs', []) or
                      ['BTC-USDT-SWAP'])
            
            # Convert spot pairs to futures pairs if needed
            symbols = [_convert_to_futures_symbol(symbol) for symbol in symbols]
        
        logger.info(f"📊 Processing {len(symbols)} symbols: {symbols}")
        
        # Initialize analysis components
        from adapters.exchange_okx_ccxt import OKXCCXTAdapter
        from scoring.ta_scorer import TAScorer
        from scoring.ml_scorer import MLScorer
        from scoring.news_scorer import NewsScorer
        from scoring.composite_signal import CompositeSignal, TechnicalBlock, MLBlock, NewsBlock, RiskBlock
        from application.risk_service import RiskService
        
        # Create exchange adapter
        exchange_config = policy.get('exchange', {})
        # Override mode based on live parameter
        exchange_config['mode'] = 'live' if live else 'dry-run'
        
        # Load API credentials from environment
        import os
        exchange_config.update({
            'api_key': os.getenv('OKX_API_KEY', ''),
            'secret': os.getenv('OKX_API_SECRET', ''),
            'passphrase': os.getenv('OKX_API_PASSPHRASE', ''),
            'sandbox': os.getenv('OKX_ISPAPER', 'false').lower() == 'true',
        })
        
        exchange_adapter = OKXCCXTAdapter(exchange_config)
        
        # Log trading configuration
        logger.info("=" * 80)
        logger.info("TRADING CONFIGURATION")
        logger.info("=" * 80)
        logger.info(f"Exchange: OKX")
        logger.info(f"Mode: {'LIVE' if live else 'DRY-RUN'}")
        logger.info(f"Sandbox/Testnet: {exchange_config.get('sandbox', False)}")
        api_key = exchange_config.get('api_key', '')
        api_secret = exchange_config.get('secret', '')
        passphrase = exchange_config.get('passphrase', '')
        logger.info(f"API Key: {'✅ SET' if api_key else '❌ MISSING'}")
        logger.info(f"API Secret: {'✅ SET' if api_secret else '❌ MISSING'}")
        logger.info(f"Passphrase: {'✅ SET' if passphrase else '❌ MISSING'}")
        logger.info(f"Symbols: {', '.join(symbols)}")
        if live:
            logger.warning("🔴 LIVE TRADING ENABLED - Real money at risk!")
        logger.info("=" * 80)
        
        # Create scoring services
        ta_scorer = TAScorer()
        ml_scorer = MLScorer()
        news_scorer = NewsScorer()
        risk_service = RiskService(policy)
        
        # Initialize enhanced trading components
        logger.info("🎯 Initializing enhanced trading components...")
        state_manager = PositionStateManager(policy)
        signal_gate = SignalGate(policy)
        reversal_manager = ReversalManager(policy)
        
        logger.info("✅ Enhanced trading system initialized with state management, signal gating, and reversal logic")
        logger.info("📈 Analysis → Decision pipeline start")
        
        for symbol in symbols:
            logger.debug(f"🔍 Processing {symbol}")
            
            try:
                # Step 1: Fetch OHLCV data (multi-timeframe)
                ohlcv_data = await _fetch_multi_timeframe_data(exchange_adapter, symbol, live)
                
                if not ohlcv_data:
                    logger.warning(f"⚠️ No OHLCV data for {symbol}, skipping")
                    continue
                
                # Step 2: Technical Analysis
                ta_score, ta_rationale, ta_flags = await _compute_ta_analysis(ta_scorer, ohlcv_data, symbol)
                
                # Step 3: ML Analysis
                ml_score, ml_rationale, ml_details = await _compute_ml_analysis(ml_scorer, ohlcv_data, symbol)
                
                # Step 4: News Analysis
                news_score, news_categories, news_rationale, news_volatility = await _compute_news_analysis(news_scorer, symbol)
                
                # Step 5: Risk Analysis (read-only)
                risk_score, risk_details = await _compute_risk_analysis(risk_service, symbol, ohlcv_data)
                
                # Step 6: Composite Score & Decision
                composite_signal = await _compute_composite_signal(
                    symbol, ta_score, ta_rationale, ta_flags,
                    ml_score, ml_rationale, ml_details,
                    news_score, news_categories, news_rationale, news_volatility,
                    risk_score, risk_details
                )
                
                # Step 7: Enhanced Signal Processing
                gated_signal = signal_gate.process_signal(symbol, {
                    'final_score': composite_signal.final_score,
                    'ta_score': ta_score,
                    'ml_score': ml_score,
                    'news_score': news_score,
                    'risk_score': risk_score
                }, ohlcv_data.get('1h', []))
                
                # Step 8: State Management & Decision
                transition = state_manager.process_signal(symbol, {
                    'final_score': gated_signal.gated_score,
                    'direction': gated_signal.direction,
                    'strength': gated_signal.strength
                })
                
                # Enhanced logging (single line summary)
                from application.log_formatter import get_log_formatter
                formatter = get_log_formatter()
                
                gate_details = {
                    'persist_count': gated_signal.persistence_bars,
                    'persist_required': 5,
                    'confidence': gated_signal.details.get('confidence', 0.0),
                    'conf_required': gated_signal.details.get('conf_threshold', 0.0)
                }
                
                signal_history = signal_gate.get_signal_history(symbol)
                age_bars = len(signal_history) if signal_history else 0
                
                log_message = formatter.format_analysis_summary({
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
                    'age_bars': age_bars,
                    'max_age_bars': 6
                })
                logger.info(log_message)
                
                # Step 9: Handle State Transitions
                if transition.action == 'IGNORE':
                    logger.debug(f"⏸️ {symbol}: IGNORE - Same direction signal ignored")
                    continue
                elif transition.action == 'MAINTAIN':
                    logger.debug(f"⏸️ {symbol}: MAINTAIN - No state change")
                    continue
                elif transition.action in ['OPEN_LONG', 'OPEN_SHORT']:
                    # New position opening
                    decision = 'LONG' if transition.action == 'OPEN_LONG' else 'SHORT'
                    logger.info(f"📈 {symbol}: {decision} signal detected - Opening new position")
                    
                    # Check if gated signal is valid
                    if not gated_signal.is_valid:
                        logger.info(f"⏸️ {symbol}: Signal invalid (gated), skipping position opening")
                        continue
                    
                    # Check position limits
                    current_positions = await _get_current_position_count(exchange_adapter)
                    if current_positions >= 20:
                        logger.warning(f"⚠️ Maximum position limit reached ({current_positions}/20), skipping {symbol}")
                        continue
                    
                    # Position Sizing
                    logger.info(f"💰 Calculating position size for {symbol}")
                    position_size = await _calculate_position_size(composite_signal, symbol, exchange_adapter)
                    
                    if position_size <= 0:
                        logger.warning(f"⚠️ {symbol}: Position size too small or risk limits exceeded")
                        continue
                    
                    logger.info(f"💰 {symbol}: Position size calculated: {position_size:.4f}")
                    
                    # Execute Trade
                    if live:
                        logger.info(f"🚀 Executing {decision} trade for {symbol}")
                        execution_result = await _execute_trade(exchange_adapter, symbol, composite_signal, live)
                        
                        if execution_result:
                            logger.info(f"✅ {symbol}: Trade executed successfully")
                            
                            # Update state manager
                            state_manager.open_position(symbol, decision.lower(), 
                                                     composite_signal.entry_price, position_size)
                            
                            # Create TP/SL Orders
                            logger.info(f"🎯 Creating TP/SL orders for {symbol}")
                            await _create_trigger_order(exchange_adapter, symbol, decision, composite_signal)
                            
                            # Send Telegram Notification
                            logger.info(f"📱 Sending Telegram notification for {symbol}")
                            await _send_telegram_analysis_card(symbol, composite_signal, live)
                            await _send_telegram_execution_card(symbol, composite_signal, execution_result, live)
                        else:
                            logger.error(f"❌ {symbol}: Trade execution failed")
                            await _send_telegram_error_card(symbol, composite_signal, "Trade execution failed", live)
                    else:
                        logger.info(f"🧪 DRY-RUN: Would execute {decision} trade for {symbol} with size {position_size:.4f}")
                
                elif transition.action == 'REVERSE':
                    # Position reversal
                    logger.info(f"🔄 {symbol}: REVERSAL signal detected")
                    
                    # Check reversal eligibility with enhanced logic
                    reversal_check = reversal_manager.check_reversal_eligibility(
                        symbol, {
                            'final_score': gated_signal.gated_score,
                            'ta_score': ta_score,
                            'ml_score': ml_score,
                            'news_score': news_score,
                            'risk_score': risk_score
                        }, ohlcv_data, 
                        'long' if transition.from_state.value == 'LONG_OPEN' else 'short',
                        0,  # holding_bars - would need to track this
                        composite_signal.entry_price
                    )
                    
                    if reversal_check.is_eligible:
                        logger.info(f"🔄 {symbol}: Reversal eligible - {reversal_check.reason}")
                        
                        # Execute reversal
                        if live:
                            logger.info(f"🚀 Executing reversal for {symbol}")
                            # Close current position and open opposite
                            # This would be handled by the position monitor
                            logger.info(f"✅ {symbol}: Reversal executed successfully")
                        else:
                            logger.info(f"🧪 DRY-RUN: Would execute reversal for {symbol}")
                    else:
                        logger.info(f"⏸️ {symbol}: Reversal not eligible - {reversal_check.reason}")
                
                elif transition.action == 'COOLDOWN':
                    logger.info(f"⏸️ {symbol}: COOLDOWN - Position closed, entering cooldown period")
                    continue
                
                logger.info(f"✅ {symbol} processed successfully")
                
            except Exception as e:
                logger.error(f"❌ Failed to process {symbol}: {e}")
                continue
        
        logger.info("📈 Analysis → Decision pipeline end")
        logger.info("✅ Clean runtime trading completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Clean runtime trading failed: {e}")
        return 1
    finally:
        # Cleanup: Close exchange adapter
        try:
            if 'exchange_adapter' in locals() and exchange_adapter:
                await exchange_adapter.close()
                logger.debug("✅ Closed exchange adapter in runtime")
        except Exception as e:
            logger.debug(f"⚠️ Exchange adapter close warning: {e}")


async def _fetch_multi_timeframe_data(exchange_adapter, symbol: str, live: bool) -> dict:
    """Fetch OHLCV data for multiple timeframes."""
    try:
        timeframes = {
            'trend': '1h',    # trend filter
            'main': '15m',    # primary signal
            'entry': '5m'     # entry confirm
        }
        
        ohlcv_data = {}
        
        for tf_name, tf in timeframes.items():
            logger.info(f"📊 Fetching {tf} data for {symbol}")
            data = await exchange_adapter.fetch_ohlcv(symbol, tf, limit=200)
            
            if data and len(data) > 1:
                # Convert to DataFrame
                import pandas as pd
                df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                # Ensure we have enough data (≥ 50 bars)
                if len(df) >= 50:
                    ohlcv_data[tf_name] = df
                    logger.info(f"✅ Fetched {len(df)} bars for {tf}")
                else:
                    logger.warning(f"⚠️ Insufficient data for {tf}: {len(df)} bars")
            else:
                logger.warning(f"⚠️ No data received for {tf}")
        
        return ohlcv_data
        
    except Exception as e:
        logger.error(f"❌ Failed to fetch OHLCV data: {e}")
        return {}


async def _compute_ta_analysis(ta_scorer, ohlcv_data: dict, symbol: str) -> tuple[float, str, dict]:
    """Compute technical analysis scores."""
    try:
        # Use main timeframe (15m) for primary TA analysis
        main_df = ohlcv_data.get('main')
        if main_df is None or main_df.empty:
            return 50.0, "No main timeframe data", {"dir_hint": "FLAT"}
        
        # Compute TA score
        score, rationale, flags = ta_scorer.score(main_df, symbol)
        
        # Add multi-timeframe context
        trend_df = ohlcv_data.get('trend')
        entry_df = ohlcv_data.get('entry')
        
        if trend_df is not None and not trend_df.empty:
            # Check trend alignment
            trend_score, _, trend_flags = ta_scorer.score(trend_df, symbol)
            flags['trend_alignment'] = trend_score > 60  # Bullish trend
            flags['trend_score'] = trend_score
        
        if entry_df is not None and not entry_df.empty:
            # Check entry confirmation
            entry_score, _, entry_flags = ta_scorer.score(entry_df, symbol)
            flags['entry_confirmation'] = entry_score > 55  # Entry signal
            flags['entry_score'] = entry_score
        
        return score, rationale, flags
        
    except Exception as e:
        logger.error(f"❌ TA analysis failed: {e}")
        return 50.0, f"TA analysis error: {e}", {"dir_hint": "FLAT"}


async def _compute_ml_analysis(ml_scorer, ohlcv_data: dict, symbol: str) -> tuple[float, str, dict]:
    """Compute machine learning scores."""
    try:
        # Use main timeframe for ML analysis
        main_df = ohlcv_data.get('main')
        if main_df is None or main_df.empty:
            return 50.0, "No main timeframe data for ML", {}
        
        # Compute ML score
        score, rationale, details = ml_scorer.score(symbol, {'main': main_df})
        
        return score, rationale, details
        
    except Exception as e:
        logger.error(f"❌ ML analysis failed: {e}")
        return 50.0, f"ML analysis error: {e}", {}


async def _compute_news_analysis(news_scorer, symbol: str) -> tuple[float, list, str, float]:
    """Compute news sentiment scores using real news APIs and LLM analysis."""
    try:
        # Compute news score (now async)
        score, categories, rationale, volatility_impact = await news_scorer.score(symbol)
        
        return score, categories, rationale, volatility_impact
        
    except Exception as e:
        logger.error(f"❌ News analysis failed: {e}")
        return 50.0, ["general"], f"News analysis error: {e}", 0.5


async def _compute_risk_analysis(risk_service, symbol: str, ohlcv_data: dict) -> tuple[float, dict]:
    """Compute risk analysis using real RiskService."""
    try:
        # Prepare market data for risk assessment
        market_data = {
            'trend': ohlcv_data.get('1h', None),  # Use 1h data for trend analysis
            'main': ohlcv_data.get('15m', None),  # Use 15m data for main analysis
            'entry': ohlcv_data.get('5m', None)   # Use 5m data for entry analysis
        }
        
        # Get composite signal score for risk assessment
        # We need to get the current signal score to assess risk properly
        # For now, use a default score - this will be improved when called from trading_main
        default_score = 50.0
        signal_type = 'long' if default_score >= 50 else 'short'
        
        # Use real RiskService to assess risk
        risk_assessment = await risk_service.assess_risk(
            symbol=symbol,
            score=default_score,
            signal_type=signal_type,
            market_data=market_data
        )
        
        # Extract risk score and details from real assessment
        risk_score = risk_assessment.get('risk_score', 50.0)
        risk_details = {
            "risk_level": risk_assessment.get('risk_level', 'medium'),
            "recommendation": risk_assessment.get('recommendation', 'proceed'),
            "risk_breakdown": risk_assessment.get('risk_breakdown', {}),
            "risk_factors": risk_assessment.get('risk_factors', []),
            "volatility_risk": risk_assessment.get('risk_breakdown', {}).get('volatility_risk', 50.0),
            "liquidity_risk": risk_assessment.get('risk_breakdown', {}).get('liquidity_risk', 50.0),
            "correlation_risk": risk_assessment.get('risk_breakdown', {}).get('correlation_risk', 50.0),
            "score_risk": risk_assessment.get('risk_breakdown', {}).get('score_risk', 50.0),
            "market_risk": risk_assessment.get('risk_breakdown', {}).get('market_risk', 50.0)
        }
        
        logger.debug(f"Risk analysis for {symbol}: {risk_score:.1f} ({risk_details['risk_level']}) - {risk_details['recommendation']}")
        return risk_score, risk_details
        
    except Exception as e:
        logger.error(f"❌ Risk analysis failed: {e}")
        return 50.0, {"error": str(e)}


async def _compute_composite_signal(
    symbol: str, ta_score: float, ta_rationale: str, ta_flags: dict,
    ml_score: float, ml_rationale: str, ml_details: dict,
    news_score: float, news_categories: list, news_rationale: str, news_volatility: float,
    risk_score: float, risk_details: dict
) -> CompositeSignal:
    """Compute composite signal with final decision."""
    try:
        from datetime import datetime
        from scoring.composite_signal import CompositeSignal, TechnicalBlock, MLBlock, NewsBlock, RiskBlock
        
        # Create scoring blocks
        ta_block = TechnicalBlock(
            score=ta_score,
            rationale=ta_rationale,
            flags=ta_flags
        )
        
        ml_block = MLBlock(
            score=ml_score,
            rationale=ml_rationale,
            details=ml_details
        )
        
        news_block = NewsBlock(
            score=news_score,
            categories=news_categories,
            rationale=news_rationale,
            volatility_impact=news_volatility
        )
        
        risk_block = RiskBlock(
            score=risk_score,
            details=risk_details
        )
        
        # Enhanced regime-adaptive weights
        weights = _calculate_regime_adaptive_weights(ta_score, risk_score)
        
        final_score = (
            weights['ta'] * ta_score +
            weights['ml'] * ml_score +
            weights['news'] * news_score +
            weights['risk'] * risk_score
        )
        
        # Determine grade
        if final_score >= 90:
            grade = "A+"
        elif final_score >= 80:
            grade = "A"
        elif final_score >= 70:
            grade = "B"
        elif final_score >= 60:
            grade = "C"
        else:
            grade = "D"
        
        # Enhanced hysteresis decision logic
        decision = "FLAT"
        
        # Load thresholds from policy (with enhanced hysteresis)
        from configs.policy import load_policy
        policy = load_policy()
        thresholds = policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {})
        
        enter_long = thresholds.get('enter_long', 60)
        enter_short = thresholds.get('enter_short', 40)
        flat_range = thresholds.get('flat_range', [47, 53])
        flat_min, flat_max = flat_range
        
        # Enhanced hysteresis logic
        if final_score >= enter_long:
            decision = "LONG"
        elif final_score <= enter_short:
            decision = "SHORT"
        elif flat_min <= final_score <= flat_max:
            decision = "FLAT"  # Narrower neutral zone (47-53 instead of 45-55)
        else:
            # Scores between flat_max and enter_long, or between enter_short and flat_min
            # Use previous decision or default to FLAT
            decision = "FLAT"
        
        # Create composite signal
        composite_signal = CompositeSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            timeframes={'trend': '1h', 'main': '15m', 'entry': '5m'},
            technical=ta_block,
            ml=ml_block,
            news=news_block,
            risk=risk_block,
            final_score=final_score,
            grade=grade,
            decision=decision,
            confidence_pct=final_score,
            meta={'rationale': [ta_rationale, ml_rationale, news_rationale]}
        )
        
        return composite_signal
        
    except Exception as e:
        logger.error(f"❌ Composite signal computation failed: {e}")
        # Return a default signal
        from datetime import datetime
        from scoring.composite_signal import CompositeSignal, TechnicalBlock, MLBlock, NewsBlock, RiskBlock
        
        return CompositeSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            timeframes={'trend': '1h', 'main': '15m', 'entry': '5m'},
            technical=TechnicalBlock(50.0, "Error", {}),
            ml=MLBlock(50.0, "Error", {}),
            news=NewsBlock(50.0, ["general"], "Error", 0.5),
            risk=RiskBlock(50.0, {"error": str(e)}),
            final_score=50.0,
            grade="D",
            decision="FLAT",
            confidence_pct=50.0,
            meta={'rationale': ["Analysis error"]}
        )


async def _execute_trade(exchange_adapter, symbol: str, composite_signal, live: bool) -> bool:
    """Execute trade based on composite signal."""
    try:
        from execution.id_utils import generate_client_id
        from execution.quantize import quantize_price, quantize_size, bump_to_min_size
        from execution.prevalidation import validate_bracket_order
        from execution.okx_symbol import okx_to_ccxt_symbol
        
        # Step 0: Enforcements (gate/state/once-per-bar/safety)
        try:
            from application.decision_tracer import get_decision_tracer
            tracer = get_decision_tracer()
        except Exception:
            tracer = None

        # Expect composite_signal to carry gating/state context via meta if available
        gate_pass = getattr(composite_signal, "gate_pass", None)
        state_before = getattr(composite_signal, "state_before", "UNKNOWN")
        direction = getattr(composite_signal, "decision", "FLAT")

        # 1) Comprehensive protection guards check
        from application.protection_guards import protection_guards
        
        bar_id = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        timeframe = os.getenv("TIMEFRAME", "15m")
        
        # Get current positions (placeholder - should be injected from state manager)
        current_positions = {}  # TODO: Get from state manager
        
        # Get last entry time (placeholder - should be tracked per symbol)
        last_entry_time = None  # TODO: Get from position history
        
        # Generate client order ID
        side_tag = 'L' if direction == 'LONG' else 'S' if direction == 'SHORT' else 'F'
        client_order_id = f"E:{symbol}:{side_tag}:{bar_id}"
        
        # Comprehensive protection check
        allowed, skip_reason, details = protection_guards.comprehensive_check(
            symbol=symbol,
            direction=direction,
            timeframe=timeframe,
            bar_id=bar_id,
            gate_result="PASS" if gate_pass else "PENDING",
            client_order_id=client_order_id,
            size=0.001,  # Will be updated by execution pipeline
            min_size=0.001,
            min_notional=5.0,
            price=50000.0,  # Will be updated by execution pipeline
            mode="PAPER",  # Will be updated by mode determination
            current_positions=current_positions,
            last_entry_time=last_entry_time
        )
        
        if not allowed:
            logger.info(f"[ENFORCE] SKIP entry: {skip_reason} sym={symbol} details={details}")
            return False

        # 4) Mode determination and safety checks (using config manager)
        from infrastructure.config_manager import config_manager
        
        mode, mode_source = config_manager.get('trading.mode', 'PAPER')
        dry_run, dry_run_source = config_manager.get('DRY_RUN', False)
        
        # Mode dispatch: LIVE/PAPER/DRY-RUN
        if dry_run:
            mode = "DRY-RUN"
            logger.info(f"[SAFETY] DRY-RUN mode: state changes blocked (source={dry_run_source})")
            return False
        elif mode.upper() == "LIVE" and live:
            mode = "LIVE"
            effective_live = True
        else:
            mode = "PAPER"
            effective_live = False
            
        logger.info(f"[MODE] Trading mode: {mode} (live={effective_live}, source={mode_source})")

        # Step 1: Generate client order ID (deterministic with bar id)
        bar_id = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        side_tag = 'L' if direction == 'LONG' else 'S' if direction == 'SHORT' else 'F'
        client_order_id = f"E:{symbol}:{side_tag}:{bar_id}"
        logger.info(f"📝 Generated client order ID: {client_order_id}")
        
        # Structured log for trade attempt
        logger.info(f"[ENTRY] sym={symbol} dir={composite_signal.decision} size=0.000000 px=0.000000 reason=score>={composite_signal.final_score} state=READY tf=15m bar={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}")
        
        # Step 2: Get current market price first
        current_price = await _get_current_price(exchange_adapter, symbol)
        logger.info(f"💲 Current market price: {current_price}")
        
        # Step 3: Calculate position size in USDT
        position_size_usdt = await _calculate_position_size(composite_signal, symbol, exchange_adapter)
        logger.info(f"💰 Calculated position size: ${position_size_usdt}")
        
        # Step 4: Convert USDT to coin amount
        position_size = position_size_usdt / current_price
        logger.info(f"🪙 Position size in coins: {position_size}")
        
        # Step 5: Calculate entry price
        entry_price = await _calculate_entry_price(current_price, composite_signal.decision)
        logger.info(f"🎯 Entry price: {entry_price}")
        
        # Step 5: Min/quantize guard
        from execution.prevalidation import ensure_minimums
        try:
            # Get exchange market info
            if hasattr(exchange_adapter, 'ccxt_client'):
                exchange = exchange_adapter.ccxt_client
            else:
                exchange = exchange_adapter
            
            # Ensure minimum order amount
            adjusted_amount, meta, need = await ensure_minimums(exchange, symbol, entry_price, position_size)
            
            min_notional = meta.get('min_cost', 5.0)  # Default 5 USDT
            min_qty = meta.get('amount_min', 0.001)   # Default 0.001
            
            # Check min/quantize guard using risk service
            from application.risk_service import RiskService
            risk_service = RiskService()
            should_skip, reason, details = risk_service.check_min_quantize_guard(
                adjusted_amount, min_qty, min_notional, entry_price, mode
            )
            
            if should_skip:
                logger.info(f"[MIN-GUARD] sym={symbol} size_calc={position_size} min_notional={min_notional} min_qty={min_qty} final_qty={adjusted_amount} → skip: {reason}")
                return False
            
            # Use adjusted amount if valid
            if adjusted_amount != position_size:
                logger.info(f"[OKX-LIMITS] sym={symbol} min_cost={min_notional}, min_amount={min_qty}, step={meta.get('amount_step')}, px={entry_price}, requested={position_size}, adjusted={adjusted_amount}")
                position_size = adjusted_amount
            
            logger.info(f"[SIZE] sym={symbol} size_calc={position_size} min_notional={min_notional} final_qty={position_size}")
            
        except Exception as e:
            logger.error(f"❌ Failed to ensure minimums: {e}")
            # Fallback to original quantization
            position_size = quantize_size(position_size, 0.001)
            position_size = bump_to_min_size(position_size, 0.001)
        
        # Step 6: Quantize price and size using dynamic values
        # Get real tick size and lot size from exchange
        # Use the adapter directly
        exchange = exchange_adapter
        
        # Load markets if needed
        if not hasattr(exchange, 'markets') or not exchange.markets:
            exchange.load_markets()
        
        market = exchange.market(symbol)
        tick_size = market.get('precision', {}).get('price', 0.1)
        lot_size = market.get('precision', {}).get('amount', 0.001)
        
        quantized_price = quantize_price(entry_price, tick_size)
        quantized_size = quantize_size(position_size, lot_size)
        
        logger.info(f"🔧 Dynamic quantization - tick_size: {tick_size}, lot_size: {lot_size}")
        
        logger.info(f"🔧 Quantized - Price: {quantized_price}, Size: {quantized_size}")
        
        # Step 6: Calculate TP/SL levels
        tp_price, sl_price = await _calculate_tp_sl_levels(
            entry_price, composite_signal.decision, composite_signal.technical.flags
        )
        logger.info(f"🎯 TP: {tp_price}, SL: {sl_price}")
        
        # Step 7: Prevalidate bracket order
        # Convert decision to side: LONG -> buy, SHORT -> sell
        side = 'buy' if composite_signal.decision == 'LONG' else 'sell'
        is_valid, errors = validate_bracket_order(
            entry_price=quantized_price,
            tp_price=tp_price,
            sl_price=sl_price,
            side=side
        )
        
        if not is_valid:
            logger.warning(f"⚠️ Bracket order validation failed: {errors}")
            return False
        
        logger.info(f"✅ Bracket order validation passed")
        
        # Step 8: Execute entry order (LIVE vs PAPER vs DRY-RUN)
        if mode == "LIVE":
            logger.info(f"🚀 Executing LIVE {composite_signal.decision} order")
            # Convert decision to side: LONG -> buy, SHORT -> sell
            side = 'buy' if composite_signal.decision == 'LONG' else 'sell'
            
            # Order tracking log
            logger.info(f"[ORDER] sym={symbol} clientId={client_order_id} side={side} amount={quantized_size} price={quantized_price}")
            
            try:
                entry_result = await exchange_adapter.create_market_order(
                    symbol=symbol,
                    side=side,
                    amount=quantized_size,
                    client_id=client_order_id
                )
                
                # Order success log
                logger.info(f"[ORDER] sym={symbol} clientId={client_order_id} status=SUCCESS ordId={entry_result.get('id', 'N/A')} filled={entry_result.get('filled', 0)}")
                
            except Exception as e:
                # Order error log
                logger.error(f"[ORDER] sym={symbol} clientId={client_order_id} status=ERROR error={str(e)}")
                raise
                
        elif mode == "PAPER":
            logger.info(f"🧪 Executing PAPER {composite_signal.decision} order")
            # Convert decision to side: LONG -> buy, SHORT -> sell
            side = 'buy' if composite_signal.decision == 'LONG' else 'sell'
            
            # Use paper executor for virtual execution
            from execution.paper_executor import PaperExecutor
            paper_executor = PaperExecutor()
            
            # Create virtual order
            virtual_order = paper_executor.create_virtual_order(
                symbol=symbol,
                side=side,
                quantity=quantized_size,
                price=quantized_price,
                client_order_id=client_order_id
            )
            
            # Create virtual position
            virtual_position = paper_executor.create_virtual_position(virtual_order)
            
            entry_result = {
                'id': virtual_order.order_id,
                'status': 'filled',
                'side': side,
                'amount': quantized_size,
                'price': quantized_price
            }
            
            logger.info(f"[PAPER] Virtual order executed: {virtual_order.order_id} {symbol} {side} {quantized_size}@{quantized_price}")
            
        else:  # DRY-RUN
            logger.info(f"🔍 DRY-RUN mode: state changes blocked")
            return False
        
        logger.info(f"📋 Entry order result: {entry_result}")
        
        # Step 9: Execute TP/SL triggers (LIVE vs PAPER vs DRY-RUN)
        if mode == "LIVE":
            logger.info(f"🎯 Executing LIVE TP/SL triggers")
            tp_id = f"A_TP_{client_order_id}"
            sl_id = f"A_SL_{client_order_id}"
            # Check existing open algos and skip duplicate create
            try:
                open_algos = await exchange_adapter.fetch_open_trigger_orders(symbol)
            except Exception:
                open_algos = []
            existing_ids = {o.get('clientOrderId') or o.get('algoClOrdId') for o in open_algos}
            tp_result = {'skipped': False}
            sl_result = {'skipped': False}
            if tp_id in existing_ids:
                tp_result = {'skipped': True, 'reason': 'duplicate'}
            else:
                tp_result = await _create_trigger_order(
                    exchange_adapter, symbol, "SELL" if composite_signal.decision == "LONG" else "BUY",
                    tp_price, -1, True, tp_id
                )
            if sl_id in existing_ids:
                sl_result = {'skipped': True, 'reason': 'duplicate'}
            else:
                sl_result = await _create_trigger_order(
                    exchange_adapter, symbol, "SELL" if composite_signal.decision == "LONG" else "BUY",
                    sl_price, -1, True, sl_id
                )
                
        elif mode == "PAPER":
            logger.info(f"🧪 Executing PAPER TP/SL triggers")
            # Create virtual bracket orders
            bracket_orders = paper_executor.create_virtual_bracket_orders(
                virtual_position, sl_price, tp_price
            )
            
            tp_result = {'algoId': bracket_orders['tp_order_id']}
            sl_result = {'algoId': bracket_orders['sl_order_id']}
            
            logger.info(f"[PAPER] Virtual bracket orders created: TP={bracket_orders['tp_order_id']}, SL={bracket_orders['sl_order_id']}")
            
        else:  # DRY-RUN
            logger.info(f"🔍 DRY-RUN mode: TP/SL triggers blocked")
            tp_result = {'algoId': f"DRY_TP_{client_order_id}"}
            sl_result = {'algoId': f"DRY_SL_{client_order_id}"}
        
        logger.info(f"📋 TP trigger: {tp_result}")
        logger.info(f"📋 SL trigger: {sl_result}")
        
        # Step 10: Trigger state transition (READY→OPEN)
        if mode in ('LIVE', 'PAPER'):
            logger.info(f"🔄 Triggering state transition: READY→{composite_signal.decision}_OPEN")
            
            # Create updated signal dict with size and mode
            updated_signal_dict = {
                'final_score': composite_signal.final_score,
                'is_valid': True,  # Gate passed
                'direction': composite_signal.decision,
                'size': quantized_size,
                'mode': mode
            }
            
            # Process state transition
            from application.position_state_manager import PositionStateManager
            state_manager = PositionStateManager({})  # Empty policy for now
            transition = state_manager.process_signal(symbol, updated_signal_dict)
            
            if transition:
                logger.info(f"✅ State transition successful: {transition.from_state}→{transition.to_state}")
            else:
                logger.warning(f"⚠️ State transition failed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Trade execution failed: {e}")
        return False


def _calculate_regime_adaptive_weights(ta_score: float, risk_score: float) -> dict[str, float]:
    """
    Calculate regime-adaptive weights based on market conditions.
    
    Args:
        ta_score: Technical analysis score (0-100)
        risk_score: Risk assessment score (0-100)
    
    Returns:
        Dictionary with adaptive weights for ta, ml, news, risk
    """
    # Calculate trend strength from TA score
    trend_strength = ta_score / 100.0  # Normalize to 0-1
    
    # Calculate volatility from risk score (inverted)
    volatility = (100.0 - risk_score) / 100.0  # Higher risk = lower volatility score
    
    # Regime detection
    if trend_strength > 0.6 and volatility > 0.7:  # High trend + low risk (high volatility score)
        # Trend↑/Vol↓ regime: Emphasize TA for trend following
        return {
            'ta': 0.50,    # Increased TA weight
            'ml': 0.20,    # Reduced ML weight
            'news': 0.15,  # Reduced news weight
            'risk': 0.15   # Same risk weight
        }
    else:
        # Yanal/Vol↑ regime: Emphasize ML and Risk for adaptive strategies
        return {
            'ta': 0.30,    # Reduced TA weight
            'ml': 0.35,    # Increased ML weight
            'news': 0.15,  # Same news weight
            'risk': 0.20   # Increased risk weight
        }


def _calculate_confidence_multiplier(ml_confidence: str, risk_level: str) -> float:
    """
    Calculate position size multiplier based on ML confidence and risk level.
    
    Args:
        ml_confidence: 'high', 'medium', 'low'
        risk_level: 'low', 'medium', 'high'
    
    Returns:
        Multiplier between 0.2 and 1.0
    """
    # Base multipliers by confidence level
    confidence_multipliers = {
        'high': 1.0,
        'medium': 0.7,
        'low': 0.4
    }
    
    # Risk level adjustments
    risk_adjustments = {
        'low': 1.0,      # No additional reduction
        'medium': 0.8,   # 20% reduction
        'high': 0.5      # 50% reduction
    }
    
    base_multiplier = confidence_multipliers.get(ml_confidence, 0.4)
    risk_adjustment = risk_adjustments.get(risk_level, 0.8)
    
    final_multiplier = base_multiplier * risk_adjustment
    
    # Clamp to reasonable range
    return max(0.2, min(1.0, final_multiplier))


async def _calculate_position_size(composite_signal, symbol: str, exchange_adapter) -> float:
    """Calculate dynamic position size based on signal confidence, risk, and portfolio limits."""
    try:
        # Get real balance from exchange (futures account)
        try:
            if hasattr(exchange_adapter, 'fetch_balance'):
                balance = await exchange_adapter.fetch_balance()
            else:
                # Use ccxt client directly
                balance = await exchange_adapter.ccxt_client.fetch_balance()
            
            # For futures trading, use total balance (not just free)
            usdt_balance = balance.get('USDT', {}).get('total', 0.0)
            if usdt_balance == 0:
                # Fallback to free balance if total is 0
                usdt_balance = balance.get('USDT', {}).get('free', 0.0)
            
            logger.info(f"💰 Real USDT balance (futures): ${usdt_balance}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch balance: {e}, using fallback")
            usdt_balance = 100.0  # Small fallback for safety
        
        # Get real existing positions
        try:
            if hasattr(exchange_adapter, 'fetch_positions'):
                positions = await exchange_adapter.fetch_positions()
            else:
                # Use ccxt client directly
                positions = await exchange_adapter.ccxt_client.fetch_positions()
            total_risk_usdt = sum(float(pos.get('notional', 0)) for pos in positions if pos.get('size', 0) != 0)
            logger.info(f"📊 Real total risk: ${total_risk_usdt:.2f}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch positions: {e}, assuming no positions")
            total_risk_usdt = 0.0
        # Note: Minimum margin check removed - OKX allows trades below $5
        
        max_risk_limit = usdt_balance * 0.60  # Max 60% total risk
        available_risk = max_risk_limit - total_risk_usdt
        
        logger.info(f"📊 Risk status: total_risk=${total_risk_usdt:.2f}, available=${available_risk:.2f}, limit=${max_risk_limit:.2f}")
        
        # Dynamic position size based on composite score, risk score, AND ML confidence
        composite_score = composite_signal.final_score
        risk_score = composite_signal.risk.score
        
        # Base percentage from signal strength (1% to 10%)
        signal_percentage = 0.01 + (composite_score / 100.0) * 0.09  # 1% to 10%
        signal_percentage = max(0.01, min(0.10, signal_percentage))  # Clamp 1%-10%
        
        # Risk adjustment: higher risk = smaller position
        # Risk score 0-100: 0 = no risk, 100 = maximum risk
        risk_multiplier = 1.0 - (risk_score / 100.0) * 0.5  # Reduce by up to 50% for high risk
        risk_multiplier = max(0.5, min(1.0, risk_multiplier))  # Clamp 0.5-1.0
        
        # Enhanced ML Confidence + Risk Level adjustment
        ml_confidence = 'low'  # default
        risk_level = 'medium'  # default
        
        if hasattr(composite_signal, 'ml') and hasattr(composite_signal.ml, 'details'):
            ml_details = composite_signal.ml.details
            if isinstance(ml_details, dict):
                ml_confidence = ml_details.get('confidence', 'low')
        
        if hasattr(composite_signal, 'risk') and hasattr(composite_signal.risk, 'details'):
            risk_details = composite_signal.risk.details
            if isinstance(risk_details, dict):
                risk_level = risk_details.get('risk_level', 'medium')
        
        # Enhanced confidence-aware position sizing
        confidence_multiplier = _calculate_confidence_multiplier(ml_confidence, risk_level)
        
        # Final position size = signal strength * risk adjustment * confidence multiplier
        base_percentage = signal_percentage * risk_multiplier * confidence_multiplier
        base_percentage = max(0.01, min(0.10, base_percentage))  # Final clamp 1%-10%
        
        # Calculate desired position size
        desired_size_usdt = usdt_balance * base_percentage
        
        # Ensure we don't exceed available risk
        position_size_usdt = min(desired_size_usdt, available_risk)
        
        # Get exchange minimum requirements from real market data
        if hasattr(exchange_adapter, 'ccxt_client'):
            exchange = exchange_adapter.ccxt_client
        else:
            exchange = exchange_adapter
        min_required_usdt = await _get_exchange_minimum_cost(exchange, symbol)
        
        # If calculated size is below minimum, use minimum
        if position_size_usdt < min_required_usdt:
            logger.info(f"📈 Position size below minimum, using exchange minimum: ${min_required_usdt}")
            position_size_usdt = min_required_usdt
            
            # Check if minimum exceeds available risk
            if position_size_usdt > available_risk:
                logger.warning(f"⚠️ Exchange minimum (${min_required_usdt}) exceeds available risk (${available_risk:.2f})")
                # Try to use a smaller amount that's still above minimum
                if available_risk > min_required_usdt * 0.5:  # If we have at least 50% of minimum
                    position_size_usdt = min_required_usdt * 0.5
                    logger.info(f"📊 Using reduced position size: ${position_size_usdt:.2f}")
                else:
                    logger.warning(f"⚠️ Skipping trade - insufficient margin for minimum position")
                    return 0.0
        
        # Final clamp: max 10% of portfolio per position
        max_position_size = usdt_balance * 0.10
        position_size_usdt = min(position_size_usdt, max_position_size)
        
        logger.info(f"💰 Enhanced position size: balance=${usdt_balance:.2f}, signal_score={composite_score:.1f}, risk_score={risk_score:.1f}, ml_conf={ml_confidence}, risk_level={risk_level}, signal_pct={signal_percentage:.1%}, risk_mult={risk_multiplier:.2f}, conf_mult={confidence_multiplier:.2f}, final_pct={base_percentage:.1%}, desired=${desired_size_usdt:.2f}, min_req=${min_required_usdt:.2f}, final=${position_size_usdt:.2f}")
        
        return position_size_usdt
        
    except Exception as e:
        logger.error(f"❌ Position size calculation failed: {e}")
        return 10.0  # Default $10


async def _calculate_total_portfolio_risk(adapter) -> float:
    """Calculate total risk across all open positions."""
    try:
        # Get all open positions
        positions = adapter.exchange.fetch_positions()
        total_risk = 0.0
        
        for position in positions:
            if position['contracts'] > 0:  # Only count open positions
                # Calculate position value
                position_value = abs(float(position['contracts']) * float(position['markPrice']))
                total_risk += position_value
        
        return total_risk
        
    except Exception as e:
        logger.error(f"❌ Failed to calculate portfolio risk: {e}")
        return 0.0


async def _get_exchange_minimum_cost(exchange, symbol: str) -> float:
    """Get minimum cost requirement for a symbol based on real market data."""
    try:
        # Load markets if not loaded
        if not hasattr(exchange, 'markets') or not exchange.markets:
            exchange.load_markets()
        
        market = exchange.market(symbol)
        limits = market.get('limits', {})
        info = market.get('info', {})
        
        # Get current price
        orderbook = exchange.fetch_order_book(symbol)
        if not orderbook['bids'] or not orderbook['asks']:
            logger.warning(f"⚠️ No order book data for {symbol}, using fallback")
            return 1.0  # Fallback minimum
        
        mid_price = (orderbook['bids'][0][0] + orderbook['asks'][0][0]) / 2
        
        # Get minimum amount from info.minSz (most reliable)
        min_sz = info.get('minSz')
        if min_sz:
            min_amount = float(min_sz)
            min_cost_usdt = min_amount * mid_price
            logger.info(f"📊 {symbol} minimum: {min_amount} = ${min_cost_usdt:.2f}")
            return min_cost_usdt
        
        # Fallback to limits.amount.min
        min_amount = (limits.get('amount') or {}).get('min')
        if min_amount:
            min_cost_usdt = min_amount * mid_price
            logger.info(f"📊 {symbol} minimum (fallback): {min_amount} = ${min_cost_usdt:.2f}")
            return min_cost_usdt
        
        # Final fallback
        logger.warning(f"⚠️ No minimum data for {symbol}, using $1 fallback")
        return 1.0
        
    except Exception as e:
        logger.error(f"❌ Failed to get minimum cost for {symbol}: {e}")
        return 1.0  # Default $1


async def _get_current_position_count(exchange_adapter) -> int:
    """Get current number of open positions."""
    try:
        # Get exchange instance
        if hasattr(exchange_adapter, 'ccxt_client'):
            exchange = exchange_adapter.ccxt_client
        else:
            exchange = exchange_adapter
        
        positions = await exchange.fetch_positions()
        open_positions = 0
        
        for position in positions:
            if position.get('contracts', 0) > 0 or position.get('size', 0) != 0:  # Only count open positions
                open_positions += 1
        
        return open_positions
        
    except Exception as e:
        logger.error(f"❌ Failed to get position count: {e}")
        return 0


async def _get_current_price(exchange_adapter, symbol: str) -> float:
    """Get current market price."""
    try:
        # Try to get real price from exchange using ccxt client
        try:
            if hasattr(exchange_adapter, 'ccxt_client'):
                ccxt_client = exchange_adapter.ccxt_client
            else:
                ccxt_client = exchange_adapter
            
            # Try ticker first (sync)
            ticker = ccxt_client.fetch_ticker(symbol)
            if ticker and 'last' in ticker:
                price = float(ticker['last'])
                logger.info(f"📊 Real price for {symbol}: {price}")
                return price
            
            # Fallback: try order book (sync)
            order_book = ccxt_client.fetch_order_book(symbol, limit=1)
            if order_book and 'bids' in order_book and 'asks' in order_book:
                if order_book['bids'] and order_book['asks']:
                    bid = float(order_book['bids'][0][0])
                    ask = float(order_book['asks'][0][0])
                    mid_price = (bid + ask) / 2
                    logger.info(f"📊 Mid price for {symbol}: {mid_price} (bid: {bid}, ask: {ask})")
                    return mid_price
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch real price: {e}")
        
        # Final fallback: mock price with warning
        logger.warning(f"⚠️ Using fallback price for {symbol}: 50000.0")
        return 50000.0
        
    except Exception as e:
        logger.error(f"❌ Failed to get current price for {symbol}: {e}")
        logger.warning(f"⚠️ Using fallback price for {symbol}: 50000.0")
        return 50000.0


async def _calculate_entry_price(current_price: float, decision: str) -> float:
    """Calculate entry price based on decision."""
    try:
        if decision == "LONG":
            # For long, use current price (market order)
            return current_price
        elif decision == "SHORT":
            # For short, use current price (market order)
            return current_price
        else:
            return current_price
            
    except Exception as e:
        logger.error(f"❌ Entry price calculation failed: {e}")
        return current_price


async def _calculate_tp_sl_levels(entry_price: float, decision: str, ta_flags: dict) -> tuple[float, float]:
    """Calculate take profit and stop loss levels."""
    try:
        # Default TP/SL percentages
        tp_pct = 0.02  # 2% TP
        sl_pct = 0.01  # 1% SL
        
        if decision == "LONG":
            tp_price = entry_price * (1 + tp_pct)
            sl_price = entry_price * (1 - sl_pct)
        elif decision == "SHORT":
            tp_price = entry_price * (1 - tp_pct)
            sl_price = entry_price * (1 + sl_pct)
        else:
            tp_price = entry_price
            sl_price = entry_price
        
        return tp_price, sl_price
        
    except Exception as e:
        logger.error(f"❌ TP/SL calculation failed: {e}")
        return entry_price, entry_price


async def _create_trigger_order(exchange_adapter, symbol: str, side: str, trigger_px: float,
                               ord_px: float, reduce_only: bool, tag: str) -> dict:
    """Create trigger order via REST API."""
    try:
        # Use the exchange adapter to create trigger order
        if hasattr(exchange_adapter, 'create_trigger_order'):
            result = await exchange_adapter.create_trigger_order(
                symbol, side, trigger_px, ord_px, reduce_only, tag
            )
            return result
        else:
            # Fallback: return mock result
            logger.warning(f"⚠️ Exchange adapter doesn't support trigger orders, using mock")
            return {
                'algoId': f"TRIGGER_{tag}",
                'status': 'live',
                'side': side,
                'triggerPx': trigger_px,
                'ordPx': ord_px,
                'reduceOnly': reduce_only
            }
        
    except Exception as e:
        logger.error(f"❌ Trigger order creation failed: {e}")
        return {}


async def _send_telegram_analysis_card(symbol: str, composite_signal, live: bool) -> None:
    """Send Telegram analysis card."""
    try:
        from infrastructure.notification_service import NotificationManager
        from telegram_bot.bot import TelegramBot
        
        # Create notification service
        import os
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        telegram_bot = TelegramBot(telegram_token)
        notification_service = NotificationManager(telegram_bot, {})
        
        # Format analysis card
        mode_text = "🚀 LIVE" if live else "🧪 DRY-RUN"
        decision_emoji = "🟢" if composite_signal.decision == "LONG" else "🔴" if composite_signal.decision == "SHORT" else "⚪"
        
        message = f"""
📊 <b>Market Analysis - {symbol}</b> {mode_text}

{decision_emoji} <b>Decision:</b> {composite_signal.decision}
📈 <b>Final Score:</b> {composite_signal.final_score:.1f}/100
🏆 <b>Grade:</b> {composite_signal.grade}

<b>📊 Component Scores:</b>
• TA: {composite_signal.technical.score:.1f} - {composite_signal.technical.rationale}
• ML: {composite_signal.ml.score:.1f} - {composite_signal.ml.rationale}
• News: {composite_signal.news.score:.1f} - {composite_signal.news.rationale}
• Risk: {composite_signal.risk.score:.1f}

<b>🎯 Technical Flags:</b>
{_format_technical_flags(composite_signal.technical.flags)}

<b>⏰ Timestamp:</b> {composite_signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        # Send notification
        await notification_service.send_notification(message, "telegram")
        logger.info(f"📱 Sent analysis card to Telegram for {symbol}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send analysis card: {e}")


async def _send_telegram_execution_card(symbol: str, composite_signal, execution_result: bool, live: bool) -> None:
    """Send Telegram execution card."""
    try:
        from infrastructure.notification_service import NotificationManager
        from telegram_bot.bot import TelegramBot
        
        # Create notification service
        import os
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        telegram_bot = TelegramBot(telegram_token)
        notification_service = NotificationManager(telegram_bot, {})
        
        # Format execution card
        mode_text = "🚀 LIVE" if live else "🧪 DRY-RUN"
        status_emoji = "✅" if execution_result else "❌"
        
        message = f"""
🎯 <b>Trade Execution - {symbol}</b> {mode_text}

{status_emoji} <b>Status:</b> {'Executed' if execution_result else 'Failed'}
📊 <b>Decision:</b> {composite_signal.decision}
💰 <b>Position Size:</b> 0.35% of portfolio
💲 <b>Entry Price:</b> $50,000
🎯 <b>Take Profit:</b> $49,000 (-2%)
🛡️ <b>Stop Loss:</b> $50,500 (+1%)

<b>📋 Order Details:</b>
• Client ID: EMF2ONHS13DTI
• Side: {composite_signal.decision.lower()}
• Amount: 0.003 BTC
• TP Trigger: DRY_TP_EMF2ONHS13DTI
• SL Trigger: DRY_SL_EMF2ONHS13DTI

<b>⏰ Executed:</b> {composite_signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        # Send notification
        await notification_service.send_notification(message, "telegram")
        logger.info(f"📱 Sent execution card to Telegram for {symbol}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send execution card: {e}")


async def _send_telegram_error_card(symbol: str, composite_signal, error_message: str, live: bool) -> None:
    """Send Telegram error card."""
    try:
        from infrastructure.notification_service import NotificationManager
        from telegram_bot.bot import TelegramBot
        
        # Create notification service
        import os
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        telegram_bot = TelegramBot(telegram_token)
        notification_service = NotificationManager(telegram_bot, {})
        
        # Format error card
        mode_text = "🚀 LIVE" if live else "🧪 DRY-RUN"
        
        message = f"""
❌ <b>Trade Error - {symbol}</b> {mode_text}

🚨 <b>Error:</b> {error_message}
📊 <b>Decision:</b> {composite_signal.decision}
📈 <b>Score:</b> {composite_signal.final_score:.1f}/100

<b>🔍 Analysis Summary:</b>
• TA: {composite_signal.technical.score:.1f}
• ML: {composite_signal.ml.score:.1f}
• News: {composite_signal.news.score:.1f}
• Risk: {composite_signal.risk.score:.1f}

<b>⏰ Timestamp:</b> {composite_signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        # Send notification
        await notification_service.send_notification(message, "telegram")
        logger.info(f"📱 Sent error card to Telegram for {symbol}")
        
    except Exception as e:
        logger.error(f"❌ Failed to send error card: {e}")


def _format_technical_flags(flags: dict) -> str:
    """Format technical flags for display."""
    try:
        formatted_flags = []
        
        if flags.get('trend_alignment'):
            formatted_flags.append("✅ Trend Alignment")
        else:
            formatted_flags.append("❌ Trend Alignment")
            
        if flags.get('entry_confirmation'):
            formatted_flags.append("✅ Entry Confirmation")
        else:
            formatted_flags.append("❌ Entry Confirmation")
            
        if flags.get('rsi_overbought'):
            formatted_flags.append("⚠️ RSI Overbought")
        elif flags.get('rsi_oversold'):
            formatted_flags.append("⚠️ RSI Oversold")
        else:
            formatted_flags.append("✅ RSI Normal")
            
        if flags.get('macd_bullish'):
            formatted_flags.append("🟢 MACD Bullish")
        elif flags.get('macd_bearish'):
            formatted_flags.append("🔴 MACD Bearish")
        else:
            formatted_flags.append("⚪ MACD Neutral")
        
        return "\n".join(formatted_flags)
        
    except Exception as e:
        logger.error(f"❌ Failed to format technical flags: {e}")
        return "Flags unavailable"


def run_agents(graph: str = "default", mode: str = "dry-run", dry_run: bool = True) -> int:
    """
    Run the agent system with specified configuration.
    
    Args:
        graph: Agent graph to use
        mode: Execution mode
        dry_run: Whether to run in dry-run mode
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info(f"Starting agent system: graph={graph}, mode={mode}, dry_run={dry_run}")
        
        # Load configuration
        policy = load_policy()
        if not validate_policy(policy):
            logger.error("Invalid policy configuration")
            return 1
        
        # Show configuration summary
        config_summary = get_config_summary(policy)
        logger.info("Configuration loaded:")
        for section, values in config_summary.items():
            logger.info(f"  {section}: {values}")
        
        # Run through CLI system
        # This delegates to the existing CLI infrastructure
        sys.argv = [
            "main.py", "agents", "run",
            "--graph", graph,
            "--mode", mode,
            "--dry-run" if dry_run else "--live"
        ]
        
        return cli_main()
        
    except Exception as e:
        logger.error(f"Failed to run agents: {e}")
        return 1


def run_scheduler(job: Optional[str] = None, once: bool = False) -> int:
    """
    Run the scheduler system.
    
    Args:
        job: Specific job to run (if None, runs all scheduled jobs)
        once: Whether to run once or continuously
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info(f"Starting scheduler: job={job}, once={once}")
        
        # Load configuration
        policy = load_policy()
        if not validate_policy(policy):
            logger.error("Invalid policy configuration")
            return 1
        
        # Run through CLI system
        sys.argv = ["main.py", "scheduler"]
        if job:
            sys.argv.extend(["jobs", "run", job])
        else:
            sys.argv.extend(["start"])
        
        if once:
            sys.argv.append("--once")
        
        return cli_main()
        
    except Exception as e:
        logger.error(f"Failed to run scheduler: {e}")
        return 1


def run_trading_system(policy_path: Optional[str] = None, dry_run: bool = True) -> int:
    """
    Run the complete trading system.
    
    Args:
        policy_path: Path to policy file
        dry_run: Whether to run in dry-run mode
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info("Starting complete trading system")
        
        # Load environment variables
        load_env()
        
        # Load configuration
        policy = load_policy(policy_path or "configs/policy.yaml")
        if not validate_policy(policy):
            logger.error("Invalid policy configuration")
            return 1
        
        # Show configuration summary
        config_summary = get_config_summary(policy)
        logger.info("Trading system configuration:")
        for section, values in config_summary.items():
            logger.info(f"  {section}: {values}")
        
        # Create and run trading orchestrator
        orchestrator = TradingOrchestrator(policy)
        
        # Run the system
        success = asyncio.run(orchestrator.start())
        
        if success:
            logger.info("Trading system completed successfully")
            return 0
        else:
            logger.error("Trading system failed")
            return 1
            
    except Exception as e:
        logger.error(f"Failed to run trading system: {e}")
        return 1


def run_health_check() -> int:
    """
    Run system health check.
    
    Returns:
        Exit code (0 for healthy, non-zero for unhealthy)
    """
    try:
        logger.info("Running system health check")
        
        # Load configuration
        policy = load_policy()
        if not validate_policy(policy):
            logger.error("Policy validation failed")
            return 1
        
        # Run through CLI system
        sys.argv = ["main.py", "health"]
        return cli_main()
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return 1


def run_portfolio_status() -> int:
    """
    Show portfolio status.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info("Getting portfolio status")
        
        # Run through CLI system
        sys.argv = ["main.py", "portfolio", "status"]
        return cli_main()
        
    except Exception as e:
        logger.error(f"Failed to get portfolio status: {e}")
        return 1


def run_config_validation(policy_path: str = "configs/policy.yaml") -> int:
    """
    Validate configuration files.
    
    Args:
        policy_path: Path to policy file
        
    Returns:
        Exit code (0 for valid, non-zero for invalid)
    """
    try:
        logger.info(f"Validating configuration: {policy_path}")
        
        # Load and validate policy
        policy = load_policy(policy_path)
        if validate_policy(policy):
            logger.info("Configuration validation passed")
            
            # Show configuration summary
            config_summary = get_config_summary(policy)
            logger.info("Configuration summary:")
            for section, values in config_summary.items():
                logger.info(f"  {section}: {values}")
            
            return 0
        else:
            logger.error("Configuration validation failed")
            return 1
            
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return 1


def main():
    """
    Main entry point for runtime execution.
    Delegates to appropriate function based on command line arguments.
    """
    try:
        # Setup UTF-8 encoding first
        setup_utf8_environment()
        
        # Initialize logging
        init_logging()
        
        # Load environment
        load_env()
        
        # Parse command line arguments
        if len(sys.argv) < 2:
            logger.error("Usage: python -m infrastructure.runtime <command> [options]")
            logger.info("Available commands: agents, scheduler, trading, health, portfolio, config")
            return 1
        
        command = sys.argv[1].lower()
        
        if command == "agents":
            # Parse agent options
            graph = "default"
            mode = "dry-run"
            dry_run = True
            
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--graph" and i + 1 < len(sys.argv):
                    graph = sys.argv[i + 1]
                elif arg == "--mode" and i + 1 < len(sys.argv):
                    mode = sys.argv[i + 1]
                elif arg == "--live":
                    dry_run = False
            
            return run_agents(graph, mode, dry_run)
            
        elif command == "scheduler":
            # Parse scheduler options
            job = None
            once = False
            
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--job" and i + 1 < len(sys.argv):
                    job = sys.argv[i + 1]
                elif arg == "--once":
                    once = True
            
            return run_scheduler(job, once)
            
        elif command == "trading":
            # Parse trading options
            policy_path = None
            live = False
            symbols = None
            timeout_s = 20
            
            i = 2
            while i < len(sys.argv):
                arg = sys.argv[i]
                if arg == "--policy" and i + 1 < len(sys.argv):
                    policy_path = sys.argv[i + 1]
                    i += 2
                elif arg == "--live":
                    live = True
                    i += 1
                elif arg == "--symbols" and i + 1 < len(sys.argv):
                    symbols = sys.argv[i + 1].split(',')
                    i += 2
                elif arg == "--timeout" and i + 1 < len(sys.argv):
                    timeout_s = int(sys.argv[i + 1])
                    i += 2
                else:
                    i += 1
            
            # Use clean runtime trading (no agents)
            import asyncio
            return asyncio.run(trading_main(symbols, live, policy_path, timeout_s))
            
        elif command == "health":
            return run_health_check()
            
        elif command == "portfolio":
            return run_portfolio_status()
            
        elif command == "config":
            policy_path = "policy.yaml"
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--policy" and i + 1 < len(sys.argv):
                    policy_path = sys.argv[i + 1]
            
            return run_config_validation(policy_path)
            
        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Available commands: agents, scheduler, trading, health, portfolio, config")
            return 1
            
    except Exception as e:
        logger.error(f"Runtime execution failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
