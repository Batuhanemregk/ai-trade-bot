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
        """Format as single line."""
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
        
        return (
            f"ℹ️ {ts} | {symbol} | tf={tf} | "
            f"TA={ta:.1f} ML={ml:.1f} News={news:.1f} Risk={risk:.1f} | "
            f"Final={final:.1f} ({grade}) | Dir={direction}{age_str} | "
            f"Gate={gate_status} (persist {persist}, conf {conf})"
        )
    
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
        
        if hyst_status or state_trans or action:
            lines.append(f"│ {'─' * (width - 2)} │")
            
            if hyst_status:
                lines.append(f"│ hyst={hyst_status:56s} │")
            
            if state_trans and action:
                lines.append(f"│ state: {state_trans:32s} action={action:13s} │")
            
            # Position sizing info
            size = data.get('position_size')
            lev = data.get('leverage')
            sl_atr = data.get('sl_atr')
            tp_atr = data.get('tp_atr')
            
            if size is not None or lev or sl_atr or tp_atr:
                size_str = f"size={size:.1f}%" if size is not None else ""
                lev_str = f"lev={lev:.0f}x" if lev else ""
                sl_str = f"SL={sl_atr:.1f}ATR" if sl_atr else ""
                tp_str = f"TP={tp_atr:.1f}ATR" if tp_atr else ""
                pos_line = f"{size_str} {lev_str} {sl_str} {tp_str}".strip()
                lines.append(f"│ {pos_line:60s} │")
            
            # Risk info
            exp = data.get('risk_exposure')
            tier = data.get('risk_tier')
            cb = data.get('circuit_breaker')
            
            if exp is not None or tier or cb:
                risk_parts = []
                if exp is not None:
                    risk_parts.append(f"exp={exp:.1f}%")
                if tier:
                    risk_parts.append(f"tier={tier}")
                if cb:
                    risk_parts.append(f"cb={cb}")
                risk_line = "risk: " + " ".join(risk_parts)
                lines.append(f"│ {risk_line:60s} │")
        
        lines.append(f"╰{'─' * (width - 2)}╯")
        
        return "\n".join(lines)
    
    def _create_bar(self, score: float, width: int = 10) -> str:
        """Create a simple progress bar."""
        filled = int((score / 100.0) * width)
        empty = width - filled
        return "█" * filled + "░" * empty
    
    def format_batch_summary(self, data: Dict[str, Any]) -> str:
        """
        Format batch analysis summary.
        
        Args:
            data: Summary data containing:
                - timeframe: str
                - total: int
                - success: int
                - fail: int
                - signals: Dict[str, int] (LONG, SHORT, HOLD counts)
                - avg_score: float
                - duration: float (seconds)
        
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
        
        return (
            f"✅ SUM | {tf} analysis | "
            f"total={total} success={success} fail={fail} | "
            f"signals: LONG={long_count} SHORT={short_count} HOLD={hold_count} | "
            f"avg_score={avg_score:.1f} | duration={duration:.1f}s"
        )


# Global singleton instance
_log_formatter = None


def get_log_formatter() -> LogFormatter:
    """Get the global log formatter instance."""
    global _log_formatter
    if _log_formatter is None:
        _log_formatter = LogFormatter()
    return _log_formatter

