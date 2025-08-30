# ⚡ Execution Layer Guide

> **Order Execution, Quantization, and Position Management**

## 🎯 Overview

The execution layer handles all trading operations including order placement, position management, and risk controls. It provides a robust interface between the application layer and external exchanges.

## 🏗️ Execution Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Trade Service  │  │ Portfolio Svc   │  │  Risk Svc   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Execution Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Order Executor  │  │ Position Mgr    │  │ Quantizer   │ │
│  │   Entry Orders  │  │   TP/SL Mgmt    │  │ Price/Size  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Prevalidator    │  │ Symbol Utils    │  │ ID Utils    │ │
│  │   Validation    │  │   Conversion    │  │  Management │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   OKX CCXT      │  │   OKX REST      │  │   Logging   │ │
│  │   Adapters      │  │   Adapters      │  │  Metrics    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔢 Quantization System

### Purpose
The quantization system ensures that all prices and sizes conform to exchange requirements, preventing order rejections due to precision violations.

### Core Functions

#### `quantize_price(symbol, price)`
Quantizes price to exchange tick size.

```python
from execution.quantize import quantize_price

# Quantize BTC-USDT price to 0.1 tick size
quantized_price = quantize_price("BTC-USDT", 30000.05)
# Result: 30000.0 (aligned to 0.1 tick)
```

#### `quantize_size(symbol, size)`
Quantizes order size to exchange lot size.

```python
from execution.quantize import quantize_size

# Quantize BTC-USDT size to 0.0001 lot size
quantized_size = quantize_size("BTC-USDT", 0.12345)
# Result: 0.1234 (aligned to 0.0001 lot)
```

#### `bump_to_min_size(symbol, size)`
Ensures order size meets minimum requirements.

```python
from execution.quantize import bump_to_min_size

# Bump size to minimum if below threshold
adjusted_size = bump_to_min_size("BTC-USDT", 0.00005)
# Result: 0.0001 (minimum size for BTC-USDT)
```

### Quantization Rules

| Symbol | Tick Size | Lot Size | Min Size | Max Size |
|--------|-----------|----------|----------|----------|
| BTC-USDT | 0.1 | 0.0001 | 0.0001 | 1000 |
| ETH-USDT | 0.01 | 0.001 | 0.001 | 10000 |
| BTC-USDT-SWAP | 0.1 | 1 | 1 | 1000000 |

### Implementation Details

```python
class Quantizer:
    def quantize_price(self, price: float, tick_size: float) -> float:
        """Quantize price to tick size using Decimal for precision."""
        from decimal import Decimal, ROUND_HALF_UP
        
        tick_decimal = Decimal(str(tick_size))
        price_decimal = Decimal(str(price))
        
        return float(price_decimal.quantize(tick_decimal, rounding=ROUND_HALF_UP))
```

## ✅ Prevalidation System

### Purpose
The prevalidation system validates orders before execution, ensuring they meet business rules and exchange constraints.

### Validation Rules

#### 1. Basic Validation
- Symbol exists and is valid
- Side is 'buy' or 'sell'
- Amount is positive and above minimum
- Price is valid for limit orders

#### 2. TP/SL Validation
- Take Profit above entry for long positions
- Stop Loss below entry for long positions
- Take Profit below entry for short positions
- Stop Loss above entry for short positions

#### 3. Risk Validation
- Position size within limits
- Daily loss within threshold
- Correlation limits respected
- Exposure limits maintained

### Implementation

```python
class OrderPrevalidator:
    def validate_order(self, order_dict_or_symbol=None, side=None, 
                      type_=None, amount=None, price=None, **kwargs) -> dict:
        """Validate order with flexible signature (dict or keyword args)."""
        
        # Parse parameters
        if isinstance(order_dict_or_symbol, dict):
            order_dict = order_dict_or_symbol
            symbol = order_dict.get("symbol")
            side = order_dict.get("side")
            price = order_dict.get("price")
            tp_price = order_dict.get("tp")
            sl_price = order_dict.get("sl")
        else:
            symbol = order_dict_or_symbol or kwargs.get("symbol")
            side = side or kwargs.get("side")
            price = price or kwargs.get("price")
            tp_price = kwargs.get("tp")
            sl_price = kwargs.get("sl")
        
        # Basic validation
        if not symbol or not side:
            return {
                'valid': False,
                'errors': ['Missing required fields: symbol, side']
            }
        
        # TP/SL validation
        if tp_price is not None and sl_price is not None:
            if side == 'buy':  # LONG position
                if tp_price <= price:  # TP should be above price
                    return {'valid': False, 'error': 'TP below entry for long'}
                if sl_price >= price:  # SL should be below price
                    return {'valid': False, 'error': 'SL above entry for long'}
            elif side == 'sell':  # SHORT position
                if tp_price >= price:  # TP should be below price
                    return {'valid': False, 'error': 'TP above entry for short'}
                if sl_price <= price:  # SL should be above price
                    return {'valid': False, 'error': 'SL below entry for short'}
        
        return {'valid': True}
```

