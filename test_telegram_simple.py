#!/usr/bin/env python3
"""
Simple Telegram test with signal timeout.
"""

import asyncio
import signal
import os
from infrastructure.bootstrap import load_env
from telegram_bot.bot import TelegramBot

# Global flag for timeout
timeout_flag = False

def timeout_handler(signum, frame):
    """Handle timeout signal."""
    global timeout_flag
    print("\n⏰ Timeout reached! Stopping...")
    timeout_flag = True

async def simple_telegram_test():
    """Simple Telegram test with signal timeout."""
    global timeout_flag
    
    try:
        print("🚀 Simple Telegram Test (10 seconds timeout)...")
        
        # Set signal handler for timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # 10 seconds timeout
        
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
        
        # Check timeout
        if timeout_flag:
            print("⏰ Timeout reached during bot start")
            return
        
        # Wait for initialization
        await asyncio.sleep(2)
        
        # Check timeout again
        if timeout_flag:
            print("⏰ Timeout reached during initialization")
            return
        
        # Send test message
        print("🔄 Sending test message...")
        test_msg = "🧪 Test Message\n\n✅ Bot çalışıyor\n⏰ Time: " + str(asyncio.get_event_loop().time())
        result = await bot.send_message(test_msg)
        print(f"✅ Test message result: {result}")
        
        # Check timeout
        if timeout_flag:
            print("⏰ Timeout reached after sending message")
            return
        
        # Wait for message to be sent
        await asyncio.sleep(1)
        
        # Stop bot
        print("🔄 Stopping bot...")
        await bot.stop()
        print("✅ Bot stopped")
        
        print("🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cancel alarm
        signal.alarm(0)

if __name__ == "__main__":
    try:
        asyncio.run(simple_telegram_test())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
