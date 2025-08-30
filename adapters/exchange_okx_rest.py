"""
OKX REST API adapter.
Handles trigger/algo orders and advanced features via direct REST API.
"""

import asyncio
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from loguru import logger

from execution.id_utils import generate_algo_id
from execution.okx_symbol import ccxt_to_okx_symbol
from adapters.error_mapping import map_okx_error, is_retryable_error


class OKXRESTAdapter:
    """OKX REST API adapter for advanced trading features."""
    
    def __init__(self, api_key: str = "", secret: str = "", passphrase: str = "",
                 sandbox: bool = False, testnet: bool = False):
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.sandbox = sandbox
        self.testnet = testnet
        
        # API endpoints
        if sandbox or testnet:
            self.base_url = "https://www.okx.com"
            if testnet:
                self.base_url = "https://www.okx.com"
        else:
            self.base_url = "https://www.okx.com"
        
        # API paths
        self.api_paths = {
            'place_order': '/api/v5/trade/order',
            'cancel_order': '/api/v5/trade/cancel-order',
            'amend_order': '/api/v5/trade/amend-order',
            'get_order': '/api/v5/trade/order',
            'get_orders': '/api/v5/trade/orders-pending',
            'get_order_history': '/api/v5/trade/orders-history',
            'place_algo_order': '/api/v5/trade/order-algo',
            'cancel_algo_order': '/api/v5/trade/cancel-algos',
            'get_algo_order': '/api/v5/trade/orders-algo-pending',
            'get_algo_history': '/api/v5/trade/orders-algo-history',
            'get_positions': '/api/v5/account/positions',
            'get_balance': '/api/v5/account/balance',
            'get_instruments': '/api/v5/public/instruments',
            'get_ticker': '/api/v5/market/ticker',
            'get_klines': '/api/v5/market/candles',
            'get_trades': '/api/v5/market/trades',
            'get_order_book': '/api/v5/market/order-book',
        }
        
        # Connection settings
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests
        self._semaphore = asyncio.Semaphore(3)  # Max concurrent requests
        
        # Retry settings
        self._max_retries = 3
        self._base_delay = 1.0
        self._timeout_seconds = 30
        
        # Initialize session
        self._init_session()
    
    def _init_session(self):
        """Initialize HTTP session."""
        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'Content-Type': 'application/json',
                    'OK-ACCESS-KEY': self.api_key,
                    'OK-ACCESS-PASSPHRASE': self.passphrase,
                }
            )
            self._initialized = True
            logger.info("✅ OKX REST adapter initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize OKX REST adapter: {e}")
            self._initialized = False
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - time_since_last)
        
        self._last_request_time = time.time()
    
    def _generate_signature(self, timestamp: str, method: str, request_path: str, 
                           body: str = "") -> str:
        """
        Generate OKX API signature.
        
        Args:
            timestamp: ISO timestamp
            method: HTTP method
            request_path: API request path
            body: Request body
        
        Returns:
            Generated signature
        """
        message = timestamp + method + request_path + body
        signature = hmac.new(
            self.secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _prepare_headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        """
        Prepare request headers with authentication.
        
        Args:
            method: HTTP method
            request_path: API request path
            body: Request body
        
        Returns:
            Request headers
        """
        timestamp = str(int(time.time()))
        signature = self._generate_signature(timestamp, method, request_path, body)
        
        headers = {
            'Content-Type': 'application/json',
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
        }
        
        if self.sandbox:
            headers['x-simulated-trading'] = '1'
        
        return headers
    
    async def _make_request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None,
                           params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Make authenticated HTTP request with retry logic.
        
        Args:
            method: HTTP method
            path: API path
            data: Request body data
            params: Query parameters
        
        Returns:
            Response data
        
        Raises:
            Exception: If all retries fail
        """
        if not self._initialized or not self._session:
            raise RuntimeError("OKX REST adapter not initialized")
        
        async with self._semaphore:
            for attempt in range(self._max_retries + 1):
                try:
                    await self._rate_limit()
                    
                    # Prepare request
                    url = self.base_url + path
                    body = json.dumps(data) if data else ""
                    headers = self._prepare_headers(method, path, body)
                    
                    # Add query parameters
                    if params:
                        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                        url += "?" + query_string
                    
                    logger.debug(f"Making {method} request to {url}")
                    if data:
                        logger.debug(f"Request body: {data}")
                    
                    # Make request
                    async with self._session.request(method, url, headers=headers, data=body) as response:
                        response_text = await response.text()
                        
                        if response.status == 200:
                            try:
                                result = json.loads(response_text)
                                
                                # Check OKX API response
                                if result.get('code') == '0':
                                    return result.get('data', [])
                                else:
                                    error_code = result.get('code', 'unknown')
                                    error_msg = result.get('msg', 'Unknown error')
                                    raise map_okx_error(error_code, error_msg, {
                                        'method': method,
                                        'path': path,
                                        'response': result
                                    })
                                    
                            except json.JSONDecodeError:
                                raise RuntimeError(f"Invalid JSON response: {response_text}")
                        else:
                            raise RuntimeError(f"HTTP {response.status}: {response_text}")
                    
                except Exception as e:
                    if attempt == self._max_retries:
                        # Last attempt failed
                        raise
                    
                    if not is_retryable_error(e):
                        # Non-retryable error
                        raise
                    
                    # Wait before retry
                    delay = self._base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
    
    async def place_order(self, symbol: str, side: str, order_type: str, size: str,
                         price: Optional[str] = None, client_order_id: Optional[str] = None,
                         **kwargs) -> Dict[str, Any]:
        """
        Place an order via REST API.
        
        Args:
            symbol: Trading symbol (CCXT format, will be converted to OKX instId)
            side: Order side ('buy' or 'sell')
            order_type: Order type ('market', 'limit', 'post_only', 'fok', 'ioc')
            size: Order size
            price: Order price (required for limit orders)
            client_order_id: Client order ID (auto-generated if not provided)
            **kwargs: Additional order parameters
        
        Returns:
            Order information
        """
        # Convert symbol to OKX format
        okx_symbol = ccxt_to_okx_symbol(symbol)
        
        # Generate client order ID if not provided
        if not client_order_id:
            client_order_id = generate_algo_id('A')
        
        # Prepare order data
        order_data = {
            'instId': okx_symbol,
            'tdMode': kwargs.get('tdMode', 'cross'),
            'side': side,
            'ordType': order_type,
            'sz': size,
            'clOrdId': client_order_id,
        }
        
        if price:
            order_data['px'] = price
        
        # Add optional parameters
        optional_params = ['posSide', 'tag', 'reduceOnly', 'postOnly', 'tgtCcy']
        for param in optional_params:
            if param in kwargs:
                order_data[param] = kwargs[param]
        
        logger.info(f"📝 Placing {order_type} {side} order: {okx_symbol} {size} @ {price}")
        logger.info(f"   ClientOrderId: {client_order_id} (len: {len(client_order_id)})")
        logger.info(f"   Symbol converted: {symbol} -> {okx_symbol}")
        
        try:
            result = await self._make_request('POST', self.api_paths['place_order'], order_data)
            
            if result and len(result) > 0:
                order_info = result[0]
                logger.info(f"✅ Order placed successfully: {order_info.get('ordId', 'N/A')}")
                return order_info
            else:
                raise RuntimeError("Empty response from order placement")
                
        except Exception as e:
            logger.error(f"❌ Failed to place order: {e}")
            raise
    
    async def place_algo_order(self, symbol: str, side: str, order_type: str, size: str,
                              price: Optional[str] = None, client_order_id: Optional[str] = None,
                              **kwargs) -> Dict[str, Any]:
        """
        Place an algo order (trigger, conditional, etc.).
        
        Args:
            symbol: Trading symbol (CCXT format)
            side: Order side ('buy' or 'sell')
            order_type: Algo order type ('conditional', 'oco', 'trigger', 'move_order_stop', 'twap', 'iceberg')
            size: Order size
            price: Order price
            client_order_id: Client order ID (auto-generated if not provided)
            **kwargs: Additional algo order parameters
        
        Returns:
            Algo order information
        """
        # Convert symbol to OKX format
        okx_symbol = ccxt_to_okx_symbol(symbol)
        
        # Generate client order ID if not provided
        if not client_order_id:
            client_order_id = generate_algo_id('A')
        
        # Prepare algo order data
        algo_data = {
            'instId': okx_symbol,
            'tdMode': kwargs.get('tdMode', 'cross'),
            'side': side,
            'ordType': order_type,
            'sz': size,
            'clOrdId': client_order_id,
        }
        
        if price:
            algo_data['px'] = price
        
        # Add algo-specific parameters
        if order_type == 'conditional':
            algo_data['triggerPx'] = kwargs.get('triggerPx')
            algo_data['orderPx'] = kwargs.get('orderPx')
        elif order_type == 'oco':
            algo_data['tpTriggerPx'] = kwargs.get('tpTriggerPx')
            algo_data['tpOrdPx'] = kwargs.get('tpOrdPx')
            algo_data['slTriggerPx'] = kwargs.get('slTriggerPx')
            algo_data['slOrdPx'] = kwargs.get('slOrdPx')
        elif order_type == 'trigger':
            algo_data['triggerPx'] = kwargs.get('triggerPx')
            algo_data['orderPx'] = kwargs.get('orderPx')
        
        # Add optional parameters
        optional_params = ['posSide', 'tag', 'reduceOnly', 'postOnly', 'tgtCcy']
        for param in optional_params:
            if param in kwargs:
                algo_data[param] = kwargs[param]
        
        logger.info(f"🤖 Placing {order_type} algo order: {okx_symbol} {size} @ {price}")
        logger.info(f"   ClientOrderId: {client_order_id} (len: {len(client_order_id)})")
        
        try:
            result = await self._make_request('POST', self.api_paths['place_algo_order'], algo_data)
            
            if result and len(result) > 0:
                algo_info = result[0]
                logger.info(f"✅ Algo order placed successfully: {algo_info.get('algoId', 'N/A')}")
                return algo_info
            else:
                raise RuntimeError("Empty response from algo order placement")
                
        except Exception as e:
            logger.error(f"❌ Failed to place algo order: {e}")
            raise
    
    async def place_order_with_tp_sl(self, symbol: str, side: str, order_type: str, size: str,
                                    price: str, tp_price: str, sl_price: str,
                                    client_order_id: Optional[str] = None,
                                    **kwargs) -> Dict[str, Any]:
        """
        Place an order with Take Profit and Stop Loss.
        
        Args:
            symbol: Trading symbol
            side: Order side ('buy' or 'sell')
            order_type: Order type ('limit', 'market', etc.)
            size: Order size
            price: Entry order price
            tp_price: Take profit price
            sl_price: Stop loss price
            client_order_id: Client order ID (optional)
            **kwargs: Additional parameters
        
        Returns:
            Order placement result with TP/SL orders
        """
        try:
            # Place entry order
            entry_result = await self.place_order(
                symbol, side, order_type, size, price, client_order_id, **kwargs
            )
            
            if not entry_result.get('data', [{}])[0].get('ordId'):
                raise Exception("Failed to place entry order")
            
            entry_order_id = entry_result['data'][0]['ordId']
            
            # Place TP order
            tp_result = await self.place_algo_order(
                symbol, side, 'conditional', size, tp_price,
                client_order_id=f"{client_order_id}_TP" if client_order_id else None,
                **kwargs
            )
            
            # Place SL order
            sl_result = await self.place_algo_order(
                symbol, side, 'conditional', size, sl_price,
                client_order_id=f"{client_order_id}_SL" if client_order_id else None,
                **kwargs
            )
            
            logger.info(f"✅ Order with TP/SL placed: {symbol} {side} {size}")
            
            return {
                'entry_order': entry_result,
                'tp_order': tp_result,
                'sl_order': sl_result,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to place order with TP/SL: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: str, 
                          client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            symbol: Trading symbol (CCXT format)
            order_id: Exchange order ID
            client_order_id: Client order ID (optional)
        
        Returns:
            Cancellation result
        """
        # Convert symbol to OKX format
        okx_symbol = ccxt_to_okx_symbol(symbol)
        
        # Prepare cancellation data
        cancel_data = {
            'instId': okx_symbol,
            'ordId': order_id,
        }
        
        if client_order_id:
            cancel_data['clOrdId'] = client_order_id
        
        logger.info(f"❌ Cancelling order {order_id} for {okx_symbol}")
        
        try:
            result = await self._make_request('POST', self.api_paths['cancel_order'], cancel_data)
            
            if result and len(result) > 0:
                cancel_info = result[0]
                logger.info(f"✅ Order cancelled successfully: {order_id}")
                return cancel_info
            else:
                raise RuntimeError("Empty response from order cancellation")
                
        except Exception as e:
            logger.error(f"❌ Failed to cancel order {order_id}: {e}")
            raise
    
    async def cancel_algo_order(self, symbol: str, algo_id: str,
                               client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancel an algo order.
        
        Args:
            symbol: Trading symbol (CCXT format)
            algo_id: Exchange algo order ID
            client_order_id: Client order ID (optional)
        
        Returns:
            Cancellation result
        """
        # Convert symbol to OKX format
        okx_symbol = ccxt_to_okx_symbol(symbol)
        
        # Prepare cancellation data
        cancel_data = {
            'instId': okx_symbol,
            'algoId': algo_id,
        }
        
        if client_order_id:
            cancel_data['clOrdId'] = client_order_id
        
        logger.info(f"❌ Cancelling algo order {algo_id} for {okx_symbol}")
        
        try:
            result = await self._make_request('POST', self.api_paths['cancel_algo_order'], cancel_data)
            
            if result and len(result) > 0:
                cancel_info = result[0]
                logger.info(f"✅ Algo order cancelled successfully: {algo_id}")
                return cancel_info
            else:
                raise RuntimeError("Empty response from algo order cancellation")
                
        except Exception as e:
            logger.error(f"❌ Failed to cancel algo order {algo_id}: {e}")
            raise
    
    async def get_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order information.
        
        Args:
            symbol: Trading symbol (CCXT format)
            order_id: Exchange order ID
        
        Returns:
            Order information
        """
        # Convert symbol to OKX format
        okx_symbol = ccxt_to_okx_symbol(symbol)
        
        params = {
            'instId': okx_symbol,
            'ordId': order_id,
        }
        
        try:
            result = await self._make_request('GET', self.api_paths['get_order'], params=params)
            
            if result and len(result) > 0:
                return result[0]
            else:
                raise RuntimeError("Order not found")
                
        except Exception as e:
            logger.error(f"❌ Failed to get order {order_id}: {e}")
            raise
    
    async def get_algo_order(self, symbol: str, algo_id: str) -> Dict[str, Any]:
        """
        Get algo order information.
        
        Args:
            symbol: Trading symbol (CCXT format)
            algo_id: Exchange algo order ID
        
        Returns:
            Algo order information
        """
        # Convert symbol to OKX format
        okx_symbol = ccxt_to_okx_symbol(symbol)
        
        params = {
            'instId': okx_symbol,
            'algoId': algo_id,
        }
        
        try:
            result = await self._make_request('GET', self.api_paths['get_algo_order'], params=params)
            
            if result and len(result) > 0:
                return result[0]
            else:
                raise RuntimeError("Algo order not found")
                
        except Exception as e:
            logger.error(f"❌ Failed to get algo order {algo_id}: {e}")
            raise
    
    async def get_open_orders(self, symbol: Optional[str] = None, 
                             limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get open orders.
        
        Args:
            symbol: Trading symbol (CCXT format, optional)
            limit: Maximum number of orders to fetch
        
        Returns:
            List of open orders
        """
        params = {}
        
        if symbol:
            # Convert symbol to OKX format
            okx_symbol = ccxt_to_okx_symbol(symbol)
            params['instId'] = okx_symbol
        
        if limit:
            params['limit'] = str(limit)
        
        try:
            result = await self._make_request('GET', self.api_paths['get_orders'], params=params)
            return result or []
            
        except Exception as e:
            logger.error(f"❌ Failed to get open orders: {e}")
            raise
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get positions.
        
        Args:
            symbol: Trading symbol (CCXT format, optional)
        
        Returns:
            List of positions
        """
        params = {}
        
        if symbol:
            # Convert symbol to OKX format
            okx_symbol = ccxt_to_okx_symbol(symbol)
            params['instId'] = okx_symbol
        
        try:
            result = await self._make_request('GET', self.api_paths['get_positions'], params=params)
            return result or []
            
        except Exception as e:
            logger.error(f"❌ Failed to get positions: {e}")
            raise
    
    async def get_balance(self, ccy: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get account balance.
        
        Args:
            ccy: Currency (optional)
        
        Returns:
            Account balance information
        """
        params = {}
        
        if ccy:
            params['ccy'] = ccy
        
        try:
            result = await self._make_request('GET', self.api_paths['get_balance'], params=params)
            return result or []
            
        except Exception as e:
            logger.error(f"❌ Failed to get balance: {e}")
            raise
    
    async def get_instruments(self, inst_type: str = 'SWAP', 
                             uly: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get instrument information.
        
        Args:
            inst_type: Instrument type ('SPOT', 'SWAP', 'FUTURES', 'OPTION')
            uly: Underlying (optional)
        
        Returns:
            List of instruments
        """
        params = {'instType': inst_type}
        
        if uly:
            params['uly'] = uly
        
        try:
            result = await self._make_request('GET', self.api_paths['get_instruments'], params=params)
            return result or []
            
        except Exception as e:
            logger.error(f"❌ Failed to get instruments: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """
        Test API connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self.get_balance()
            logger.info("✅ OKX REST connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ OKX REST connection test failed: {e}")
            return False
    
    async def close(self):
        """Close HTTP session."""
        try:
            if self._session:
                await self._session.close()
            logger.info("✅ OKX REST adapter closed")
        except Exception as e:
            logger.error(f"❌ Error closing OKX REST adapter: {e}")
    
    def __repr__(self):
        return (f"OKXRESTAdapter(sandbox={self.sandbox}, testnet={self.testnet}, "
                f"initialized={self._initialized})")


# Global adapter instance
_rest_adapter = None

def get_rest_adapter(api_key: str = "", secret: str = "", passphrase: str = "",
                    sandbox: bool = False, testnet: bool = False) -> OKXRESTAdapter:
    """Get the global REST adapter instance."""
    global _rest_adapter
    if _rest_adapter is None:
        _rest_adapter = OKXRESTAdapter(api_key, secret, passphrase, sandbox, testnet)
    return _rest_adapter


async def place_order_via_rest(symbol: str, side: str, order_type: str, size: str,
                              price: Optional[str] = None, client_order_id: Optional[str] = None,
                              **kwargs) -> Dict[str, Any]:
    """Place order using global REST adapter."""
    adapter = get_rest_adapter()
    return await adapter.place_order(symbol, side, order_type, size, price, client_order_id, **kwargs)


async def place_algo_order_via_rest(symbol: str, side: str, order_type: str, size: str,
                                   price: Optional[str] = None, client_order_id: Optional[str] = None,
                                   **kwargs) -> Dict[str, Any]:
    """Place algo order using global REST adapter."""
    adapter = get_rest_adapter()
    return await adapter.place_algo_order(symbol, side, order_type, size, price, client_order_id, **kwargs)


async def place_order_with_tp_sl_via_rest(symbol: str, side: str, order_type: str, size: str,
                                         price: str, tp_price: str, sl_price: str,
                                         client_order_id: Optional[str] = None,
                                         **kwargs) -> Dict[str, Any]:
    """Place order with TP/SL using global REST adapter."""
    adapter = get_rest_adapter()
    return await adapter.place_order_with_tp_sl(symbol, side, order_type, size, price, tp_price, sl_price, client_order_id, **kwargs)
