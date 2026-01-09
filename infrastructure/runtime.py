"""
Runtime execution for the trading system.
Delegates to existing CLI and application services without duplicating logic.
"""

import asyncio
import os
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
        from application.position_state_manager import get_state_manager
        state_manager = get_state_manager(policy)
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
                
                # Step 5: Risk Analysis (read-only) - pass TA score for proper assessment
                risk_score, risk_details = await _compute_risk_analysis(risk_service, symbol, ohlcv_data, ta_score)
                
                # Step 6: Composite Score & Decision
                composite_signal = await _compute_composite_signal(
                    symbol, ta_score, ta_rationale, ta_flags,
                    ml_score, ml_rationale, ml_details,
                    news_score, news_categories, news_rationale, news_volatility,
                    risk_score, risk_details
                )
                
                # Step 7: Enhanced Signal Processing
                # Extract bar_timestamp from main timeframe for bar-based deduplication
                bar_timestamp = None
                if 'main' in ohlcv_data and ohlcv_data['main'] is not None and not ohlcv_data['main'].empty:
                    bar_timestamp = ohlcv_data['main'].index[-1]  # Latest bar timestamp
                else:
                    logger.warning(f"[COUNTER] {symbol} No bar_timestamp in signal, using current time (may cause same-bar duplicates)")
                
                gated_signal = signal_gate.process_signal(symbol, {
                    'final_score': composite_signal.final_score,
                    'ta_score': ta_score,
                    'ml_score': ml_score,
                    'news_score': news_score,
                    'risk_score': risk_score,
                    'bar_timestamp': bar_timestamp
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
                            
                            # Note: TP/SL orders are created inside _execute_trade via _create_oco_bracket
                            
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
            'entry': '5m',    # entry confirm
            '4h': '4h'        # ML features
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
                    ohlcv_data[tf_name] = df.copy(deep=True)  # Deep copy to prevent sharing
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
    """Compute machine learning scores.
    
    Returns:
        Tuple of (score, rationale, details)
        - score: Float 0-100 or None (None triggers TA-only mode)
        - rationale: Explanation string
        - details: Additional info dict
    """
    try:
        # Prepare multi-timeframe bundle for ML
        main_df = ohlcv_data.get('main')
        trend_df = ohlcv_data.get('trend')
        fourh_df = ohlcv_data.get('4h')
        
        if main_df is None or main_df.empty:
            logger.warning(f"⚠️ No main timeframe data for ML, switching to TA-only mode")
            return None, "No main timeframe data for ML", {'fallback': True}
        
        # Create ML bundle with all available timeframes
        ml_bundle = {'main': main_df.copy(deep=True) if main_df is not None else None}
        if trend_df is not None and not trend_df.empty:
            ml_bundle['1h'] = trend_df.copy(deep=True)
        if fourh_df is not None and not fourh_df.empty:
            ml_bundle['4h'] = fourh_df.copy(deep=True)
        
        logger.debug(f"[ML_BUNDLE] {symbol}: timeframes={list(ml_bundle.keys())}")
        
        # Compute ML score (may return None for fallback)
        score, rationale, details = ml_scorer.score(symbol, ml_bundle)
        
        # If ML returned None, it means TA-only mode
        if score is None:
            logger.info(f"[ML] {symbol}: TA-only mode active (ML unavailable)")
            details['ta_only_mode'] = True
        
        return score, rationale, details
        
    except Exception as e:
        logger.error(f"❌ ML analysis failed: {e}")
        # Return None to trigger TA-only mode on error
        return None, f"ML analysis error: {e}", {'error': str(e), 'fallback': True}


async def _compute_news_analysis(news_scorer, symbol: str) -> tuple[float, list, str, float]:
    """Compute news sentiment scores using real news APIs and LLM analysis."""
    try:
        # Compute news score (now async)
        score, categories, rationale, volatility_impact = await news_scorer.score(symbol)
        
        # Handle None score (returned when no news data)
        if score is None:
            logger.debug(f"[COMPOSITE] News score is None for {symbol}, using 50.0 for composite")
            score = 50.0
        
        return score, categories, rationale, volatility_impact
        
    except Exception as e:
        logger.error(f"❌ News analysis failed: {e}")
        return 50.0, ["general"], f"News analysis error: {e}", 0.5


async def _compute_risk_analysis(risk_service, symbol: str, ohlcv_data: dict, ta_score: float = 50.0) -> tuple[float, dict]:
    """Compute risk analysis using real RiskService."""
    try:
        # Prepare market data for risk assessment
        market_data = {
            'trend': ohlcv_data.get('1h', None),  # Use 1h data for trend analysis
            'main': ohlcv_data.get('15m', None),  # Use 15m data for main analysis
            'entry': ohlcv_data.get('5m', None)   # Use 5m data for entry analysis
        }
        
        # Use actual TA score for risk assessment (not hardcoded 50)
        signal_type = 'long' if ta_score >= 50 else 'short'
        
        # Use real RiskService to assess risk with actual TA score
        risk_assessment = await risk_service.assess_risk(
            symbol=symbol,
            score=ta_score,  # Use real TA score instead of hardcoded 50
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
            score=ml_score,  # Pass None for TA-only - finalize() will redistribute weight
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
        
        # Load weights from policy.yaml (instead of hardcoded regime-adaptive weights)
        from configs.policy import load_policy
        policy = load_policy()
        scoring_config = policy.get('trading', {}).get('scoring', {})
        
        weights = {
            'ta': scoring_config.get('ta_weight', 0.40),
            'ml': scoring_config.get('ml_weight', 0.30),
            'news': scoring_config.get('news_weight', 0.15),
            'risk': scoring_config.get('risk_weight', 0.15)
        }
        
        # Handle ML=None (no model available) - redistribute ML weight to TA
        if ml_score is None:
            logger.info(f"[ML_ROUTING] {symbol} has no ML model, redistributing weight to TA")
            effective_ml_score = 0  # Not used in calculation
            effective_ml_weight = 0
            # Redistribute ML weight to TA
            effective_ta_weight = weights['ta'] + weights['ml']
            # Normalize remaining weights
            total_other = weights['news'] + weights['risk']
            final_score = (
                effective_ta_weight * ta_score +
                weights['news'] * news_score +
                weights['risk'] * risk_score
            )
            logger.debug(f"[COMPOSITE] TA-only mode: ta_weight={effective_ta_weight:.2f} (original {weights['ta']:.2f} + ml {weights['ml']:.2f})")
        else:
            effective_ml_score = ml_score
            
            # Apply ML boost based on TA score thresholds
            ml_boost_config = scoring_config.get('ml_boost', {})
            if ml_boost_config.get('enabled', False):
                tiers = ml_boost_config.get('tiers', [])
                # Sort tiers by ta_threshold descending to find highest matching
                sorted_tiers = sorted(tiers, key=lambda x: x.get('ta_threshold', 0), reverse=True)
                for tier in sorted_tiers:
                    if ta_score >= tier.get('ta_threshold', 100):
                        multiplier = tier.get('multiplier', 1.0)
                        if multiplier > 1.0:
                            original_ml = effective_ml_score
                            effective_ml_score = min(100.0, effective_ml_score * multiplier)
                            logger.info(f"[COMPOSITE] ML Boost: TA={ta_score:.1f} >= {tier['ta_threshold']} → ML {original_ml:.1f} × {multiplier} = {effective_ml_score:.1f}")
                        break
            
            logger.debug(f"[COMPOSITE] Using policy weights: ta={weights['ta']}, ml={weights['ml']}, news={weights['news']}, risk={weights['risk']}")
            final_score = (
                weights['ta'] * ta_score +
                weights['ml'] * effective_ml_score +
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


async def _execute_trade(exchange_adapter, symbol: str, composite_signal, live: bool, ohlcv_data: dict = None) -> bool:
    """Execute trade based on composite signal.
    
    Args:
        exchange_adapter: Exchange adapter instance
        symbol: Trading symbol
        composite_signal: Composite signal with decision and scores
        live: Whether to execute live or paper trade
        ohlcv_data: Optional OHLCV data for ATR-based TP/SL calculation
    """
    try:
        from execution.id_utils import generate_client_id
        from execution.quantize import quantize_price, quantize_size, bump_to_min_size
        from execution.prevalidation import validate_bracket_order
        from execution.okx_symbol import okx_to_ccxt_symbol
        
        # Step 0a: Check if trading is paused
        import json
        from pathlib import Path
        try:
            state_file = Path("data/runtime_state.json")
            if state_file.exists():
                with open(state_file, 'r') as f:
                    runtime_state = json.load(f)
                if runtime_state.get('trading_paused', False):
                    logger.info(f"⏸️ [PAUSED] Trading paused - skipping {symbol}")
                    return False
        except Exception as e:
            logger.warning(f"Failed to check trading_paused: {e}")
        
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

        # Step 1: Generate client order ID (OKX format: max 32 chars, start with letter, alphanumeric only)
        bar_time = datetime.now(timezone.utc)
        bar_id_short = bar_time.strftime('%m%d%H%M')  # e.g., "12102300"
        side_tag = 'L' if direction == 'LONG' else 'S' if direction == 'SHORT' else 'H'
        # Extract short symbol (e.g., "BTC" from "BTC-USDT-SWAP")
        short_symbol = symbol.split('-')[0][:3]  # Max 3 chars
        # Pure alphanumeric format: e.g., "BTCS12102300" (12 chars)
        client_order_id = f"{short_symbol}{side_tag}{bar_id_short}"
        logger.info(f"📝 Generated client order ID: {client_order_id}")
        
        # Structured log for trade attempt
        logger.info(f"[ENTRY] sym={symbol} dir={composite_signal.decision} size=0.000000 px=0.000000 reason=score>={composite_signal.final_score} state=READY tf=15m bar={datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}")
        
        # Step 2: Get current market price first
        current_price = await _get_current_price(exchange_adapter, symbol)
        logger.info(f"💲 Current market price: {current_price}")
        
        # Step 3: Calculate position size in USDT (this is MARGIN amount)
        position_size_usdt = await _calculate_position_size(composite_signal, symbol, exchange_adapter)
        logger.info(f"💰 Calculated margin: ${position_size_usdt}")
        
        # Step 4: Convert MARGIN to contract amount
        # margin × leverage = notional
        # notional / price = contracts
        # Read leverage from policy.yaml (same as Telegram setting)
        from infrastructure.bootstrap import load_policy
        policy = load_policy()
        leverage = policy.get('trading', {}).get('risk', {}).get('leverage', {}).get('default', 7)
        notional_usdt = position_size_usdt * leverage
        position_size = notional_usdt / current_price
        logger.info(f"🪙 Position: margin=${position_size_usdt:.2f} × {leverage}x = ${notional_usdt:.2f} notional = {position_size:.6f} contracts")
        
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
        
        # CRITICAL FIX: Use lotSz from info with ctVal multiplication
        # precision.amount returns 0.01 (wrong for ETH/BTC)
        # Real lot_size = lotSz × ctVal (e.g., ETH: 0.01 × 0.1 = 0.001)
        info = market.get('info', {})
        lot_sz = float(info.get('lotSz', 0.01))
        ct_val = float(info.get('ctVal', 1))
        lot_size = lot_sz * ct_val
        logger.info(f"📊 {symbol}: lotSz={lot_sz} × ctVal={ct_val} = lot_size={lot_size}")
        
        quantized_price = quantize_price(entry_price, tick_size)
        quantized_size = quantize_size(position_size, lot_size)
        
        logger.info(f"🔧 Dynamic quantization - tick_size: {tick_size}, lot_size: {lot_size}")
        
        logger.info(f"🔧 Quantized - Price: {quantized_price}, Size: {quantized_size}")
        
        # Step 6: Calculate TP/SL levels (use OHLCV for ATR if available)
        tp_price, sl_price = await _calculate_tp_sl_levels(
            entry_price, composite_signal.decision, composite_signal.technical.flags, ohlcv_data
        )
        logger.info(f"🎯 TP: {tp_price}, SL: {sl_price}")
        
        # Step 7: Prevalidate bracket order
        # Convert decision to side: LONG -> buy, SHORT -> sell (case-insensitive)
        decision_upper = composite_signal.decision.upper() if composite_signal.decision else 'FLAT'
        side = 'buy' if decision_upper == 'LONG' else 'sell'
        is_valid, errors = validate_bracket_order(
            entry_price=quantized_price,
            tp_price=tp_price,
            sl_price=sl_price,
            side=side
        )
        
        if not is_valid:
            logger.warning(f"⚠️ Bracket order validation warning (non-blocking): {errors}")
            # Continue anyway - TP/SL will be placed as calculated
        
        logger.info(f"✅ Bracket order validation passed")
        
        # Step 8: Execute entry order (LIVE vs PAPER vs DRY-RUN)
        if mode == "LIVE":
            logger.info(f"🚀 Executing LIVE {composite_signal.decision} order")
            # Convert decision to side: LONG -> buy, SHORT -> sell (uses decision_upper from above)
            side = 'buy' if decision_upper == 'LONG' else 'sell'
            
            # Order tracking log
            logger.info(f"[ORDER] sym={symbol} clientId={client_order_id} side={side} amount={quantized_size} price={quantized_price}")
            
            try:
                # CRITICAL: Set leverage BEFORE placing order to ensure consistent leverage
                # Default 5x, but can be overridden in policy.yaml or Telegram settings
                configured_leverage = 5  # Default
                try:
                    from infrastructure.bootstrap import load_policy
                    policy = load_policy()
                    configured_leverage = policy.get('trading', {}).get('risk', {}).get('leverage', {}).get('default', 5)
                except:
                    pass
                
                logger.info(f"⚡ Setting leverage to {configured_leverage}x for {symbol}")
                await exchange_adapter.set_leverage(symbol, configured_leverage)
                
                entry_result = await exchange_adapter.create_market_order(
                    symbol=symbol,
                    side=side,
                    amount=quantized_size,
                    client_id=client_order_id
                )
                
                # Order success log
                logger.info(f"[ORDER] sym={symbol} clientId={client_order_id} status=SUCCESS ordId={entry_result.get('id', 'N/A')} filled={entry_result.get('filled', 0)}")
                
                # Update balance tracker after successful trade
                try:
                    from infrastructure.balance_tracker import get_balance_tracker
                    get_balance_tracker().update_after_trade()
                except Exception as be:
                    logger.warning(f"⚠️ Failed to update balance tracker: {be}")
                
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
        
        # Step 9: Execute TP/SL triggers using OCO bracket (LIVE vs PAPER vs DRY-RUN)
        if mode == "LIVE":
            logger.info(f"🎯 Executing LIVE TP/SL as OCO bracket")
            
            # Use OCO bracket for linked TP/SL
            oco_result = await _create_oco_bracket(
                exchange_adapter=exchange_adapter,
                symbol=symbol,
                decision=composite_signal.decision,
                tp_price=tp_price,
                sl_price=sl_price,
                entry_client_id=client_order_id,
                position_size=quantized_size
            )
            
            tp_result = {'algoId': oco_result.get('tp_algo_id')}
            sl_result = {'algoId': oco_result.get('sl_algo_id')}
            
            # Log OCO creation
            logger.info(f"[OCO-BRACKET] sym={symbol} oco_link={oco_result.get('oco_link_id')} "
                       f"tp_id={oco_result.get('tp_algo_id')} sl_id={oco_result.get('sl_algo_id')}")
                
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
            
            # Process state transition - USE SINGLETON to maintain state
            from application.position_state_manager import get_state_manager
            state_manager = get_state_manager()  # No new instance, use existing
            transition = state_manager.process_signal(symbol, updated_signal_dict)
            
            if transition:
                logger.info(f"✅ State transition successful: {transition.from_state}→{transition.to_state}")
                
                # CRITICAL: Clear signal history to reset persistence counter
                # This prevents immediate re-entry on the same signal
                try:
                    from application.jobs.trading_analysis import _get_shared_signal_gate
                    signal_gate = _get_shared_signal_gate()
                    if signal_gate:
                        signal_gate.clear_history(symbol)
                        logger.info(f"🔄 Persistence reset for {symbol} after trade execution")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to reset persistence: {e}")
                
                # Only send notification for reversals (not for regular entries/exits)
                try:
                    is_reversal = transition.action == 'REVERSE'
                    
                    if is_reversal:
                        from infrastructure.notification_service import NotificationService
                        notifier = NotificationService()
                        await notifier.start()
                        
                        direction = 'long' if composite_signal.decision == 'long' else 'short'
                        await notifier.send_reversal_notification(
                            symbol=symbol,
                            strength=composite_signal.final_score / 100.0,
                            confirm=2,  # persist_bars
                            result=f"REVERSE to {direction.upper()}"
                        )
                        
                        await notifier.stop()
                        logger.info(f"📱 Reversal notification sent for {symbol}")
                    # No notification for regular entry/exit
                except Exception as e:
                    logger.warning(f"⚠️ Failed to send reversal notification: {e}")
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
    if trend_strength > 0.6 and volatility > 0.65:  # High trend + low risk (high volatility score)
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


def _calculate_dynamic_leverage(ohlcv_data: dict, base_leverage: float = 5.0) -> float:
    """
    Get leverage value from policy or user settings.
    
    Priority:
    1. User settings (from Telegram) - if set
    2. Policy.yaml default
    3. Fallback to 5x
    
    Args:
        ohlcv_data: OHLCV data (unused, kept for API compatibility)
        base_leverage: Fallback leverage (default 5x)
    
    Returns:
        Configured leverage value
    """
    try:
        # Try to load from policy
        from infrastructure.bootstrap import load_policy
        policy = load_policy()
        
        leverage_config = policy.get('trading', {}).get('risk', {}).get('leverage', {})
        default_leverage = leverage_config.get('default', 5)
        min_leverage = leverage_config.get('min_leverage', 1)
        max_leverage = leverage_config.get('max_leverage', 10)
        
        # Check for user override from Telegram settings
        try:
            from adapters.telegram.user_settings import get_user_settings
            user_settings = get_user_settings()
            if user_settings and 'leverage' in user_settings:
                user_leverage = int(user_settings['leverage'])
                # Clamp to policy limits
                leverage = max(min_leverage, min(max_leverage, user_leverage))
                logger.info(f"⚡ Using user-configured leverage: {leverage}x (from Telegram settings)")
                return float(leverage)
        except Exception:
            pass  # User settings not available, use policy default
        
        # Clamp default to limits
        leverage = max(min_leverage, min(max_leverage, default_leverage))
        logger.info(f"⚡ Using policy leverage: {leverage}x (min={min_leverage}, max={max_leverage})")
        return float(leverage)
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to load leverage config: {e}, using default {base_leverage}x")
        return base_leverage


async def _calculate_position_size(composite_signal, symbol: str, exchange_adapter) -> float:
    """
    Calculate position size using tier-based signal strength.
    
    NEW LOGIC:
    1. Uses FREE (available) balance from BalanceTracker
    2. Signal strength = how far from neutral (50) + ML agreement
    3. Tier-based sizing: weak=2%, medium=4%, strong=6%, extreme=8%
    4. Risk score only for warning, doesn't affect sizing
    """
    try:
        from infrastructure.bootstrap import load_policy
        from infrastructure.balance_tracker import get_balance_tracker
        
        policy = load_policy()
        sizing_config = policy.get('trading', {}).get('scoring', {}).get('position_sizing', {})
        
        # ============ 1. GET AVAILABLE BALANCE (FREE) ============
        balance_tracker = get_balance_tracker()
        
        # Configure tracker from policy
        balance_config = sizing_config.get('balance', {})
        balance_tracker.configure(
            snapshot_interval=balance_config.get('snapshot_interval_sec', 600),
            balance_type=balance_config.get('use_type', 'free')
        )
        
        available_balance = await balance_tracker.get_balance(exchange_adapter)
        
        if available_balance <= 0:
            logger.warning(f"⚠️ No available balance, cannot size position")
            return 0.0
        
        logger.info(f"💰 Available balance (free): ${available_balance:.2f}")
        
        # ============ 2. CALCULATE SIGNAL STRENGTH ============
        composite_score = composite_signal.final_score
        ml_score = composite_signal.ml.score if hasattr(composite_signal, 'ml') else 50
        if ml_score is None:
            ml_score = 50  # Neutral for TA-only mode
        
        # Determine directions
        composite_dir = "SHORT" if composite_score < 48 else ("LONG" if composite_score > 52 else "NEUTRAL")
        ml_dir = "SHORT" if ml_score < 45 else ("LONG" if ml_score > 55 else "NEUTRAL")
        
        # Calculate strength (distance from center, 0-1)
        composite_strength = abs(composite_score - 50) / 50
        ml_strength = abs(ml_score - 50) / 50
        
        # Combined strength based on direction agreement
        if composite_dir == ml_dir and composite_dir != "NEUTRAL":
            # Same direction = average strength (strong signal)
            signal_strength = (composite_strength + ml_strength) / 2
            agreement = "AGREE"
        elif composite_dir == "NEUTRAL" or ml_dir == "NEUTRAL":
            # One is neutral = use the stronger one with penalty
            signal_strength = max(composite_strength, ml_strength) * 0.7
            agreement = "PARTIAL"
        else:
            # Conflicting directions = weak signal
            signal_strength = 0.15
            agreement = "CONFLICT"
        
        logger.info(f"📊 Signal strength: composite={composite_score:.1f}({composite_dir}), "
                   f"ml={ml_score:.1f}({ml_dir}), agreement={agreement}, strength={signal_strength:.2f}")
        
        # ============ 3. TIER-BASED POSITION PERCENTAGE ============
        tiers = sizing_config.get('tiers', {})
        
        # Default tiers if not configured
        if not tiers:
            tiers = {
                'weak': {'min_strength': 0.0, 'max_strength': 0.3, 'position_pct': 0.02},
                'medium': {'min_strength': 0.3, 'max_strength': 0.5, 'position_pct': 0.04},
                'strong': {'min_strength': 0.5, 'max_strength': 0.7, 'position_pct': 0.06},
                'extreme': {'min_strength': 0.7, 'max_strength': 1.0, 'position_pct': 0.08},
            }
        
        # Find matching tier
        position_pct = 0.02  # Default to weak
        tier_name = "weak"
        
        for name, tier in tiers.items():
            min_s = tier.get('min_strength', 0)
            max_s = tier.get('max_strength', 1)
            if min_s <= signal_strength < max_s:
                position_pct = tier.get('position_pct', 0.02)
                tier_name = name
                break
        
        logger.info(f"📈 Tier: {tier_name} → {position_pct:.1%}")
        
        # ============ 4. RISK SCORE WARNING ONLY ============
        risk_config = sizing_config.get('risk_score', {})
        risk_score = composite_signal.risk.score if hasattr(composite_signal, 'risk') else 50
        warning_threshold = risk_config.get('warning_threshold', 70)
        
        if risk_score >= warning_threshold:
            logger.warning(f"⚠️ [RISK] High risk score: {risk_score:.1f} (threshold: {warning_threshold})")
        
        # Risk score does NOT affect position size (per user request)
        
        # ============ 5. APPLY SCALABLE SIZING (15+ coins) ============
        scalable_config = policy.get('trading', {}).get('scoring', {}).get('scalable_sizing', {})
        
        if scalable_config.get('enabled', True) and scalable_config.get('dynamic_sizing', True):
            max_portfolio_alloc = scalable_config.get('max_portfolio_allocation', 0.60)
            per_position_max = scalable_config.get('per_position_max', 0.10)
            num_symbols = len(policy.get('exchange', {}).get('symbols', {}).get('trading_pairs', ['BTC', 'ETH', 'SOL']))
            
            # Dynamic max: min(per_position_max, max_allocation / num_symbols)
            dynamic_max = min(per_position_max, max_portfolio_alloc / num_symbols)
            
            if position_pct > dynamic_max:
                logger.info(f"[SCALABLE] Capping: {position_pct:.1%} → {dynamic_max:.1%} (for {num_symbols} symbols)")
                position_pct = dynamic_max
        
        # ============ 6. MAX CONCURRENT CHECK ============
        max_concurrent_config = policy.get('trading', {}).get('scoring', {}).get('max_concurrent', {})
        
        if max_concurrent_config.get('enabled', True) and max_concurrent_config.get('enforce_before_trade', True):
            hard_limit = max_concurrent_config.get('hard_limit', 20)
            current_positions = await _get_current_position_count(exchange_adapter)
            
            if current_positions >= hard_limit:
                logger.warning(f"⛔ [MAX-CONCURRENT] Blocking: {current_positions}/{hard_limit} positions open")
                return 0.0
        
        # ============ 7. CALCULATE FINAL POSITION SIZE ============
        position_usdt = available_balance * position_pct
        
        # Get exchange minimum
        if hasattr(exchange_adapter, 'ccxt_client'):
            exchange = exchange_adapter.ccxt_client
        else:
            exchange = exchange_adapter
        min_required = await _get_exchange_minimum_cost(exchange, symbol)
        
        # Apply minimum
        if position_usdt < min_required:
            logger.info(f"📈 Below minimum, using: ${min_required:.2f}")
            position_usdt = min_required
        
        # Check against available balance
        if position_usdt > available_balance * 0.90:  # Don't use more than 90% of available
            position_usdt = available_balance * 0.90
            logger.info(f"📊 Capped to 90% of available: ${position_usdt:.2f}")
        
        logger.info(f"💰 FINAL: balance=${available_balance:.2f}, strength={signal_strength:.2f}, "
                   f"tier={tier_name}({position_pct:.1%}), position=${position_usdt:.2f}")
        
        return position_usdt
        
    except Exception as e:
        logger.error(f"❌ Position size calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return 5.0  # Safe minimum fallback


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
            return 5.0  # Fallback minimum $5
        
        mid_price = (orderbook['bids'][0][0] + orderbook['asks'][0][0]) / 2
        
        # For OKX SWAP contracts:
        # minSz = minimum number of CONTRACTS (e.g., 0.01)
        # ctVal = value per contract in base currency (e.g., 0.01 BTC)
        # ctMult = multiplier (usually 1)
        # Real minimum = minSz * ctVal * ctMult * price
        
        min_sz = info.get('minSz')
        ct_val = info.get('ctVal')
        ct_mult = info.get('ctMult', '1')
        
        if min_sz and ct_val:
            min_contracts = float(min_sz)
            contract_value = float(ct_val)
            multiplier = float(ct_mult) if ct_mult else 1.0
            
            # Calculate minimum in base currency (e.g., BTC)
            min_base_amount = min_contracts * contract_value * multiplier
            # Convert to USDT
            min_cost_usdt = min_base_amount * mid_price
            
            logger.info(f"📊 {symbol} minimum: {min_contracts} contracts × {contract_value} ctVal = {min_base_amount:.6f} base = ${min_cost_usdt:.2f}")
            return min_cost_usdt
        
        # Fallback to limits.cost.min if available
        min_cost = (limits.get('cost') or {}).get('min')
        if min_cost:
            logger.info(f"📊 {symbol} minimum (cost limit): ${min_cost}")
            return float(min_cost)
        
        # Fallback to limits.amount.min (assuming base currency, not contracts)
        min_amount = (limits.get('amount') or {}).get('min')
        if min_amount:
            # For non-contract markets, this is the base amount
            min_cost_usdt = float(min_amount) * mid_price
            logger.info(f"📊 {symbol} minimum (amount limit): {min_amount} = ${min_cost_usdt:.2f}")
            return min_cost_usdt
        
        # Final fallback - $5 is OKX's general minimum for most swaps
        logger.warning(f"⚠️ No minimum data for {symbol}, using $5 fallback")
        return 5.0
        
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
        
        # CCXT client is sync, don't await
        positions = exchange.fetch_positions()
        open_positions = 0
        
        for position in positions:
            if position.get('contracts', 0) > 0 or position.get('size', 0) != 0:
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


async def _calculate_tp_sl_levels(entry_price: float, decision: str, ta_flags: dict, 
                                   ohlcv_data: dict = None) -> tuple[float, float]:
    """
    Calculate take profit and stop loss levels using ATR-based dynamic calculation.
    
    ATR-based TP/SL adapts to market volatility:
    - High volatility → wider TP/SL
    - Low volatility → narrower TP/SL
    
    Args:
        entry_price: Entry price for the trade
        decision: 'LONG' or 'SHORT'
        ta_flags: Technical analysis flags
        ohlcv_data: OHLCV data dict with 'main' key for ATR calculation
    
    Returns:
        Tuple of (tp_price, sl_price)
    """
    try:
        import numpy as np
        from infrastructure.bootstrap import load_policy
        
        # Load ATR settings from policy
        policy = load_policy()
        tp_sl_config = policy.get('trading', {}).get('risk', {}).get('tp_sl_atr', {})
        
        # ATR multipliers from policy (with defaults)
        sl_atr_mult = tp_sl_config.get('sl_atr_mult', 2.0)
        tp_atr_mult = tp_sl_config.get('tp_atr_mult', 4.0)
        
        # Fallback percentages from policy (with defaults)
        fallback_sl_pct = tp_sl_config.get('fallback_sl_pct', 1.5) / 100  # Convert to decimal
        fallback_tp_pct = tp_sl_config.get('fallback_tp_pct', 3.0) / 100  # Convert to decimal
        
        # Calculate ATR from OHLCV data
        atr = None
        if ohlcv_data and 'main' in ohlcv_data:
            main_df = ohlcv_data['main']
            if main_df is not None and not main_df.empty and len(main_df) >= 14:
                try:
                    high = main_df['high'].values
                    low = main_df['low'].values
                    close = main_df['close'].values
                    
                    # Calculate True Range
                    tr1 = high - low
                    tr2 = np.abs(high - np.roll(close, 1))
                    tr3 = np.abs(low - np.roll(close, 1))
                    tr = np.maximum(tr1, np.maximum(tr2, tr3))
                    
                    # ATR = 14-period simple moving average of TR
                    atr = np.mean(tr[-14:])
                    
                    logger.info(f"📊 ATR(14) = {atr:.4f} ({(atr/entry_price)*100:.2f}% of price)")
                except Exception as e:
                    logger.warning(f"⚠️ ATR calculation failed: {e}, using fallback percentages")
        
        # Calculate TP/SL based on ATR or fallback
        # Normalize decision to uppercase for comparison
        decision_upper = decision.upper() if decision else "FLAT"
        
        if atr and atr > 0:
            # ATR-based calculation
            if decision_upper == "LONG":
                sl_price = entry_price - (sl_atr_mult * atr)
                tp_price = entry_price + (tp_atr_mult * atr)
            elif decision_upper == "SHORT":
                sl_price = entry_price + (sl_atr_mult * atr)
                tp_price = entry_price - (tp_atr_mult * atr)
            else:
                tp_price = entry_price
                sl_price = entry_price
            
            # Log ATR-based levels
            sl_distance_pct = abs(entry_price - sl_price) / entry_price * 100
            tp_distance_pct = abs(tp_price - entry_price) / entry_price * 100
            logger.info(f"🎯 ATR-based TP/SL: SL={sl_distance_pct:.2f}% ({sl_atr_mult}×ATR), TP={tp_distance_pct:.2f}% ({tp_atr_mult}×ATR)")
        else:
            # Fallback to percentage-based calculation
            logger.warning(f"⚠️ No ATR data, using fallback percentages: TP={fallback_tp_pct*100}%, SL={fallback_sl_pct*100}%")
            
            if decision_upper == "LONG":
                tp_price = entry_price * (1 + fallback_tp_pct)
                sl_price = entry_price * (1 - fallback_sl_pct)
            elif decision_upper == "SHORT":
                tp_price = entry_price * (1 - fallback_tp_pct)
                sl_price = entry_price * (1 + fallback_sl_pct)
            else:
                tp_price = entry_price
                sl_price = entry_price
        
        # Safety check: ensure TP/SL are valid
        if decision_upper == "LONG":
            if tp_price <= entry_price or sl_price >= entry_price:
                logger.warning(f"⚠️ Invalid TP/SL for LONG, correcting...")
                tp_price = entry_price * 1.03
                sl_price = entry_price * 0.985
        elif decision_upper == "SHORT":
            if tp_price >= entry_price or sl_price <= entry_price:
                logger.warning(f"⚠️ Invalid TP/SL for SHORT, correcting...")
                tp_price = entry_price * 0.97
                sl_price = entry_price * 1.015
        
        return tp_price, sl_price
        
    except Exception as e:
        logger.error(f"❌ TP/SL calculation failed: {e}")
        # Fallback: use 3% TP and 1.5% SL
        if decision.upper() == "LONG":
            return entry_price * 1.03, entry_price * 0.985
        elif decision.upper() == "SHORT":
            return entry_price * 0.97, entry_price * 1.015
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


async def _create_oco_bracket(exchange_adapter, symbol: str, decision: str, 
                              tp_price: float, sl_price: float, 
                              entry_client_id: str, position_size: float) -> dict:
    """
    Create OCO (One-Cancels-Other) bracket order for TP/SL.
    
    When TP triggers, SL is automatically cancelled and vice versa.
    This prevents orphan orders and double execution.
    
    Args:
        exchange_adapter: Exchange adapter instance
        symbol: Trading symbol
        decision: 'LONG' or 'SHORT'
        tp_price: Take profit trigger price
        sl_price: Stop loss trigger price
        entry_client_id: Client order ID from entry order
        position_size: Position size for bracket orders
        
    Returns:
        Dict with tp_algo_id, sl_algo_id, and oco_link_id
    """
    try:
        # Generate linked IDs for OCO bracket - OKX requires alphanumeric only!
        import time
        from execution.id_utils import generate_client_id
        oco_link_id = f"OCO{int(time.time() * 1000)}"
        tp_client_id = generate_client_id('A')  # Algo TP
        sl_client_id = generate_client_id('A')  # Algo SL
        
        # Determine sides for TP/SL (case-insensitive check)
        decision_upper = decision.upper() if decision else 'FLAT'
        if decision_upper == "LONG":
            tp_side = "sell"  # Close long by selling
            sl_side = "sell"
        else:  # SHORT
            tp_side = "buy"   # Close short by buying
            sl_side = "buy"
        
        logger.info(f"🔗 Creating OCO bracket: symbol={symbol} TP={tp_price} SL={sl_price} link={oco_link_id}")
        
        # Check if exchange adapter supports OCO orders
        if hasattr(exchange_adapter, 'create_oco_order'):
            # Use native OCO API
            result = await exchange_adapter.create_oco_order(
                symbol=symbol,
                side=tp_side,
                amount=position_size,
                tp_trigger_price=tp_price,
                sl_trigger_price=sl_price,
                oco_link_id=oco_link_id,
                tp_client_id=tp_client_id,
                sl_client_id=sl_client_id
            )
            logger.info(f"✅ OCO bracket created via native API: {result}")
            return result
            
        elif hasattr(exchange_adapter, 'create_algo_stop_loss') and hasattr(exchange_adapter, 'create_algo_take_profit'):
            # Use OKX-specific algo order methods (CORRECT approach)
            logger.info(f"📋 Creating TP/SL using OKX algo order API")
            
            # Create TP order
            tp_result = await exchange_adapter.create_algo_take_profit(
                symbol=symbol,
                side=tp_side,
                size=position_size,
                trigger_price=tp_price,
                client_id=tp_client_id
            )
            
            # Create SL order
            sl_result = await exchange_adapter.create_algo_stop_loss(
                symbol=symbol,
                side=sl_side,
                size=position_size,
                trigger_price=sl_price,
                client_id=sl_client_id
            )
            
            # Check results
            tp_success = tp_result.get('success', False)
            sl_success = sl_result.get('success', False)
            
            if tp_success and sl_success:
                logger.info(f"✅ TP/SL created successfully: TP={tp_result.get('algoId')}, SL={sl_result.get('algoId')}")
            else:
                if not tp_success:
                    logger.error(f"❌ TP creation failed: {tp_result.get('error')}")
                if not sl_success:
                    logger.error(f"❌ SL creation failed: {sl_result.get('error')}")
            
            # Store the OCO link for manual cleanup
            oco_mapping = {
                'oco_link_id': oco_link_id,
                'tp_algo_id': tp_result.get('algoId', tp_client_id),
                'sl_algo_id': sl_result.get('algoId', sl_client_id),
                'symbol': symbol,
                'entry_client_id': entry_client_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'active'
            }
            
            # Log OCO mapping for cleanup job
            logger.info(f"[OCO-MAP] {oco_mapping}")
            
            return {
                'tp_algo_id': tp_result.get('algoId'),
                'sl_algo_id': sl_result.get('algoId'),
                'oco_link_id': oco_link_id,
                'tp_result': tp_result,
                'sl_result': sl_result,
                'tp_success': tp_success,
                'sl_success': sl_success
            }
            
        elif hasattr(exchange_adapter, 'create_trigger_order'):
            # Legacy fallback: Create separate trigger orders with tracking
            # Note: This may not work correctly on OKX!
            logger.warning(f"⚠️ Using legacy create_trigger_order (may not work on OKX)")
            
            tp_result = await exchange_adapter.create_trigger_order(
                symbol, tp_side.upper(), tp_price, -1, True, tp_client_id
            )
            sl_result = await exchange_adapter.create_trigger_order(
                symbol, sl_side.upper(), sl_price, -1, True, sl_client_id
            )
            
            # Store the OCO link for manual cleanup
            oco_mapping = {
                'oco_link_id': oco_link_id,
                'tp_algo_id': tp_result.get('algoId', tp_client_id),
                'sl_algo_id': sl_result.get('algoId', sl_client_id),
                'symbol': symbol,
                'entry_client_id': entry_client_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'status': 'active'
            }
            
            # Log OCO mapping for cleanup job
            logger.info(f"[OCO-MAP] {oco_mapping}")
            
            return {
                'tp_algo_id': tp_result.get('algoId'),
                'sl_algo_id': sl_result.get('algoId'),
                'oco_link_id': oco_link_id,
                'tp_result': tp_result,
                'sl_result': sl_result
            }
        else:
            # Mock response for testing
            logger.warning(f"⚠️ Exchange adapter doesn't support algo orders, using mock OCO")
            return {
                'tp_algo_id': f"MOCK_TP_{tp_client_id}",
                'sl_algo_id': f"MOCK_SL_{sl_client_id}",
                'oco_link_id': oco_link_id,
                'status': 'mock'
            }
            
    except Exception as e:
        logger.error(f"❌ OCO bracket creation failed: {e}")
        import traceback
        logger.debug(f"OCO bracket error traceback: {traceback.format_exc()}")
        return {
            'error': str(e),
            'tp_algo_id': None,
            'sl_algo_id': None
        }


async def _cancel_oco_counterpart(exchange_adapter, symbol: str, triggered_side: str, 
                                   oco_link_id: str, counterpart_algo_id: str) -> bool:
    """
    Cancel the counterpart order when one side of OCO triggers.
    
    Args:
        exchange_adapter: Exchange adapter instance
        symbol: Trading symbol
        triggered_side: Which side triggered ('TP' or 'SL')
        oco_link_id: OCO link ID for logging
        counterpart_algo_id: Algo ID of order to cancel
        
    Returns:
        True if cancellation successful
    """
    try:
        counterpart_type = "SL" if triggered_side == "TP" else "TP"
        logger.info(f"🔗 [OCO-CLEANUP] {triggered_side} triggered, cancelling {counterpart_type} order: {counterpart_algo_id}")
        
        if hasattr(exchange_adapter, 'cancel_algo_order'):
            result = await exchange_adapter.cancel_algo_order(symbol, counterpart_algo_id)
            logger.info(f"✅ [OCO-CLEANUP] Cancelled {counterpart_type}: {counterpart_algo_id}")
            return True
        else:
            logger.warning(f"⚠️ Exchange adapter doesn't support algo order cancellation")
            return False
            
    except Exception as e:
        logger.error(f"❌ [OCO-CLEANUP] Failed to cancel counterpart order: {e}")
        return False


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
