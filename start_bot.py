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
from infrastructure.logger import initialize_logging
from adapters.telegram.client import init_telegram_app


from datetime import datetime, timedelta


def get_seconds_until_next_15min():
    """Calculate seconds until next 15-minute mark (clock-aligned)."""
    now = datetime.now()
    # Calculate minutes until next 15-min boundary
    minutes_past = now.minute % 15
    if minutes_past == 0 and now.second < 10:
        # Just started at a 15-min mark, wait for next one
        minutes_until = 15
    else:
        minutes_until = 15 - minutes_past
    
    # Calculate next 15-min mark time
    next_time = now.replace(second=5, microsecond=0) + timedelta(minutes=minutes_until)
    seconds_until = (next_time - now).total_seconds()
    
    return max(5, int(seconds_until))  # At least 5 seconds


async def continuous_trading():
    """Run continuous trading cycles at clock-aligned 15-minute intervals."""
    cycle = 0
    
    # Wait for first aligned slot
    initial_wait = get_seconds_until_next_15min()
    next_slot = (datetime.now() + timedelta(seconds=initial_wait)).strftime("%H:%M")
    print(f"[INFO] First cycle scheduled at {next_slot} (waiting {initial_wait}s)")
    await asyncio.sleep(initial_wait)
    
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
        
        # Wait until next 15-minute mark (clock-aligned: :00, :15, :30, :45)
        wait_seconds = get_seconds_until_next_15min()
        next_slot = (datetime.now() + timedelta(seconds=wait_seconds)).strftime("%H:%M")
        print(f"[INFO] Next cycle at {next_slot} (waiting {wait_seconds}s)")
        await asyncio.sleep(wait_seconds)


async def main():
    """Main entrypoint with Telegram bot integration."""
    # Initialize logging system (writes to logs/aibotbs.log)
    initialize_logging()
    
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
