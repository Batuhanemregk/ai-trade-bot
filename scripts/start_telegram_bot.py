#!/usr/bin/env python3
"""
Telegram Bot Starter Script
Standalone script to start Telegram bot independently.
Used by dev.ps1 and can be run directly.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_file = Path(__file__).parent.parent / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"[OK] Loaded .env from: {env_file}")
else:
    print(f"[WARN] .env file not found at: {env_file}")

from adapters.telegram.client import init_telegram_app


async def main():
    """Main entrypoint for Telegram bot."""
    try:
        print("[INFO] Initializing Telegram bot...")
        client = await init_telegram_app()
        print("[OK] Telegram bot started successfully")
        print("[INFO] Bot is running. Press Ctrl+C to stop...")
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n[INFO] Stopping Telegram bot...")
            await client.stop()
            print("[INFO] Telegram bot stopped")
            
    except Exception as e:
        print(f"[ERROR] Failed to start Telegram bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

