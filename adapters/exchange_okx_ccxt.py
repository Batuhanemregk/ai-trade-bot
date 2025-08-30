"""
OKX exchange adapter using CCXT library.
Handles entry orders via CCXT with clientOrderId management.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import ccxt
import ccxt.pro as ccxtpro
from loguru import logger

from execution.id_utils import generate_client_id
from execution.okx_symbol import okx_to_ccxt_symbol
from execution.quantize import create_quantizer_from_instrument
from adapters.error_mapping import map_ccxt_error, is_retryable_error


class OKXExchangeAdapter:
    """OKX exchange adapter using CCXT library for entry orders."""
    
    def __init__(self, config: dict = None, ccxt_client: Any = None):
        self.config = config or {}
        self.ccxt_client = ccxt_client
        self.mode = self.config.get('mode', 'dry-run')
        
        # Initialize CCXT client if not provided
        if not self.ccxt_client:
            self._init_ccxt_client()
    
    def _init_ccxt_client(self):
        """Initialize CCXT client."""
        try:
            exchange_params = {
                'apiKey': self.config.get('api_key', ''),
                'secret': self.config.get('secret', ''),
                'password': self.config.get('passphrase', ''),
                'sandbox': self.config.get('sandbox', True),
                'testnet': self.config.get('testnet', True),
                'enableRateLimit': True,
                'rateLimit': 100,
                'timeout': 30000,
                'options': {
                    'defaultType': 'swap',
                    'adjustForTimeDifference': True,
                    'recvWindow': 5000,
                }
            }
            self.ccxt_client = ccxt.okx(exchange_params)
            logger.info("✅ OKX CCXT client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize CCXT client: {e}")
            self.ccxt_client = None
    
    async def test_connection(self) -> bool:
        """Test connection to the exchange."""
        try:
            if not self.ccxt_client:
                return False
            
            # Try to fetch ticker for a known symbol
            ticker = self.ccxt_client.fetch_ticker('BTC/USDT')
            return True
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False
    
    def place_order(self, symbol: str, side: str, type: str, amount: Any, 
                   price: Any = None, params: dict = None) -> dict:
        """Place an order."""
        try:
            # Convert OKX symbol to CCXT symbol
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            # Generate client order ID
            cl_ord_id = generate_client_id('E')
            
            # Prepare parameters
            order_params = params or {}
            order_params['clientOrderId'] = cl_ord_id
            
            if self.mode == 'dry-run':
                return {
                    "id": "MOCK",
                    "status": "mock",
                    "info": {
                        "symbol": symbol,
                        "side": side,
                        "type": type,
                        "amount": amount,
                        "price": price,
                        "params": order_params
                    }
                }
            
            # Place real order
            result = self.ccxt_client.create_order(
                symbol=ccxt_symbol,
                type=type,
                side=side,
                amount=amount,
                price=price,
                params=order_params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Order placement failed: {e}")
            raise map_ccxt_error(e) if hasattr(map_ccxt_error, '__call__') else e
    
    def cancel_order(self, order_id: str, symbol: str, params: dict = None) -> dict:
        """Cancel an order."""
        try:
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            if self.mode == 'dry-run':
                return {
                    "id": "MOCK",
                    "status": "cancelled",
                    "info": {"order_id": order_id, "symbol": symbol}
                }
            
            result = self.ccxt_client.cancel_order(order_id, ccxt_symbol, params or {})
            return result
            
        except Exception as e:
            logger.error(f"❌ Order cancellation failed: {e}")
            raise map_ccxt_error(e) if hasattr(map_ccxt_error, '__call__') else e
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = "15m", limit: int = 200) -> list:
        """Fetch OHLCV data."""
        try:
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            if self.mode == 'dry-run':
                return [["MOCK", 0, 0, 0, 0, 0]]
            
            result = self.ccxt_client.fetch_ohlcv(ccxt_symbol, timeframe, limit=limit)
            return result
            
        except Exception as e:
            logger.error(f"❌ OHLCV fetch failed: {e}")
            raise map_ccxt_error(e) if hasattr(map_ccxt_error, '__call__') else e
    
    async def fetch_positions(self, symbols: list = None) -> list:
        """Fetch positions."""
        try:
            if self.mode == 'dry-run':
                return [{"symbol": "MOCK", "size": 0, "side": "0"}]
            
            result = self.ccxt_client.fetch_positions(symbols)
            return result
            
        except Exception as e:
            logger.error(f"❌ Positions fetch failed: {e}")
            raise map_ccxt_error(e) if hasattr(map_ccxt_error, '__call__') else e
    
    def fetch_open_orders(self, symbol: str = None) -> list:
        """Fetch open orders."""
        try:
            if symbol:
                ccxt_symbol = okx_to_ccxt_symbol(symbol)
            else:
                ccxt_symbol = None
            
            if self.mode == 'dry-run':
                return [{"id": "MOCK", "symbol": symbol or "MOCK", "status": "open"}]
            
            result = self.ccxt_client.fetch_open_orders(symbol=ccxt_symbol)
            return result
            
        except Exception as e:
            logger.error(f"❌ Open orders fetch failed: {e}")
            raise map_ccxt_error(e) if hasattr(map_ccxt_error, '__call__') else e


class OKXCCXTAdapter:
    """OKX exchange adapter using CCXT library for entry orders."""
    
    def __init__(self, api_key: str = "", secret: str = "", passphrase: str = "",
                 sandbox: bool = False, testnet: bool = False):
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.sandbox = sandbox
        self.testnet = testnet
        
        # Exchange instance
        self.exchange: Optional[ccxt.Exchange] = None
        self.pro_exchange: Optional[ccxtpro.Exchange] = None
        
        # Connection settings
        self._initialized = False
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests
        self._semaphore = asyncio.Semaphore(5)  # Max concurrent requests
        
        # Retry settings
        self._max_retries = 3
        self._base_delay = 1.0
        self._timeout_seconds = 30
        
        # Initialize exchange
        self._init_exchange()
    
    def _init_exchange(self):
        """Initialize the CCXT exchange instance."""
        try:
            # Configure exchange parameters
            exchange_params = {
                'apiKey': self.api_key,
                'secret': self.secret,
                'password': self.passphrase,
                'sandbox': self.sandbox,
                'testnet': self.testnet,
                'enableRateLimit': True,
                'rateLimit': 100,  # 100ms between requests
                'timeout': self._timeout_seconds * 1000,
                'options': {
                    'defaultType': 'swap',  # Default to SWAP for futures
                    'adjustForTimeDifference': True,
                    'recvWindow': 5000,
                }
            }
            
            # Create exchange instance
            self.exchange = ccxt.okx(exchange_params)
            
            # Create pro exchange for async operations
            self.pro_exchange = ccxtpro.okx(exchange_params)
            
            self._initialized = True
            logger.info("✅ OKX CCXT adapter initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OKX CCXT adapter: {e}")
            self._initialized = False
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)
        
        self._last_request_time = time.time()
    
    async def _make_request(self, request_func, *args, **kwargs) -> Any:
        """
        Make a rate-limited request with retry logic.
        
        Args:
            request_func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Request result
        
        Raises:
            Exception: If all retries fail
        """
        if not self._initialized:
            raise RuntimeError("OKX CCXT adapter not initialized")
        
        async with self._semaphore:
            for attempt in range(self._max_retries + 1):
                try:
                    await self._rate_limit()
                    
                    if asyncio.iscoroutinefunction(request_func):
                        result = await request_func(*args, **kwargs)
                    else:
                        result = request_func(*args, **kwargs)
                    
                    return result
                    
                except Exception as e:
                    if attempt == self._max_retries:
                        # Last attempt failed
                        raise map_ccxt_error(e, {
                            'attempt': attempt + 1,
                            'max_retries': self._max_retries,
                            'function': request_func.__name__
                        })
                    
                    if not is_retryable_error(e):
                        # Non-retryable error
                        raise map_ccxt_error(e, {
                            'attempt': attempt + 1,
                            'function': request_func.__name__
                        })
                    
                    # Wait before retry
                    delay = self._base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
    
    async def create_order(self, symbol: str, order_type: str, side: str, 
                          amount: float, price: Optional[float] = None,
                          params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an order via CCXT.
        
        Args:
            symbol: Trading symbol (OKX instId format)
            order_type: Order type ('limit', 'market', etc.)
            side: Order side ('buy' or 'sell')
            amount: Order amount
            price: Order price (required for limit orders)
            params: Additional order parameters
        
        Returns:
            Order information
        """
        if params is None:
            params = {}
        
        # Generate unique client order ID
        client_order_id = generate_client_id('E')
        
        # Convert symbol to CCXT format
        ccxt_symbol = okx_to_ccxt_symbol(symbol)
        
        # Set clientOrderId in params (CCXT will handle this)
        params['clientOrderId'] = client_order_id
        
        # Prepare order parameters
        order_params = {
            'symbol': ccxt_symbol,
            'type': order_type,
            'side': side,
            'amount': amount,
            'params': params
        }
        
        if price is not None:
            order_params['price'] = price
        
        logger.info(f"📝 Creating {order_type} {side} order: {ccxt_symbol} {amount} @ {price}")
        logger.info(f"   ClientOrderId: {client_order_id} (len: {len(client_order_id)})")
        logger.info(f"   Symbol normalized: {symbol} -> {ccxt_symbol}")
        
        try:
            result = await self._make_request(
                self.pro_exchange.create_order,
                **order_params
            )
            
            logger.info(f"✅ Order created successfully: {result.get('id', 'N/A')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to create order: {e}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: str, 
                          params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading symbol
            params: Additional parameters
        
        Returns:
            Cancellation result
        """
        if params is None:
            params = {}
        
        # Convert symbol to CCXT format
        ccxt_symbol = okx_to_ccxt_symbol(symbol)
        
        logger.info(f"❌ Cancelling order {order_id} for {ccxt_symbol}")
        
        try:
            result = await self._make_request(
                self.pro_exchange.cancel_order,
                order_id,
                ccxt_symbol,
                params
            )
            
            logger.info(f"✅ Order cancelled successfully: {order_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to cancel order {order_id}: {e}")
            raise
    
    async def fetch_order(self, order_id: str, symbol: str, 
                         params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch order information.
        
        Args:
            order_id: Order ID
            symbol: Trading symbol
            params: Additional parameters
        
        Returns:
            Order information
        """
        if params is None:
            params = {}
        
        # Convert symbol to CCXT format
        ccxt_symbol = okx_to_ccxt_symbol(symbol)
        
        try:
            result = await self._make_request(
                self.pro_exchange.fetch_order,
                order_id,
                ccxt_symbol,
                params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch order {order_id}: {e}")
            raise
    
    async def fetch_open_orders(self, symbol: Optional[str] = None, 
                               since: Optional[int] = None, limit: Optional[int] = None,
                               params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Fetch open orders.
        
        Args:
            symbol: Trading symbol (optional)
            since: Timestamp since when to fetch
            limit: Maximum number of orders to fetch
            params: Additional parameters
        
        Returns:
            List of open orders
        """
        if params is None:
            params = {}
        
        if symbol:
            # Convert symbol to CCXT format
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
        else:
            ccxt_symbol = None
        
        try:
            result = await self._make_request(
                self.pro_exchange.fetch_open_orders,
                ccxt_symbol,
                since,
                limit,
                params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch open orders: {e}")
            raise
    
    async def fetch_positions(self, symbols: Optional[List[str]] = None,
                             params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Fetch positions.
        
        Args:
            symbols: List of symbols (optional)
            params: Additional parameters
        
        Returns:
            List of positions
        """
        if params is None:
            params = {}
        
        if symbols:
            # Convert symbols to CCXT format
            ccxt_symbols = [okx_to_ccxt_symbol(s) for s in symbols]
        else:
            ccxt_symbols = None
        
        try:
            result = await self._make_request(
                self.pro_exchange.fetch_positions,
                ccxt_symbols,
                params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch positions: {e}")
            raise
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m',
                          since: Optional[int] = None, limit: Optional[int] = None,
                          params: Optional[Dict[str, Any]] = None) -> List[List[float]]:
        """
        Fetch OHLCV data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe ('1m', '5m', '1h', '1d', etc.)
            since: Timestamp since when to fetch
            limit: Maximum number of candles to fetch
            params: Additional parameters
        
        Returns:
            List of OHLCV candles
        """
        if params is None:
            params = {}
        
        # Convert symbol to CCXT format
        ccxt_symbol = okx_to_ccxt_symbol(symbol)
        
        try:
            result = await self._make_request(
                self.pro_exchange.fetch_ohlcv,
                ccxt_symbol,
                timeframe,
                since,
                limit,
                params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch OHLCV for {symbol}: {e}")
            raise
    
    async def fetch_ticker(self, symbol: str, 
                          params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch ticker information.
        
        Args:
            symbol: Trading symbol
            params: Additional parameters
        
        Returns:
            Ticker information
        """
        if params is None:
            params = {}
        
        # Convert symbol to CCXT format
        ccxt_symbol = okx_to_ccxt_symbol(symbol)
        
        try:
            result = await self._make_request(
                self.pro_exchange.fetch_ticker,
                ccxt_symbol,
                params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch ticker for {symbol}: {e}")
            raise
    
    async def fetch_balance(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch account balance.
        
        Args:
            params: Additional parameters
        
        Returns:
            Account balance
        """
        if params is None:
            params = {}
        
        try:
            result = await self._make_request(
                self.pro_exchange.fetch_balance,
                params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch balance: {e}")
            raise
    
    async def fetch_order_book(self, symbol: str, limit: Optional[int] = None,
                              params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch order book.
        
        Args:
            symbol: Trading symbol
            limit: Maximum number of orders to fetch
            params: Additional parameters
        
        Returns:
            Order book
        """
        if params is None:
            params = {}
        
        # Convert symbol to CCXT format
        ccxt_symbol = okx_to_ccxt_symbol(symbol)
        
        try:
            result = await self._make_request(
                self.pro_exchange.fetch_order_book,
                ccxt_symbol,
                limit,
                params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch order book for {symbol}: {e}")
            raise
    
    async def fetch_trades(self, symbol: str, since: Optional[int] = None,
                          limit: Optional[int] = None, 
                          params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Fetch recent trades.
        
        Args:
            symbol: Trading symbol
            since: Timestamp since when to fetch
            limit: Maximum number of trades to fetch
            params: Additional parameters
        
        Returns:
            List of recent trades
        """
        if params is None:
            params = {}
        
        # Convert symbol to CCXT format
        ccxt_symbol = okx_to_ccxt_symbol(symbol)
        
        try:
            result = await self._make_request(
                self.pro_exchange.fetch_trades,
                ccxt_symbol,
                since,
                limit,
                params
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch trades for {symbol}: {e}")
            raise
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information.
        
        Returns:
            Exchange information
        """
        if not self._initialized or not self.exchange:
            raise RuntimeError("OKX CCXT adapter not initialized")
        
        return {
            'name': self.exchange.name,
            'id': self.exchange.id,
            'urls': self.exchange.urls,
            'version': self.exchange.version,
            'sandbox': self.sandbox,
            'testnet': self.testnet,
            'has': self.exchange.has,
            'timeframes': self.exchange.timeframes,
            'precision': self.exchange.precision,
            'limits': self.exchange.limits,
            'fees': self.exchange.fees,
        }
    
    async def test_connection(self) -> bool:
        """
        Test exchange connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self.fetch_balance()
            logger.info("✅ OKX CCXT connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ OKX CCXT connection test failed: {e}")
            return False
    
    async def close(self):
        """Close exchange connections."""
        try:
            if self.pro_exchange:
                await self.pro_exchange.close()
            logger.info("✅ OKX CCXT adapter closed")
        except Exception as e:
            logger.error(f"❌ Error closing OKX CCXT adapter: {e}")
    
    def __repr__(self):
        return (f"OKXCCXTAdapter(sandbox={self.sandbox}, testnet={self.testnet}, "
                f"initialized={self._initialized})")


class OKXCCXTProAdapter:
    """OKX CCXT Pro adapter for advanced async operations."""
    
    def __init__(self, api_key: str = "", secret: str = "", passphrase: str = "",
                 sandbox: bool = False, testnet: bool = False):
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.sandbox = sandbox
        self.testnet = testnet
        
        # Pro exchange instance
        self.pro_exchange: Optional[ccxtpro.Exchange] = None
        
        # Initialize
        self._init_pro_exchange()
    
    def _init_pro_exchange(self):
        """Initialize the CCXT Pro exchange instance."""
        try:
            exchange_params = {
                'apiKey': self.api_key,
                'secret': self.secret,
                'password': self.passphrase,
                'sandbox': self.sandbox,
                'testnet': self.testnet,
                'enableRateLimit': True,
                'rateLimit': 100,
                'timeout': 30000,
                'options': {
                    'defaultType': 'swap',
                    'adjustForTimeDifference': True,
                    'recvWindow': 5000,
                }
            }
            
            self.pro_exchange = ccxtpro.okx(exchange_params)
            logger.info("✅ OKX CCXT Pro adapter initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OKX CCXT Pro adapter: {e}")
            self.pro_exchange = None
    
    async def close(self):
        """Close pro exchange connection."""
        try:
            if self.pro_exchange:
                await self.pro_exchange.close()
            logger.info("✅ OKX CCXT Pro adapter closed")
        except Exception as e:
            logger.error(f"❌ Error closing OKX CCXT Pro adapter: {e}")


# Global adapter instance
_ccxt_adapter = None

def get_ccxt_adapter(api_key: str = "", secret: str = "", passphrase: str = "",
                     sandbox: bool = False, testnet: bool = False) -> OKXCCXTAdapter:
    """Get the global CCXT adapter instance."""
    global _ccxt_adapter
    if _ccxt_adapter is None:
        _ccxt_adapter = OKXCCXTAdapter(api_key, secret, passphrase, sandbox, testnet)
    return _ccxt_adapter


async def create_order_via_ccxt(symbol: str, order_type: str, side: str,
                               amount: float, price: Optional[float] = None,
                               params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create order using global CCXT adapter."""
    adapter = get_ccxt_adapter()
    return await adapter.create_order(symbol, order_type, side, amount, price, params)


async def cancel_order_via_ccxt(order_id: str, symbol: str,
                               params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Cancel order using global CCXT adapter."""
    adapter = get_ccxt_adapter()
    return await adapter.cancel_order(order_id, symbol, params)


__all__ = [
    "OKXExchangeAdapter",
    "OKXCCXTAdapter",
    "OKXCCXTProAdapter",
    "get_ccxt_adapter",
    "create_order_via_ccxt",
    "cancel_order_via_ccxt",
]
