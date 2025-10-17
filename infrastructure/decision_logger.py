"""
Decision Logger - Structured logging for trading decisions
Follows Single Responsibility Principle: Only handles decision logging
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class DecisionLogger:
    """
    Logs trading decisions in structured JSONL format.
    
    Responsibilities:
    - Log every trading decision (OPEN, CLOSE, SKIP)
    - Structured JSONL format for easy parsing
    - Compact inline format for quick scanning
    - Daily log rotation
    """
    
    def __init__(self, log_dir: str = 'logs/decisions'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ DecisionLogger initialized: {self.log_dir}")
    
    def log_decision(
        self,
        symbol: str,
        composite_signal,
        action: str,
        position_size: float = 0.0,
        tp_price: Optional[float] = None,
        sl_price: Optional[float] = None,
        reason: str = "",
        gate_results: Optional[Dict] = None
    ):
        """
        Log a trading decision.
        
        Args:
            symbol: Trading symbol
            composite_signal: CompositeSignal object
            action: 'OPEN', 'CLOSE', 'SKIP', 'REJECTED'
            position_size: Position size in base currency
            tp_price: Take profit price
            sl_price: Stop loss price
            reason: Decision reason/explanation
            gate_results: Signal gate check results
        """
        try:
            timestamp = datetime.now(timezone.utc)
            
            # Extract gate status
            gate_status = self._format_gate_status(gate_results) if gate_results else "n/a"
            
            # Structured log entry (JSONL)
            log_entry = {
                # Timestamp
                't': timestamp.isoformat(),
                'ts_unix': int(timestamp.timestamp()),
                
                # Symbol
                'sym': symbol,
                
                # Composite signal
                'comp': round(composite_signal.final_score, 2),
                'dir': composite_signal.decision,
                'grade': composite_signal.grade,
                'conf': round(composite_signal.confidence_pct, 2),
                
                # Component scores
                'ta': round(composite_signal.technical.score, 2),
                'ml': round(composite_signal.ml.score, 2),
                'news': round(composite_signal.news.score, 2),
                'risk': round(composite_signal.risk.score, 2),
                
                # Technical flags
                'ta_trend': composite_signal.technical.flags.get('trend', 'n/a'),
                'ta_meanrev': composite_signal.technical.flags.get('meanrev', 'n/a'),
                'ta_breakout': composite_signal.technical.flags.get('breakout', 'n/a'),
                
                # Gate status
                'gate': gate_status,
                
                # Execution
                'action': action,
                'size': round(position_size, 6) if position_size else 0.0,
                'tp': round(tp_price, 2) if tp_price else None,
                'sl': round(sl_price, 2) if sl_price else None,
                
                # Metadata
                'reason': reason,
                'timeframe': composite_signal.timeframes.get('main', '15m'),
                'meta': composite_signal.meta
            }
            
            # Write to daily JSONL file
            self._write_jsonl(log_entry, timestamp)
            
            # Also log compact inline format for quick scanning
            self._log_compact(log_entry)
            
        except Exception as e:
            logger.error(f"❌ Failed to log decision: {e}")
    
    def _write_jsonl(self, entry: Dict, timestamp: datetime):
        """Write decision to JSONL file."""
        try:
            # Daily file rotation
            date_str = timestamp.strftime('%Y-%m-%d')
            log_file = self.log_dir / f"decisions_{date_str}.jsonl"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
                
        except Exception as e:
            logger.error(f"❌ Failed to write JSONL: {e}")
    
    def _log_compact(self, entry: Dict):
        """Log compact inline format for quick scanning."""
        try:
            # Compact format: t=... sym=... comp=... dir=... ta=... ml=... news=... risk=... gate=... action=... size=...
            compact = (
                f"t={entry['t'][11:19]} "  # HH:MM:SS only
                f"sym={entry['sym']:15} "
                f"comp={entry['comp']:5.1f} "
                f"dir={entry['dir']:5} "
                f"ta={entry['ta']:4.0f} "
                f"ml={entry['ml']:4.0f} "
                f"news={entry['news']:4.0f} "
                f"risk={entry['risk']:4.0f} "
                f"gate={entry['gate']:15} "
                f"action={entry['action']:8} "
                f"size={entry['size']:.6f}"
            )
            
            if entry.get('tp'):
                compact += f" tp={entry['tp']:.2f}"
            if entry.get('sl'):
                compact += f" sl={entry['sl']:.2f}"
            
            logger.info(f"[DECISION] {compact}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log compact format: {e}")
    
    def _format_gate_status(self, gate_results: Dict) -> str:
        """Format gate check results compactly."""
        try:
            if not gate_results:
                return "n/a"
            
            checks = []
            
            # Persistence
            if 'persistence' in gate_results:
                result = gate_results['persistence']
                checks.append(f"pers={result.get('passed', False)}")
            
            # Bias filters
            if 'bias' in gate_results:
                result = gate_results['bias']
                checks.append(f"bias={result.get('passed', False)}")
            
            # Reversal
            if 'reversal' in gate_results:
                result = gate_results['reversal']
                checks.append(f"rev={result.get('approved', False)}")
            
            return ','.join(checks) if checks else "pass"
            
        except Exception as e:
            logger.error(f"❌ Gate status formatting error: {e}")
            return "error"
    
    def get_recent_decisions(self, symbol: Optional[str] = None, limit: int = 10) -> list:
        """
        Get recent decisions from log.
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Max number of decisions to return
            
        Returns:
            List of decision entries
        """
        try:
            decisions = []
            
            # Get today's and yesterday's files
            today = datetime.now(timezone.utc)
            files_to_check = [
                self.log_dir / f"decisions_{today.strftime('%Y-%m-%d')}.jsonl",
                self.log_dir / f"decisions_{(today.replace(hour=0, minute=0) - timedelta(days=1)).strftime('%Y-%m-%d')}.jsonl"
            ]
            
            for log_file in files_to_check:
                if not log_file.exists():
                    continue
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            
                            # Filter by symbol if specified
                            if symbol and entry.get('sym') != symbol:
                                continue
                            
                            decisions.append(entry)
                            
                        except json.JSONDecodeError:
                            continue
            
            # Return most recent
            decisions.sort(key=lambda x: x.get('ts_unix', 0), reverse=True)
            return decisions[:limit]
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent decisions: {e}")
            return []


# Global instance
_decision_logger = None


def get_decision_logger() -> DecisionLogger:
    """Get global decision logger instance."""
    global _decision_logger
    if _decision_logger is None:
        _decision_logger = DecisionLogger()
    return _decision_logger

