"""
Paper Executor - Virtual order execution for PAPER mode
Handles virtual fills, position tracking, and simulated PnL
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class VirtualOrder:
    """Virtual order for paper trading"""
    order_id: str
    client_order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    price: float
    status: str  # 'filled', 'cancelled'
    created_at: datetime
    filled_at: Optional[datetime] = None
    fill_price: Optional[float] = None

@dataclass
class VirtualPosition:
    """Virtual position for paper trading"""
    symbol: str
    side: str  # 'long' or 'short'
    quantity: float
    entry_price: float
    entry_time: datetime
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    sl_order_id: Optional[str] = None
    tp_order_id: Optional[str] = None

class PaperExecutor:
    """Handles virtual order execution and position management"""
    
    def __init__(self):
        self.positions: Dict[str, VirtualPosition] = {}
        self.orders: Dict[str, VirtualOrder] = {}
        self.order_counter = 0
        
    def create_virtual_order(self, symbol: str, side: str, quantity: float, 
                           price: float, client_order_id: str) -> VirtualOrder:
        """Create a virtual order"""
        self.order_counter += 1
        order_id = f"PAPER_{self.order_counter:06d}"
        
        order = VirtualOrder(
            order_id=order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            status='filled',  # Paper orders are immediately filled
            created_at=datetime.now(),
            filled_at=datetime.now(),
            fill_price=price
        )
        
        self.orders[order_id] = order
        
        logger.info(f"[PAPER] Virtual order created: {order_id} {symbol} {side} {quantity}@{price}")
        
        return order
    
    def create_virtual_position(self, order: VirtualOrder) -> VirtualPosition:
        """Create a virtual position from a filled order"""
        symbol = order.symbol
        side = 'long' if order.side == 'buy' else 'short'
        
        position = VirtualPosition(
            symbol=symbol,
            side=side,
            quantity=order.quantity,
            entry_price=order.fill_price,
            entry_time=order.filled_at
        )
        
        self.positions[symbol] = position
        
        logger.info(f"[PAPER] Virtual position created: {symbol} {side} {order.quantity}@{order.fill_price}")
        
        return position
    
    def create_virtual_bracket_orders(self, position: VirtualPosition, 
                                    sl_price: float, tp_price: float) -> Dict[str, str]:
        """Create virtual SL and TP orders"""
        symbol = position.symbol
        side = 'sell' if position.side == 'long' else 'buy'
        
        # Create SL order
        sl_order_id = f"PAPER_SL_{self.order_counter + 1:06d}"
        sl_order = VirtualOrder(
            order_id=sl_order_id,
            client_order_id=f"{symbol}:SL:{position.entry_time.strftime('%Y%m%d_%H%M%S')}",
            symbol=symbol,
            side=side,
            quantity=position.quantity,
            price=sl_price,
            status='open',
            created_at=datetime.now()
        )
        
        # Create TP order
        tp_order_id = f"PAPER_TP_{self.order_counter + 2:06d}"
        tp_order = VirtualOrder(
            order_id=tp_order_id,
            client_order_id=f"{symbol}:TP:{position.entry_time.strftime('%Y%m%d_%H%M%S')}",
            symbol=symbol,
            side=side,
            quantity=position.quantity,
            price=tp_price,
            status='open',
            created_at=datetime.now()
        )
        
        self.orders[sl_order_id] = sl_order
        self.orders[tp_order_id] = tp_order
        
        # Update position with bracket order IDs
        position.sl_order_id = sl_order_id
        position.tp_order_id = tp_order_id
        
        logger.info(f"[PAPER] Virtual bracket orders created: {symbol} SL@{sl_price} TP@{tp_price}")
        
        return {
            'sl_order_id': sl_order_id,
            'tp_order_id': tp_order_id
        }
    
    def modify_virtual_order(self, order_id: str, new_price: float) -> bool:
        """Modify a virtual order (for trailing stops)"""
        if order_id not in self.orders:
            logger.warning(f"[PAPER] Order not found for modification: {order_id}")
            return False
        
        order = self.orders[order_id]
        old_price = order.price
        order.price = new_price
        
        logger.info(f"[PAPER] Virtual order modified: {order_id} {old_price} → {new_price}")
        
        return True
    
    def close_virtual_position(self, symbol: str, exit_price: float) -> Optional[VirtualPosition]:
        """Close a virtual position"""
        if symbol not in self.positions:
            logger.warning(f"[PAPER] Position not found for closing: {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Calculate PnL
        if position.side == 'long':
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
        
        position.realized_pnl = pnl
        
        # Close bracket orders
        if position.sl_order_id and position.sl_order_id in self.orders:
            self.orders[position.sl_order_id].status = 'cancelled'
        if position.tp_order_id and position.tp_order_id in self.orders:
            self.orders[position.tp_order_id].status = 'cancelled'
        
        # Remove position
        del self.positions[symbol]
        
        logger.info(f"[PAPER] Virtual position closed: {symbol} PnL={pnl:.2f}")
        
        return position
    
    def get_position(self, symbol: str) -> Optional[VirtualPosition]:
        """Get virtual position for symbol"""
        return self.positions.get(symbol)
    
    def get_open_orders(self, symbol: str) -> List[VirtualOrder]:
        """Get open virtual orders for symbol"""
        return [order for order in self.orders.values() 
                if order.symbol == symbol and order.status == 'open']
    
    def get_position_summary(self) -> Dict[str, Dict]:
        """Get summary of all virtual positions"""
        summary = {}
        for symbol, position in self.positions.items():
            summary[symbol] = {
                'side': position.side,
                'quantity': position.quantity,
                'entry_price': position.entry_price,
                'unrealized_pnl': position.unrealized_pnl,
                'sl_order_id': position.sl_order_id,
                'tp_order_id': position.tp_order_id
            }
        return summary
