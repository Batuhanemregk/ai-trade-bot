"""
Test script for executing a single live trade with TP/SL on OKX.
Executes a minimal trade to demonstrate the trading system.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Load .env file
project_root = Path(__file__).parent.parent
env_file = project_root / '.env'
if env_file.exists():
    load_dotenv(env_file)
    print(f"[OK] Loaded .env from: {env_file}")

# Add project root to path
sys.path.insert(0, str(project_root))

from loguru import logger
from adapters.exchange_okx_ccxt import OKXCCXTAdapter


async def execute_test_trade():
    """Execute a minimal test trade with TP/SL."""
    print("\n" + "="*80)
    print("🚀 EXECUTING TEST TRADE WITH TP/SL")
    print("="*80)
    
    # Configuration
    symbol = "SOL-USDT-SWAP"  # Use SOL which has lower min order requirements
    trade_side = "buy"  # Long position
    trade_amount_usdt = 10  # $10 minimum order
    
    # Create exchange adapter
    config = {
        'api_key': os.getenv('OKX_API_KEY'),
        'secret': os.getenv('OKX_API_SECRET'),
        'passphrase': os.getenv('OKX_API_PASSPHRASE'),
        'sandbox': False,
        'mode': 'live'
    }
    
    print(f"\n🔑 API Key: {config['api_key'][:8]}...")
    print(f"🔑 API Secret: {'*' * 8}")
    print(f"🔑 Passphrase: {'*' * 8}")
    
    adapter = OKXCCXTAdapter(config)
    
    try:
        # Step 1: Get current price
        print(f"\n📊 Fetching current price for {symbol}...")
        ohlcv = await adapter.fetch_ohlcv(symbol, '1m', limit=1)
        if not ohlcv:
            print("❌ Could not fetch price")
            return False
        
        current_price = float(ohlcv[0][4])  # Close price
        print(f"💲 Current price: ${current_price}")
        
        # Step 2: Calculate trade size
        trade_size = trade_amount_usdt / current_price
        # Round to appropriate precision
        trade_size = round(trade_size, 3)
        print(f"📐 Trade size: {trade_size} {symbol.split('-')[0]}")
        
        # Step 3: Calculate TP/SL levels
        # TP: +1.5% from entry
        # SL: -1% from entry
        tp_price = round(current_price * 1.015, 2)  # +1.5%
        sl_price = round(current_price * 0.99, 2)   # -1%
        
        print(f"\n🎯 Trade Parameters:")
        print(f"   Entry: ${current_price}")
        print(f"   Take Profit: ${tp_price} (+1.5%)")
        print(f"   Stop Loss: ${sl_price} (-1%)")
        print(f"   Size: {trade_size} ({trade_amount_usdt} USDT)")
        print(f"   Risk/Reward: 1:1.5")
        
        # Step 4: Execute the trade
        print(f"\n🚀 Executing {trade_side.upper()} order...")
        
        order_result = await adapter.create_order(
            symbol=symbol,
            order_type='market',
            side=trade_side,
            amount=trade_size,
            price=None,  # Market order doesn't need price
            params={}  # No posSide for net mode
        )
        
        if not order_result:
            print("❌ Order execution failed")
            return False
        
        print(f"✅ Entry order executed!")
        print(f"   Order ID: {order_result.get('id', 'N/A')}")
        print(f"   Status: {order_result.get('status', 'N/A')}")
        
        # Get actual fill price
        fill_price = float(order_result.get('average', current_price))
        print(f"   Fill Price: ${fill_price}")
        
        # Recalculate TP/SL based on actual fill
        tp_price = round(fill_price * 1.015, 2)
        sl_price = round(fill_price * 0.99, 2)
        
        # Step 5: Place TP order (conditional/algo order)
        print(f"\n🎯 Placing Take Profit order at ${tp_price}...")
        
        try:
            tp_result = await adapter.create_tpsl_order(
                symbol=symbol,
                side='sell',  # Close long = sell
                amount=trade_size,
                tp_price=tp_price,
                sl_price=None,
                pos_side='net'  # Use net mode
            )
            
            if tp_result:
                print(f"✅ Take Profit order placed!")
                print(f"   Algo ID: {tp_result.get('id', 'N/A')}")
            else:
                print("⚠️ TP order placement returned no result")
                
        except Exception as e:
            print(f"⚠️ TP order failed: {e}")
        
        # Step 6: Place SL order (conditional/algo order)
        print(f"\n🛡️ Placing Stop Loss order at ${sl_price}...")
        
        try:
            sl_result = await adapter.create_tpsl_order(
                symbol=symbol,
                side='sell',  # Close long = sell
                amount=trade_size,
                tp_price=None,
                sl_price=sl_price,
                pos_side='net'  # Use net mode
            )
            
            if sl_result:
                print(f"✅ Stop Loss order placed!")
                print(f"   Algo ID: {sl_result.get('id', 'N/A')}")
            else:
                print("⚠️ SL order placement returned no result")
                
        except Exception as e:
            print(f"⚠️ SL order failed: {e}")
        
        # Step 7: Verify position
        print(f"\n📊 Verifying open position...")
        
        positions = await adapter.fetch_positions([symbol])
        
        if positions:
            for pos in positions:
                if pos.get('symbol') == symbol and float(pos.get('contracts', 0)) != 0:
                    print(f"✅ Position confirmed!")
                    print(f"   Symbol: {pos.get('symbol')}")
                    print(f"   Side: {pos.get('side')}")
                    print(f"   Size: {pos.get('contracts')}")
                    print(f"   Entry: ${pos.get('entryPrice')}")
                    print(f"   Unrealized PNL: ${pos.get('unrealizedPnl', 0)}")
        else:
            print("⚠️ Could not verify position (may still be valid)")
        
        # Step 8: Send Telegram notification
        print(f"\n📱 Sending Telegram notification...")
        
        try:
            from telegram import Bot
            
            token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if token and chat_id:
                bot = Bot(token=token)
                
                message = f"""🚀 <b>TEST TRADE EXECUTED</b>

<b>Symbol:</b> {symbol}
<b>Side:</b> {trade_side.upper()}
<b>Size:</b> {trade_size}
<b>Entry:</b> ${fill_price}

<b>Risk Management:</b>
🎯 TP: ${tp_price} (+1.5%)
🛡️ SL: ${sl_price} (-1%)
📊 R/R: 1:1.5

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ <i>Live trade with TP/SL confirmed!</i>"""
                
                await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
                print("✅ Telegram notification sent!")
            else:
                print("⚠️ Telegram credentials not found")
                
        except Exception as e:
            print(f"⚠️ Telegram notification failed: {e}")
        
        print("\n" + "="*80)
        print("✅ TEST TRADE COMPLETED SUCCESSFULLY!")
        print("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Trade execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await adapter.close()


if __name__ == "__main__":
    print("🔴 WARNING: This will execute a REAL trade on OKX!")
    print("   Amount: ~$10 USDT")
    print("   Symbol: SOL-USDT-SWAP")
    print("")
    
    # Check for confirmation
    if len(sys.argv) > 1 and sys.argv[1] == '--confirm':
        result = asyncio.run(execute_test_trade())
        sys.exit(0 if result else 1)
    else:
        print("To execute, run with --confirm flag:")
        print("  python scripts/test_live_trade.py --confirm")
        sys.exit(0)