## 📋 Bracket Order Management

### Purpose
Bracket orders automatically attach Take Profit (TP) and Stop Loss (SL) orders to positions after entry fills.

### Bracket Types

#### 1. Entry + Attach Mode
```python
# Place entry order first, then attach TP/SL
result = await trade_service.execute_signal(
    symbol="BTC-USDT",
    side="buy",
    qty=0.1,
    price=30000.0,
    sl=29900.0,    # Stop Loss
    tp=30100.0,    # Take Profit
    mode="entry_then_attach"
)
```

#### 2. OCO Mode (One-Cancels-Other)
```python
# Place TP and SL as OCO orders
bracket_result = await position_manager.attach_bracket(
    symbol="BTC-USDT",
    side_close="sell",  # Close long position
    ref_price=30000.0,
    tp=30100.0,
    sl=29900.0,
    reduce_only=True
)
```

### Bracket Lifecycle

```
1. Entry Order Placed
2. Wait for Fill
3. Attach TP Order
4. Attach SL Order
5. Monitor TP/SL
6. Handle Fills
7. Update Position
```

### Implementation

```python
class PositionManager:
    async def attach_bracket(self, symbol: str, side_close: str, 
                           ref_price: float, tp: Optional[float], 
                           sl: Optional[float], reduce_only: bool = True) -> dict:
        """Attach take profit and stop loss orders to existing position."""
        
        bracket_orders = []
        
        # Take Profit order
        if tp is not None:
            tp_order = await self._create_tp_order(
                symbol, side_close, tp, reduce_only
            )
            if tp_order.get("status") == "success":
                bracket_orders.append({
                    "type": "take_profit",
                    "order": tp_order
                })
        
        # Stop Loss order
        if sl is not None:
            sl_order = await self._create_sl_order(
                symbol, side_close, sl, reduce_only
            )
            if sl_order.get("status") == "success":
                bracket_orders.append({
                    "type": "stop_loss",
                    "order": sl_order
                })
        
        return {
            "status": "success",
            "bracket_orders": bracket_orders,
            "symbol": symbol,
            "side_close": side_close,
            "ref_price": ref_price
        }
```

## 🔄 Symbol Conversion

### Purpose
The symbol conversion system handles the mapping between OKX internal symbols and CCXT standard formats.

### Conversion Functions

#### `okx_to_ccxt_symbol(okx_symbol)`
Convert OKX symbol to CCXT format.

```python
from execution.okx_symbol import okx_to_ccxt_symbol

# Convert OKX symbol to CCXT
ccxt_symbol = okx_to_ccxt_symbol("BTC-USDT")
# Result: "BTC/USDT"

# Handle futures contracts
ccxt_symbol = okx_to_ccxt_symbol("BTC-USDT-240628")
# Result: "BTC/USDT:USDT-240628"
```

#### `ccxt_to_okx_symbol(ccxt_symbol)`
Convert CCXT symbol to OKX format.

```python
from execution.okx_symbol import ccxt_to_okx_symbol

# Convert CCXT symbol to OKX
okx_symbol = ccxt_to_okx_symbol("BTC/USDT")
# Result: "BTC-USDT"

# Handle futures contracts
okx_symbol = ccxt_to_okx_symbol("BTC/USDT:USDT-240628")
# Result: "BTC-USDT-240628"
```

#### `normalize_symbol(symbol, route="ccxt")`
Normalize symbol for specific route.

