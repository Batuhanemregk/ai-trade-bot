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
        import os
        self.config = config or {}
        self.ccxt_client = ccxt_client
        # Get mode from config, or env var TRADING_MODE, default to paper (safer than dry-run)
        self.mode = self.config.get('mode') or os.getenv('TRADING_MODE', 'paper')
        
        # Initialize CCXT client if not provided
        if not self.ccxt_client:
            self._init_ccxt_client()
    
    def _init_ccxt_client(self):
        """Initialize CCXT client."""
        try:
            import os
            
            # Get API credentials from environment variables
            api_key = os.getenv('OKX_API_KEY', '')
            secret = os.getenv('OKX_API_SECRET', '')
            passphrase = os.getenv('OKX_API_PASSPHRASE', '')
            testnet = os.getenv('OKX_TESTNET', 'false').lower() == 'true'
            default_type = os.getenv('OKX_DEFAULT_TYPE', 'swap')
            
            # Validate required credentials
            if not api_key:
                raise RuntimeError("OKX_API_KEY is required but not found in environment variables")
            if not secret:
                raise RuntimeError("OKX_API_SECRET is required but not found in environment variables")
            if not passphrase:
                raise RuntimeError("OKX_API_PASSPHRASE is required but not found in environment variables")
            
            # Check for simulated trading flag
            simulated_flag = os.environ.get('OKX_SIMULATED', '').strip() in ('1', 'true', 'True')
            
            exchange_params = {
                'apiKey': api_key,
                'secret': secret,
                'password': passphrase,
                'sandbox': testnet,
                'testnet': testnet,
                'enableRateLimit': True,
                'rateLimit': 100,
                'timeout': 30000,
                'headers': {'x-simulated-trading': '1'} if simulated_flag else {},
                'options': {
                    'defaultType': default_type,
                    'adjustForTimeDifference': True,
                    'recvWindow': 5000,
                }
            }
            
            logger.info(f"🔑 Initializing OKX client with API key: {api_key[:8]}...")
            logger.info(f"🔑 Testnet mode: {testnet}, Default type: {default_type}")
            
            self.ccxt_client = ccxt.okx(exchange_params)
            logger.info("✅ OKX CCXT client initialized successfully")
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
                # Return mock OHLCV data with proper timestamp
                import time
                current_time = int(time.time() * 1000)  # Current timestamp in ms
                mock_data = []
                for i in range(200):  # 200 bars
                    timestamp = current_time - (i * 900000)  # 15min intervals
                    mock_data.append([timestamp, 50000, 51000, 49000, 50500, 1000])
                return mock_data
            
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
    
    async def fetch_balance(self) -> dict:
        """Fetch account balance."""
        try:
            if self.mode == 'dry-run':
                return {'USDT': {'free': 10000.0, 'used': 0.0, 'total': 10000.0}}
            
            result = self.ccxt_client.fetch_balance()
            return result
            
        except Exception as e:
            logger.error(f"❌ Balance fetch failed: {e}")
            raise map_ccxt_error(e) if hasattr(map_ccxt_error, '__call__') else e
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT-SWAP')
            leverage: Leverage multiplier (e.g., 5)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.mode == 'dry-run':
                logger.info(f"[DRY-RUN] Would set leverage for {symbol} to {leverage}x")
                return True
            
            # Convert symbol to CCXT format
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            # Set leverage via CCXT
            result = self.ccxt_client.set_leverage(leverage, ccxt_symbol)
            logger.info(f"[LEVERAGE] Set {symbol} leverage to {leverage}x")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to set leverage for {symbol}: {e}")
            return False
    
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

    async def create_market_order(self, symbol: str, side: str, amount: float, 
                                 client_id: str = None, params: dict = None) -> dict:
        """Create a market order."""
        try:
            # Symbol mapping
            from execution.okx_symbol import okx_to_ccxt_symbol
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            # Robust quantization with exchange limits
            from execution.quantize import ensure_min_requirements, get_market
            q_amount = ensure_min_requirements(ccxt_symbol, amount, price=None, client=self.ccxt_client)
            
            # Log amount bumping if it occurred
            if q_amount > amount:
                try:
                    m = get_market(ccxt_symbol, self.ccxt_client)
                    min_amount = m.get('limits', {}).get('amount', {}).get('min', 'unknown')
                    min_cost = m.get('limits', {}).get('cost', {}).get('min', 'unknown')
                    logger.info("amount_bumped", extra={
                        "symbol": symbol, 
                        "computed": amount, 
                        "min_amount": min_amount, 
                        "min_cost": min_cost, 
                        "final_amount": q_amount
                    })
                except Exception as e:
                    logger.warning(f"Could not log amount bump details: {e}")
            
            # Client ID
            if client_id is None:
                from execution.id_utils import generate_client_id
                client_id = generate_client_id('E')
            
            # OKX params
            td_mode = self.config.get('td_mode', 'cross')
            hedge_mode = self.config.get('hedge_mode', False)
            
            order_params = {
                'tdMode': td_mode,
                'reduceOnly': False,
                'clientOrderId': client_id,
                'clOrdId': client_id,
            }
            
            if hedge_mode:
                order_params['posSide'] = 'long' if side == 'buy' else 'short'
            
            if params:
                order_params.update(params)
            
            # Create order
            result = self.ccxt_client.create_order(
                ccxt_symbol, 'market', side, q_amount, None, order_params
            )
            
            # Normalize result
            return {
                'status': result.get('status', 'unknown'),
                'type': 'market',
                'id': result.get('id', ''),
                'clientOrderId': client_id,
                'symbol': symbol,
                'side': side,
                'amount': q_amount,
                'price': result.get('price'),
                'raw': result
            }
            
        except Exception as e:
            from adapters.error_mapping import normalize_error
            error_info = normalize_error(e, {'operation': 'create_market_order', 'symbol': symbol})
            logger.error(f"❌ Market order failed for {symbol}: {error_info}")
            raise

    async def create_limit_order(self, symbol: str, side: str, amount: float, price: float,
                                client_id: str = None, params: dict = None) -> dict:
        """Create a limit order."""
        try:
            # Symbol mapping
            from execution.okx_symbol import okx_to_ccxt_symbol
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            # Robust quantization with exchange limits
            from execution.quantize import ensure_min_requirements, quantize_price, get_market
            q_amount = ensure_min_requirements(ccxt_symbol, amount, price=price, client=self.ccxt_client)
            q_price = quantize_price(ccxt_symbol, price, client=self.ccxt_client)
            
            # Log amount bumping if it occurred
            if q_amount > amount:
                try:
                    m = get_market(ccxt_symbol, self.ccxt_client)
                    min_amount = m.get('limits', {}).get('amount', {}).get('min', 'unknown')
                    min_cost = m.get('limits', {}).get('cost', {}).get('min', 'unknown')
                    logger.info("amount_bumped", extra={
                        "symbol": symbol, 
                        "computed": amount, 
                        "min_amount": min_amount, 
                        "min_cost": min_cost, 
                        "final_amount": q_amount
                    })
                except Exception as e:
                    logger.warning(f"Could not log amount bump details: {e}")
            
            # Client ID
            if client_id is None:
                from execution.id_utils import generate_client_id
                client_id = generate_client_id('E')
            
            # OKX params
            td_mode = self.config.get('td_mode', 'cross')
            hedge_mode = self.config.get('hedge_mode', False)
            
            order_params = {
                'tdMode': td_mode,
                'reduceOnly': False,
                'clientOrderId': client_id,
                'clOrdId': client_id,
            }
            
            if hedge_mode:
                order_params['posSide'] = 'long' if side == 'buy' else 'short'
            
            if params:
                order_params.update(params)
            
            # Create order
            result = self.ccxt_client.create_order(
                ccxt_symbol, 'limit', side, q_amount, q_price, order_params
            )
            
            # Normalize result
            return {
                'status': result.get('status', 'unknown'),
                'type': 'limit',
                'id': result.get('id', ''),
                'clientOrderId': client_id,
                'symbol': symbol,
                'side': side,
                'amount': q_amount,
                'price': q_price,
                'raw': result
            }
            
        except Exception as e:
            from adapters.error_mapping import normalize_error
            error_info = normalize_error(e, {'operation': 'create_limit_order', 'symbol': symbol})
            logger.error(f"❌ Limit order failed for {symbol}: {error_info}")
            raise


