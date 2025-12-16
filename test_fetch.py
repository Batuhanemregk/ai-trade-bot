"""Quick test for OHLCV data fetching"""
import asyncio
from adapters.exchange_okx_ccxt import OKXCCXTAdapter

async def test_fetch():
    print("Testing OKX OHLCV fetch...")
    adapter = OKXCCXTAdapter()
    await adapter.initialize()
    
    try:
        # Test XRP
        bars = await adapter.fetch_ohlcv('XRP/USDT:USDT', '15m', limit=10)
        print(f"XRP: Got {len(bars)} bars")
        if bars:
            print(f"  Sample: {bars[0]}")
    except Exception as e:
        print(f"XRP Error: {e}")
    
    try:
        # Test DOGE
        bars = await adapter.fetch_ohlcv('DOGE/USDT:USDT', '15m', limit=10)
        print(f"DOGE: Got {len(bars)} bars")
    except Exception as e:
        print(f"DOGE Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_fetch())
