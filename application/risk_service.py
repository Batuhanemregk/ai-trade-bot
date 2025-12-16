"""
Risk Service - Real risk management with market analysis
Enhanced with log deduplication to reduce spam.
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from loguru import logger

from application.log_dedup_service import get_log_dedup_service


class RiskService:
    """Real risk service with comprehensive risk assessment."""
    
    def __init__(self, policy: Dict[str, Any] = None):
        self.policy = policy or {}
        self._volatility_cache = {}
        self._correlation_cache = {}
        self._log_dedup = get_log_dedup_service()
    
    async def assess_risk(self, symbol: str, score: float, signal_type: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess comprehensive risk for a trading decision."""
        try:
            # Calculate various risk metrics
            volatility_risk = await self._calculate_volatility_risk(symbol, market_data)
            liquidity_risk = await self._calculate_liquidity_risk(symbol, market_data)
            correlation_risk = await self._calculate_correlation_risk(symbol, market_data)
            score_risk = self._calculate_score_risk(score, signal_type)
            market_risk = self._calculate_market_risk(market_data)
            
            # Combine risk metrics
            total_risk = self._combine_risk_metrics({
                'volatility': volatility_risk,
                'liquidity': liquidity_risk,
                'correlation': correlation_risk,
                'score': score_risk,
                'market': market_risk
            })
            
            # Determine risk level and recommendation
            risk_level = self._get_risk_level(total_risk)
            recommendation = self._get_recommendation(total_risk, risk_level)
            
            result = {
                'risk_score': total_risk,
                'risk_level': risk_level,
                'recommendation': recommendation,
                'risk_breakdown': {
                    'volatility_risk': volatility_risk,
                    'liquidity_risk': liquidity_risk,
                    'correlation_risk': correlation_risk,
                    'score_risk': score_risk,
                    'market_risk': market_risk
                },
                'risk_factors': self._identify_risk_factors({
                    'volatility': volatility_risk,
                    'liquidity': liquidity_risk,
                    'correlation': correlation_risk,
                    'score': score_risk,
                    'market': market_risk
                })
            }
            
            logger.debug(f"Risk assessment for {symbol}: {risk_level} ({total_risk:.1f}) - {recommendation}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to assess risk for {symbol}: {e}")
            return {
                'risk_score': 100.0,  # High risk on error
                'risk_level': 'high',
                'recommendation': 'reject',
                'risk_breakdown': {},
                'risk_factors': ['assessment_error']
            }
    
    async def _calculate_volatility_risk(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Calculate volatility-based risk with symbol-specific thresholds from policy."""
        try:
            # Cache disabled to allow dynamic volatility-based risk
            # if symbol in self._volatility_cache:
            #     return self._volatility_cache[symbol]
            
            # Policy'den volatility risk konfigürasyonunu al
            risk_config = self.policy.get('trading', {}).get('risk', {}).get('risk_assessment', {}).get('volatility_risk', {})
            
            if not risk_config:
                key = "risk:no_volatility_config"
                should_log, is_first = self._log_dedup.should_log(key)
                if should_log:
                    suffix = " (first occurrence)" if is_first else ""
                    logger.info(f"No volatility risk config in policy, using defaults{suffix}")
                return 50.0
            
            # Policy'den volatility threshold'ları al
            volatility_thresholds = risk_config.get('volatility_thresholds', {})
            default_unknown = risk_config.get('default_unknown', 0.40)
            
            if not volatility_thresholds:
                key = "risk:no_volatility_thresholds"
                should_log, is_first = self._log_dedup.should_log(key)
                if should_log:
                    suffix = " (first occurrence)" if is_first else ""
                    logger.info(f"No volatility thresholds in policy, using defaults{suffix}")
                return 50.0
            
            # Get price data for volatility calculation
            if 'trend' in market_data and market_data['trend'] is not None and hasattr(market_data['trend'], 'empty') and not market_data['trend'].empty:
                prices = market_data['trend']['close'].values
                
                if len(prices) < 20:
                    logger.warning(f"[RISK_SCORE] {symbol} insufficient data (n={len(prices)}), returning None")
                    return None  # Skip instead of default
                
                # Calculate returns
                returns = np.diff(np.log(prices))
                
                # Calculate volatility (annualized)
                volatility = np.std(returns) * np.sqrt(365 * 24)  # Assuming hourly data
                
                # Symbol'ü temizle (BTC-USDT-SWAP → BTC)
                base_symbol = symbol.split('-')[0]
                
                # Symbol-specific threshold'ları bul
                thresholds = None
                if base_symbol in volatility_thresholds:
                    thresholds = volatility_thresholds[base_symbol]
                else:
                    # Tier-based fallback
                    for tier_key, tier_thresholds in volatility_thresholds.items():
                        if tier_key.startswith('tier_'):
                            thresholds = tier_thresholds
                            break
                
                if not thresholds:
                    key = f"risk:no_vol_thresholds:{symbol}"
                    should_log, is_first = self._log_dedup.should_log(key)
                    if should_log:
                        suffix = " (first occurrence)" if is_first else ""
                        logger.info(f"No thresholds found for {symbol}, using default{suffix}")
                    return None  # Skip instead of default
                
                # Dynamic volatility-based risk calculation
                # Map volatility directly to risk score with non-linear scaling
                low_threshold = thresholds.get('low', 0.25)
                medium_threshold = thresholds.get('medium', 0.45)
                high_threshold = thresholds.get('high', 0.65)
                
                # Non-linear mapping for better risk differentiation
                if volatility < low_threshold:
                    # Low vol: 20-40 risk
                    risk = 20.0 + (volatility / low_threshold) * 20.0
                elif volatility < medium_threshold:
                    # Medium vol: 40-60 risk
                    vol_range = medium_threshold - low_threshold
                    risk = 40.0 + ((volatility - low_threshold) / vol_range) * 20.0
                elif volatility < high_threshold:
                    # High vol: 60-80 risk
                    vol_range = high_threshold - medium_threshold
                    risk = 60.0 + ((volatility - medium_threshold) / vol_range) * 20.0
                else:
                    # Very high vol: 80-100 risk with cap
                    risk = 80.0 + min(20.0, (volatility - high_threshold) * 50.0)
                
                # Remove cache to allow dynamic updates
                # Cache caused flat scores (same volatility → same cached risk)
                # self._volatility_cache[symbol] = risk
                
                logger.info(f"[RISK_SCORE] {symbol} volatility={volatility:.3f} (thresholds: {thresholds}) → risk={risk:.1f}")
                return risk
            else:
                key = f"risk:no_price_volatility:{symbol}"
                should_log, is_first = self._log_dedup.should_log(key)
                if should_log:
                    suffix = " (first occurrence)" if is_first else ""
                    logger.info(f"No price data for {symbol}, using default{suffix}")
                return 50.0
                
        except Exception as e:
            logger.warning(f"Failed to calculate volatility risk for {symbol}: {e}")
            return 50.0
    
    async def _calculate_liquidity_risk(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Calculate liquidity-based risk with symbol-specific thresholds from policy."""
        try:
            # Policy'den liquidity risk konfigürasyonunu al
            risk_config = self.policy.get('trading', {}).get('risk', {}).get('risk_assessment', {}).get('liquidity_risk', {})
            
            if not risk_config:
                logger.warning("No liquidity risk config in policy, using defaults")
                return 50.0
            
            # Policy'den volume threshold'ları al
            volume_thresholds = risk_config.get('volume_thresholds', {})
            default_unknown = risk_config.get('default_unknown', 50.0)
            
            if not volume_thresholds:
                logger.warning("No volume thresholds in policy, using defaults")
                return 50.0
            
            # Get volume data
            if 'trend' in market_data and market_data['trend'] is not None and hasattr(market_data['trend'], 'empty') and not market_data['trend'].empty:
                volumes = market_data['trend']['volume'].values
                recent_volume = np.mean(volumes[-10:])  # Average of last 10 periods
                
                # Symbol'ü temizle (BTC-USDT-SWAP → BTC)
                base_symbol = symbol.split('-')[0]
                
                # Symbol-specific threshold'ları bul
                thresholds = None
                if base_symbol in volume_thresholds:
                    thresholds = volume_thresholds[base_symbol]
                else:
                    # Tier-based fallback
                    for tier_key, tier_thresholds in volume_thresholds.items():
                        if tier_key.startswith('tier_'):
                            thresholds = tier_thresholds
                            break
                
                if not thresholds:
                    key = f"risk:no_thresholds:{symbol}"
                    should_log, is_first = self._log_dedup.should_log(key)
                    if should_log:
                        suffix = " (first occurrence)" if is_first else ""
                        logger.info(f"No thresholds found for {symbol}, using default{suffix}")
                    return default_unknown
                
                # Calculate volume-based risk
                high_threshold = thresholds.get('high', 1000000)
                medium_threshold = thresholds.get('medium', 100000)
                low_threshold = thresholds.get('low', 10000)
                
                if recent_volume > high_threshold:
                    risk = 20.0  # High volume = low risk
                elif recent_volume > medium_threshold:
                    risk = 40.0  # Medium volume = medium risk
                elif recent_volume > low_threshold:
                    risk = 70.0  # Low volume = high risk
                else:
                    risk = 90.0  # Very low volume = very high risk
                
                logger.debug(f"Liquidity risk for {symbol}: {risk} (volume: {recent_volume:.0f}, thresholds: {thresholds})")
                return risk
            else:
                key = f"risk:no_volume:{symbol}"
                should_log, is_first = self._log_dedup.should_log(key)
                if should_log:
                    suffix = " (first occurrence)" if is_first else ""
                    logger.info(f"No volume data for {symbol}, using default{suffix}")
                return default_unknown
                
        except Exception as e:
            logger.warning(f"Failed to calculate liquidity risk for {symbol}: {e}")
            return 50.0
    
    async def _calculate_correlation_risk(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Calculate correlation-based risk using CoinRegistry for tier lookups."""
        try:
            # Use CoinRegistry for tier-based correlation risk
            from application.coin_registry import get_coin_registry
            registry = get_coin_registry()
            
            # Get correlation risk from registry (based on tier)
            risk_value = registry.get_correlation_risk(symbol)
            tier = registry.get_tier(symbol)
            
            logger.debug(f"[RISK] {symbol} correlation_risk={risk_value} (tier={tier})")
            return risk_value
            
        except Exception as e:
            logger.warning(f"Failed to calculate correlation risk for {symbol}: {e}")
            return 60.0  # Conservative default
    
    def _calculate_score_risk(self, score: float, signal_type: str) -> float:
        """Calculate risk based on signal score with policy-based thresholds."""
        try:
            # Policy'den score risk konfigürasyonunu al
            risk_config = self.policy.get('trading', {}).get('risk', {}).get('risk_assessment', {}).get('score_risk', {})
            
            if not risk_config:
                key = "risk:no_score_config"
                should_log, is_first = self._log_dedup.should_log(key)
                if should_log:
                    suffix = " (first occurrence)" if is_first else ""
                    logger.info(f"No score risk config in policy, using defaults{suffix}")
                return 50.0
            
            # Policy'den threshold'ları al
            long_thresholds = risk_config.get('long_thresholds', {})
            short_thresholds = risk_config.get('short_thresholds', {})
            risk_levels = risk_config.get('risk_levels', {})
            
            if not long_thresholds or not short_thresholds or not risk_levels:
                logger.warning("Incomplete score risk config in policy, using defaults")
                return 50.0
            
            # Score-based risk assessment
            if signal_type == 'long':
                strong_threshold = long_thresholds.get('strong', 80.0)
                medium_threshold = long_thresholds.get('medium', 60.0)
                weak_threshold = long_thresholds.get('weak', 50.0)
                
                if score >= strong_threshold:
                    risk = risk_levels.get('strong', 20.0)
                elif score >= medium_threshold:
                    risk = risk_levels.get('medium', 40.0)
                elif score >= weak_threshold:
                    risk = risk_levels.get('weak', 60.0)
                else:
                    risk = risk_levels.get('very_weak', 80.0)
            else:  # short
                strong_threshold = short_thresholds.get('strong', 20.0)
                medium_threshold = short_thresholds.get('medium', 40.0)
                weak_threshold = short_thresholds.get('weak', 50.0)
                
                if score <= strong_threshold:
                    risk = risk_levels.get('strong', 20.0)
                elif score <= medium_threshold:
                    risk = risk_levels.get('medium', 40.0)
                elif score <= weak_threshold:
                    risk = risk_levels.get('weak', 60.0)
                else:
                    risk = risk_levels.get('very_weak', 80.0)
            
            logger.debug(f"Score risk for {signal_type} signal (score: {score}): {risk}")
            return risk
            
        except Exception as e:
            logger.warning(f"Failed to calculate score risk: {e}")
            return 50.0
    
    def _calculate_market_risk(self, market_data: Dict[str, Any]) -> float:
        """Calculate overall market risk with policy-based parameters."""
        try:
            # Policy'den market risk konfigürasyonunu al
            risk_config = self.policy.get('trading', {}).get('risk', {}).get('risk_assessment', {}).get('market_risk', {})
            
            if not risk_config:
                key = "risk:no_market_config"
                should_log, is_first = self._log_dedup.should_log(key)
                if should_log:
                    suffix = " (first occurrence)" if is_first else ""
                    logger.info(f"No market risk config in policy, using defaults{suffix}")
                return 40.0
            
            # Policy'den parametreleri al
            base_risk = risk_config.get('base_risk', 30.0)
            volatility_penalty = risk_config.get('volatility_penalty', 20.0)
            trend_bonus = risk_config.get('trend_bonus', 10.0)
            extreme_change_threshold = risk_config.get('extreme_change_threshold', 0.2)
            strong_trend_threshold = risk_config.get('strong_trend_threshold', 0.1)
            min_risk = risk_config.get('min_risk', 10.0)
            max_risk = risk_config.get('max_risk', 90.0)
            
            # Analyze market conditions
            market_risk = base_risk
            recent_change = 0.0
            trend_strength = 0.0
            
            # Add market-specific risk factors
            if 'trend' in market_data and market_data['trend'] is not None and hasattr(market_data['trend'], 'empty') and not market_data['trend'].empty:
                # Check for extreme market conditions
                prices = market_data['trend']['close'].values
                recent_change = (prices[-1] - prices[-20]) / prices[-20] if len(prices) >= 20 else 0
                
                if abs(recent_change) > extreme_change_threshold:
                    market_risk += volatility_penalty  # Increase risk for volatile markets
                
                # Check for trend strength
                if len(prices) >= 50:
                    sma_20 = np.mean(prices[-20:])
                    sma_50 = np.mean(prices[-50:])
                    trend_strength = abs(sma_20 - sma_50) / sma_50
                    
                    if trend_strength > strong_trend_threshold:
                        market_risk -= trend_bonus  # Reduce risk in trending markets
            
            result = max(min_risk, min(max_risk, market_risk))  # Clamp between min-max
            logger.debug(f"Market risk: {result} (base: {base_risk}, recent_change: {recent_change:.3f}, trend_strength: {trend_strength:.3f})")
            return result
            
        except Exception as e:
            logger.warning(f"Failed to calculate market risk: {e}")
            return 40.0
    
    def _combine_risk_metrics(self, risks: Dict[str, Optional[float]]) -> float:
        """Combine multiple risk metrics into a single score."""
        try:
            # Weighted combination of risk factors
            weights = {
                'volatility': 0.30,
                'liquidity': 0.20,
                'correlation': 0.20,
                'score': 0.15,
                'market': 0.15
            }
            
            # Filter out None values (invalid metrics)
            valid_metrics = {k: v for k, v in risks.items() if v is not None}
            
            if not valid_metrics:
                logger.warning("[RISK_SCORE] no valid metrics, returning neutral")
                return 50.0
            
            # Recalculate weights to sum to 1.0
            total_weight = sum(weights[k] for k in valid_metrics.keys())
            weighted_sum = sum(valid_metrics[k] * weights.get(k, 0.1) for k in valid_metrics.keys())
            
            final_risk = weighted_sum / total_weight if total_weight > 0 else 50.0
            
            logger.info(f"[RISK_SCORE] combined: {valid_metrics} → {final_risk:.1f}")
            return min(100.0, max(0.0, final_risk))  # Clamp between 0-100
            
        except Exception as e:
            logger.warning(f"Failed to combine risk metrics: {e}")
            return 50.0
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level."""
        if risk_score < 30:
            return 'low'
        elif risk_score < 60:
            return 'medium'
        elif risk_score < 80:
            return 'high'
        else:
            return 'very_high'
    
    def _get_recommendation(self, risk_score: float, risk_level: str) -> str:
        """Get trading recommendation based on risk."""
        if risk_level == 'low':
            return 'proceed'
        elif risk_level == 'medium':
            return 'proceed_with_caution'
        elif risk_level == 'high':
            return 'reduce_size'
        else:  # very_high
            return 'reject'
    
    def _identify_risk_factors(self, risks: Dict[str, float]) -> List[str]:
        """Identify the main risk factors."""
        factors = []
        
        for factor, risk in risks.items():
            if risk > 70:
                factors.append(f"high_{factor}")
            elif risk < 30:
                factors.append(f"low_{factor}")
        
        return factors
    
    async def get_portfolio_risk(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall portfolio risk."""
        try:
            if not positions:
                return {
                    'portfolio_risk': 0.0,
                    'concentration_risk': 0.0,
                    'correlation_risk': 0.0,
                    'recommendation': 'no_positions'
                }
            
            # Calculate concentration risk
            total_value = sum(pos.get('value', 0) for pos in positions)
            if total_value == 0:
                return {
                    'portfolio_risk': 0.0,
                    'concentration_risk': 0.0,
                    'correlation_risk': 0.0,
                    'recommendation': 'no_value'
                }
            
            # Calculate position concentration
            max_position_ratio = max(pos.get('value', 0) / total_value for pos in positions)
            concentration_risk = max_position_ratio * 100
            
            # Estimate correlation risk (simplified)
            correlation_risk = min(50.0, len(positions) * 10)  # More positions = higher correlation risk
            
            # Combine portfolio risks
            portfolio_risk = (concentration_risk * 0.6 + correlation_risk * 0.4)
            
            return {
                'portfolio_risk': portfolio_risk,
                'concentration_risk': concentration_risk,
                'correlation_risk': correlation_risk,
                'recommendation': 'monitor' if portfolio_risk < 60 else 'reduce_exposure'
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio risk: {e}")
            return {
                'portfolio_risk': 100.0,
                'concentration_risk': 100.0,
                'correlation_risk': 100.0,
                'recommendation': 'error'
            }
    
    def check_min_quantize_guard(self, size: float, min_size: float, min_notional: float, 
                                price: float, mode: str = "PAPER") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check min/quantize guard and return skip decision with reason and details.
        
        Args:
            size: Order size
            min_size: Minimum order size
            min_notional: Minimum notional value
            price: Order price
            mode: Trading mode (LIVE/PAPER/DRY-RUN)
        
        Returns:
            Tuple of (should_skip, reason, details)
        """
        # Handle None values with defaults
        min_size = min_size if min_size is not None else 0.001
        min_notional = min_notional if min_notional is not None else 5.0
        price = price if price is not None else 0.0
        
        # Check size constraints
        if size < min_size:
            return True, "below_min_size", {
                'size': size,
                'min_size': min_size,
                'deficit': min_size - size,
                'mode': mode
            }
        
        # Check notional constraints
        notional_value = size * price
        if notional_value < min_notional:
            return True, "below_min_notional", {
                'size': size,
                'price': price,
                'notional_value': notional_value,
                'min_notional': min_notional,
                'deficit': min_notional - notional_value,
                'mode': mode
            }
        
        return False, "ok", {
            'size': size,
            'price': price,
            'notional_value': notional_value,
            'min_size': min_size,
            'min_notional': min_notional,
            'mode': mode
        }
    
    def check_leverage_limit(self, requested_leverage: float, symbol: str = None, 
                             mode: str = "PAPER") -> Tuple[bool, float, str, Dict[str, Any]]:
        """
        Check and enforce leverage limit from policy.
        
        Args:
            requested_leverage: Requested leverage multiplier
            symbol: Trading symbol (for symbol-specific limits)
            mode: Trading mode (LIVE/PAPER/DRY-RUN)
        
        Returns:
            Tuple of (should_limit, final_leverage, reason, details)
            - should_limit: True if leverage was limited
            - final_leverage: The leverage to use (may be adjusted)
            - reason: 'ok', 'limited', or 'rejected'
            - details: Additional information
        """
        try:
            # Get leverage limits from policy
            leverage_config = self.policy.get('trading', {}).get('risk', {}).get('leverage', {})
            
            # Default limits if not configured
            max_leverage = leverage_config.get('max_leverage', 5.0)
            min_leverage = leverage_config.get('min_leverage', 1.0)
            default_leverage = leverage_config.get('default', 3.0)
            
            # Symbol-specific limits
            symbol_limits = leverage_config.get('symbol_limits', {})
            if symbol:
                base_symbol = symbol.split('-')[0]
                if base_symbol in symbol_limits:
                    max_leverage = symbol_limits[base_symbol].get('max', max_leverage)
            
            details = {
                'requested_leverage': requested_leverage,
                'max_leverage': max_leverage,
                'min_leverage': min_leverage,
                'default_leverage': default_leverage,
                'symbol': symbol,
                'mode': mode
            }
            
            # Validate leverage
            if requested_leverage <= 0:
                logger.warning(f"[LEVERAGE] Invalid leverage {requested_leverage}, using default {default_leverage}")
                return True, default_leverage, 'invalid', details
            
            if requested_leverage < min_leverage:
                logger.info(f"[LEVERAGE] Requested {requested_leverage}x below minimum {min_leverage}x, using minimum")
                details['adjustment'] = f'{requested_leverage}x -> {min_leverage}x (below min)'
                return True, min_leverage, 'limited_up', details
            
            if requested_leverage > max_leverage:
                logger.warning(f"[LEVERAGE] Requested {requested_leverage}x exceeds max {max_leverage}x, limiting")
                details['adjustment'] = f'{requested_leverage}x -> {max_leverage}x (above max)'
                return True, max_leverage, 'limited_down', details
            
            # Leverage is within limits
            logger.debug(f"[LEVERAGE] {requested_leverage}x within limits ({min_leverage}x-{max_leverage}x)")
            details['status'] = 'ok'
            return False, requested_leverage, 'ok', details
            
        except Exception as e:
            logger.error(f"[LEVERAGE] Check failed: {e}, using default")
            return True, 3.0, 'error', {'error': str(e)}