#!/usr/bin/env python3
"""
Trading Bot Starter with Telegram Integration
"""

import asyncio
import os
import time
import signal
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    load_dotenv(env_file)

from infrastructure.runtime import trading_main
from adapters.telegram.client import init_telegram_app


async def continuous_trading():
    """Run continuous trading cycles."""
    cycle = 0
    while True:
        cycle += 1
        current_time = time.strftime("%H:%M:%S")
        print(f"[INFO] Cycle {cycle} at {current_time}")
        
        try:
            # Use paper mode (live=False) unless explicitly enabled
            live_mode = os.getenv('TRADING_LIVE', 'false').lower() == 'true'
            result = await trading_main(live=live_mode)
            print(f"[OK] Cycle {cycle} completed: {result}")
        except Exception as e:
            print(f"[ERROR] Cycle {cycle} failed: {e}")
        
        print("[INFO] Waiting 15 minutes...")
        await asyncio.sleep(900)  # 15 minutes


async def main():
    """Main entrypoint with Telegram bot integration."""
    print("[INFO] Starting trading bot with Telegram integration")
    
    # Check if Telegram is enabled
    telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'true').lower() == 'true'
    telegram_client = None
    
    # Initialize Telegram bot if enabled
    if telegram_enabled:
        try:
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            if token:
                print("[INFO] Initializing Telegram bot...")
                telegram_client = await init_telegram_app()
                print("[OK] Telegram bot started successfully")
            else:
                print("[WARN] TELEGRAM_BOT_TOKEN not set, Telegram bot disabled")
        except Exception as e:
            print(f"[ERROR] Failed to start Telegram bot: {e}")
            print("[WARN] Continuing without Telegram bot")
    
    # Start trading bot
    trading_task = asyncio.create_task(continuous_trading())
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("\n[INFO] Received shutdown signal, stopping...")
        trading_task.cancel()
        if telegram_client:
            asyncio.create_task(telegram_client.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for trading task
    try:
        await trading_task
    except asyncio.CancelledError:
        print("[INFO] Trading bot stopped")
    finally:
        if telegram_client:
            await telegram_client.stop()
            print("[INFO] Telegram bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
