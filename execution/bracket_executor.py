"""
Bracket order management utilities.
Handles bracket orders and their lifecycle, including post-fill TP/SL and OCO emulation.
"""

import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


class BracketState(Enum):
    """Bracket order state machine states."""
    ENTRY_SENT = "entry_sent"
    ENTRY_PARTIAL_FILLED = "entry_partial_filled"
    ENTRY_FILLED = "entry_filled"
    BRACKET_PENDING = "bracket_pending"
    BRACKET_PLACED = "bracket_placed"
    TP_FILLED = "tp_filled"
    SL_FILLED = "sl_filled"
    CANCELLED = "cancelled"


class BracketOrder:
    """Represents a bracket order with entry, TP, and SL."""
    
    def __init__(self, symbol: str, side: str, pos_side: str, qty: float,
                 entry_price: float, tp_price: float, sl_price: float,
                 entry_order_id: str, client_order_id: str):
        self.symbol = symbol
        self.side = side  # 'buy' or 'sell'
        self.pos_side = pos_side  # 'long' or 'short'
        self.qty = qty
        self.entry_price = entry_price
        self.tp_price = tp_price
        self.sl_price = sl_price
        self.entry_order_id = entry_order_id
        self.client_order_id = client_order_id
        
        # Bracket orders
        self.tp_order_id: Optional[str] = None
        self.sl_order_id: Optional[str] = None
        self.tp_algo_id: Optional[str] = None  # Algo ID for TP trigger order
        self.sl_algo_id: Optional[str] = None  # Algo ID for SL trigger order
        self.tp_trigger_price: Optional[float] = None
        self.sl_trigger_price: Optional[float] = None
        
        # State tracking
        self.state = BracketState.ENTRY_SENT
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # Fill tracking
        self.filled_qty = 0.0
        self.avg_fill_price = 0.0
    
    def update_state(self, new_state: BracketState):
        """Update bracket state."""
        self.state = new_state
        self.updated_at = datetime.now()
    
    def update_fill(self, fill_qty: float, fill_price: float):
        """Update fill information."""
        if self.filled_qty == 0:
            self.avg_fill_price = fill_price
        else:
            # Weighted average
            total_value = (self.filled_qty * self.avg_fill_price) + (fill_qty * fill_price)
            self.filled_qty += fill_qty
            self.avg_fill_price = total_value / self.filled_qty
        self.filled_qty += fill_qty
    
    def is_fully_filled(self) -> bool:
        """Check if entry order is fully filled."""
        return abs(self.filled_qty - self.qty) < 0.0001
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'pos_side': self.pos_side,
            'qty': self.qty,
            'entry_price': self.entry_price,
            'tp_price': self.tp_price,
            'sl_price': self.sl_price,
            'entry_order_id': self.entry_order_id,
            'client_order_id': self.client_order_id,
            'tp_order_id': self.tp_order_id,
            'sl_order_id': self.sl_order_id,
            'tp_algo_id': self.tp_algo_id,
            'sl_algo_id': self.sl_algo_id,
            'tp_trigger_price': self.tp_trigger_price,
            'sl_trigger_price': self.sl_trigger_price,
            'state': self.state.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'filled_qty': self.filled_qty,
            'avg_fill_price': self.avg_fill_price
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BracketOrder':
        """Create BracketOrder from dictionary."""
        bracket = cls(
            symbol=data['symbol'],
            side=data['side'],
            pos_side=data['pos_side'],
            qty=data['qty'],
            entry_price=data['entry_price'],
            tp_price=data['tp_price'],
            sl_price=data['sl_price'],
            entry_order_id=data['entry_order_id'],
            client_order_id=data['client_order_id']
        )
        
        bracket.tp_order_id = data.get('tp_order_id')
        bracket.sl_order_id = data.get('sl_order_id')
        bracket.tp_algo_id = data.get('tp_algo_id')
        bracket.sl_algo_id = data.get('sl_algo_id')
        bracket.tp_trigger_price = data.get('tp_trigger_price')
        bracket.sl_trigger_price = data.get('sl_trigger_price')
        bracket.state = BracketState(data['state'])
        bracket.created_at = datetime.fromisoformat(data['created_at'])
        bracket.updated_at = datetime.fromisoformat(data['updated_at'])
        bracket.filled_qty = data.get('filled_qty', 0.0)
        bracket.avg_fill_price = data.get('avg_fill_price', 0.0)
        
        return bracket
    
    def __repr__(self):
        return (f"BracketOrder(symbol='{self.symbol}', side='{self.side}', "
                f"pos_side='{self.pos_side}', qty={self.qty}, "
                f"state='{self.state.value}')")


