"""
Exit Strategies - Pure Calculation Functions

Testable, deterministic functions for all exit strategy calculations.
No exchange dependencies - can be unit tested in isolation.

Strategies:
- Trailing Stop (activation, breakeven, tight)
- Partial Take Profit (multi-level)
- Time-Based Exit
- Stop Hit Detection
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class TrailingMode(Enum):
    NOT_ACTIVATED = "NOT_ACTIVATED"
    NORMAL = "NORMAL"
    BREAKEVEN = "BREAKEVEN"
    TIGHT = "TIGHT"


@dataclass
class TrailingStopResult:
    """Result of trailing stop calculation."""
    mode: TrailingMode
    new_stop_price: float
    should_update: bool
    reason: str


@dataclass
class PartialTPResult:
    """Result of partial TP check."""
    should_close: bool
    level_index: int
    level_r: float
    close_pct: float
    close_size: float
    reason: str


@dataclass
class TimeExitResult:
    """Result of time exit check."""
    should_exit: bool
    should_warn: bool
    age_hours: float
    action: str  # 'close', 'alert', 'reduce'
    reason: str


# ============================================================
# R-MULTIPLE CALCULATION
# ============================================================

def calculate_r_multiple(
    entry_price: float,
    current_price: float,
    stop_loss: float,
    side: str
) -> float:
    """
    Calculate R-multiple for a position.
    
    R-multiple = (current profit) / (initial risk)
    
    Args:
        entry_price: Position entry price
        current_price: Current market price  
        stop_loss: Stop loss price
        side: 'long' or 'short'
        
    Returns:
        R-multiple value (positive = profit, negative = loss)
    """
    risk = abs(entry_price - stop_loss)
    if risk == 0:
        return 0.0
    
    if side == 'long':
        pnl = current_price - entry_price
    else:
        pnl = entry_price - current_price
    
    return pnl / risk


def calculate_r_multiple_simple(
    entry_price: float,
    current_price: float,
    side: str
) -> float:
    """
    Calculate simple R-multiple (as percentage of entry).
    
    Used when stop_loss is not available.
    This matches the logic in trailing_5m.py._calculate_r_multiple()
    """
    if entry_price == 0:
        return 0.0
        
    if side == 'long':
        return (current_price - entry_price) / entry_price
    else:
        return (entry_price - current_price) / entry_price


# ============================================================
# TRAILING STOP CALCULATION
# ============================================================

def compute_trailing_stop(
    entry_price: float,
    current_price: float,
    side: str,
    r_multiple: float,
    config: Dict[str, Any],
    current_stop: Optional[float] = None
) -> TrailingStopResult:
    """
    Compute trailing stop level based on R-multiple.
    
    Logic:
    - R < activation_r: Not activated
    - activation_r <= R < breakeven_r: Normal trail (2% offset)
    - breakeven_r <= R < tight_r: Breakeven (entry price)
    - R >= tight_r: Tight trail (0.3% offset from current)
    
    Args:
        entry_price: Position entry price
        current_price: Current market price
        side: 'long' or 'short'
        r_multiple: Current R-multiple
        config: Trailing config dict with keys:
            - activation_r_multiple (default 0.5)
            - breakeven_r_multiple (default 1.0)
            - tight_r_multiple (default 1.5)
            - tight_offset (default 0.3, as percentage)
        current_stop: Current stop loss price (optional)
            
    Returns:
        TrailingStopResult with mode, new_stop_price, should_update
    """
    activation_r = config.get('activation_r_multiple', 0.5)
    breakeven_r = config.get('breakeven_r_multiple', 1.0)
    tight_r = config.get('tight_r_multiple', 1.5)
    tight_offset_pct = config.get('tight_offset', 0.3) / 100  # Convert to decimal
    normal_trail_pct = 0.02  # 2% for normal trailing
    breakeven_buffer = 0.001  # 0.1% buffer for breakeven
    
    # Check activation threshold
    if r_multiple < activation_r:
        return TrailingStopResult(
            mode=TrailingMode.NOT_ACTIVATED,
            new_stop_price=current_stop or 0.0,
            should_update=False,
            reason=f"R={r_multiple:.3f} < activation={activation_r}"
        )
    
    # Determine mode and calculate new stop
    if r_multiple >= tight_r:
        mode = TrailingMode.TIGHT
        if side == 'long':
            new_stop = current_price * (1 - tight_offset_pct)
        else:
            new_stop = current_price * (1 + tight_offset_pct)
        reason = f"Tight trail @ R={r_multiple:.2f}, offset={tight_offset_pct*100:.1f}%"
        
    elif r_multiple >= breakeven_r:
        mode = TrailingMode.BREAKEVEN
        if side == 'long':
            new_stop = entry_price * (1 + breakeven_buffer)
        else:
            new_stop = entry_price * (1 - breakeven_buffer)
        reason = f"Breakeven @ R={r_multiple:.2f}"
        
    else:
        mode = TrailingMode.NORMAL
        if side == 'long':
            new_stop = current_price * (1 - normal_trail_pct)
        else:
            new_stop = current_price * (1 + normal_trail_pct)
        reason = f"Normal trail @ R={r_multiple:.2f}, offset=2%"
    
    # Check if update is beneficial
    should_update = True
    if current_stop is not None:
        if side == 'long':
            should_update = new_stop > current_stop
        else:
            should_update = new_stop < current_stop
        
        if not should_update:
            reason = f"New stop {new_stop:.4f} not better than current {current_stop:.4f}"
    
    return TrailingStopResult(
        mode=mode,
        new_stop_price=new_stop,
        should_update=should_update,
        reason=reason
    )


def is_stop_hit(
    current_price: float,
    stop_price: float,
    side: str
) -> bool:
    """
    Check if stop loss is hit.
    
    Args:
        current_price: Current market price
        stop_price: Stop loss price
        side: 'long' or 'short'
        
    Returns:
        True if stop is hit
    """
    if side == 'long':
        return current_price <= stop_price
    else:
        return current_price >= stop_price


# ============================================================
# PARTIAL TAKE PROFIT
# ============================================================

def check_partial_tp_levels(
    r_multiple: float,
    position_size: float,
    config: Dict[str, Any],
    executed_levels: List[int]
) -> List[PartialTPResult]:
    """
    Check which partial TP levels should be executed.
    
    Args:
        r_multiple: Current R-multiple
        position_size: Current position size
        config: Partial TP config with 'levels' list, each containing:
            - r_multiple: R level to trigger
            - close_pct: Percentage to close (0-1)
        executed_levels: List of already executed level indices
        
    Returns:
        List of PartialTPResult for levels that should execute
    """
    levels = config.get('levels', [])
    results = []
    
    for i, level in enumerate(levels):
        # Skip already executed levels
        if i in executed_levels:
            continue
            
        level_r = level.get('r_multiple', 0)
        close_pct = level.get('close_pct', 0)
        
        if r_multiple >= level_r:
            close_size = position_size * close_pct
            results.append(PartialTPResult(
                should_close=True,
                level_index=i,
                level_r=level_r,
                close_pct=close_pct,
                close_size=close_size,
                reason=f"Level {i+1} hit: R={r_multiple:.2f} >= {level_r}"
            ))
    
    return results


def get_remaining_size_after_partial_tp(
    original_size: float,
    config: Dict[str, Any],
    executed_levels: List[int]
) -> float:
    """
    Calculate remaining position size after partial TPs.
    
    Args:
        original_size: Original position size
        config: Partial TP config
        executed_levels: List of executed level indices
        
    Returns:
        Remaining position size
    """
    levels = config.get('levels', [])
    total_closed_pct = 0.0
    
    for i in executed_levels:
        if i < len(levels):
            total_closed_pct += levels[i].get('close_pct', 0)
    
    remaining_pct = max(0, 1.0 - total_closed_pct)
    return original_size * remaining_pct


# ============================================================
# TIME-BASED EXIT
# ============================================================

def check_time_exit(
    opened_at: datetime,
    current_time: datetime,
    config: Dict[str, Any]
) -> TimeExitResult:
    """
    Check if position should be closed due to age.
    
    Args:
        opened_at: Position open timestamp
        current_time: Current timestamp
        config: Time exit config with:
            - max_position_age_hours (default 24)
            - warning_hours (default 20)
            - stale_position_action (default 'close')
            
    Returns:
        TimeExitResult with should_exit, should_warn, etc.
    """
    max_age_hours = config.get('max_position_age_hours', 24)
    warning_hours = config.get('warning_hours', 20)
    action = config.get('stale_position_action', 'close')
    
    age = current_time - opened_at
    age_hours = age.total_seconds() / 3600
    
    if age_hours >= max_age_hours:
        return TimeExitResult(
            should_exit=True,
            should_warn=False,
            age_hours=age_hours,
            action=action,
            reason=f"Max age reached: {age_hours:.1f}h >= {max_age_hours}h"
        )
    
    if age_hours >= warning_hours:
        remaining = max_age_hours - age_hours
        return TimeExitResult(
            should_exit=False,
            should_warn=True,
            age_hours=age_hours,
            action=action,
            reason=f"Warning: {age_hours:.1f}h old, {remaining:.1f}h until exit"
        )
    
    return TimeExitResult(
        should_exit=False,
        should_warn=False,
        age_hours=age_hours,
        action=action,
        reason=f"OK: {age_hours:.1f}h < {warning_hours}h warning threshold"
    )


# ============================================================
# FIXED TP/SL CHECK
# ============================================================

def check_fixed_tp_sl(
    current_price: float,
    take_profit: float,
    stop_loss: float,
    side: str
) -> Tuple[bool, str]:
    """
    Check if fixed TP or SL is hit.
    
    Args:
        current_price: Current market price
        take_profit: Take profit price
        stop_loss: Stop loss price
        side: 'long' or 'short'
        
    Returns:
        Tuple of (is_triggered, trigger_type)
        trigger_type is 'TP', 'SL', or 'NONE'
    """
    if side == 'long':
        if current_price >= take_profit:
            return True, 'TP'
        if current_price <= stop_loss:
            return True, 'SL'
    else:
        if current_price <= take_profit:
            return True, 'TP'
        if current_price >= stop_loss:
            return True, 'SL'
    
    return False, 'NONE'
