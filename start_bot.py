#!/usr/bin/env python3
"""
Simple Trading Bot Starter
"""

import asyncio
import time
from infrastructure.runtime import trading_main

async def continuous_trading():
    cycle = 0
    while True:
        cycle += 1
        current_time = time.strftime("%H:%M:%S")
        print(f"🔄 Cycle {cycle} at {current_time}")
        
        try:
            result = await trading_main(live=True)
            print(f"✅ Cycle {cycle} completed: {result}")
        except Exception as e:
            print(f"❌ Cycle {cycle} failed: {e}")
        
        print("⏰ Waiting 15 minutes...")
        await asyncio.sleep(900)  # 15 minutes

if __name__ == "__main__":
    print("🚀 Starting continuous trading bot")
    asyncio.run(continuous_trading())
