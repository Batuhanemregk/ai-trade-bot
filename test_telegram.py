"""
Telegram Test - Gerçek API Token'ları Test Et
"""

import asyncio
import os
from dotenv import load_dotenv
from adapters.telegram_client import TelegramClient

async def test_telegram():
    """Test Telegram notifications with real API keys"""
    print("🧪 Testing Telegram Notifications...")
    
    # Load environment variables
    load_dotenv()
    
    # Get API credentials
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print(f"🔑 Bot Token: {bot_token[:10]}..." if bot_token else "❌ Bot Token: NOT FOUND")
    print(f"💬 Chat ID: {chat_id}")
    
    if not bot_token or not chat_id:
        print("❌ Telegram credentials not found in .env file")
        return
    
    if bot_token == "test_token" or chat_id == "test_chat":
        print("⚠️ WARNING: Using test credentials! Update .env with real values")
        return
    
    # Test environment variable loading
    print(f"\n🔍 Environment Variables:")
    print(f"TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN', 'NOT_SET')}")
    print(f"TELEGRAM_CHAT_ID: {os.getenv('TELEGRAM_CHAT_ID', 'NOT_SET')}")
    
    # Test different message types
    test_messages = [
        "🧪 Test Message 1: Basic notification",
        "🚀 [ENTRY] BTC-USDT-SWAP LONG size=0.001 px=50000.0 reason=score>=75",
        "💰 [EXIT] ETH-USDT-SWAP reason=TP pnl=+150.0 r=2.5x",
        "🔄 [REVCHK] SOL-USDT-SWAP strength=0.85 confirm=3 → REVERSE",
        "📈 [TRAIL] ADA-USDT-SWAP moved to BE=0.45 tightened=true",
        "⚠️ [RISK] DOT-USDT-SWAP position_size_high size=5.2% limit=5.0%",
        "📰 [NEWS] BTC-USDT-SWAP positive conf=0.85 Bitcoin ETF approved",
        "🔧 [SYSTEM] scheduler_started jobs=6 next=00:35:00"
    ]
    
    # Initialize Telegram client
    telegram_config = {
        'bot_token': bot_token,
        'chat_id': chat_id,
        'timeout_sec': 10,
        'retries': 3,
        'backoff_seconds': [2, 4, 8]
    }
    telegram_client = TelegramClient(telegram_config)
    
    print(f"\n📤 Sending {len(test_messages)} test messages...")
    
    for i, message in enumerate(test_messages, 1):
        try:
            print(f"📤 Sending message {i}/{len(test_messages)}...")
            success = await telegram_client.send_message(message)
            
            if success:
                print(f"✅ Message {i} sent successfully")
            else:
                print(f"❌ Message {i} failed to send")
                
            # Wait 1 second between messages
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Error sending message {i}: {e}")
    
    print("\n🎯 Telegram test completed!")
    print("📱 Check your Telegram chat for messages")

if __name__ == "__main__":
    asyncio.run(test_telegram())