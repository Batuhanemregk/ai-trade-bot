#!/usr/bin/env python3
"""
Test script for Telegram bot integration with trading system.
"""

import asyncio
import os
from infrastructure.bootstrap import load_env
from application.trading_orchestrator import TradingOrchestrator

async def test_telegram_integration():
    """Test Telegram bot integration with trading system."""
    try:
        print("🚀 Testing Telegram Bot Integration...")
        
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
        
        # Wait a bit for initialization
        await asyncio.sleep(5)
        
        # Test startup notification
        print("🔄 Testing startup notification...")
        await orchestrator._send_startup_notification()
        print("✅ Startup notification sent")
        
        # Test analysis notification
        print("🔄 Testing analysis notification...")
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
        print("✅ Analysis notification sent")
        
        # Wait a bit for messages to be sent
        await asyncio.sleep(3)
        
        # Stop orchestrator
        print("🔄 Stopping orchestrator...")
        await orchestrator.stop()
        print("✅ Orchestrator stopped")
        
        print("🎉 All Telegram integration tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_telegram_integration())
