"""
Direct Telegram API Test - Bot API'yi doğrudan test et
"""

import asyncio
import aiohttp
import json

async def test_telegram_direct():
    """Test Telegram Bot API directly"""
    print("🧪 Testing Telegram Bot API Directly...")
    
    bot_token = "8464603852:AAFJ8HLSep9981KhNIwwrDe8yiBlObMbG1Q"
    chat_id = "-4948600750"
    
    # Test 1: Get Bot Info
    print("\n1️⃣ Testing Bot Info...")
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Bot Info: {data}")
            else:
                print(f"❌ Bot Info Failed: {response.status}")
                text = await response.text()
                print(f"Response: {text}")
    
    # Test 2: Send Message
    print("\n2️⃣ Testing Send Message...")
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": "🧪 Direct API Test Message",
            "parse_mode": "HTML"
        }
        async with session.post(url, json=data) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Message Sent: {result}")
            else:
                print(f"❌ Message Failed: {response.status}")
                text = await response.text()
                print(f"Response: {text}")
    
    # Test 3: Get Updates
    print("\n3️⃣ Testing Get Updates...")
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Updates: {data}")
            else:
                print(f"❌ Updates Failed: {response.status}")
                text = await response.text()
                print(f"Response: {text}")

if __name__ == "__main__":
    asyncio.run(test_telegram_direct())
