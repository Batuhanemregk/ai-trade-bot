"""
Technical Analysis Scorer - Computes technical scores from indicators
"""

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from .strategy_scorer import calculate_all_indicators
from .columns import COL


class TAScorer:
    """Technical analysis scorer for computing unified technical scores."""

    def __init__(self):
        self.indicators = {}
        self.strategy_flags = {}
        self._skip_warnings = set()  # Track which warnings we've already logged

    def _col_or_none(self, indicators: dict, col_name: str, symbol: str = "") -> "pd.Series|None":
        """Safely get column or None if missing/NaN-only."""
        if col_name not in indicators:
            warning_key = f"{symbol}:{col_name}"
            if warning_key not in self._skip_warnings:
                logger.warning(f"⚠️ Missing indicator column '{col_name}' for {symbol}")
                self._skip_warnings.add(warning_key)
            return None
        
        s = indicators[col_name]
        if hasattr(s, "isna") and s.isna().all():
            warning_key = f"{symbol}:{col_name}:nan"
            if warning_key not in self._skip_warnings:
                logger.warning(f"⚠️ Indicator '{col_name}' is all NaN for {symbol} (warmup period)")
                self._skip_warnings.add(warning_key)
            return None
        
        return s

    def score(self, df: pd.DataFrame, symbol: str) -> tuple[float, str, dict[str, Any]]:
        """
        Compute technical analysis score from OHLCV data.
        
        Args:
            df: OHLCV DataFrame with timestamp index
            symbol: Trading symbol
            
        Returns:
            Tuple of (score: float, rationale: str, flags: dict)
        """
        if df.empty or len(df) < 50:
            return 50.0, "Insufficient data for analysis", {"dir_hint": "FLAT"}

        # Calculate all required indicators using strategy_scorer
        indicators_df = calculate_all_indicators(df)

        # Extract indicators from DataFrame
        indicators = self._extract_indicators(indicators_df)
        
        # NaN-safe logging for key indicators
        rsi_val = indicators.get('rsi', pd.Series([np.nan])).iloc[-1] if 'rsi' in indicators and len(indicators['rsi']) > 0 else np.nan
        macd_hist_val = indicators.get('macd_histogram', pd.Series([np.nan])).iloc[-1] if 'macd_histogram' in indicators and len(indicators['macd_histogram']) > 0 else np.nan
        sma_20_val = indicators.get('sma_20', pd.Series([np.nan])).iloc[-1] if 'sma_20' in indicators and len(indicators['sma_20']) > 0 else np.nan
        sma_50_val = indicators.get('sma_50', pd.Series([np.nan])).iloc[-1] if 'sma_50' in indicators and len(indicators['sma_50']) > 0 else np.nan
        
        rsi_txt = 'NaN' if pd.isna(rsi_val) else f"{rsi_val:.2f}"
        macd_txt = 'NaN' if pd.isna(macd_hist_val) else f"{macd_hist_val:.4f}"
        sma20_txt = 'NaN' if pd.isna(sma_20_val) else f"{sma_20_val:.2f}"
        sma50_txt = 'NaN' if pd.isna(sma_50_val) else f"{sma_50_val:.2f}"
        
        logger.debug(f"[TA_INDICATORS] {symbol}: RSI={rsi_txt}, MACD_hist={macd_txt}, SMA20={sma20_txt}, SMA50={sma50_txt}")

        # Compute individual component scores (each has own error handling)
        trend_score = self._score_trend(indicators)
        momentum_score = self._score_momentum(indicators)
        volatility_score = self._score_volatility(indicators)
        volume_score = self._score_volume(indicators)

        # Enhanced weighted composite score with more active features
        adx_score = self._score_adx(indicators)
        ema_score = self._score_ema(indicators)
        stoch_score = self._score_stochastic(indicators)
        
        logger.debug(f"[TA_COMPONENTS] {symbol}: trend={trend_score:.1f}, momentum={momentum_score:.1f}, volatility={volatility_score:.1f}, volume={volume_score:.1f}")
        
        technical_score = (
            0.25 * trend_score +      # Trend analysis (reduced weight)
            0.20 * momentum_score +   # Momentum analysis (reduced weight)
            0.15 * volatility_score + # Volatility analysis (reduced weight)
            0.10 * volume_score +     # Volume analysis (reduced weight)
            0.15 * adx_score +        # ADX trend strength (new)
            0.10 * ema_score +        # EMA analysis (new)
            0.05 * stoch_score        # Stochastic analysis (new)
        )

        # Determine strategy flags
        flags = self._determine_strategy_flags(indicators)

        # Generate rationale
        rationale = self._generate_rationale(indicators, technical_score, flags)

        logger.debug(f"[TA_FINAL] {symbol}: score={technical_score:.1f}, dir={flags.get('dir_hint', 'FLAT')}")

        return technical_score, rationale, flags

    def _extract_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
        """Extract indicators from DataFrame into dictionary format."""
        indicators = {}

        # Extract all indicator columns (expanded list for full TA scoring)
        indicator_columns = [
            # Core indicators
            'sma_20', 'sma_50', 'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'atr',
            'volume_sma', 'volume_ratio', 'current_price', 'high_20', 'low_20',
            # ADX indicators
            'adx', 'di_plus', 'di_minus',
            # EMA indicators
            'ema_20', 'ema_50', 'ema_200',
            # Stochastic indicators
            'stoch_k', 'stoch_d',
            # SuperTrend
            'supertrend', 'supertrend_direction'
        ]

        for col in indicator_columns:
            if col in df.columns:
                indicators[col] = df[col]
            else:
                # Create NaN series if column doesn't exist
                indicators[col] = pd.Series([np.nan] * len(df), index=df.index)

        return indicators

    def _calculate_indicators(self, df: pd.DataFrame) -> dict[str, Any]:
        """Calculate all required technical indicators."""
        indicators = {}

        try:
            # Check if we have enough data
            if len(df) < 50:
                raise ValueError(f"Insufficient data: {len(df)} rows, need at least 50")

            # Use the strategy_scorer calculator
            indicators_df = calculate_all_indicators(df)
            indicators = self._extract_indicators(indicators_df)

        except Exception as e:
            logger.error(f"Indicator calculation error: {e}")
            # Return empty indicators
            indicators = {key: pd.Series([np.nan] * len(df)) for key in [
                'sma_20', 'sma_50', 'rsi', 'macd', 'macd_signal', 'macd_histogram',
                'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'atr',
                'volume_sma', 'volume_ratio', 'current_price', 'high_20', 'low_20'
            ]}

        return indicators

    def _score_trend(self, indicators: dict[str, Any]) -> float:
        """Score trend strength and direction."""
        try:
            # Get latest values
            sma_20 = indicators['sma_20'].iloc[-1]
            sma_50 = indicators['sma_50'].iloc[-1]
            current_price = indicators['current_price'].iloc[-1]

            if pd.isna(sma_20) or pd.isna(sma_50):
                return 50.0

            # Trend direction score
            if sma_20 > sma_50 and current_price > sma_20:
                # Strong uptrend
                trend_score = 85.0
            elif sma_20 > sma_50:
                # Moderate uptrend
                trend_score = 70.0
            elif sma_20 < sma_50 and current_price < sma_20:
                # Strong downtrend
                trend_score = 15.0
            elif sma_20 < sma_50:
                # Moderate downtrend
                trend_score = 30.0
            else:
                # Sideways
                trend_score = 50.0

            return trend_score

        except Exception as e:
            logger.error(f"Trend scoring error: {e}")
            return 50.0

    def _score_momentum(self, indicators: dict[str, Any]) -> float:
        """Score momentum indicators (RSI, MACD)."""
        try:
            # RSI scoring
            rsi = indicators['rsi'].iloc[-1]
            if pd.isna(rsi):
                rsi_score = 50.0
            elif rsi > 70:
                rsi_score = 20.0  # Overbought
            elif rsi < 30:
                rsi_score = 80.0  # Oversold
            elif rsi > 60:
                rsi_score = 35.0  # Bullish but near overbought
            elif rsi < 40:
                rsi_score = 65.0  # Bearish but near oversold
            else:
                rsi_score = 50.0  # Neutral

            # MACD scoring
            macd_hist = indicators['macd_histogram'].iloc[-1]
            if pd.isna(macd_hist):
                macd_score = 50.0
            elif macd_hist > 0:
                # Positive histogram (bullish)
                macd_score = 60.0 + min(30.0, abs(macd_hist) * 100)
            else:
                # Negative histogram (bearish)
                macd_score = 40.0 - min(30.0, abs(macd_hist) * 100)

            # Combined momentum score
            momentum_score = (rsi_score + macd_score) / 2
            return max(0.0, min(100.0, momentum_score))

        except Exception as e:
            logger.error(f"Momentum scoring error: {e}")
            return 50.0

    def _score_volatility(self, indicators: dict[str, Any]) -> float:
        """Score volatility using ATR and Bollinger Bands."""
        try:
            # ATR scoring (normalized)
            atr = indicators['atr'].iloc[-1]
            atr_20 = indicators['atr'].rolling(20).mean().iloc[-1]

            if pd.isna(atr) or pd.isna(atr_20):
                atr_score = 50.0
            else:
                atr_ratio = atr / atr_20
                if atr_ratio > 1.5:
                    atr_score = 30.0  # High volatility (riskier)
                elif atr_ratio < 0.5:
                    atr_score = 70.0  # Low volatility (safer)
                else:
                    atr_score = 50.0  # Normal volatility

            # Bollinger Band width scoring
            bb_width = indicators['bb_width'].iloc[-1]
            if pd.isna(bb_width):
                bb_score = 50.0
            else:
                # Normalize BB width (typical range 0.02-0.08)
                if bb_width > 0.08:
                    bb_score = 30.0  # Wide bands (high volatility)
                elif bb_width < 0.02:
                    bb_score = 70.0  # Narrow bands (low volatility)
                else:
                    bb_score = 50.0  # Normal width

            # Combined volatility score
            volatility_score = (atr_score + bb_score) / 2
            return max(0.0, min(100.0, volatility_score))

        except Exception as e:
            logger.error(f"Volatility scoring error: {e}")
            return 50.0

    def _score_volume(self, indicators: dict[str, Any]) -> float:
        """Score volume analysis."""
        try:
            volume_ratio = indicators['volume_ratio'].iloc[-1]

            if pd.isna(volume_ratio):
                return 50.0

            # Volume scoring
            if volume_ratio > 2.0:
                volume_score = 80.0  # High volume (good)
            elif volume_ratio > 1.5:
                volume_score = 70.0  # Above average volume
            elif volume_ratio > 1.0:
                volume_score = 60.0  # Normal volume
            elif volume_ratio > 0.7:
                volume_score = 40.0  # Below average volume
            else:
                volume_score = 20.0  # Low volume (concerning)

            return max(0.0, min(100.0, volume_score))

        except Exception as e:
            logger.error(f"Volume scoring error: {e}")
            return 50.0

    def _score_adx(self, indicators: dict[str, Any]) -> float:
        """Score ADX trend strength."""
        try:
            adx_series = self._col_or_none(indicators, COL["ADX"])
            if adx_series is None:
                return 50.0  # Neutral score for missing indicator
            
            adx = adx_series.iloc[-1]
            
            if pd.isna(adx):
                return 50.0
            
            # ADX scoring (0-100 scale)
            if adx > 50:
                adx_score = 80.0  # Strong trend
            elif adx > 25:
                adx_score = 60.0  # Moderate trend
            elif adx > 20:
                adx_score = 50.0  # Weak trend
            else:
                adx_score = 30.0  # No trend
            
            return max(0.0, min(100.0, adx_score))
            
        except Exception as e:
            logger.error(f"ADX scoring error: {e}")
            return 50.0

    def _score_ema(self, indicators: dict[str, Any]) -> float:
        """Score EMA analysis."""
        try:
            ema_20_series = self._col_or_none(indicators, COL["EMA20"])
            ema_50_series = self._col_or_none(indicators, COL["EMA50"])
            ema_200_series = self._col_or_none(indicators, COL["EMA200"])
            current_price_series = self._col_or_none(indicators, COL["CURRENT_PRICE"])
            
            if any(series is None for series in [ema_20_series, ema_50_series, ema_200_series, current_price_series]):
                return 50.0  # Neutral score for missing indicators
            
            ema_20 = ema_20_series.iloc[-1]
            ema_50 = ema_50_series.iloc[-1]
            ema_200 = ema_200_series.iloc[-1]
            current_price = current_price_series.iloc[-1]
            
            if any(pd.isna([ema_20, ema_50, ema_200, current_price])):
                return 50.0
            
            # EMA scoring based on alignment and position
            score = 50.0
            
            # EMA alignment bonus
            if ema_20 > ema_50 > ema_200:
                score += 20.0  # Bullish alignment
            elif ema_20 < ema_50 < ema_200:
                score -= 20.0  # Bearish alignment
            
            # Price position relative to EMAs
            if current_price > ema_20:
                score += 10.0
            if current_price > ema_50:
                score += 10.0
            if current_price > ema_200:
                score += 10.0
            
            return max(0.0, min(100.0, score))
            
        except Exception as e:
            logger.error(f"EMA scoring error: {e}")
            return 50.0

    def _score_stochastic(self, indicators: dict[str, Any]) -> float:
        """Score Stochastic analysis."""
        try:
            stoch_k_series = self._col_or_none(indicators, COL["STOCH_K"])
            stoch_d_series = self._col_or_none(indicators, COL["STOCH_D"])
            
            if stoch_k_series is None or stoch_d_series is None:
                return 50.0  # Neutral score for missing indicators
            
            stoch_k = stoch_k_series.iloc[-1]
            stoch_d = stoch_d_series.iloc[-1]
            
            if pd.isna(stoch_k) or pd.isna(stoch_d):
                return 50.0
            
            # Stochastic scoring
            if stoch_k > 80 and stoch_d > 80:
                stoch_score = 30.0  # Overbought
            elif stoch_k < 20 and stoch_d < 20:
                stoch_score = 70.0  # Oversold (bullish)
            elif stoch_k > stoch_d:
                stoch_score = 60.0  # Bullish crossover
            elif stoch_k < stoch_d:
                stoch_score = 40.0  # Bearish crossover
            else:
                stoch_score = 50.0  # Neutral
            
            return max(0.0, min(100.0, stoch_score))
            
        except Exception as e:
            logger.error(f"Stochastic scoring error: {e}")
            return 50.0

    def _determine_strategy_flags(self, indicators: dict[str, Any]) -> dict[str, Any]:
        """Determine strategy flags based on indicator conditions."""
        flags = {
            "trend": "side",
            "meanrev": "off",
            "breakout": "off",
            "dir_hint": "FLAT"
        }

        try:
            # Get latest values
            sma_20 = indicators['sma_20'].iloc[-1]
            sma_50 = indicators['sma_50'].iloc[-1]
            rsi = indicators['rsi'].iloc[-1]
            current_price = indicators['current_price'].iloc[-1]
            bb_upper = indicators['bb_upper'].iloc[-1]
            bb_lower = indicators['bb_lower'].iloc[-1]
            high_20 = indicators['high_20'].iloc[-1]
            low_20 = indicators['low_20'].iloc[-1]
            volume_ratio = indicators['volume_ratio'].iloc[-1]

            # Trend following flags
            if sma_20 > sma_50 and rsi < 70:
                flags["trend"] = "up"
                flags["dir_hint"] = "LONG"
            elif sma_20 < sma_50 and rsi > 30:
                flags["trend"] = "down"
                flags["dir_hint"] = "SHORT"
            else:
                flags["trend"] = "side"

            # Mean reversion flags
            if rsi < 30 and current_price <= bb_lower * 1.01:
                flags["meanrev"] = "on"
                if flags["dir_hint"] == "FLAT":
                    flags["dir_hint"] = "LONG"
            elif rsi > 70 and current_price >= bb_upper * 0.99:
                flags["meanrev"] = "on"
                if flags["dir_hint"] == "FLAT":
                    flags["dir_hint"] = "SHORT"

            # Breakout flags
            if (current_price > high_20 * 0.99 and volume_ratio > 1.5):
                flags["breakout"] = "on"
                if flags["dir_hint"] == "FLAT":
                    flags["dir_hint"] = "LONG"
            elif (current_price < low_20 * 1.01 and volume_ratio > 1.5):
                flags["breakout"] = "on"
                if flags["dir_hint"] == "FLAT":
                    flags["dir_hint"] = "SHORT"

        except Exception as e:
            logger.error(f"Strategy flag determination error: {e}")
            flags = {"trend": "side", "meanrev": "off", "breakout": "off", "dir_hint": "FLAT"}

        return flags

    def _generate_rationale(self, indicators: dict[str, Any], score: float, flags: dict[str, Any]) -> str:
        """Generate human-readable rationale for the technical score."""
        try:
            rationale_parts = []

            # Add trend analysis
            if flags["trend"] == "up":
                rationale_parts.append("Uptrend detected (SMA20 > SMA50)")
            elif flags["trend"] == "down":
                rationale_parts.append("Downtrend detected (SMA20 < SMA50)")
            else:
                rationale_parts.append("Sideways trend (SMA20 ≈ SMA50)")

            # Add strategy identification
            if flags["meanrev"] == "on":
                rationale_parts.append("Mean reversion opportunity")
            if flags["breakout"] == "on":
                rationale_parts.append("Breakout pattern detected")

            # Add RSI context
            rsi = indicators['rsi'].iloc[-1]
            if not pd.isna(rsi):
                if rsi > 70:
                    rationale_parts.append("RSI overbought (>70)")
                elif rsi < 30:
                    rationale_parts.append("RSI oversold (<30)")
                else:
                    rationale_parts.append(f"RSI neutral ({rsi:.1f})")

            # Add MACD context
            macd_hist = indicators['macd_histogram'].iloc[-1]
            if not pd.isna(macd_hist):
                if macd_hist > 0:
                    rationale_parts.append("MACD bullish")
                else:
                    rationale_parts.append("MACD bearish")

            # Add volume context
            volume_ratio = indicators['volume_ratio'].iloc[-1]
            if not pd.isna(volume_ratio):
                if volume_ratio > 1.5:
                    rationale_parts.append("High volume confirmation")
                elif volume_ratio < 0.7:
                    rationale_parts.append("Low volume (caution)")

            # Add final direction
            if flags["dir_hint"] != "FLAT":
                rationale_parts.append(f"Direction: {flags['dir_hint']}")

            return " | ".join(rationale_parts)

        except Exception as e:
            logger.error(f"Rationale generation error: {e}")
            return f"Technical score: {score:.1f} (analysis error)"


# Global instance
ta_scorer = TAScorer()
