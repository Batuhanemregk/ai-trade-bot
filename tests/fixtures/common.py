"""
Common test fixtures for AiBotBS.
Provides offline, deterministic fixtures for testing.
"""

import os
import pytest
from typing import Dict, List, Any, Optional
from decimal import Decimal


class FakeExchange:
    """Fake exchange adapter for offline testing."""
    
    def __init__(self):
        self.orders = {}
        self.positions = {}
        self.open_orders = []
        self.order_id_counter = 1000
    
    async def create_order(self, symbol: str, type_: str = None, side: str = None, amount: float = None, 
                          price: Optional[float] = None, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Create a fake order with flexible parameter handling."""
        # Handle both old-style (type_, side, amount) and new-style (kwargs) calls
        if type_ is None and 'type' in kwargs:
            type_ = kwargs['type']
        if side is None and 'side' in kwargs:
            side = kwargs['side']
        if amount is None and 'amount' in kwargs:
            amount = kwargs['amount']
        
        order_id = f"fake_order_{self.order_id_counter}"
        self.order_id_counter += 1
        
        order = {
            "id": order_id,
            "symbol": symbol,
            "type": type_,
            "side": side,
            "amount": amount,
            "price": price,
            "status": "closed",  # Auto-fill for testing
            "filled": amount,
            "remaining": 0.0,
            "cost": (price or 0.0) * amount,
            "timestamp": 1234567890000,
            "datetime": "2023-01-01T00:00:00.000Z",
            "clientOrderId": params.get("clientOrderId") if params else None,
        }
        
        self.orders[order_id] = order
        self.open_orders.append(order)
        
        return order
    
    async def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Fetch fake positions."""
        if not self.positions:
            # Create some default positions
            self.positions = {
                "BTC-USDT": {
                    "symbol": "BTC-USDT",
                    "side": "long",
                    "size": 0.1,
                    "notional": 3000.0,
                    "unrealized_pnl": 150.0,
                    "entry_price": 30000.0,
                    "mark_price": 30150.0,
                    "liquidation_price": 25000.0,
                },
                "ETH-USDT": {
                    "symbol": "ETH-USDT",
                    "side": "short",
                    "size": 1.0,
                    "notional": 2000.0,
                    "unrealized_pnl": -50.0,
                    "entry_price": 2000.0,
                    "mark_price": 1950.0,
                    "liquidation_price": 2500.0,
                }
            }
        
        if symbols:
            return [pos for sym, pos in self.positions.items() if sym in symbols]
        return list(self.positions.values())
    
    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch fake open orders."""
        if symbol:
            return [order for order in self.open_orders if order["symbol"] == symbol]
        return self.open_orders.copy()
    
    async def fetch_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Fetch a specific order by ID."""
        for order in self.orders.values():
            if order["id"] == order_id:
                return order
        raise ValueError(f"Order {order_id} not found")
    
    async def fetch_market(self, symbol: str) -> Dict[str, Any]:
        """Fetch fake market information."""
        return {
            "symbol": symbol,
            "limits": {
                "amount": {
                    "min": 0.0001 if "BTC" in symbol else 0.001,
                    "max": 1000 if "BTC" in symbol else 10000
                }
            },
            "precision": {
                "amount": 6 if "BTC" in symbol else 3,
                "price": 2 if "BTC" in symbol else 2
            }
        }


class FakeREST:
    """Fake REST adapter for offline testing."""
    
    def __init__(self):
        self.trigger_orders = {}
        self.order_id_counter = 2000
    
    async def place_trigger_order(self, symbol: str, side: str, order_type: str,
                                size: float, trigger_price: float, 
                                order_price: float, **kwargs) -> Dict[str, Any]:
        """Place a fake trigger order."""
        order_id = f"fake_trigger_{self.order_id_counter}"
        self.order_id_counter += 1
        
        order = {
            "orderId": order_id,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "size": size,
            "triggerPrice": trigger_price,
            "orderPrice": order_price,
            "status": "pending",
            "timestamp": 1234567890000,
            **kwargs
        }
        
        self.trigger_orders[order_id] = order
        return order
    
    async def cancel_trigger_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a fake trigger order."""
        if order_id in self.trigger_orders:
            order = self.trigger_orders[order_id]
            order["status"] = "cancelled"
            return {"success": True, "orderId": order_id}
        return {"success": False, "error": "Order not found"}
    
    async def create_order(self, symbol: str, side: str, type: str, price: float = None, 
                          params: Dict = None, **kwargs) -> Dict[str, Any]:
        """Create a fake order via REST."""
        order_id = f"fake_rest_{self.order_id_counter}"
        self.order_id_counter += 1
        
        order = {
            "id": order_id,
            "symbol": symbol,
            "type": type,
            "side": side,
            "price": price,
            "status": "active",
            "timestamp": 1234567890000,
            "datetime": "2023-01-01T00:00:00.000Z",
        }
        
        return order


@pytest.fixture
def fake_exchange():
    """Provide a fake exchange adapter."""
    return FakeExchange()


@pytest.fixture
def fake_rest():
    """Provide a fake REST adapter."""
    return FakeREST()


@pytest.fixture
def env_isolation():
    """Isolate environment variables for testing."""
    # Store original values
    original_env = {}
    for key in ["OPENAI_API_KEY", "OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE"]:
        if key in os.environ:
            original_env[key] = os.environ[key]
            del os.environ[key]
    
    yield
    
    # Restore original values
    for key, value in original_env.items():
        os.environ[key] = value


@pytest.fixture
def tmp_symbol_meta():
    """Provide temporary symbol metadata for testing."""
    return {
        "BTC-USDT": {
            "tickSz": "0.1",
            "lotSz": "0.0001",
            "minSz": "0.0001",
            "maxSz": "1000",
            "baseCcy": "BTC",
            "quoteCcy": "USDT"
        },
        "ETH-USDT": {
            "tickSz": "0.01",
            "lotSz": "0.001",
            "minSz": "0.001",
            "maxSz": "10000",
            "baseCcy": "ETH",
            "quoteCcy": "USDT"
        },
        "BTC-USDT-SWAP": {
            "tickSz": "0.1",
            "lotSz": "1",
            "minSz": "1",
            "maxSz": "1000000",
            "baseCcy": "BTC",
            "quoteCcy": "USDT",
            "contractType": "SWAP"
        }
    }


@pytest.fixture
def mock_policy():
    """Provide mock trading policy for testing."""
    return {
        "timeframes": {
            "main": "1h",
            "trend_filter": "4h",
            "entry_confirmation": "15m"
        },
        "risk": {
            "max_position_size": 0.1,
            "max_daily_loss": 0.05,
            "stop_loss_atr_multiplier": 2.0
        },
        "scoring": {
            "min_score": 0.6,
            "ta_weight": 0.4,
            "news_weight": 0.3,
            "ml_weight": 0.3
        }
    }
