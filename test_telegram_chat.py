"""
Test Telegram Chat ID - Doğru chat'i bul
"""

import asyncio
import aiohttp

async def test_telegram_chat():
    """Test different chat IDs"""
    print("🧪 Testing Telegram Chat IDs...")
    
    bot_token = "8464603852:AAFJ8HLSep9981KhNIwwrDe8yiBlObMbG1Q"
    
    # Test different chat IDs
    chat_ids = [
        "-4948600750",  # Group chat
        "4948600750",   # Positive group chat
        "4948600750",   # User chat (if it's a user)
    ]
    
    async with aiohttp.ClientSession() as session:
        for i, chat_id in enumerate(chat_ids, 1):
            print(f"\n{i}️⃣ Testing Chat ID: {chat_id}")
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                "chat_id": chat_id,
                "text": f"🧪 Test Message {i} - Chat ID: {chat_id}",
                "parse_mode": "HTML"
            }
            
            try:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('ok'):
                            print(f"✅ Message sent to {chat_id}")
                            print(f"   Chat Type: {result['result']['chat']['type']}")
                            print(f"   Chat Title: {result['result']['chat'].get('title', 'N/A')}")
                        else:
                            print(f"❌ API Error: {result}")
                    else:
                        print(f"❌ HTTP Error: {response.status}")
                        text = await response.text()
                        print(f"   Response: {text}")
            except Exception as e:
                print(f"❌ Exception: {e}")
            
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_telegram_chat())
