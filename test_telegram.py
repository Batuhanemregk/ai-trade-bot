#!/usr/bin/env python3
"""
Test script for Telegram bot functionality.
"""

import asyncio
import os
from infrastructure.bootstrap import load_env
from telegram_bot.bot import TelegramBot

async def test_telegram_bot():
    """Test Telegram bot functionality."""
    try:
        print("🚀 Testing Telegram Bot...")
        
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
        
        # Start bot in background
        print("🔄 Starting bot...")
        start_task = asyncio.create_task(bot.start())
        
        # Wait a bit for bot to initialize
        await asyncio.sleep(3)
        
        # Test initialize
        print("🔄 Testing initialize...")
        init_result = await bot.initialize()
        print(f"✅ Initialize result: {init_result}")
        
        # Test send message
        print("🔄 Testing send_message...")
        message_result = await bot.send_message("🤖 AiBotBS Test Message\n\nBot çalışıyor! 🚀")
        print(f"✅ Send message result: {message_result}")
        
        # Test send notification
        print("🔄 Testing send_notification...")
        notification_result = await bot.send_notification(
            "Test Notification", 
            "Bu bir test bildirimidir!\n\n✅ Bot aktif\n✅ Sistem çalışıyor\n✅ Trading hazır", 
            "success"
        )
        print(f"✅ Send notification result: {notification_result}")
        
        # Stop bot
        print("🔄 Stopping bot...")
        await bot.stop()
        
        print("🎉 All Telegram tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_telegram_bot())
