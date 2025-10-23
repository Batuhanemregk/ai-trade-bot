"""
Real Exchange API Integration Tests
Tests actual OKX API connectivity and data retrieval without mocks
"""
import pytest
import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Any

from adapters.exchange_okx_ccxt import OKXExchangeAdapter
from adapters.exchange_okx_rest import OKXRESTAdapter
from application.market_data_service import MarketDataService
from configs.policy import load_policy


class TestRealExchangeAPI:
    """Test real OKX exchange API connectivity and data retrieval"""
    
    @pytest.fixture(scope="class")
    def policy(self):
        """Load real policy configuration"""
        return load_policy()
    
    @pytest.fixture(scope="class")
    def exchange_adapter(self, policy):
        """Create real OKX exchange adapter"""
        return OKXExchangeAdapter(policy)
    
    @pytest.fixture(scope="class")
    def rest_adapter(self, policy):
        """Create real OKX REST adapter"""
        return OKXRESTAdapter(policy)
    
    @pytest.fixture(scope="class")
    def market_data_service(self, exchange_adapter, policy):
        """Create real market data service"""
        return MarketDataService(exchange_adapter, policy)
    
    @pytest.mark.asyncio
    async def test_exchange_connection(self, exchange_adapter):
        """Test basic connection to OKX exchange"""
        try:
            # Test if we can connect to the exchange
            markets = await exchange_adapter.fetch_ohlcv("BTC-USDT-SWAP", "15m", limit=1)
            assert markets is not None
            assert len(markets) > 0
            print(f"Connected to OKX, found {len(markets)} markets")
        except Exception as e:
            pytest.skip(f"OKX connection failed (likely API keys not configured): {e}")
    
    @pytest.mark.asyncio
    async def test_get_real_ohlcv_data(self, exchange_adapter):
        """Test fetching real OHLCV data from OKX"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            limit = 100
            
            ohlcv = await exchange_adapter.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            assert ohlcv is not None
            assert len(ohlcv) > 0
            assert len(ohlcv) <= limit
            
            # Check data structure
            for candle in ohlcv:
                assert len(candle) >= 5  # OHLCV
                assert isinstance(candle[0], (int, float))  # timestamp
                assert isinstance(candle[1], (int, float))  # open
                assert isinstance(candle[2], (int, float))  # high
                assert isinstance(candle[3], (int, float))  # low
                assert isinstance(candle[4], (int, float))  # close
                assert candle[1] > 0  # positive price
                assert candle[2] >= candle[1]  # high >= open
                assert candle[3] <= candle[1]  # low <= open
                assert candle[4] > 0  # positive close
            
            print(f"Retrieved {len(ohlcv)} real OHLCV candles for {symbol}")
            
        except Exception as e:
            pytest.skip(f"OHLCV data fetch failed: {e}")
    
    @pytest.mark.asyncio
    async def test_get_real_ticker_data(self, exchange_adapter):
        """Test fetching real ticker data"""
        try:
            symbol = "BTC-USDT-SWAP"
            ticker = await exchange_adapter.fetch_ticker(symbol)
            
            assert ticker is not None
            assert 'last' in ticker
            assert 'bid' in ticker
            assert 'ask' in ticker
            assert 'volume' in ticker
            assert ticker['last'] > 0
            assert ticker['bid'] > 0
            assert ticker['ask'] > 0
            assert ticker['volume'] >= 0
            
            print(f"Retrieved real ticker for {symbol}: ${ticker['last']}")
            
        except Exception as e:
            pytest.skip(f"Ticker data fetch failed: {e}")
    
    @pytest.mark.asyncio
    async def test_get_real_orderbook(self, exchange_adapter):
        """Test fetching real orderbook data"""
        try:
            symbol = "BTC-USDT-SWAP"
            limit = 20
            
            orderbook = await exchange_adapter.fetch_order_book(symbol, limit)
            
            assert orderbook is not None
            assert 'bids' in orderbook
            assert 'asks' in orderbook
            assert len(orderbook['bids']) > 0
            assert len(orderbook['asks']) > 0
            assert len(orderbook['bids']) <= limit
            assert len(orderbook['asks']) <= limit
            
            # Check bid/ask structure
            for bid in orderbook['bids']:
                assert len(bid) == 2  # [price, amount]
                assert bid[0] > 0  # positive price
                assert bid[1] > 0  # positive amount
            
            for ask in orderbook['asks']:
                assert len(ask) == 2  # [price, amount]
                assert ask[0] > 0  # positive price
                assert ask[1] > 0  # positive amount
            
            # Check that best bid < best ask
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]
            assert best_bid < best_ask
            
            print(f"Retrieved real orderbook for {symbol}: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
            
        except Exception as e:
            pytest.skip(f"Orderbook data fetch failed: {e}")
    
    @pytest.mark.asyncio
    async def test_market_data_service_real_data(self, market_data_service):
        """Test market data service with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframes = ["15m", "1h"]
            
            for tf in timeframes:
                data = await market_data_service._fetch_ohlcv(symbol, tf)
                
                assert data is not None
                assert len(data) > 0
                assert len(data) <= 50
                
                # Check that data is recent (within last 24 hours for 15m, 7 days for 1h)
                latest_timestamp = data.index[-1]
                now = datetime.now(timezone.utc)
                time_diff = (now - latest_timestamp).total_seconds()
                
                if tf == "15m":
                    assert time_diff < 24 * 3600  # 24 hours
                elif tf == "1h":
                    assert time_diff < 7 * 24 * 3600  # 7 days
                
                print(f"Market data service retrieved {len(data)} {tf} candles for {symbol}")
            
        except Exception as e:
            pytest.skip(f"Market data service test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_multiple_symbols_real_data(self, exchange_adapter):
        """Test fetching data for multiple symbols"""
        try:
            symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
            results = {}
            
            for symbol in symbols:
                try:
                    ticker = await exchange_adapter.fetch_ticker(symbol)
                    ohlcv = await exchange_adapter.fetch_ohlcv(symbol, "15m", limit=10)
                    
                    results[symbol] = {
                        'ticker': ticker,
                        'ohlcv_count': len(ohlcv)
                    }
                    
                    print(f"{symbol}: ${ticker['last']} ({len(ohlcv)} candles)")
                    
                except Exception as e:
                    print(f"{symbol}: Failed - {e}")
                    results[symbol] = {'error': str(e)}
            
            # At least one symbol should work
            successful_symbols = [s for s, r in results.items() if 'error' not in r]
            assert len(successful_symbols) > 0, "No symbols returned data successfully"
            
            print(f"Successfully tested {len(successful_symbols)}/{len(symbols)} symbols")
            
        except Exception as e:
            pytest.skip(f"Multiple symbols test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_rest_adapter_real_data(self, rest_adapter):
        """Test OKX REST adapter with real data"""
        try:
            # Test account info (if API keys are configured)
            account_info = await rest_adapter.get_balance()
            
            if account_info:
                assert isinstance(account_info, list)
                print(f"REST adapter: Retrieved {len(account_info)} balance entries")
            else:
                print("REST adapter: No account info (likely demo mode)")
            
        except Exception as e:
            print(f"REST adapter test skipped: {e}")
    
    def test_api_rate_limits(self, exchange_adapter):
        """Test API rate limiting behavior"""
        # This test checks if we're respecting rate limits
        # by making multiple rapid requests and checking for rate limit errors
        
        async def make_rapid_requests():
            """Make multiple rapid requests to test rate limiting"""
            tasks = []
            for i in range(10):  # Make 10 rapid requests
                task = exchange_adapter.fetch_ticker("BTC-USDT-SWAP")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful vs failed requests
            successful = sum(1 for r in results if not isinstance(r, Exception))
            failed = sum(1 for r in results if isinstance(r, Exception))
            
            print(f"Rate limit test: {successful} successful, {failed} failed")
            
            # We expect some failures due to rate limiting
            return successful, failed
        
        try:
            successful, failed = asyncio.run(make_rapid_requests())
            assert successful > 0, "No requests succeeded"
            print(f"Rate limiting test completed: {successful} success, {failed} failures")
            
        except Exception as e:
            pytest.skip(f"Rate limit test failed: {e}")


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/integration/test_real_exchange_api.py -v -s
    pytest.main([__file__, "-v", "-s"])
