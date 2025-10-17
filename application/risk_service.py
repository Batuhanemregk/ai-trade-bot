"""
Risk Service - Real risk management with market analysis
Enhanced with log deduplication to reduce spam.
"""

from typing import Dict, Any, List, Optional
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
            # Check cache first
            if symbol in self._volatility_cache:
                return self._volatility_cache[symbol]
            
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
                    return 50.0  # Medium risk if insufficient data
                
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
                    return 50.0
                
                # Calculate volatility-based risk
                low_threshold = thresholds.get('low', 0.25)
                medium_threshold = thresholds.get('medium', 0.45)
                high_threshold = thresholds.get('high', 0.65)
                
                if volatility < low_threshold:
                    risk = 20.0  # Low volatility = low risk
                elif volatility < medium_threshold:
                    risk = 50.0  # Medium volatility = medium risk
                elif volatility < high_threshold:
                    risk = 75.0  # High volatility = high risk
                else:
                    risk = 95.0  # Very high volatility = very high risk
                
                # Cache the result
                self._volatility_cache[symbol] = risk
                
                logger.debug(f"Volatility risk for {symbol}: {risk} (volatility: {volatility:.3f}, thresholds: {thresholds})")
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
        """Calculate correlation-based risk with market cap tiers from policy."""
        try:
            # Policy'den risk konfigürasyonunu al
            risk_config = self.policy.get('trading', {}).get('risk', {}).get('risk_assessment', {}).get('correlation_risk', {})
            
            if not risk_config:
                logger.warning("No correlation risk config in policy, using defaults")
                return 50.0
            
            # Policy'den tier'ları ve risk seviyelerini al
            market_cap_tiers = risk_config.get('market_cap_tiers', {})
            risk_levels = risk_config.get('risk_levels', {})
            default_unknown = risk_config.get('default_unknown', 60.0)
            
            if not market_cap_tiers or not risk_levels:
                logger.warning("Incomplete correlation risk config in policy, using defaults")
                return 50.0
            
            # Symbol'ü temizle (BTC-USDT-SWAP → BTC)
            base_symbol = symbol.split('-')[0]
            
            # Tier'ı bul
            for tier, symbols in market_cap_tiers.items():
                if base_symbol in symbols:
                    risk_value = risk_levels.get(tier, default_unknown)
                    logger.debug(f"Correlation risk for {symbol}: {risk_value} (tier: {tier})")
                    return risk_value
            
            # Bilinmeyen coin için varsayılan
            logger.warning(f"Unknown symbol {symbol}, using default correlation risk: {default_unknown}")
            return default_unknown
            
        except Exception as e:
            logger.warning(f"Failed to calculate correlation risk for {symbol}: {e}")
            return 50.0
    
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
    
    def _combine_risk_metrics(self, risks: Dict[str, float]) -> float:
        """Combine multiple risk metrics into a single score."""
        try:
            # Weighted combination of risk factors
            weights = {
                'volatility': 0.25,
                'liquidity': 0.20,
                'correlation': 0.15,
                'score': 0.25,
                'market': 0.15
            }
            
            total_risk = sum(risks[factor] * weight for factor, weight in weights.items())
            
            return min(100.0, max(0.0, total_risk))  # Clamp between 0-100
            
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