```python
from execution.okx_symbol import normalize_symbol

# Normalize for CCXT route
ccxt_symbol = normalize_symbol("BTC-USDT", route="ccxt")
# Result: "BTC/USDT"

# Normalize for REST route
rest_symbol = normalize_symbol("BTC/USDT", route="rest")
# Result: "BTC-USDT"
```

### Symbol Types

| Type | OKX Format | CCXT Format | Example |
|------|------------|-------------|---------|
| Spot | BASE-QUOTE | BASE/QUOTE | BTC-USDT → BTC/USDT |
| Futures | BASE-QUOTE-DATE | BASE/QUOTE:QUOTE-DATE | BTC-USDT-240628 → BTC/USDT:USDT-240628 |
| Swap | BASE-QUOTE-SWAP | BASE/QUOTE:USDT | BTC-USDT-SWAP → BTC/USDT:USDT |

## 🆔 ID Management

### Purpose
The ID management system generates and tracks unique identifiers for orders, positions, and other entities.

### ID Types

#### 1. Client Order IDs
```python
from execution.id_utils import generate_client_id

# Generate client order ID
client_id = generate_client_id("BTC-USDT")
# Result: "BTC-USDT_1756418909063_QVX574"
```

#### 2. Algorithm IDs
```python
from execution.id_utils import generate_algo_id

# Generate algorithm ID
algo_id = generate_algo_id("E")  # Entry strategy
# Result: "E_1756418909063_ABC123"
```

#### 3. Position IDs
```python
from execution.id_utils import generate_position_id

# Generate position ID
position_id = generate_position_id("BTC-USDT", "long")
# Result: "BTC-USDT_long_1756418909063"
```

### ID Validation

```python
from execution.id_utils import validate_client_id, is_id_used

# Validate client ID format
is_valid = validate_client_id("BTC-USDT_1756418909063_QVX574")
# Result: True

# Check if ID is already used
is_used = is_id_used("BTC-USDT_1756418909063_QVX574")
# Result: False (new ID)
```

### ID Persistence

IDs are persisted to prevent duplicates across system restarts:

```python
# Save used IDs
used_ids = {
    "used_ids": [
        "BTC-USDT_1756418909063_QVX574",
        "ETH-USDT_1756418909064_DEF789"
    ]
}

# Load used IDs
with open("state/used_ids.json", "w") as f:
    json.dump(used_ids, f)
```

## 🚨 Error Mapping

### Purpose
The error mapping system provides consistent error handling and user-friendly error messages across the execution layer.

### Error Categories

#### 1. Validation Errors
```python
VALIDATION_ERRORS = {
    "missing_fields": "Missing required fields: {fields}",
    "invalid_symbol": "Invalid symbol: {symbol}",
    "invalid_side": "Invalid side: {side}. Must be 'buy' or 'sell'",
    "invalid_amount": "Invalid amount: {amount}. Must be positive",
    "invalid_price": "Invalid price: {price}. Must be positive for limit orders"
}
```

#### 2. Exchange Errors
```python
EXCHANGE_ERRORS = {
    "insufficient_balance": "Insufficient balance for order",
    "symbol_not_found": "Symbol not found: {symbol}",
    "order_rejected": "Order rejected: {reason}",
    "rate_limit": "Rate limit exceeded. Please wait and retry"
}
```

#### 3. Business Logic Errors
```python
BUSINESS_ERRORS = {
    "tp_below_entry": "TP price ({tp}) must be above entry ({entry}) for long position",
    "sl_above_entry": "SL price ({sl}) must be below entry ({entry}) for long position",
    "exposure_limit": "Position would exceed exposure limit: {current}/{limit}",
    "daily_loss_limit": "Daily loss limit exceeded: {current}/{limit}"
}
```

### Error Handling

```python
class ExecutionError(Exception):
    """Base class for execution errors."""
    
    def __init__(self, error_code: str, message: str, details: dict = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

def handle_execution_error(error: Exception) -> dict:
    """Handle execution errors and return user-friendly response."""
    
    if isinstance(error, ExecutionError):
        return {
            "status": "error",
            "error_code": error.error_code,
            "message": error.message,
            "details": error.details
        }
    
    # Handle unexpected errors
    return {
        "status": "error",
        "error_code": "unexpected_error",
        "message": "An unexpected error occurred",
        "details": {"original_error": str(error)}
    }
```

## 🔌 OKX Adapters

