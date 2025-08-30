#!/usr/bin/env python3
"""
Test script for trading logic functionality.
"""

import asyncio
import os
from infrastructure.bootstrap import load_env
from application.trading_orchestrator import TradingOrchestrator

async def test_trading_logic():
    """Test trading logic functionality."""
    try:
        print("🚀 Testing Trading Logic...")
        
        # Load environment variables
        load_env()
        
        # Create mock config
        config = {
            'mode': 'dry-run',
            'symbols': ['BTC-USDT', 'ETH-USDT'],
            'analysis_interval': 300,
            'position_update_interval': 60
        }
        
        print("✅ Config created")
        
        # Create orchestrator
        orchestrator = TradingOrchestrator(config)
        print("✅ TradingOrchestrator created")
        
        # Test RSI calculation
        print("🔄 Testing RSI calculation...")
        prices = [100, 101, 99, 102, 98, 103, 97, 104, 96, 105, 95, 106, 94, 107, 93, 108, 92, 109, 91, 110]
        rsi = orchestrator._calculate_rsi(prices, 14)
        print(f"✅ RSI: {rsi:.2f}")
        
        # Test MACD calculation
        print("🔄 Testing MACD calculation...")
        macd, signal = orchestrator._calculate_macd(prices)
        print(f"✅ MACD: {macd:.4f}, Signal: {signal:.4f}")
        
        # Test symbol analysis
        print("🔄 Testing symbol analysis...")
        ohlcv = [
            [1000000000, 50000, 51000, 49000, 50500, 1000],  # Mock OHLCV data
            [1000000000, 50500, 52000, 50000, 51500, 1200],
            [1000000000, 51500, 53000, 51000, 52500, 1100],
            [1000000000, 52500, 54000, 52000, 53500, 1300],
            [1000000000, 53500, 55000, 53000, 54500, 1400]
        ] * 20  # 100 data points
        
        signal = await orchestrator._analyze_symbol('BTC-USDT', ohlcv)
        if signal:
            print(f"✅ Signal generated: {signal['side']} with score {signal['score']:.2f}")
        else:
            print("ℹ️ No signal generated (normal)")
        
        print("🎉 All trading logic tests completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_trading_logic())