class OKXCCXTAdapter:
    """OKX exchange adapter using CCXT library for entry orders."""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.api_key = self.config.get('api_key', '')
        self.secret = self.config.get('secret', '')
        self.passphrase = self.config.get('passphrase', '')
        self.sandbox = self.config.get('sandbox', False)
        self.testnet = self.config.get('testnet', False)
        
        # Exchange instance
        self.exchange: Optional[ccxt.Exchange] = None
        self.pro_exchange: Optional[ccxtpro.Exchange] = None
        self.ccxt_client: Optional[ccxt.Exchange] = None
        
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
            import os
            
            # Get API credentials from environment variables
            api_key = os.getenv('OKX_API_KEY', '')
            secret = os.getenv('OKX_API_SECRET', '')
            passphrase = os.getenv('OKX_API_PASSPHRASE', '')
            testnet = os.getenv('OKX_TESTNET', 'false').lower() == 'true'
            default_type = os.getenv('OKX_DEFAULT_TYPE', 'swap')
            
            # Validate required credentials
            if not api_key:
                raise RuntimeError("OKX_API_KEY is required but not found in environment variables")
            if not secret:
                raise RuntimeError("OKX_API_SECRET is required but not found in environment variables")
            if not passphrase:
                raise RuntimeError("OKX_API_PASSPHRASE is required but not found in environment variables")
            
            # Configure exchange parameters
            exchange_params = {
                'apiKey': api_key,
                'secret': secret,
                'password': passphrase,
                'enableRateLimit': True,
                'rateLimit': 100,  # 100ms between requests
                'timeout': self._timeout_seconds * 1000,
                'options': {
                    'defaultType': default_type,
                    'adjustForTimeDifference': True,
                    'recvWindow': 5000,
                }
            }
            
            # Only add sandbox/testnet if explicitly enabled (OKX doesn't support it well in CCXT)
            if testnet:
                logger.warning("⚠️ Testnet mode requested but OKX testnet support in CCXT is limited")
                # Don't set sandbox/testnet params as they cause hostname to be None
            
            logger.info(f"🔑 Initializing OKX client with API key: {api_key[:8]}...")
            logger.info(f"🔑 Testnet mode: {testnet}, Default type: {default_type}")
            
            # Create exchange instance
            self.exchange = ccxt.okx(exchange_params)
            self.ccxt_client = self.exchange  # Alias for compatibility
            
            # Create pro exchange for async operations
            self.pro_exchange = ccxtpro.okx(exchange_params)
            
            self._initialized = True
            logger.info("✅ OKX CCXT adapter initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OKX CCXT adapter: {e}")
            self._initialized = False
    
    def load_markets(self):
        """Load markets from the exchange."""
        if self.exchange:
            return self.exchange.load_markets()
        return {}
    
    def normalize_symbol_for_ccxt(self, symbol: str) -> str:
        """Normalize symbol for CCXT format."""
        try:
            # Convert from OKX format to CCXT format
            # BTC-USDT-SWAP -> BTC/USDT:USDT
            if symbol.endswith('-USDT-SWAP'):
                base = symbol.replace('-USDT-SWAP', '')
                return f"{base}/USDT:USDT"
            elif symbol.endswith('-USDT'):
                base = symbol.replace('-USDT', '')
                return f"{base}/USDT"
            else:
                return symbol
        except Exception as e:
            logger.error(f"❌ Failed to normalize symbol {symbol}: {e}")
            return symbol
    
    def market(self, symbol: str):
        """Get market information for a symbol."""
        if self.exchange:
            return self.exchange.market(symbol)
        return {}
    
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
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Set leverage for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT-SWAP')
            leverage: Leverage multiplier (e.g., 5)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert symbol to CCXT format
            ccxt_symbol = self.normalize_symbol_for_ccxt(symbol)
            
            # Set leverage via CCXT
            result = self.exchange.set_leverage(leverage, ccxt_symbol)
            logger.info(f"[LEVERAGE] Set {symbol} leverage to {leverage}x")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to set leverage for {symbol}: {e}")
            # Don't raise - leverage setting failure shouldn't block trade
            return False
    
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
    
    async def create_market_order(self, symbol: str, side: str, amount: float, 
                                 *, reduce_only: bool = False, client_id: str = None, 
                                 params: dict = None) -> dict:
        """Create a market order."""
        try:
            # Symbol mapping
            from execution.okx_symbol import okx_to_ccxt_symbol
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            # Get current price for minimum validation
            try:
                ticker = await self.fetch_ticker(symbol)
                current_price = float(ticker.get('last', 0)) if ticker else 0
            except:
                current_price = 0
            
            # Ensure minimum order requirements
            from execution.prevalidation import ensure_minimums
            try:
                adjusted_amount, meta, need = await ensure_minimums(self, ccxt_symbol, current_price, amount)
                
                if need:
                    logger.warning(f"⚠️ Amount below minimum for {symbol}. Required: {need}, Requested: {amount}")
                    logger.info(f"[OKX-LIMITS] sym={symbol} min_cost={meta.get('min_cost')}, min_amount={meta.get('amount_min')}, step={meta.get('amount_step')}, px={current_price}, requested={amount}, adjusted={adjusted_amount}")
                    amount = adjusted_amount
                
            except Exception as e:
                logger.error(f"❌ Failed to ensure minimums: {e}")
                # Fallback to original quantization
                from execution.quantize import quantize_size, bump_to_min_size
                amount = quantize_size(symbol, amount)
                amount = bump_to_min_size(symbol, amount)
            
            # Final quantization
            from execution.quantize import quantize_size, bump_to_min_size
            q_amount = quantize_size(symbol, amount)
            q_amount = bump_to_min_size(symbol, q_amount)
            
            # Client ID
            if client_id is None:
                from execution.id_utils import generate_client_id
                client_id = generate_client_id('E')
            
            # OKX params
            import os
            td_mode = os.getenv('OKX_TD_MODE', 'cross')
            hedge_mode = os.getenv('OKX_HEDGE_MODE', '').strip() in ('1', 'true', 'True')
            
            order_params = {
                'tdMode': td_mode,
                'reduceOnly': reduce_only,
                'clientOrderId': client_id,
                'clOrdId': client_id,
            }
            
            if hedge_mode:
                order_params['posSide'] = 'long' if side == 'buy' else 'short'
            
            if params:
                order_params.update(params)
            
            # CRITICAL FIX: Convert base amount to contract count for OKX swaps
            # OKX expects contract count, not base amount!
            # contracts = base_amount / ctVal
            # e.g., 0.0005 BTC / 0.01 ctVal = 0.05 contracts
            market = self.ccxt_client.market(ccxt_symbol)
            ct_val = float(market.get('info', {}).get('ctVal', 1))
            if ct_val and ct_val != 1.0:
                contracts = q_amount / ct_val
                logger.info(f"📊 {symbol}: Converting base {q_amount} to contracts: {q_amount} / {ct_val} = {contracts}")
                q_amount = contracts
            
            # Ensure minimum 0.01 contracts
            min_contracts = 0.01
            if q_amount < min_contracts:
                logger.warning(f"⚠️ {symbol}: Contracts {q_amount} below minimum {min_contracts}, bumping up")
                q_amount = min_contracts
            
            # Round to lot size (0.01 for OKX swaps)
            lot_sz = float(market.get('info', {}).get('lotSz', 0.01))
            from decimal import Decimal, ROUND_HALF_UP
            q_amount = float(Decimal(str(q_amount)).quantize(Decimal(str(lot_sz)), rounding=ROUND_HALF_UP))
            
            logger.info(f"📊 {symbol}: Final order contracts: {q_amount}")
            
            # Create order
            result = self.ccxt_client.create_order(
                ccxt_symbol, 'market', side, q_amount, None, order_params
            )
            
            # Normalize result
            return {
                'id': result.get('id', ''),
                'status': result.get('status', 'unknown'),
                'symbol': symbol,
                'side': side,
                'type': 'market',
                'amount': q_amount,
                'price': result.get('price'),
                'clientOrderId': client_id
            }
            
        except Exception as e:
            from adapters.error_mapping import normalize_error
            error_info = normalize_error(e, {'operation': 'create_market_order', 'symbol': symbol})
            logger.error(f"❌ Market order failed for {symbol}: {error_info}")
            raise
    
    async def create_trigger_order(self, symbol: str, side: str, trigger_px: float, 
                                  ord_px: float, reduce_only: bool, tag: str) -> dict:
        """Create trigger order (TP/SL)."""
        try:
            # Symbol mapping
            from execution.okx_symbol import okx_to_ccxt_symbol
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            # Prepare trigger order parameters
            order_params = {
                'tdMode': 'cross',
                'ordType': 'conditional',
                'tpTriggerPx': str(trigger_px) if 'TP' in tag else None,
                'slTriggerPx': str(trigger_px) if 'SL' in tag else None,
                'ordPx': str(ord_px) if ord_px > 0 else '-1',
                'reduceOnly': str(reduce_only).lower(),
                'side': side.lower(),  # Convert to lowercase
            }
            
            # Remove None values
            order_params = {k: v for k, v in order_params.items() if v is not None}
            
            # Create trigger order with minimum amount
            result = self.ccxt_client.create_order(
                ccxt_symbol, 'market', side, 0.01, None, order_params
            )
            
            logger.info(f"✅ Trigger order created: {tag} - {side} @ {trigger_px}")
            return {
                'algoId': result.get('id', tag),
                'status': 'live',
                'side': side,
                'triggerPx': trigger_px,
                'ordPx': ord_px,
                'reduceOnly': reduce_only
            }
            
        except Exception as e:
            logger.error(f"❌ Trigger order creation failed for {symbol}: {e}")
            return {}
    
    async def create_limit_order(self, symbol: str, side: str, amount: float, price: float,
                                *, reduce_only: bool = False, client_id: str = None, 
                                params: dict = None) -> dict:
        """Create a limit order."""
        try:
            # Symbol mapping
            from execution.okx_symbol import okx_to_ccxt_symbol
            ccxt_symbol = okx_to_ccxt_symbol(symbol)
            
            # Quantization
            from execution.quantize import quantize_size, bump_to_min_size, quantize_price
            q_amount = quantize_size(symbol, amount)
            q_amount = bump_to_min_size(symbol, q_amount)
            q_price = quantize_price(symbol, price)
            
            # Client ID
            if client_id is None:
                from execution.id_utils import generate_client_id
                client_id = generate_client_id('E')
            
            # OKX params
            import os
            td_mode = os.getenv('OKX_TD_MODE', 'cross')
            hedge_mode = os.getenv('OKX_HEDGE_MODE', '').strip() in ('1', 'true', 'True')
            
            order_params = {
                'tdMode': td_mode,
                'reduceOnly': reduce_only,
                'clientOrderId': client_id,
                'clOrdId': client_id,
            }
            
            if hedge_mode:
                order_params['posSide'] = 'long' if side == 'buy' else 'short'
            
            if params:
                order_params.update(params)
            
            # Create order
            result = await self.ccxt_client.create_order(
                ccxt_symbol, 'limit', side, q_amount, q_price, order_params
            )
            
            # Normalize result
            return {
                'id': result.get('id', ''),
                'status': result.get('status', 'unknown'),
                'symbol': symbol,
                'side': side,
                'type': 'limit',
                'amount': q_amount,
                'price': q_price,
                'clientOrderId': client_id
            }
            
        except Exception as e:
            from adapters.error_mapping import normalize_error
            error_info = normalize_error(e, {'operation': 'create_limit_order', 'symbol': symbol})
            logger.error(f"❌ Limit order failed for {symbol}: {error_info}")
            raise
    
    # ============================================================
    # EXIT STRATEGY METHODS (Trailing Stop, Partial TP, etc.)
    # ============================================================
    
    async def fetch_algo_orders(self, symbol: str = None, order_type: str = 'conditional') -> list:
        """
        Fetch algo orders (TP/SL/conditional orders) from OKX.
        
        Args:
            symbol: Trading symbol (optional, all if None)
            order_type: 'conditional' for TP/SL orders
            
        Returns:
            List of algo orders
        """
        try:
            from execution.okx_symbol import okx_to_ccxt_symbol, ccxt_to_okx_symbol
            
            # OKX uses instId format for algo orders
            params = {'ordType': order_type}
            if symbol:
                okx_symbol = ccxt_to_okx_symbol(symbol) if '/' in symbol else symbol
                params['instId'] = okx_symbol
            
            # CCXT doesn't have native algo order support, use private API
            result = self.exchange.private_get_trade_orders_algo_pending(params)
            
            orders = result.get('data', [])
            logger.info(f"📋 Fetched {len(orders)} algo orders for {symbol or 'all'}")
            return orders
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch algo orders: {e}")
            return []
    
    async def cancel_algo_order(self, algo_order_id: str, symbol: str) -> bool:
        """
        Cancel an algo order (TP/SL).
        
        Args:
            algo_order_id: The algoId from OKX
            symbol: Trading symbol
            
        Returns:
            True if cancelled successfully
        """
        try:
            from execution.okx_symbol import ccxt_to_okx_symbol
            
            okx_symbol = ccxt_to_okx_symbol(symbol) if '/' in symbol else symbol
            
            params = {
                'algoId': algo_order_id,
                'instId': okx_symbol
            }
            
            result = self.exchange.private_post_trade_cancel_algos([params])
            
            if result.get('code') == '0':
                logger.info(f"✅ Cancelled algo order {algo_order_id} for {symbol}")
                return True
            else:
                logger.warning(f"⚠️ Cancel algo order response: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to cancel algo order {algo_order_id}: {e}")
            return False
    
    async def create_algo_stop_loss(self, symbol: str, side: str, size: float, 
                                    trigger_price: float, client_id: str = None) -> dict:
        """
        Create an algo stop-loss order.
        
        Args:
            symbol: Trading symbol
            side: 'buy' to close short, 'sell' to close long
            size: Position size
            trigger_price: Stop loss trigger price
            client_id: Optional client order ID
            
        Returns:
            Algo order result
        """
        try:
            from execution.okx_symbol import ccxt_to_okx_symbol
            from execution.id_utils import generate_client_id
            import os
            
            okx_symbol = ccxt_to_okx_symbol(symbol) if '/' in symbol else symbol
            
            if client_id is None:
                client_id = generate_client_id('A')  # Use 'A' for algo orders
            
            td_mode = os.getenv('OKX_TD_MODE', 'cross')
            
            # Convert size to contracts for swaps - MUST be integer (lot size multiple)
            market = self.exchange.market(symbol if '/' in symbol else f"{symbol.split('-')[0]}/USDT:USDT")
            ct_val = float(market.get('info', {}).get('ctVal', 1))
            if ct_val != 1.0:
                contracts = int(size / ct_val)  # Must be integer for lot size
            else:
                contracts = int(size)  # Must be integer
            
            # Ensure at least 1 contract
            if contracts < 1:
                contracts = 1
            
            # OKX algo order params
            algo_params = {
                'instId': okx_symbol,
                'tdMode': td_mode,
                'side': side,
                'ordType': 'conditional',
                'sz': str(contracts),
                'slTriggerPx': str(trigger_price),
                'slOrdPx': '-1',  # Market order when triggered
                'reduceOnly': True,
                'algoClOrdId': client_id
            }
            
            result = self.exchange.private_post_trade_order_algo(algo_params)
            
            if result.get('code') == '0' and result.get('data'):
                algo_id = result['data'][0].get('algoId', '')
                logger.info(f"✅ Created SL algo order {algo_id} for {symbol} @ {trigger_price}")
                return {
                    'success': True,
                    'algoId': algo_id,
                    'symbol': symbol,
                    'triggerPrice': trigger_price,
                    'size': size
                }
            else:
                logger.error(f"❌ Failed to create SL algo order: {result}")
                return {'success': False, 'error': str(result)}
                
        except Exception as e:
            logger.error(f"❌ Failed to create algo SL for {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def create_algo_take_profit(self, symbol: str, side: str, size: float, 
                                      trigger_price: float, client_id: str = None) -> dict:
        """
        Create an algo take-profit order.
        
        Args:
            symbol: Trading symbol
            side: 'buy' to close short, 'sell' to close long
            size: Position size
            trigger_price: Take profit trigger price
            client_id: Optional client order ID
            
        Returns:
            Algo order result
        """
        try:
            from execution.okx_symbol import ccxt_to_okx_symbol
            from execution.id_utils import generate_client_id
            import os
            
            okx_symbol = ccxt_to_okx_symbol(symbol) if '/' in symbol else symbol
            
            if client_id is None:
                client_id = generate_client_id('A')  # Use 'A' for algo orders
            
            td_mode = os.getenv('OKX_TD_MODE', 'cross')
            
            # Convert size to contracts for swaps - MUST be integer (lot size multiple)
            market = self.exchange.market(symbol if '/' in symbol else f"{symbol.split('-')[0]}/USDT:USDT")
            ct_val = float(market.get('info', {}).get('ctVal', 1))
            if ct_val != 1.0:
                contracts = int(size / ct_val)  # Must be integer for lot size
            else:
                contracts = int(size)  # Must be integer
            
            # Ensure at least 1 contract
            if contracts < 1:
                contracts = 1
            
            # OKX algo order params
            algo_params = {
                'instId': okx_symbol,
                'tdMode': td_mode,
                'side': side,
                'ordType': 'conditional',
                'sz': str(contracts),
                'tpTriggerPx': str(trigger_price),
                'tpOrdPx': '-1',  # Market order when triggered
                'reduceOnly': True,
                'algoClOrdId': client_id
            }
            
            result = self.exchange.private_post_trade_order_algo(algo_params)
            
            if result.get('code') == '0' and result.get('data'):
                algo_id = result['data'][0].get('algoId', '')
                logger.info(f"✅ Created TP algo order {algo_id} for {symbol} @ {trigger_price}")
                return {
                    'success': True,
                    'algoId': algo_id,
                    'symbol': symbol,
                    'triggerPrice': trigger_price,
                    'size': size
                }
            else:
                logger.error(f"❌ Failed to create TP algo order: {result}")
                return {'success': False, 'error': str(result)}
                
        except Exception as e:
            logger.error(f"❌ Failed to create algo TP for {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def update_stop_loss(self, symbol: str, new_stop_price: float, 
                               position_size: float, side: str,
                               current_algo_id: str = None) -> dict:
        """
        Update stop loss - cancels old SL and creates new one.
        
        Args:
            symbol: Trading symbol
            new_stop_price: New stop loss price
            position_size: Current position size
            side: Position side ('long' or 'short')
            current_algo_id: Current SL algo order ID to cancel
            
        Returns:
            Result dict with new algo order info
        """
        try:
            logger.info(f"🔄 Updating SL for {symbol}: new_price={new_stop_price:.4f}")
            
            # Step 1: Cancel existing SL if provided
            if current_algo_id:
                cancelled = await self.cancel_algo_order(current_algo_id, symbol)
                if not cancelled:
                    logger.warning(f"⚠️ Could not cancel existing SL {current_algo_id}")
            
            # Step 2: Create new SL
            # For long position: SL is sell order
            # For short position: SL is buy order
            sl_side = 'sell' if side == 'long' else 'buy'
            
            result = await self.create_algo_stop_loss(
                symbol=symbol,
                side=sl_side,
                size=position_size,
                trigger_price=new_stop_price
            )
            
            if result.get('success'):
                logger.info(f"✅ Updated SL for {symbol} to {new_stop_price:.4f}, algo_id={result.get('algoId')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to update SL for {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def close_position_market(self, symbol: str, size: float, 
                                    side: str, reason: str = "Manual") -> dict:
        """
        Close a position with market order.
        
        Args:
            symbol: Trading symbol
            size: Position size to close
            side: Position side ('long' or 'short')
            reason: Reason for closing
            
        Returns:
            Order result
        """
        try:
            logger.info(f"🔴 Closing {side} position for {symbol}, size={size}, reason={reason}")
            
            # To close: long → sell, short → buy
            close_side = 'sell' if side == 'long' else 'buy'
            
            result = await self.create_market_order(
                symbol=symbol,
                side=close_side,
                amount=size,
                reduce_only=True,
                params={'reduceOnly': True}
            )
            
            if result.get('id'):
                logger.info(f"✅ Position closed: {symbol} {side} {size}, order_id={result.get('id')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to close position {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_position_sl_order(self, symbol: str) -> dict:
        """
        Get the current SL order for a position.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            SL order info or None
        """
        try:
            orders = await self.fetch_algo_orders(symbol)
            
            for order in orders:
                # Check if it's a SL order
                if order.get('slTriggerPx') and float(order.get('slTriggerPx', 0)) > 0:
                    return {
                        'algoId': order.get('algoId'),
                        'triggerPrice': float(order.get('slTriggerPx')),
                        'size': float(order.get('sz', 0)),
                        'side': order.get('side')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get SL order for {symbol}: {e}")
            return None
    
    async def get_position_tp_order(self, symbol: str) -> dict:
        """
        Get the current TP order for a position.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            TP order info or None
        """
        try:
            orders = await self.fetch_algo_orders(symbol)
            
            for order in orders:
                # Check if it's a TP order
                if order.get('tpTriggerPx') and float(order.get('tpTriggerPx', 0)) > 0:
                    return {
                        'algoId': order.get('algoId'),
                        'triggerPrice': float(order.get('tpTriggerPx')),
                        'size': float(order.get('sz', 0)),
                        'side': order.get('side')
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get TP order for {symbol}: {e}")
            return None

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