class BracketOrderManager:
    """Manages bracket orders and their lifecycle."""
    
    def __init__(self, state_dir: str = "state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        self.brackets: Dict[str, BracketOrder] = {}  # client_order_id -> BracketOrder
        self.state_file = self.state_dir / "bracket_orders.json"
        self.load_brackets()
    
    def load_brackets(self):
        """Load brackets from persistent storage."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for bracket_data in data.values():
                        bracket = BracketOrder.from_dict(bracket_data)
                        self.brackets[bracket.client_order_id] = bracket
                print(f"✅ Loaded {len(self.brackets)} bracket orders from storage")
            else:
                print("📁 No existing bracket orders found, starting fresh")
        except Exception as e:
            print(f"❌ Failed to load bracket orders: {e}")
    
    def save_brackets(self):
        """Save brackets to persistent storage."""
        try:
            data = {client_id: bracket.to_dict() for client_id, bracket in self.brackets.items()}
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Failed to save bracket orders: {e}")
    
    def add_bracket(self, bracket: BracketOrder):
        """Add a new bracket order."""
        self.brackets[bracket.client_order_id] = bracket
        self.save_brackets()
        print(f"✅ Added bracket order: {bracket.symbol} {bracket.side} {bracket.qty}")
    
    def get_bracket(self, client_order_id: str) -> Optional[BracketOrder]:
        """Get bracket by client order ID."""
        return self.brackets.get(client_order_id)
    
    def update_bracket_state(self, client_order_id: str, new_state: BracketState):
        """Update bracket state."""
        if client_order_id in self.brackets:
            self.brackets[client_order_id].update_state(new_state)
            self.save_brackets()
    
    def get_brackets_by_symbol(self, symbol: str) -> List[BracketOrder]:
        """Get all brackets for a specific symbol."""
        return [b for b in self.brackets.values() if b.symbol == symbol]
    
    def get_pending_brackets(self) -> List[BracketOrder]:
        """Get brackets that need bracket orders placed."""
        return [b for b in self.brackets.values()
                if b.state in [BracketState.ENTRY_FILLED, BracketState.BRACKET_PENDING]]
    
    def cleanup_filled_brackets(self):
        """Remove brackets that are fully filled and closed."""
        to_remove = []
        for client_id, bracket in self.brackets.items():
            if bracket.state in [BracketState.TP_FILLED, BracketState.SL_FILLED, BracketState.CANCELLED]:
                to_remove.append(client_id)
        
        for client_id in to_remove:
            del self.brackets[client_id]
        
        if to_remove:
            self.save_brackets()
            print(f"🧹 Cleaned up {len(to_remove)} completed brackets")
    
    def get_bracket_stats(self) -> Dict[str, Any]:
        """Get statistics about bracket orders."""
        stats = {
            'total_brackets': len(self.brackets),
            'by_state': {},
            'by_symbol': {},
            'by_side': {},
            'recent_activity': {}
        }
        
        # Count by state
        for bracket in self.brackets.values():
            state = bracket.state.value
            if state not in stats['by_state']:
                stats['by_state'][state] = 0
            stats['by_state'][state] += 1
        
        # Count by symbol
        for bracket in self.brackets.values():
            symbol = bracket.symbol
            if symbol not in stats['by_symbol']:
                stats['by_symbol'][symbol] = 0
            stats['by_symbol'][symbol] += 1
        
        # Count by side
        for bracket in self.brackets.values():
            side = bracket.side
            if side not in stats['by_side']:
                stats['by_side'][side] = 0
            stats['by_side'][side] += 1
        
        # Recent activity (last 24h)
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        for bracket in self.brackets.values():
            if bracket.created_at > cutoff:
                date_str = bracket.created_at.strftime('%Y-%m-%d')
                if date_str not in stats['recent_activity']:
                    stats['recent_activity'][date_str] = 0
                stats['recent_activity'][date_str] += 1
        
        return stats
    
    def cancel_bracket(self, client_order_id: str) -> bool:
        """Cancel a bracket order."""
        if client_order_id in self.brackets:
            self.brackets[client_order_id].update_state(BracketState.CANCELLED)
            self.save_brackets()
            print(f"❌ Cancelled bracket order: {client_order_id}")
            return True
        return False
    
    def get_expired_brackets(self, max_age_hours: int = 24) -> List[BracketOrder]:
        """Get brackets that are older than specified age."""
        cutoff = datetime.now().replace(hour=datetime.now().hour - max_age_hours)
        return [b for b in self.brackets.values() if b.created_at < cutoff]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for compatibility."""
        return self.get_bracket_stats()


class BracketOrderExecutor:
    """Executes bracket order operations."""
    
    def __init__(self, bracket_manager: BracketOrderManager):
        self.bracket_manager = bracket_manager
    
    async def create_bracket_order(self, symbol: str, side: str, pos_side: str, qty: float,
                                 entry_price: float, tp_price: float, sl_price: float,
                                 client_order_id: str) -> BracketOrder:
        """Create a new bracket order."""
        # Create bracket order
        bracket = BracketOrder(
            symbol=symbol,
            side=side,
            pos_side=pos_side,
            qty=qty,
            entry_price=entry_price,
            tp_price=tp_price,
            sl_price=sl_price,
            entry_order_id="",  # Will be set when entry order is placed
            client_order_id=client_order_id
        )
        
        # Add to manager
        self.bracket_manager.add_bracket(bracket)
        
        return bracket
    
    async def place_entry_order(self, client_order_id: str, entry_order_id: str) -> bool:
        """Place entry order for bracket."""
        bracket = self.bracket_manager.get_bracket(client_order_id)
        if not bracket:
            print(f"❌ Bracket not found: {client_order_id}")
            return False
        
        bracket.entry_order_id = entry_order_id
        bracket.update_state(BracketState.ENTRY_SENT)
        self.bracket_manager.save_brackets()
        
        print(f"✅ Entry order placed for bracket: {client_order_id}")
        return True
    
    async def handle_entry_fill(self, client_order_id: str, fill_qty: float, fill_price: float) -> bool:
        """Handle entry order fill."""
        bracket = self.bracket_manager.get_bracket(client_order_id)
        if not bracket:
            print(f"❌ Bracket not found: {client_order_id}")
            return False
        
        # Update fill information
        bracket.update_fill(fill_qty, fill_price)
        
        # Check if fully filled
        if bracket.is_fully_filled():
            bracket.update_state(BracketState.ENTRY_FILLED)
            print(f"✅ Entry order fully filled for bracket: {client_order_id}")
        else:
            bracket.update_state(BracketState.ENTRY_PARTIAL_FILLED)
            print(f"⚠️ Entry order partially filled for bracket: {client_order_id}")
        
        self.bracket_manager.save_brackets()
        return True
    
    async def place_bracket_orders(self, client_order_id: str, tp_order_id: str, sl_order_id: str) -> bool:
        """Place TP and SL orders for bracket."""
        bracket = self.bracket_manager.get_bracket(client_order_id)
        if not bracket:
            print(f"❌ Bracket not found: {client_order_id}")
            return False
        
        if bracket.state != BracketState.ENTRY_FILLED:
            print(f"❌ Cannot place bracket orders: entry not filled for {client_order_id}")
            return False
        
        # Set order IDs
        bracket.tp_order_id = tp_order_id
        bracket.sl_order_id = sl_order_id
        
        # Update state
        bracket.update_state(BracketState.BRACKET_PLACED)
        self.bracket_manager.save_brackets()
        
        print(f"✅ Bracket orders placed for: {client_order_id}")
        return True
    
    async def handle_tp_fill(self, client_order_id: str) -> bool:
        """Handle take profit fill."""
        bracket = self.bracket_manager.get_bracket(client_order_id)
        if not bracket:
            print(f"❌ Bracket not found: {client_order_id}")
            return False
        
        bracket.update_state(BracketState.TP_FILLED)
        self.bracket_manager.save_brackets()
        
        print(f"✅ Take profit filled for bracket: {client_order_id}")
        return True
    
    async def handle_sl_fill(self, client_order_id: str) -> bool:
        """Handle stop loss fill."""
        bracket = self.bracket_manager.get_bracket(client_order_id)
        if not bracket:
            print(f"❌ Bracket not found: {client_order_id}")
            return False
        
        bracket.update_state(BracketState.SL_FILLED)
        self.bracket_manager.save_brackets()
        
        print(f"✅ Stop loss filled for bracket: {client_order_id}")
        return True


# Global instances
_bracket_manager = None
_bracket_executor = None

def get_bracket_manager() -> BracketOrderManager:
    """Get the global bracket manager instance."""
    global _bracket_manager
    if _bracket_manager is None:
        _bracket_manager = BracketOrderManager()
    return _bracket_manager

def get_bracket_executor() -> BracketOrderExecutor:
    """Get the global bracket executor instance."""
    global _bracket_executor
    if _bracket_executor is None:
        _bracket_executor = BracketOrderExecutor(get_bracket_manager())
    return _bracket_executor
