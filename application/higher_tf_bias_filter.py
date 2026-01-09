"""
Higher Timeframe Bias Filter
4H ve 1H timeframe trend yönü ile 15m sinyal uyumu kontrol eder.
Trend karşıtı işlemler engellenir.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Literal
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class BiasResult:
    """Higher timeframe bias analysis result."""
    bias: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: float  # 0-1
    aligned_with_signal: bool
    block_trade: bool
    reason: str
    details: Dict[str, Any]


class HigherTimeframeBiasFilter:
    """
    Filters trades based on higher timeframe trend alignment.
    
    Logic:
    - Calculate bias from 1H and 4H EMA cross, ADX, trend direction
    - Block signals that go against the higher TF trend
    - NEUTRAL bias allows both directions
    """
    
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        
        # Config
        htf_config = policy.get('trading', {}).get('htf_bias', {})
        self.enabled = htf_config.get('enabled', True)
        self.ema_fast = htf_config.get('ema_fast', 20)
        self.ema_slow = htf_config.get('ema_slow', 50)
        self.adx_threshold = htf_config.get('adx_threshold', 20)
        self.min_confidence = htf_config.get('min_confidence', 0.6)
        
        logger.info(f"✅ HigherTimeframeBiasFilter initialized (enabled={self.enabled})")
    
    def check_signal_alignment(self, symbol: str, signal_direction: str,
                               ohlcv_1h: List[List], ohlcv_4h: List[List] = None) -> BiasResult:
        """
        Check if signal aligns with higher timeframe bias.
        
        Args:
            symbol: Trading symbol
            signal_direction: Proposed signal direction ('LONG' or 'SHORT')
            ohlcv_1h: 1H OHLCV data [[timestamp, open, high, low, close, volume], ...]
            ohlcv_4h: 4H OHLCV data (optional, uses 1H if not provided)
            
        Returns:
            BiasResult with alignment status
        """
        if not self.enabled:
            return BiasResult(
                bias="NEUTRAL",
                confidence=0.0,
                aligned_with_signal=True,
                block_trade=False,
                reason="htf_filter_disabled",
                details={}
            )
        
        signal_direction = signal_direction.upper()
        
        try:
            # 1H Bias hesapla
            bias_1h, conf_1h, details_1h = self._calculate_bias(ohlcv_1h, "1H")
            
            # 4H Bias hesapla (varsa)
            if ohlcv_4h and len(ohlcv_4h) >= 50:
                bias_4h, conf_4h, details_4h = self._calculate_bias(ohlcv_4h, "4H")
            else:
                bias_4h, conf_4h, details_4h = bias_1h, conf_1h * 0.8, {}
            
            # Combined bias - 4H ağırlıklı
            combined_bias = self._combine_biases(bias_1h, conf_1h, bias_4h, conf_4h)
            combined_confidence = (conf_4h * 0.6 + conf_1h * 0.4)
            
            # Alignment check
            aligned = self._check_alignment(combined_bias, signal_direction)
            block = not aligned and combined_confidence >= self.min_confidence
            
            reason = "aligned" if aligned else "against_trend"
            if combined_bias == "NEUTRAL":
                reason = "neutral_bias"
                block = False
            
            details = {
                "symbol": symbol,
                "signal_direction": signal_direction,
                "bias_1h": bias_1h,
                "conf_1h": round(conf_1h, 2),
                "bias_4h": bias_4h,
                "conf_4h": round(conf_4h, 2),
                "combined_bias": combined_bias,
                "details_1h": details_1h,
                "details_4h": details_4h
            }
            
            if block:
                logger.warning(f"[HTF_BIAS] {symbol} BLOK: {signal_direction} against {combined_bias} trend "
                              f"(conf={combined_confidence:.2f})")
            else:
                logger.debug(f"[HTF_BIAS] {symbol} OK: {signal_direction} {reason}")
            
            return BiasResult(
                bias=combined_bias,
                confidence=combined_confidence,
                aligned_with_signal=aligned,
                block_trade=block,
                reason=reason,
                details=details
            )
            
        except Exception as e:
            logger.error(f"HTF Bias check failed for {symbol}: {e}")
            return BiasResult(
                bias="NEUTRAL",
                confidence=0.0,
                aligned_with_signal=True,
                block_trade=False,
                reason=f"error: {e}",
                details={}
            )
    
    def _calculate_bias(self, ohlcv: List[List], tf: str) -> tuple:
        """Calculate bias from OHLCV data."""
        if not ohlcv or len(ohlcv) < self.ema_slow + 5:
            return "NEUTRAL", 0.0, {}
        
        closes = np.array([c[4] for c in ohlcv])
        highs = np.array([c[2] for c in ohlcv])
        lows = np.array([c[3] for c in ohlcv])
        
        # EMA hesapla
        ema_fast = self._ema(closes, self.ema_fast)
        ema_slow = self._ema(closes, self.ema_slow)
        
        # ADX hesapla
        adx = self._calculate_adx(highs, lows, closes, 14)
        
        # Son değerler
        current_ema_fast = ema_fast[-1]
        current_ema_slow = ema_slow[-1]
        current_adx = adx[-1] if len(adx) > 0 else 0
        current_close = closes[-1]
        
        # Bias belirleme
        ema_bullish = current_ema_fast > current_ema_slow
        price_above_emas = current_close > current_ema_fast and current_close > current_ema_slow
        price_below_emas = current_close < current_ema_fast and current_close < current_ema_slow
        
        # Trend strength
        ema_gap_pct = abs(current_ema_fast - current_ema_slow) / current_ema_slow * 100
        
        # Bias ve confidence
        if current_adx < self.adx_threshold:
            # Trend yok
            bias = "NEUTRAL"
            confidence = 0.3
        elif ema_bullish and price_above_emas:
            bias = "BULLISH"
            confidence = min(0.9, 0.5 + (current_adx / 100) + (ema_gap_pct / 5))
        elif not ema_bullish and price_below_emas:
            bias = "BEARISH"
            confidence = min(0.9, 0.5 + (current_adx / 100) + (ema_gap_pct / 5))
        elif ema_bullish:
            bias = "BULLISH"
            confidence = 0.5 + (current_adx / 200)
        else:
            bias = "BEARISH"
            confidence = 0.5 + (current_adx / 200)
        
        details = {
            "tf": tf,
            "ema_fast": round(current_ema_fast, 4),
            "ema_slow": round(current_ema_slow, 4),
            "adx": round(current_adx, 2),
            "ema_gap_pct": round(ema_gap_pct, 3),
            "price": round(current_close, 4)
        }
        
        return bias, confidence, details
    
    def _combine_biases(self, bias_1h: str, conf_1h: float, 
                       bias_4h: str, conf_4h: float) -> str:
        """Combine 1H and 4H biases."""
        # 4H has priority
        if bias_4h != "NEUTRAL" and conf_4h >= 0.5:
            return bias_4h
        
        # If 4H is neutral but 1H is strong
        if bias_1h != "NEUTRAL" and conf_1h >= 0.7:
            return bias_1h
        
        # If both agree
        if bias_1h == bias_4h:
            return bias_1h
        
        return "NEUTRAL"
    
    def _check_alignment(self, bias: str, signal_direction: str) -> bool:
        """Check if signal aligns with bias."""
        if bias == "NEUTRAL":
            return True
        if bias == "BULLISH" and signal_direction == "LONG":
            return True
        if bias == "BEARISH" and signal_direction == "SHORT":
            return True
        return False
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA."""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        return ema
    
    def _calculate_adx(self, high: np.ndarray, low: np.ndarray, 
                       close: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate ADX indicator."""
        try:
            n = len(close)
            if n < period + 1:
                return np.zeros(n)
            
            # True Range
            tr = np.zeros(n)
            tr[0] = high[0] - low[0]
            for i in range(1, n):
                tr[i] = max(
                    high[i] - low[i],
                    abs(high[i] - close[i-1]),
                    abs(low[i] - close[i-1])
                )
            
            # Directional Movement
            dm_plus = np.zeros(n)
            dm_minus = np.zeros(n)
            for i in range(1, n):
                up_move = high[i] - high[i-1]
                down_move = low[i-1] - low[i]
                dm_plus[i] = up_move if up_move > down_move and up_move > 0 else 0
                dm_minus[i] = down_move if down_move > up_move and down_move > 0 else 0
            
            # Smoothed values
            atr = self._wilder_smooth(tr, period)
            di_plus = 100 * self._wilder_smooth(dm_plus, period) / np.maximum(atr, 1e-10)
            di_minus = 100 * self._wilder_smooth(dm_minus, period) / np.maximum(atr, 1e-10)
            
            # DX and ADX
            dx = 100 * np.abs(di_plus - di_minus) / np.maximum(di_plus + di_minus, 1e-10)
            adx = self._wilder_smooth(dx, period)
            
            return adx
        except Exception as e:
            logger.error(f"ADX calculation failed: {e}")
            return np.zeros(len(close))
    
    def _wilder_smooth(self, data: np.ndarray, period: int) -> np.ndarray:
        """Apply Wilder's smoothing."""
        smooth = np.zeros_like(data)
        smooth[:period] = np.mean(data[:period])
        for i in range(period, len(data)):
            smooth[i] = (smooth[i-1] * (period - 1) + data[i]) / period
        return smooth


# Global instance
_htf_bias_filter: Optional[HigherTimeframeBiasFilter] = None


def get_htf_bias_filter(policy: Dict[str, Any] = None) -> HigherTimeframeBiasFilter:
    """Get global HTF bias filter instance."""
    global _htf_bias_filter
    if _htf_bias_filter is None:
        if policy is None:
            from infrastructure.bootstrap import load_policy
            policy = load_policy()
        _htf_bias_filter = HigherTimeframeBiasFilter(policy)
    return _htf_bias_filter
