#!/usr/bin/env python3
"""
Test script for Telegram messages.
"""

import asyncio
import os
from infrastructure.bootstrap import load_env
from telegram_bot.bot import TelegramBot

async def test_telegram_messages():
    """Test Telegram message sending."""
    try:
        print("🚀 Testing Telegram Messages...")
        
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
        await asyncio.sleep(3)
        
        # Test 1: Startup Message
        print("🔄 Test 1: Startup Message...")
        startup_msg = "🤖 AiBotBS Trading System\n\n✅ Sistem başlatıldı\n✅ Telegram bot aktif\n✅ Trading hazır"
        result1 = await bot.send_message(startup_msg)
        print(f"✅ Startup message: {result1}")
        
        # Test 2: Trading Signal
        print("🔄 Test 2: Trading Signal...")
        signal_msg = "📊 Trading Signal: BTC-USDT\n\n🟢 LONG Signal\n📈 Score: 0.85\n📊 RSI: 25.5 (Oversold)\n📉 MACD: Bullish\n💰 Entry: $45,000"
        result2 = await bot.send_message(signal_msg)
        print(f"✅ Signal message: {result2}")
        
        # Test 3: Risk Alert
        print("🔄 Test 3: Risk Alert...")
        risk_msg = "⚠️ Risk Alert\n\n🔴 High Risk Detected\n📊 Portfolio Exposure: 85%\n💸 Daily Loss: -2.3%\n🛑 Stop Loss Triggered"
        result3 = await bot.send_message(risk_msg)
        print(f"✅ Risk message: {result3}")
        
        # Test 4: Portfolio Update
        print("🔄 Test 4: Portfolio Update...")
        portfolio_msg = "💼 Portfolio Update\n\n💰 Total Value: $12,450\n📈 Daily PnL: +$234 (+1.9%)\n🟢 Active Positions: 3\n📊 BTC-USDT: +$156\n📊 ETH-USDT: +$78"
        result4 = await bot.send_message(portfolio_msg)
        print(f"✅ Portfolio message: {result4}")
        
        # Wait for messages to be sent
        await asyncio.sleep(5)
        
        # Stop bot
        print("🔄 Stopping bot...")
        await bot.stop()
        print("✅ Bot stopped")
        
        print("🎉 All Telegram message tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_telegram_messages())
