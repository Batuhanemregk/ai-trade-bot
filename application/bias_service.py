"""
Bias Service - Lightweight risk bias for trading decisions
"""

import time
from dataclasses import dataclass
from typing import Literal, Dict, Any, Optional
from loguru import logger


@dataclass
class BiasDecision:
    """Bias decision for trading action."""
    action: Literal["allow", "downgrade", "block"]
    score_penalty: int
    reason: str
    ttl_sec: int


class BiasService:
    """Lightweight bias service for trading decisions."""
    
    def __init__(self, policy: Dict[str, Any], providers: Dict[str, Any]):
        self.policy = policy.get('bias', {})
        self.providers = providers
        self.enabled = self.policy.get('enabled', False)
        
        # Extract bias settings with defaults
        self.trend_filter = self.policy.get('trend_filter', {'enabled': True})
        self.news_guard = self.policy.get('news_guard', {
            'enabled': True, 
            'threshold': 0.7, 
            'categories': ['REGULATION', 'SECURITY'],
            'action': 'block',
            'cooldown_sec': 3600
        })
        self.volatility_guard = self.policy.get('volatility_guard', {
            'enabled': True, 
            'atr_limit_pct': 0.05,  # 5% ATR threshold
            'penalty': 15
        })
        self.funding_guard = self.policy.get('funding_guard', {
            'enabled': False, 
            'min_abs': 0.0001,
            'action': 'downgrade',
            'penalty': 10
        })
        self.corr_guard = self.policy.get('corr_guard', {
            'enabled': True, 
            'max_correlation': 0.8,
            'max_exposure': 0.15
        })
        
        logger.info(f"✅ BiasService initialized: enabled={self.enabled}")
    
    def compute_bias(self, symbol: str, ctx: Dict[str, Any]) -> BiasDecision:
        """
        Compute bias decision for trading action.
        
        Args:
            symbol: Trading symbol
            ctx: Context with TA scores, news, portfolio data
            
        Returns:
            BiasDecision with action and penalty
        """
        if not self.enabled:
            return BiasDecision("allow", 0, "bias_disabled", 0)
        
        try:
            # Trend filter
            trend_decision = self._trend_filter(symbol, ctx)
            if trend_decision.action == "block":
                return trend_decision
            
            # News guard
            news_decision = self._news_guard(symbol, ctx)
            if news_decision.action == "block":
                return news_decision
            
            # Volatility guard
            vol_decision = self._volatility_guard(symbol, ctx)
            if vol_decision.action == "block":
                return vol_decision
            
            # Funding guard (optional)
            if self.funding_guard['enabled']:
                funding_decision = self._funding_guard(symbol, ctx)
                if funding_decision.action == "block":
                    return funding_decision
            
            # Correlation guard
            corr_decision = self._corr_guard(symbol, ctx)
            if corr_decision.action == "block":
                return corr_decision
            
            # Aggregate downgrades
            total_penalty = sum([
                trend_decision.score_penalty,
                news_decision.score_penalty,
                vol_decision.score_penalty,
                funding_decision.score_penalty if self.funding_guard['enabled'] else 0,
                corr_decision.score_penalty
            ])
            
            if total_penalty > 0:
                return BiasDecision("downgrade", total_penalty, "multiple_guards", 0)
            
            return BiasDecision("allow", 0, "all_checks_passed", 0)
            
        except Exception as e:
            logger.error(f"❌ Bias computation failed for {symbol}: {e}")
            return BiasDecision("allow", 0, f"bias_error: {str(e)}", 0)
    
    def _trend_filter(self, symbol: str, ctx: Dict[str, Any]) -> BiasDecision:
        """Apply trend-based bias filter."""
        if not self.trend_filter['enabled']:
            return BiasDecision("allow", 0, "trend_filter_disabled", 0)
        
        try:
            # Get TA indicators from context
            indicators = ctx.get('indicators', {})
            sma_20 = indicators.get('sma_20')
            sma_50 = indicators.get('sma_50')
            
            if sma_20 is None or sma_50 is None:
                return BiasDecision("allow", 0, "trend_data_missing", 0)
            
            # Determine trend
            if sma_20 > sma_50 * 1.001:  # Uptrend
                return BiasDecision("block", 0, "uptrend_block_shorts", 0)
            elif sma_20 < sma_50 * 0.999:  # Downtrend
                return BiasDecision("block", 0, "downtrend_block_longs", 0)
            else:  # Sideways
                return BiasDecision("allow", 0, "sideways_trend", 0)
                
        except Exception as e:
            logger.error(f"Trend filter error: {e}")
            return BiasDecision("allow", 0, "trend_filter_error", 0)
    
    def _news_guard(self, symbol: str, ctx: Dict[str, Any]) -> BiasDecision:
        """Apply news-based bias guard."""
        if not self.news_guard['enabled']:
            return BiasDecision("allow", 0, "news_guard_disabled", 0)
        
        try:
            news_score = ctx.get('news_score', 0)
            news_category = ctx.get('news_category', '')
            
            if (news_score >= self.news_guard['threshold'] and 
                news_category in self.news_guard['categories']):
                
                action = self.news_guard['action']
                cooldown = self.news_guard['cooldown_sec']
                
                if action == "block":
                    return BiasDecision("block", 0, f"news_{news_category.lower()}", cooldown)
                else:
                    return BiasDecision("downgrade", 20, f"news_{news_category.lower()}", cooldown)
            
            return BiasDecision("allow", 0, "news_ok", 0)
            
        except Exception as e:
            logger.error(f"News guard error: {e}")
            return BiasDecision("allow", 0, "news_guard_error", 0)
    
    def _volatility_guard(self, symbol: str, ctx: Dict[str, Any]) -> BiasDecision:
        """Apply volatility-based bias guard."""
        if not self.volatility_guard['enabled']:
            return BiasDecision("allow", 0, "volatility_guard_disabled", 0)
        
        try:
            indicators = ctx.get('indicators', {})
            atr = indicators.get('atr')
            close = ctx.get('close_price', 1.0)
            
            if atr is None or close <= 0:
                return BiasDecision("allow", 0, "volatility_data_missing", 0)
            
            atr_pct = atr / close
            if atr_pct > self.volatility_guard['atr_limit_pct']:
                penalty = self.volatility_guard['penalty']
                return BiasDecision("downgrade", penalty, f"high_volatility_{atr_pct:.3f}", 0)
            
            return BiasDecision("allow", 0, "volatility_ok", 0)
            
        except Exception as e:
            logger.error(f"Volatility guard error: {e}")
            return BiasDecision("allow", 0, "volatility_guard_error", 0)
    
    def _funding_guard(self, symbol: str, ctx: Dict[str, Any]) -> BiasDecision:
        """Apply funding-based bias guard."""
        if not self.funding_guard['enabled']:
            return BiasDecision("allow", 0, "funding_guard_disabled", 0)
        
        try:
            funding_rate = ctx.get('funding_rate', 0)
            
            if abs(funding_rate) > self.funding_guard['min_abs']:
                action = self.funding_guard['action']
                penalty = self.funding_guard['penalty']
                
                if action == "block":
                    return BiasDecision("block", 0, f"funding_{funding_rate:.4f}", 0)
                else:
                    return BiasDecision("downgrade", penalty, f"funding_{funding_rate:.4f}", 0)
            
            return BiasDecision("allow", 0, "funding_ok", 0)
            
        except Exception as e:
            logger.error(f"Funding guard error: {e}")
            return BiasDecision("allow", 0, "funding_guard_error", 0)
    
    def _corr_guard(self, symbol: str, ctx: Dict[str, Any]) -> BiasDecision:
        """Apply correlation-based bias guard."""
        if not self.corr_guard['enabled']:
            return BiasDecision("allow", 0, "corr_guard_disabled", 0)
        
        try:
            portfolio_data = ctx.get('portfolio', {})
            correlation = portfolio_data.get('correlation', 0)
            exposure = portfolio_data.get('exposure', 0)
            
            if (correlation > self.corr_guard['max_correlation'] or 
                exposure > self.corr_guard['max_exposure']):
                return BiasDecision("block", 0, f"corr_{correlation:.2f}_exp_{exposure:.2f}", 0)
            
            return BiasDecision("allow", 0, "correlation_ok", 0)
            
        except Exception as e:
            logger.error(f"Correlation guard error: {e}")
            return BiasDecision("allow", 0, "corr_guard_error", 0)
    
    def get_bias_summary(self) -> Dict[str, Any]:
        """Get bias service configuration summary."""
        return {
            "enabled": self.enabled,
            "trend_filter": self.trend_filter,
            "news_guard": self.news_guard,
            "volatility_guard": self.volatility_guard,
            "funding_guard": self.funding_guard,
            "corr_guard": self.corr_guard
        }


# Factory function for easy instantiation
def create_bias_service(policy: Dict[str, Any], providers: Dict[str, Any]) -> BiasService:
    """Create a new BiasService instance."""
    return BiasService(policy, providers)
