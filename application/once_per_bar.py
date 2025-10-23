"""
Simple once-per-bar guard to prevent duplicate actions within the same bar.
Key is based on (symbol, timeframe, bar_id).
Enabled via direct import; safe in-memory store with optional file persistence.
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Tuple, Set
from datetime import datetime, timezone


class OncePerBarGuard:
    def __init__(self, persist_path: str | None = None):
        self._hits: Set[Tuple[str, str, str]] = set()
        self.persist_path = persist_path or os.getenv("ONCE_PER_BAR_PATH", "data/once_per_bar.json")
        try:
            path = Path(self.persist_path)
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                for item in data:
                    self._hits.add((item[0], item[1], item[2]))
        except Exception:
            # Best-effort only
            pass

    def _save(self) -> None:
        try:
            path = Path(self.persist_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(list(self._hits)), encoding="utf-8")
        except Exception:
            # Best-effort only
            pass

    @staticmethod
    def current_bar_id(timeframe: str = "15m") -> str:
        now = datetime.now(timezone.utc)
        if timeframe.endswith("m"):
            minutes = int(timeframe[:-1])
            floored_minute = (now.minute // minutes) * minutes
            ts = now.replace(minute=floored_minute, second=0, microsecond=0)
        elif timeframe.endswith("h"):
            hours = int(timeframe[:-1])
            floored_hour = (now.hour // hours) * hours
            ts = now.replace(hour=floored_hour, minute=0, second=0, microsecond=0)
        else:
            ts = now.replace(second=0, microsecond=0)
        return ts.strftime("%Y-%m-%dT%H:%MZ")

    def hit(self, symbol: str, timeframe: str, bar_id: str | None = None) -> bool:
        bid = bar_id or self.current_bar_id(timeframe)
        key = (symbol, timeframe, bid)
        if key in self._hits:
            return True
        self._hits.add(key)
        self._save()
        return False



