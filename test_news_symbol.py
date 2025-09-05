"""
Test News Symbol Filtering
"""

import asyncio
from adapters.news_apis import CryptoCompareNewsAPI

async def test_news_symbol():
    """Test news filtering for specific symbols"""
    print("🧪 Testing News Symbol Filtering...")
    
    async with CryptoCompareNewsAPI() as api:
        # Test BTC
        btc_news = await api.get_news_for_symbol('BTC-USDT-SWAP', 5)
        print(f"📰 BTC News count: {len(btc_news)}")
        if btc_news:
            print(f"📰 BTC First news: {btc_news[0].get('title', 'No title')}")
        
        # Test ETH
        eth_news = await api.get_news_for_symbol('ETH-USDT-SWAP', 5)
        print(f"📰 ETH News count: {len(eth_news)}")
        if eth_news:
            print(f"📰 ETH First news: {eth_news[0].get('title', 'No title')}")
        
        # Test SOL
        sol_news = await api.get_news_for_symbol('SOL-USDT-SWAP', 5)
        print(f"📰 SOL News count: {len(sol_news)}")
        if sol_news:
            print(f"📰 SOL First news: {sol_news[0].get('title', 'No title')}")

if __name__ == "__main__":
    asyncio.run(test_news_symbol())
