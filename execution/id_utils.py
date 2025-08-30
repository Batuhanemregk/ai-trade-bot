# execution/id_utils.py
"""
ID generation, validation, and uniqueness management for OKX trading bot.
Handles client order IDs for both entry orders and algo/trigger orders.
"""

from __future__ import annotations
import os
import json
import random
import time
import re
import threading
from pathlib import Path
from typing import Literal, Optional

# ID validation regex: alphanumeric only, 1-32 chars
_ID_RE = re.compile(r"^[A-Za-z0-9]{1,32}$")

# Thread-safe storage for seen IDs
_LOCK = threading.Lock()
_STORE = {"seen": set(), "path": None}


def _base36(n: int) -> str:
    """Convert integer to base36 string."""
    s = ""
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0:
        return "0"
    neg = n < 0
    n = abs(n)
    while n:
        n, r = divmod(n, 36)
        s = chars[r] + s
    return "-" + s if neg else s


def _store_path() -> Path:
    """Get path for ID storage file."""
    p = Path("state/ids")
    p.mkdir(parents=True, exist_ok=True)
    return p / "used_ids.json"


def _load_store():
    """Load seen IDs from persistent storage."""
    with _LOCK:
        if _STORE["path"] is None:
            _STORE["path"] = _store_path()
            if _STORE["path"].exists():
                try:
                    data = json.loads(_STORE["path"].read_text())
                    _STORE["seen"] = set(data.get("seen", []))
                except Exception:
                    _STORE["seen"] = set()


def _save_store():
    """Save seen IDs to persistent storage."""
    with _LOCK:
        try:
            _STORE["path"].write_text(json.dumps({"seen": sorted(_STORE["seen"])}))
        except Exception:
            pass


def validate_id(value: str) -> bool:
    """Validate ID format: alphanumeric, 1-32 chars."""
    return bool(_ID_RE.match(value or ""))


def _normalize(raw: str) -> str:
    """Normalize raw string to valid ID format."""
    if not raw:
        return ""
    # Keep only A-Z, 0-9
    out = "".join(ch for ch in raw.upper() if ("A" <= ch <= "Z") or ("0" <= ch <= "9"))
    return out[:32]


def _unique(candidate: str) -> str:
    """Ensure ID uniqueness by checking against seen IDs."""
    _load_store()
    with _LOCK:
        i = 0
        v = candidate
        while v in _STORE["seen"]:
            # Add 2-digit base36 suffix to make unique
            suffix = _base36(random.getrandbits(8)).rjust(2, "0")[:2]
            v = (candidate[:30] + suffix)[:32]
            i += 1
            if i > 5:  # Max 5 attempts
                break
        _STORE["seen"].add(v)
    _save_store()
    return v


def generate_client_id(prefix: Literal["E", "A"], *, numeric: bool = False) -> str:
    """
    Generate unique client order ID.
    
    Args:
        prefix: "E" for entry order, "A" for algo/trigger
        numeric: If True, use numeric format for fills echo compatibility
    
    Returns:
        Unique alphanumeric ID ≤32 chars
    """
    # E: entry order, A: algo/trigger
    now = int(time.time() * 1000)
    r = random.getrandbits(20)
    
    if numeric:
        # PLAIN decimal, stay within int64 limits
        core = str(now)[-11:] + str(r % 10**5).rjust(5, "0")
        cand = prefix + core
    else:
        core = _base36(now) + _base36(r)
        cand = prefix + core
    
    cand = _normalize(cand)
    if not cand:
        cand = prefix + _base36(now)
        cand = _normalize(cand)
    
    if not validate_id(cand):
        cand = prefix + _base36(now)[:30]
        cand = _normalize(cand)
    
    return _unique(cand)


def generate_algo_id(prefix: str = 'A', length: Optional[int] = None) -> str:
    """
    Generate a unique algo order ID.
    
    Args:
        prefix: ID prefix (E=entry, A=algo, T=test, D=debug)
        length: ID length (default: 16, min: 8, max: 32)
    
    Returns:
        Unique alphanumeric algo order ID
    """
    # Allow E prefix for entry orders
    if prefix not in ['E', 'A', 'T', 'D']:
        prefix = 'A'  # Default to algo prefix
    
    # Use the new generate_client_id for consistency
    return generate_client_id(prefix, numeric=False)


def validate_client_id(id_str: str) -> bool:
    """
    Validate a client order ID.
    
    Args:
        id_str: ID to validate
    
    Returns:
        True if valid, False otherwise
    """
    # Client IDs must have valid format AND start with valid prefix
    if not validate_id(id_str):
        return False
    
    # Must start with valid prefix (E=entry, A=algo)
    if not id_str or id_str[0] not in ['E', 'A']:
        return False
    
    return True


def regenerate_client_id(old_id: str, prefix: str = None, length: Optional[int] = None) -> str:
    """
    Regenerate a client order ID.
    
    Args:
        old_id: Old ID to replace
        prefix: New prefix (uses old prefix if None)
        length: New length (uses old length if None)
    
    Returns:
        New unique client order ID
    """
    if prefix is None:
        prefix = old_id[0] if old_id else 'E'
    
    # Use the new generate_client_id for consistency
    return generate_client_id(prefix, numeric=False)


def is_id_used(id_str: str) -> bool:
    """Check if an ID is already used."""
    try:
        # Look up .state/ids/used_ids.json (create if missing)
        # Support environment variable for testing
        base_state_dir = os.environ.get("AIBOTBS_STATE_DIR", "state")
        state_dir = Path(base_state_dir)
        ids_file = state_dir / "ids" / "used_ids.json"
        
        # Create directory if missing
        ids_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not ids_file.exists():
            # Create empty file if missing
            with open(ids_file, 'w') as f:
                json.dump({"used_ids": []}, f)
            return False
        
        # Read existing IDs - handle both formats
        with open(ids_file, 'r') as f:
            data = json.load(f)
            # Handle both {"used_ids": [...]} and [...] formats
            if isinstance(data, dict):
                used_ids = data.get("used_ids", [])
            elif isinstance(data, list):
                used_ids = data
            else:
                used_ids = []
        
        return id_str in used_ids
        
    except Exception as e:
        print(f"⚠️ Error checking ID usage: {e}")
        return False


__all__ = [
    "validate_id",
    "generate_client_id",
    "generate_algo_id",
    "validate_client_id",
    "regenerate_client_id",
    "is_id_used",
]
