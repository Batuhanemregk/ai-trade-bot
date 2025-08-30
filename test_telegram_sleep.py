#!/usr/bin/env python3
"""
Telegram test with sleep timeout.
"""

import asyncio
import os
from infrastructure.bootstrap import load_env
from telegram_bot.bot import TelegramBot

async def telegram_test_with_sleep():
    """Telegram test with sleep timeout."""
    try:
        print("🚀 Telegram Test with Sleep Timeout (8 seconds total)...")
        
        # Load environment variables
        load_env()
        
        # Create bot instance
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        print(f"✅ Token: {token[:20] if token else 'None'}...")
        print(f"✅ Chat ID: {chat_id}")
        
        if not token:
            print("❌ TELEGRAM_BOT_TOKEN not found!")
            return
        
        bot = TelegramBot(token)
        print("✅ Bot instance created")
        
        # Start bot
        print("🔄 Starting bot...")
        await bot.start()
        print("✅ Bot started")
        
        # Wait for initialization
        await asyncio.sleep(2)
        
        # Send test message
        print("🔄 Sending test message...")
        test_msg = "🧪 Test Message\n\n✅ Bot çalışıyor\n⏰ Time: " + str(asyncio.get_event_loop().time())
        result = await bot.send_message(test_msg)
        print(f"✅ Test message result: {result}")
        
        # Wait for message to be sent
        await asyncio.sleep(2)
        
        # Stop bot
        print("🔄 Stopping bot...")
        await bot.stop()
        print("✅ Bot stopped")
        
        print("🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Run with sleep timeout
    print("⏰ Script will run for 8 seconds total...")
    asyncio.run(telegram_test_with_sleep())
    print("🏁 Script finished!")
