"""
Strategy service for trading decisions.
Contains orchestration and use-cases for building signals and selecting strategies.
"""

import warnings
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from domain.strategy import (
    MarketRegime,
    SignalDecision,
    TradingSignal,
    SupportResistanceLevels,
    IndicatorValues,
    DEFAULT_STRATEGY_PARAMS
)
from scoring.strategy_scorer import (
    calculate_all_indicators,
    detect_market_regime,
    find_swing_levels,
    calculate_pivot_points,
    calculate_fibonacci_levels
)


class StrategyService:
    """Service for orchestrating trading strategy decisions."""
    
    def __init__(self):
        self.params = DEFAULT_STRATEGY_PARAMS
    
    def generate_signal(self, df: pd.DataFrame, sentiment: float = None,
                       regime_hint: str = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate trading signal based on technical analysis with bias and dynamic thresholds."""
        if df.empty or len(df) < 200:
            return {
                "decision": "FLAT",
                "confidence": 0.0,
                "context": {"reason": "Insufficient data"}
            }
        
        # Calculate all indicators if not already present
        if 'ema_20' not in df.columns:
            df = calculate_all_indicators(df)
        
        # Get latest values
        current_price = df['close'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        adx = df['adx'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        macd = df['macd'].iloc[-1]
        macd_signal = df['macd_signal'].iloc[-1]
        macd_hist = df['macd_histogram'].iloc[-1]
        atr = df['atr'].iloc[-1]
        
        # Detect market regime
        regime = regime_hint or detect_market_regime(df)
        
        # Calculate support/resistance levels
        swing_levels = find_swing_levels(df)
        pivot_levels = calculate_pivot_points(df)
        fib_levels = calculate_fibonacci_levels(df)
        
        # Initialize scores
        long_score = 0.0
        short_score = 0.0
        
        # Trend analysis
        if regime in ["bullish_trend", "bearish_trend"]:
            if regime == "bullish_trend":
                long_score += 0.3
                # Look for pullbacks to EMA20
                if current_price > ema_20 and current_price < ema_50:
                    long_score += 0.2
            else:
                short_score += 0.3
                # Look for rallies to EMA20
                if current_price < ema_20 and current_price > ema_50:
                    short_score += 0.2
        
        # RSI analysis
        if rsi < 30:
            long_score += 0.2  # Oversold
        elif rsi > 70:
            short_score += 0.2  # Overbought
        
        # MACD analysis
        if macd > macd_signal and macd_hist > 0:
            long_score += 0.15
        elif macd < macd_signal and macd_hist < 0:
            short_score += 0.15
        
        # Support/Resistance analysis
        if swing_levels["support"]:
            nearest_support = max([s for s in swing_levels["support"] if s < current_price], default=0)
            if nearest_support > 0 and (current_price - nearest_support) / current_price < 0.02:
                long_score += 0.1  # Near support
        
        if swing_levels["resistance"]:
            nearest_resistance = min([r for r in swing_levels["resistance"] if r > current_price], default=0)
            if nearest_resistance > 0 and (nearest_resistance - current_price) / current_price < 0.02:
                short_score += 0.1  # Near resistance
        
        # Sentiment adjustment
        if sentiment is not None:
            if sentiment > 0.1:
                long_score += sentiment * 0.1
            elif sentiment < -0.1:
                short_score += abs(sentiment) * 0.1
        
        # Apply bias to scores (if symbol is provided in params)
        bias_applied = False
        bias_info = {}
        if params and 'symbol' in params:
            try:
                from .bias_service import create_bias_service
                
                # Create bias context for BiasService
                bias_ctx = {
                    'indicators': {
                        'sma_20': ema_20,  # Using EMA as proxy for SMA
                        'sma_50': ema_50,
                        'atr': atr
                    },
                    'close_price': df['close'].iloc[-1] if len(df) > 0 else 1.0,
                    'news_score': 0.5,  # Default neutral news score
                    'news_category': 'MARKET',
                    'portfolio': {
                        'correlation': 0.0,  # Default values
                        'exposure': 0.0
                    }
                }
                
                # Create bias service with default config
                bias_service = create_bias_service({'bias': {'enabled': True}}, {})
                bias_decision = bias_service.compute_bias(params['symbol'], bias_ctx)
                
                # Apply bias based on decision
                if bias_decision.action == "downgrade" and bias_decision.score_penalty > 0:
                    penalty_factor = bias_decision.score_penalty / 100.0
                    long_score = max(0, long_score - penalty_factor)
                    short_score = max(0, short_score - penalty_factor)
                    bias_info = {
                        'action': bias_decision.action,
                        'penalty': bias_decision.score_penalty,
                        'reason': bias_decision.reason
                    }
                    bias_applied = True
                elif bias_decision.action == "block":
                    bias_info = {
                        'action': bias_decision.action,
                        'reason': bias_decision.reason,
                        'blocked': True
                    }
                    bias_applied = True
                    
            except ImportError:
                logger.warning("Bias service not available, skipping bias adjustment")
            except Exception as e:
                logger.error(f"Bias computation failed: {e}")
        
        # Determine decision and confidence
        if long_score > short_score and long_score > 0.3:
            decision = "LONG"
            confidence = min(long_score, 1.0)
        elif short_score > long_score and short_score > 0.3:
            decision = "SHORT"
            confidence = min(short_score, 1.0)
        else:
            decision = "FLAT"
            confidence = max(long_score, short_score)
        
        # Build context
        context = {
            "regime": regime,
            "long_score": long_score,
            "short_score": short_score,
            "bias_applied": bias_applied,
            "bias_info": bias_info,
            "indicators": {
                "ema_20": ema_20,
                "ema_50": ema_50,
                "ema_200": ema_200,
                "adx": adx,
                "rsi": rsi,
                "macd": macd,
                "macd_signal": macd_signal,
                "macd_histogram": macd_hist,
                "atr": atr
            },
            "levels": {
                "swing": swing_levels,
                "pivot": pivot_levels,
                "fibonacci": fib_levels
            }
        }
        
        return {
            "decision": decision,
            "confidence": confidence,
            "context": context
        }
    
    def select_strategy(self, df: pd.DataFrame, signal: Dict[str, Any]) -> str:
        """Select appropriate strategy based on signal and market conditions."""
        decision = signal.get("decision", "FLAT")
        confidence = signal.get("confidence", 0.0)
        regime = signal.get("context", {}).get("regime", "unknown")
        
        if decision == "FLAT" or confidence < 0.3:
            return "WAIT"
        
        if regime in ["bullish_trend", "bearish_trend"] and confidence > 0.6:
            return "TREND_FOLLOWING"
        elif regime == "volatile" and confidence > 0.5:
            return "MEAN_REVERSION"
        elif confidence > 0.7:
            return "MOMENTUM"
        else:
            return "CONSERVATIVE"
    
    def compose_decision(self, df: pd.DataFrame, sentiment: float = None,
                        regime_hint: str = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Compose end-to-end trading decision."""
        # Generate signal
        signal = self.generate_signal(df, sentiment, regime_hint, params)
        
        # Select strategy
        strategy = self.select_strategy(df, signal)
        
        # Compose final decision
        decision = {
            "signal": signal,
            "strategy": strategy,
            "timestamp": pd.Timestamp.now().isoformat(),
            "metadata": {
                "data_points": len(df),
                "sentiment": sentiment,
                "regime_hint": regime_hint
            }
        }
        
        return decision


def generate_signal(df: pd.DataFrame, sentiment: float = None,
                   regime_hint: str = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate trading signal (compatibility function)."""
    warnings.warn(
        "generate_signal is deprecated. Use StrategyService.generate_signal instead.",
        DeprecationWarning,
        stacklevel=2
    )
    service = StrategyService()
    return service.generate_signal(df, sentiment, regime_hint, params)


def select_strategy(df: pd.DataFrame, signal: Dict[str, Any]) -> str:
    """Select strategy (compatibility function)."""
    warnings.warn(
        "select_strategy is deprecated. Use StrategyService.select_strategy instead.",
        DeprecationWarning,
        stacklevel=2
    )
    service = StrategyService()
    return service.select_strategy(df, signal)


def build_composite_score(df: pd.DataFrame, sentiment: float = None,
                         regime_hint: str = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Build composite score (compatibility function)."""
    warnings.warn(
        "build_composite_score is deprecated. Use StrategyService.compose_decision instead.",
        DeprecationWarning,
        stacklevel=2
    )
    service = StrategyService()
    return service.compose_decision(df, sentiment, regime_hint, params)


# Global service instance
strategy_service = StrategyService()


__all__ = [
    "StrategyService",
    "generate_signal",
    "select_strategy", 
    "build_composite_score",
    "strategy_service",
]