### Purpose
The OKX adapters provide a unified interface to OKX exchange via both CCXT and REST APIs.

### CCXT Adapter

#### Features
- Standard CCXT interface
- Automatic symbol conversion
- Rate limiting
- Error handling

#### Usage
```python
from execution.okx_symbol import normalize_symbol

# Normalize symbol for CCXT
ccxt_symbol = normalize_symbol("BTC-USDT", route="ccxt")

# Place order via CCXT
order_result = await exchange.create_order(
    symbol=ccxt_symbol,
    type="limit",
    side="buy",
    amount=0.1,
    price=30000.0
)
```

### REST Adapter

#### Features
- Direct OKX API access
- Advanced order types
- Real-time data
- WebSocket support

#### Usage
```python
from execution.position_manager import PositionManager

# Attach bracket orders via REST
position_manager = PositionManager(rest_adapter)

bracket_result = await position_manager.attach_bracket(
    symbol="BTC-USDT",
    side_close="sell",
    ref_price=30000.0,
    tp=30100.0,
    sl=29900.0
)
```

### Adapter Selection

The system automatically selects the appropriate adapter:

```python
class OrderExecutor:
    async def place_entry(self, symbol: str, side: str, type_: str, 
                         amount: float, price: Optional[float] = None, 
                         params: Optional[Dict] = None) -> Dict[str, Any]:
        """Place entry order with automatic adapter selection."""
        
        # Use CCXT for standard orders
        if type_ in ["market", "limit"]:
            return await self.exchange.create_order(
                symbol=symbol,
                type=type_,
                side=side,
                amount=amount,
                price=price,
                params=params
            )
        
        # Use REST for advanced orders
        elif type_ in ["stop", "stop_limit"]:
            return await self.rest_adapter.place_order(
                symbol=symbol,
                side=side,
                type=type_,
                amount=amount,
                price=price,
                params=params
            )
```

## 📊 Performance Monitoring

### Metrics

#### 1. Execution Metrics
- Order placement latency
- Fill rate percentage
- Slippage measurement
- Error rate tracking

#### 2. Quantization Metrics
- Quantization accuracy
- Price alignment success
- Size adjustment frequency
- Minimum size violations

#### 3. Validation Metrics
- Validation success rate
- Common validation failures
- Rule violation patterns
- Risk check performance

### Monitoring Implementation

```python
import time
from functools import wraps

def monitor_execution(func):
    """Decorator to monitor execution performance."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Record metrics
            record_metric("execution_time", execution_time)
            record_metric("execution_success", 1)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Record error metrics
            record_metric("execution_time", execution_time)
            record_metric("execution_error", 1)
            record_metric("error_type", type(e).__name__)
            
            raise
    
    return wrapper

# Apply monitoring to key functions
@monitor_execution
async def place_entry(self, symbol: str, side: str, type_: str, 
                     amount: float, price: Optional[float] = None, 
                     params: Optional[Dict] = None) -> Dict[str, Any]:
    """Place entry order with performance monitoring."""
    # ... implementation
```

## 🔧 Configuration

### Execution Configuration

```yaml
execution:
  # Quantization settings
  quantization:
    default_tick_size: 0.01
    default_lot_size: 0.001
    default_min_size: 0.001
  
  # Prevalidation settings
  prevalidation:
    enable_tp_sl_validation: true
    enable_risk_validation: true
    enable_business_validation: true
  
  # Bracket order settings
  bracket:
    default_mode: "entry_then_attach"
    auto_attach: true
    reduce_only: true
  
  # Error handling
  error_handling:
    max_retries: 3
    retry_delay: 1.0
    exponential_backoff: true
```

### Environment Variables

```bash
# Execution settings
EXECUTION_DRY_RUN=true
EXECUTION_MAX_RETRIES=3
EXECUTION_TIMEOUT=30

# Quantization settings
QUANTIZATION_PRECISION=8
QUANTIZATION_ROUNDING=HALF_UP

# Error handling
ERROR_LOG_LEVEL=WARNING
ERROR_NOTIFICATION=true
```

---

**Next**: See [SCHEDULER.md](SCHEDULER.md) for job management, [TELEGRAM.md](TELEGRAM.md) for bot interface, or [CONFIG.md](CONFIG.md) for configuration details.
