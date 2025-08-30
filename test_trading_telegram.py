#!/usr/bin/env python3
"""
Test script for Telegram integration with trading system.
"""

import asyncio
import os
from infrastructure.bootstrap import load_env
from application.trading_orchestrator import TradingOrchestrator

async def test_trading_telegram():
    """Test Telegram integration with trading system."""
    try:
        print("🚀 Testing Trading + Telegram Integration...")
        
        # Load environment variables
        load_env()
        
        # Create config with Telegram enabled
        config = {
            'mode': 'dry-run',
            'symbols': ['BTC-USDT', 'ETH-USDT'],
            'analysis_interval': 300,
            'position_update_interval': 60,
            'telegram': {
                'enabled': True,
                'token': os.getenv('TELEGRAM_BOT_TOKEN'),
                'chat_id': os.getenv('TELEGRAM_CHAT_ID')
            }
        }
        
        print("✅ Config created with Telegram settings")
        
        # Create orchestrator
        orchestrator = TradingOrchestrator(config)
        print("✅ TradingOrchestrator created")
        
        # Start orchestrator
        print("🔄 Starting orchestrator...")
        await orchestrator.start()
        print("✅ Orchestrator started")
        
        # Wait for initialization
        await asyncio.sleep(5)
        
        # Test 1: Startup notification
        print("🔄 Test 1: Startup notification...")
        await orchestrator._send_startup_notification()
        print("✅ Startup notification sent")
        
        # Test 2: Mock trading signal
        print("🔄 Test 2: Mock trading signal...")
        mock_signal = {
            'symbol': 'BTC-USDT',
            'side': 'long',
            'score': 0.85,
            'rsi': 25.5,
            'macd': 0.0023,
            'signal': 0.0018,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        await orchestrator._execute_trade_signal('BTC-USDT', mock_signal)
        print("✅ Trading signal notification sent")
        
        # Test 3: Risk alert
        print("🔄 Test 3: Risk alert...")
        await orchestrator._send_notification(
            "Risk Alert",
            "⚠️ High Risk Detected\n\n🔴 Portfolio Exposure: 85%\n💸 Daily Loss: -2.3%\n🛑 Stop Loss Triggered",
            "warning"
        )
        print("✅ Risk alert sent")
        
        # Test 4: Portfolio update
        print("🔄 Test 4: Portfolio update...")
        await orchestrator._send_notification(
            "Portfolio Update",
            "💼 Portfolio Status\n\n💰 Total Value: $12,450\n📈 Daily PnL: +$234 (+1.9%)\n🟢 Active Positions: 3\n📊 BTC-USDT: +$156\n📊 ETH-USDT: +$78",
            "info"
        )
        print("✅ Portfolio update sent")
        
        # Wait for messages to be sent
        await asyncio.sleep(5)
        
        # Stop orchestrator
        print("🔄 Stopping orchestrator...")
        await orchestrator.stop()
        print("✅ Orchestrator stopped")
        
        print("🎉 All trading + Telegram tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_trading_telegram())
