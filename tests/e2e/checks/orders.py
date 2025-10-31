"""
Order Lifecycle Checker
=======================

Order lifecycle kontrolleri:
- Entry order placement
- Bracket orders (TP/SL)
- OCO (One-Cancels-Other) logic
- Trailing stop updates
- Exit conditions
- Order state transitions
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class OrderEvent:
    """Order event for tracking."""
    timestamp: datetime
    event_type: str  # entry, tp, sl, trailing, exit, cancel
    order_id: str
    symbol: str
    side: str  # buy, sell
    pos_side: str  # long, short
    price: float
    size: float
    status: str  # pending, filled, cancelled
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class BracketOrder:
    """Bracket order tracking."""
    symbol: str
    side: str
    pos_side: str
    entry_order_id: str
    tp_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None
    entry_price: float = 0.0
    tp_price: float = 0.0
    sl_price: float = 0.0
    size: float = 0.0
    status: str = "pending"  # pending, filled, cancelled
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class OrderLifecycleChecker:
    """Checks order lifecycle and bracket order management."""
    
    def __init__(self):
        self.order_events: List[OrderEvent] = []
        self.bracket_orders: List[BracketOrder] = []
        self.trailing_updates: List[Dict] = []
        
    async def check_entry_order(self, exchange, symbol: str, side: str, 
                               size: float, price: float) -> Tuple[bool, str]:
        """
        Check entry order placement.
        
        Args:
            exchange: Exchange adapter
            symbol: Trading symbol
            side: buy/sell
            size: Order size
            price: Order price
            
        Returns:
            (success, message)
        """
        try:
            # Place entry order
            if side.lower() == 'buy':
                order = await exchange.create_market_buy_order(symbol, size)
            else:
                order = await exchange.create_market_sell_order(symbol, size)
            
            # Record event
            event = OrderEvent(
                timestamp=datetime.now(),
                event_type="entry",
                order_id=order['id'],
                symbol=symbol,
                side=side,
                pos_side="long" if side.lower() == 'buy' else "short",
                price=price,
                size=size,
                status="pending"
            )
            self.order_events.append(event)
            
            # Create bracket order tracking
            bracket = BracketOrder(
                symbol=symbol,
                side=side,
                pos_side=event.pos_side,
                entry_order_id=order['id'],
                entry_price=price,
                size=size
            )
            self.bracket_orders.append(bracket)
            
            logger.info(f"✅ Entry order placed: {symbol} {side} {size} @ {price}")
            return True, f"Entry order placed: {order['id']}"
            
        except Exception as e:
            logger.error(f"❌ Entry order failed: {e}")
            return False, f"Entry order failed: {e}"
    
    async def check_bracket_orders(self, exchange, bracket: BracketOrder, 
                                  tp_price: float, sl_price: float) -> Tuple[bool, str]:
        """
        Check bracket order placement (TP/SL).
        
        Args:
            exchange: Exchange adapter
            bracket: Bracket order to attach TP/SL
            tp_price: Take profit price
            sl_price: Stop loss price
            
        Returns:
            (success, message)
        """
        try:
            # Check if entry is filled
            entry_order = await exchange.fetch_order(bracket.entry_order_id, bracket.symbol)
            if entry_order['status'] != 'closed':
                return False, f"Entry order not filled: {entry_order['status']}"
            
            # Update bracket with fill info
            bracket.entry_price = entry_order['average'] or entry_order['price']
            bracket.size = entry_order['filled']
            bracket.status = "filled"
            
            # Place TP order
            if tp_price > 0:
                tp_side = "sell" if bracket.pos_side == "long" else "buy"
                tp_order = await exchange.create_limit_order(
                    symbol=bracket.symbol,
                    side=tp_side,
                    amount=bracket.size,
                    price=tp_price,
                    params={'reduceOnly': True}
                )
                bracket.tp_order_id = tp_order['id']
                bracket.tp_price = tp_price
                
                # Record TP event
                event = OrderEvent(
                    timestamp=datetime.now(),
                    event_type="tp",
                    order_id=tp_order['id'],
                    symbol=bracket.symbol,
                    side=tp_side,
                    pos_side=bracket.pos_side,
                    price=tp_price,
                    size=bracket.size,
                    status="pending"
                )
                self.order_events.append(event)
            
            # Place SL order
            if sl_price > 0:
                sl_side = "sell" if bracket.pos_side == "long" else "buy"
                sl_order = await exchange.create_stop_order(
                    symbol=bracket.symbol,
                    side=sl_side,
                    amount=bracket.size,
                    price=sl_price,
                    params={'reduceOnly': True}
                )
                bracket.sl_order_id = sl_order['id']
                bracket.sl_price = sl_price
                
                # Record SL event
                event = OrderEvent(
                    timestamp=datetime.now(),
                    event_type="sl",
                    order_id=sl_order['id'],
                    symbol=bracket.symbol,
                    side=sl_side,
                    pos_side=bracket.pos_side,
                    price=sl_price,
                    size=bracket.size,
                    status="pending"
                )
                self.order_events.append(event)
            
            logger.info(f"✅ Bracket orders placed: TP={tp_price}, SL={sl_price}")
            return True, f"Bracket orders placed: TP={bracket.tp_order_id}, SL={bracket.sl_order_id}"
            
        except Exception as e:
            logger.error(f"❌ Bracket orders failed: {e}")
            return False, f"Bracket orders failed: {e}"
    
    async def check_oco_logic(self, exchange, bracket: BracketOrder) -> Tuple[bool, str]:
        """
        Check OCO (One-Cancels-Other) logic.
        
        Args:
            exchange: Exchange adapter
            bracket: Bracket order to check
            
        Returns:
            (success, message)
        """
        try:
            # Check if one order is filled, the other should be cancelled
            tp_filled = False
            sl_filled = False
            
            if bracket.tp_order_id:
                tp_order = await exchange.fetch_order(bracket.tp_order_id, bracket.symbol)
                tp_filled = tp_order['status'] == 'closed'
            
            if bracket.sl_order_id:
                sl_order = await exchange.fetch_order(bracket.sl_order_id, bracket.symbol)
                sl_filled = sl_order['status'] == 'closed'
            
            if tp_filled and sl_filled:
                return False, "Both TP and SL filled - OCO logic failed"
            elif tp_filled or sl_filled:
                # One filled, check if other is cancelled
                if tp_filled and bracket.sl_order_id:
                    sl_order = await exchange.fetch_order(bracket.sl_order_id, bracket.symbol)
                    if sl_order['status'] != 'canceled':
                        return False, "TP filled but SL not cancelled"
                elif sl_filled and bracket.tp_order_id:
                    tp_order = await exchange.fetch_order(bracket.tp_order_id, bracket.symbol)
                    if tp_order['status'] != 'canceled':
                        return False, "SL filled but TP not cancelled"
                
                logger.info("✅ OCO logic working correctly")
                return True, "OCO logic working correctly"
            else:
                return True, "Both orders still pending - OCO logic not triggered"
                
        except Exception as e:
            logger.error(f"❌ OCO logic check failed: {e}")
            return False, f"OCO logic check failed: {e}"
    
    async def check_trailing_stops(self, exchange, bracket: BracketOrder) -> Tuple[bool, str]:
        """
        Check trailing stop updates.
        
        Args:
            exchange: Exchange adapter
            bracket: Bracket order to check
            
        Returns:
            (success, message)
        """
        try:
            if not bracket.sl_order_id:
                return True, "No SL order to trail"
            
            # Get current SL order
            sl_order = await exchange.fetch_order(bracket.sl_order_id, bracket.symbol)
            
            # Check if SL price has been updated (trailing)
            current_sl_price = sl_order.get('price', 0)
            original_sl_price = bracket.sl_price
            
            if current_sl_price != original_sl_price:
                # Record trailing update
                update = {
                    'timestamp': datetime.now(),
                    'symbol': bracket.symbol,
                    'order_id': bracket.sl_order_id,
                    'old_price': original_sl_price,
                    'new_price': current_sl_price,
                    'direction': 'up' if current_sl_price > original_sl_price else 'down'
                }
                self.trailing_updates.append(update)
                
                logger.info(f"✅ Trailing stop updated: {original_sl_price} → {current_sl_price}")
                return True, f"Trailing stop updated: {original_sl_price} → {current_sl_price}"
            else:
                return True, "No trailing update yet"
                
        except Exception as e:
            logger.error(f"❌ Trailing stop check failed: {e}")
            return False, f"Trailing stop check failed: {e}"
    
    async def check_exit_conditions(self, exchange, bracket: BracketOrder) -> Tuple[bool, str]:
        """
        Check exit conditions and position closure.
        
        Args:
            exchange: Exchange adapter
            bracket: Bracket order to check
            
        Returns:
            (success, message)
        """
        try:
            # Check if position is closed
            positions = await exchange.fetch_positions()
            position = next((p for p in positions if p['symbol'] == bracket.symbol), None)
            
            if not position or float(position.get('size', 0)) == 0:
                # Position is closed
                bracket.status = "closed"
                
                # Record exit event
                event = OrderEvent(
                    timestamp=datetime.now(),
                    event_type="exit",
                    order_id="",
                    symbol=bracket.symbol,
                    side="",
                    pos_side=bracket.pos_side,
                    price=0.0,
                    size=0.0,
                    status="closed"
                )
                self.order_events.append(event)
                
                logger.info(f"✅ Position closed: {bracket.symbol}")
                return True, "Position closed successfully"
            else:
                return True, f"Position still open: {position.get('size', 0)}"
                
        except Exception as e:
            logger.error(f"❌ Exit condition check failed: {e}")
            return False, f"Exit condition check failed: {e}"
    
    async def check_order_state_transitions(self, exchange, bracket: BracketOrder) -> Tuple[bool, str]:
        """
        Check order state transitions.
        
        Args:
            exchange: Exchange adapter
            bracket: Bracket order to check
            
        Returns:
            (success, message)
        """
        try:
            transitions = []
            
            # Check entry order state
            if bracket.entry_order_id:
                entry_order = await exchange.fetch_order(bracket.entry_order_id, bracket.symbol)
                transitions.append(f"Entry: {entry_order['status']}")
            
            # Check TP order state
            if bracket.tp_order_id:
                tp_order = await exchange.fetch_order(bracket.tp_order_id, bracket.symbol)
                transitions.append(f"TP: {tp_order['status']}")
            
            # Check SL order state
            if bracket.sl_order_id:
                sl_order = await exchange.fetch_order(bracket.sl_order_id, bracket.symbol)
                transitions.append(f"SL: {sl_order['status']}")
            
            logger.info(f"✅ Order states: {', '.join(transitions)}")
            return True, f"Order states: {', '.join(transitions)}"
            
        except Exception as e:
            logger.error(f"❌ Order state check failed: {e}")
            return False, f"Order state check failed: {e}"
    
    def get_order_summary(self) -> Dict[str, Any]:
        """Get summary of all orders."""
        return {
            'total_events': len(self.order_events),
            'bracket_orders': len(self.bracket_orders),
            'trailing_updates': len(self.trailing_updates),
            'events_by_type': {
                event_type: len([e for e in self.order_events if e.event_type == event_type])
                for event_type in ['entry', 'tp', 'sl', 'trailing', 'exit', 'cancel']
            },
            'active_brackets': len([b for b in self.bracket_orders if b.status != 'closed'])
        }
    
    def get_trailing_summary(self) -> List[Dict]:
        """Get summary of trailing stop updates."""
        return self.trailing_updates.copy()
    
    def get_bracket_summary(self) -> List[Dict]:
        """Get summary of bracket orders."""
        return [
            {
                'symbol': b.symbol,
                'side': b.side,
                'pos_side': b.pos_side,
                'entry_price': b.entry_price,
                'tp_price': b.tp_price,
                'sl_price': b.sl_price,
                'size': b.size,
                'status': b.status,
                'created_at': b.created_at.isoformat()
            }
            for b in self.bracket_orders
        ]

