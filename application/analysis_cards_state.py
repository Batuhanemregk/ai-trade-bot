"""
Shared state for analysis cards.
Stores latest analysis snapshot for Telegram summary/detail views.
"""

from __future__ import annotations

from datetime import datetime, timezone
import copy
from typing import Any, Dict, List, Optional

_latest_state: Dict[str, Any] = {}


def set_latest_analysis(bar_id: str, run_id: str, results: List[Dict[str, Any]]) -> None:
    """Persist latest analysis results for downstream consumers."""
    global _latest_state
    _latest_state = {
        "bar_id": bar_id,
        "run_id": run_id,
        "results": copy.deepcopy(results),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_latest_analysis() -> Dict[str, Any]:
    """Return latest analysis snapshot (may be empty dict)."""
    return _latest_state


def get_detail(symbol: str) -> Optional[Dict[str, Any]]:
    """Return detail dict for given symbol if available."""
    state = get_latest_analysis()
    results = state.get("results") or []
    for entry in results:
        if entry.get("symbol") == symbol:
            return entry
    return None


def get_symbols() -> List[str]:
    """Return list of symbols for latest analysis."""
    state = get_latest_analysis()
    results = state.get("results") or []
    return [entry.get("symbol") for entry in results if entry.get("symbol")]

