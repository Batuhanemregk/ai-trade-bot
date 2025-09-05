"""
Test News API functionality
"""

import asyncio
from adapters.news_apis import CryptoCompareNewsAPI

async def test_news_api():
    """Test news API functionality"""
    print("🧪 Testing News API...")
    
    async with CryptoCompareNewsAPI() as api:
        news = await api.get_crypto_news(5)
        print(f"📰 News count: {len(news)}")
        
        if news:
            print(f"📰 First news: {news[0]}")
            print(f"📰 News titles: {[item.get('title', 'No title') for item in news[:3]]}")
        else:
            print("❌ No news retrieved")

if __name__ == "__main__":
    asyncio.run(test_news_api())
