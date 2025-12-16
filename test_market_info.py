"""Test market info for different symbol formats"""
import asyncio
from dotenv import load_dotenv
load_dotenv()
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_policy

async def test_market():
    policy = load_policy()
    adapter = OKXCCXTAdapter(policy)
    
    # Load markets
    adapter.load_markets()
    
    symbols = [
        'ETH-USDT-SWAP',      # OKX format
        'ETH/USDT:USDT',      # CCXT format
    ]
    
    for symbol in symbols:
        print(f"\n=== Testing symbol: {symbol} ===")
        try:
            market = adapter.market(symbol)
            info = market.get('info', {})
            print(f"  lotSz: {info.get('lotSz')}")
            print(f"  ctVal: {info.get('ctVal')}")
            print(f"  minSz: {info.get('minSz')}")
            print(f"  Full info keys: {list(info.keys())[:10]}")
        except Exception as e:
            print(f"  ERROR: {e}")
    
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_market())
