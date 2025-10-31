"""
Log Formatter Service
Provides human-readable log formatting for trading analysis.
Supports two modes: line (single line) and block (multi-line with Rich panels).
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger


class LogFormatter:
    """Formatter for trading analysis logs."""
    
    def __init__(self, mode: str = None):
        """
        Initialize log formatter.
        
        Args:
            mode: 'line' or 'block'. Defaults to LOG_SUMMARY_MODE env var or 'line'
        """
        self.mode = mode or os.getenv('LOG_SUMMARY_MODE', 'line')
        
        if self.mode not in ['line', 'block']:
            logger.warning(f"Invalid LOG_SUMMARY_MODE='{self.mode}', using 'line'")
            self.mode = 'line'
    
    def format_analysis_summary(self, data: Dict[str, Any]) -> str:
        """
        Format analysis summary based on mode.
        
        Args:
            data: Analysis data containing:
                - symbol: str
                - timeframe: str
                - timestamp: datetime
                - ta_score: float
                - ml_score: float
                - news_score: float
                - risk_score: float
                - final_score: float
                - grade: str
                - direction: str
                - gate_status: str
                - gate_details: Dict (persist_count, persist_required, confidence, conf_required)
                - age: Optional[float] (hours since last signal)
                - hyst_status: Optional[str] (for block mode)
                - state_transition: Optional[str] (for block mode)
                - action: Optional[str] (for block mode)
                - position_size: Optional[float] (for block mode)
                - leverage: Optional[float] (for block mode)
                - sl_atr: Optional[float] (for block mode)
                - tp_atr: Optional[float] (for block mode)
                - risk_exposure: Optional[float] (for block mode)
                - risk_tier: Optional[str] (for block mode)
                - circuit_breaker: Optional[str] (for block mode)
        
        Returns:
            Formatted log string
        """
        if self.mode == 'line':
            return self._format_line(data)
        else:
            return self._format_block(data)
    
    def _format_line(self, data: Dict[str, Any]) -> str:
        """Format as single line with enhanced features."""
        ts = data.get('timestamp', datetime.now()).strftime('%H:%M:%S')
        symbol = data.get('symbol', 'UNKNOWN')
        tf = data.get('timeframe', '?')
        
        ta = data.get('ta_score', 0.0)
        ml = data.get('ml_score', 0.0)
        news = data.get('news_score', 0.0)
        risk = data.get('risk_score', 0.0)
        
        final = data.get('final_score', 0.0)
        grade = data.get('grade', '?')
        direction = data.get('direction', 'HOLD')
        
        gate_status = data.get('gate_status', 'UNKNOWN')
        gate_details = data.get('gate_details', {})
        persist = f"{gate_details.get('persist_count', 0)}/{gate_details.get('persist_required', 0)}"
        conf = f"{gate_details.get('confidence', 0):.2f}/{gate_details.get('conf_required', 0):.2f}"
        
        # Age (optional) - Counter format: age=3/6 or time format: age=2.3h
        age_str = ""
        if 'age_bars' in data and data['age_bars'] is not None:
            # Counter format (preferred)
            age_bars = data['age_bars']
            max_age = data.get('max_age_bars', 6)
            age_str = f" age={age_bars}/{max_age}"
        elif 'age' in data and data['age'] is not None:
            # Time format (fallback)
            age_hours = data['age']
            if age_hours < 1:
                age_str = f" age={int(age_hours * 60)}m"
            else:
                age_str = f" age={age_hours:.1f}h"
        
        # Enhanced features - Confidence-aware position sizing
        ml_confidence = data.get('ml_confidence', '')
        risk_level = data.get('risk_level', '')
        confidence_multiplier = data.get('confidence_multiplier', '')
        
        # Enhanced features - Regime-adaptive weights
        regime = data.get('regime', '')
        weights = data.get('weights', {})
        weight_str = ""
        if weights:
            ta_w = weights.get('ta', 0.0)
            ml_w = weights.get('ml', 0.0)
            weight_str = f" w=[TA:{ta_w:.2f} ML:{ml_w:.2f}]"
        
        # Enhanced features - News TTL
        news_age_hours = data.get('news_age_hours', '')
        ttl_weight = data.get('ttl_weight', '')
        news_ttl_str = ""
        if news_age_hours and ttl_weight:
            news_ttl_str = f" news_age={news_age_hours:.1f}h(ttl:{ttl_weight:.2f})"
        
        # Enhanced features - TA active features
        ta_features_count = data.get('ta_features_count', '')
        ta_active_features = data.get('ta_active_features', '')
        ta_features_str = ""
        if ta_features_count and ta_active_features:
            ta_features_str = f" ta_features={ta_active_features}/{ta_features_count}"
        
        # Build enhanced line
        base_line = (
            f"ℹ️ {ts} | {symbol} | tf={tf} | "
            f"TA={ta:.1f} ML={ml:.1f} News={news:.1f} Risk={risk:.1f} | "
            f"Final={final:.1f} ({grade}) | Dir={direction}{age_str} | "
            f"Gate={gate_status} (persist {persist}, conf {conf})"
        )
        
        # Add enhanced features if available
        enhanced_parts = []
        if ml_confidence and risk_level and confidence_multiplier:
            enhanced_parts.append(f"conf_mult={confidence_multiplier:.2f}({ml_confidence}/{risk_level})")
        if regime and weight_str:
            enhanced_parts.append(f"regime={regime}{weight_str}")
        if news_ttl_str:
            enhanced_parts.append(f"news_ttl{news_ttl_str}")
        if ta_features_str:
            enhanced_parts.append(f"ta{ta_features_str}")
        
        if enhanced_parts:
            enhanced_str = " | " + " ".join(enhanced_parts)
            return base_line + enhanced_str
        else:
            return base_line
    
    def _format_block(self, data: Dict[str, Any]) -> str:
        """Format as multi-line block with Rich panel style."""
        symbol = data.get('symbol', 'UNKNOWN')
        tf = data.get('timeframe', '?')
        ts = data.get('timestamp', datetime.now()).strftime('%H:%M:%S')
        
        ta = data.get('ta_score', 0.0)
        ml = data.get('ml_score', 0.0)
        news = data.get('news_score', 0.0)
        risk = data.get('risk_score', 0.0)
        
        final = data.get('final_score', 0.0)
        grade = data.get('grade', '?')
        direction = data.get('direction', 'HOLD')
        
        gate_status = data.get('gate_status', 'UNKNOWN')
        gate_details = data.get('gate_details', {})
        
        # Progress bars (simple text version)
        ta_bar = self._create_bar(ta)
        ml_bar = self._create_bar(ml)
        news_bar = self._create_bar(news)
        risk_bar = self._create_bar(risk)
        final_bar = self._create_bar(final)
        
        # Enhanced features progress bars
        confidence_multiplier = data.get('confidence_multiplier', 0.0)
        ttl_weight = data.get('ttl_weight', 0.0)
        ta_active_features = data.get('ta_active_features', 0)
        ta_features_count = data.get('ta_features_count', 13)
        
        conf_bar = self._create_bar(confidence_multiplier * 100) if confidence_multiplier > 0 else "░░░░░░░░░░"
        ttl_bar = self._create_bar(ttl_weight * 100) if ttl_weight > 0 else "░░░░░░░░░░"
        ta_features_bar = self._create_bar((ta_active_features / ta_features_count) * 100) if ta_features_count > 0 else "░░░░░░░░░░"
        
        # Direction emoji
        dir_emoji = "📈" if direction == "LONG" else "📉" if direction == "SHORT" else "⏸️"
        
        # Gate emoji
        gate_emoji = "✅" if gate_status == "PASS" else "⏳" if gate_status == "PENDING" else "❌"
        
        # Age - Counter or time format
        age_str = ""
        if 'age_bars' in data and data['age_bars'] is not None:
            # Counter format (preferred)
            age_bars = data['age_bars']
            max_age = data.get('max_age_bars', 6)
            age_str = f" (age: {age_bars}/{max_age})"
        elif 'age' in data and data['age'] is not None:
            # Time format (fallback)
            age_hours = data['age']
            if age_hours < 1:
                age_str = f" (age: {int(age_hours * 60)}m)"
            else:
                age_str = f" (age: {age_hours:.1f}h)"
        
        # Build basic block
        width = 62
        title = f"{symbol} Analysis ({tf}) @ {ts}"
        title_padding = max(0, width - len(title) - 4)
        
        lines = [
            f"╭─ {title} {'─' * title_padding}╮",
            f"│ TA Score:    {ta:5.1f} {ta_bar}                            │",
            f"│ ML Score:    {ml:5.1f} {ml_bar}                            │",
            f"│ News Score:  {news:5.1f} {news_bar}                            │",
            f"│ Risk Score:  {risk:5.1f} {risk_bar}                            │",
            f"│ {'─' * (width - 2)} │",
            f"│ Final Score: {final:5.1f} ({grade}) {final_bar}                     │",
            f"│ Direction:   {direction:8s} {dir_emoji}{age_str:41s} │",
            f"│ Gate:        {gate_status:8s} {gate_emoji} (p:{gate_details.get('persist_count', 0)}/{gate_details.get('persist_required', 0)} c:{gate_details.get('confidence', 0):.2f}/{gate_details.get('conf_required', 0):.2f})            │",
        ]
        
        # Add detailed info for block mode
        hyst_status = data.get('hyst_status', '')
        state_trans = data.get('state_transition', '')
        action = data.get('action', '')
        
        # Enhanced features for block mode
        ml_confidence = data.get('ml_confidence', '')
        risk_level = data.get('risk_level', '')
        confidence_multiplier = data.get('confidence_multiplier', '')
        regime = data.get('regime', '')
        weights = data.get('weights', {})
        news_age_hours = data.get('news_age_hours', '')
        ttl_weight = data.get('ttl_weight', '')
        ta_features_count = data.get('ta_features_count', '')
        ta_active_features = data.get('ta_active_features', '')
        
        if (hyst_status or state_trans or action or 
            ml_confidence or risk_level or confidence_multiplier or
            regime or weights or news_age_hours or ttl_weight or
            ta_features_count or ta_active_features):
            lines.append(f"│ {'─' * (width - 2)} │")
            
            # Enhanced features section with progress bars and rich emojis
            enhanced_lines = []
            
            # Confidence-aware position sizing with progress bar
            if ml_confidence and risk_level and confidence_multiplier:
                conf_emoji = "🔥" if ml_confidence == "high" else "⚡" if ml_confidence == "medium" else "💤"
                risk_emoji = "🟢" if risk_level == "low" else "🟡" if risk_level == "medium" else "🔴"
                enhanced_lines.append(f"│ 🎯 CONFIDENCE: {conf_emoji}{ml_confidence}/{risk_emoji}{risk_level} → {conf_bar} {confidence_multiplier:.2f}{' ' * 20} │")
            
            # Regime-adaptive weights with emojis
            if regime and weights:
                regime_emoji = "📈" if regime == "trend_vol" else "📊" if regime == "sideways_vol" else "🔄"
                ta_w = weights.get('ta', 0.0)
                ml_w = weights.get('ml', 0.0)
                news_w = weights.get('news', 0.0)
                risk_w = weights.get('risk', 0.0)
                enhanced_lines.append(f"│ {regime_emoji} REGIME: {regime} → w=[📊TA:{ta_w:.2f} 🤖ML:{ml_w:.2f} 📰News:{news_w:.2f} ⚠️Risk:{risk_w:.2f}]{' ' * 8} │")
            
            # News TTL dynamic weight with progress bar
            if news_age_hours and ttl_weight:
                news_emoji = "🆕" if news_age_hours <= 2 else "⏰" if news_age_hours <= 12 else "🗞️"
                enhanced_lines.append(f"│ 📰 NEWS TTL: {news_emoji}age={news_age_hours:.1f}h → {ttl_bar} {ttl_weight:.2f}{' ' * 20} │")
            
            # TA active features with progress bar
            if ta_features_count and ta_active_features:
                ta_emoji = "🎯" if ta_active_features >= ta_features_count * 0.8 else "📊" if ta_active_features >= ta_features_count * 0.5 else "🔧"
                enhanced_lines.append(f"│ {ta_emoji} TA FEATURES: {ta_features_bar} {ta_active_features}/{ta_features_count} active{' ' * 20} │")
            
            # Hysteresis status with emoji
            if hyst_status:
                hyst_emoji = "✅" if hyst_status == "PASS" else "⏳" if hyst_status == "PENDING" else "❌"
                enhanced_lines.append(f"│ 🔄 HYST: {hyst_emoji}{hyst_status:52s} │")
            
            # State transition and action with emojis
            if state_trans and action:
                state_emoji = "🔄" if "→" in state_trans else "⚡"
                action_emoji = "🚀" if "OPEN" in action else "🛑" if "CLOSE" in action else "⏸️"
                enhanced_lines.append(f"│ {state_emoji} STATE: {state_trans:28s} {action_emoji}ACTION: {action:9s} │")
            
            # Add enhanced lines
            lines.extend(enhanced_lines)
            
            # Position sizing info with emojis
            size = data.get('position_size')
            lev = data.get('leverage')
            sl_atr = data.get('sl_atr')
            tp_atr = data.get('tp_atr')
            
            if size is not None or lev or sl_atr or tp_atr:
                size_emoji = "💰" if size and size > 2 else "💵" if size else ""
                lev_emoji = "⚡" if lev and lev > 2 else "🔋" if lev else ""
                sl_emoji = "🛡️" if sl_atr else ""
                tp_emoji = "🎯" if tp_atr else ""
                
                size_str = f"{size_emoji}size={size:.1f}%" if size is not None else ""
                lev_str = f"{lev_emoji}lev={lev:.0f}x" if lev else ""
                sl_str = f"{sl_emoji}SL={sl_atr:.1f}ATR" if sl_atr else ""
                tp_str = f"{tp_emoji}TP={tp_atr:.1f}ATR" if tp_atr else ""
                pos_line = f"{size_str} {lev_str} {sl_str} {tp_str}".strip()
                lines.append(f"│ 📊 POSITION: {pos_line:48s} │")
            
            # Risk info with emojis
            exp = data.get('risk_exposure')
            tier = data.get('risk_tier')
            cb = data.get('circuit_breaker')
            
            if exp is not None or tier or cb:
                risk_parts = []
                if exp is not None:
                    exp_emoji = "🔴" if exp > 10 else "🟡" if exp > 5 else "🟢"
                    risk_parts.append(f"{exp_emoji}exp={exp:.1f}%")
                if tier:
                    tier_emoji = "🔴" if tier == "HIGH" else "🟡" if tier == "MEDIUM" else "🟢"
                    risk_parts.append(f"{tier_emoji}tier={tier}")
                if cb:
                    cb_emoji = "🚨" if cb == "TRIGGERED" else "🟢" if cb == "NORMAL" else "🟡"
                    risk_parts.append(f"{cb_emoji}cb={cb}")
                risk_line = "⚠️ RISK: " + " ".join(risk_parts)
                lines.append(f"│ {risk_line:58s} │")
        
        lines.append(f"╰{'─' * (width - 2)}╯")
        
        return "\n".join(lines)
    
    def _create_bar(self, score: float, width: int = 10) -> str:
        """Create a simple progress bar."""
        filled = int((score / 100.0) * width)
        empty = width - filled
        return "█" * filled + "░" * empty
    
    def format_batch_summary(self, data: Dict[str, Any]) -> str:
        """
        Format batch analysis summary with enhanced features.
        
        Args:
            data: Summary data containing:
                - timeframe: str
                - total: int
                - success: int
                - fail: int
                - signals: Dict[str, int] (LONG, SHORT, HOLD counts)
                - avg_score: float
                - duration: float (seconds)
                - enhanced_features: Dict with new feature stats
        
        Returns:
            Formatted summary line
        """
        tf = data.get('timeframe', '?')
        total = data.get('total', 0)
        success = data.get('success', 0)
        fail = data.get('fail', 0)
        
        signals = data.get('signals', {})
        long_count = signals.get('LONG', 0)
        short_count = signals.get('SHORT', 0)
        hold_count = signals.get('HOLD', 0)
        
        avg_score = data.get('avg_score', 0.0)
        duration = data.get('duration', 0.0)
        
        # Enhanced features summary
        enhanced_features = data.get('enhanced_features', {})
        
        # Confidence-aware position sizing stats
        conf_stats = enhanced_features.get('confidence_stats', {})
        conf_mult_avg = conf_stats.get('avg_multiplier', 0.0)
        conf_high_count = conf_stats.get('high_confidence_count', 0)
        
        # Regime-adaptive weights stats
        regime_stats = enhanced_features.get('regime_stats', {})
        trend_regime_count = regime_stats.get('trend_regime_count', 0)
        sideways_regime_count = regime_stats.get('sideways_regime_count', 0)
        
        # News TTL stats
        news_ttl_stats = enhanced_features.get('news_ttl_stats', {})
        fresh_news_count = news_ttl_stats.get('fresh_news_count', 0)
        stale_news_count = news_ttl_stats.get('stale_news_count', 0)
        avg_ttl_weight = news_ttl_stats.get('avg_ttl_weight', 0.0)
        
        # TA features stats
        ta_features_stats = enhanced_features.get('ta_features_stats', {})
        avg_active_features = ta_features_stats.get('avg_active_features', 0.0)
        max_features_used = ta_features_stats.get('max_features_used', 0)
        
        # Build base summary
        base_summary = (
            f"✅ SUM | {tf} analysis | "
            f"total={total} success={success} fail={fail} | "
            f"signals: LONG={long_count} SHORT={short_count} HOLD={hold_count} | "
            f"avg_score={avg_score:.1f} | duration={duration:.1f}s"
        )
        
        # Add enhanced features if available
        enhanced_parts = []
        
        if conf_mult_avg > 0:
            enhanced_parts.append(f"conf_avg={conf_mult_avg:.2f}(high:{conf_high_count})")
        
        if trend_regime_count > 0 or sideways_regime_count > 0:
            enhanced_parts.append(f"regimes=[trend:{trend_regime_count} sideways:{sideways_regime_count}]")
        
        if fresh_news_count > 0 or stale_news_count > 0:
            enhanced_parts.append(f"news=[fresh:{fresh_news_count} stale:{stale_news_count} avg_ttl:{avg_ttl_weight:.2f}]")
        
        if avg_active_features > 0:
            enhanced_parts.append(f"ta_features=avg:{avg_active_features:.1f}/max:{max_features_used}")
        
        if enhanced_parts:
            enhanced_str = " | " + " ".join(enhanced_parts)
            return base_summary + enhanced_str
        else:
            return base_summary


# Global singleton instance
_log_formatter = None


def get_log_formatter() -> LogFormatter:
    """Get the global log formatter instance."""
    global _log_formatter
    if _log_formatter is None:
        _log_formatter = LogFormatter()
    return _log_formatter

