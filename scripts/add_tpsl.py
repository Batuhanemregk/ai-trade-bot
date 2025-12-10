"""
Quick script to check positions and add TP/SL.
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from adapters.exchange_okx_ccxt import OKXCCXTAdapter

async def main():
    config = {
        'api_key': os.getenv('OKX_API_KEY'),
        'secret': os.getenv('OKX_API_SECRET'),
        'passphrase': os.getenv('OKX_API_PASSPHRASE'),
        'sandbox': False,
        'mode': 'live'
    }
    adapter = OKXCCXTAdapter(config)
    
    try:
        # Check positions
        print('📊 Fetching current positions...')
        positions = await adapter.fetch_positions()
        
        sol_position = None
        for pos in positions:
            contracts = float(pos.get('contracts', 0))
            if contracts != 0:
                print(f"✅ Position: {pos.get('symbol')} | Side: {pos.get('side')} | Size: {contracts} | Entry: {pos.get('entryPrice')} | uPnL: {pos.get('unrealizedPnl')}")
                if 'SOL' in pos.get('symbol', ''):
                    sol_position = pos
        
        if not sol_position:
            print("❌ No SOL position found")
            return
        
        entry_price = float(sol_position.get('entryPrice', 138.0))
        contracts = float(sol_position.get('contracts', 0))
        
        print(f"\n📝 SOL Position Details:")
        print(f"   Entry: ${entry_price}")
        print(f"   Size: {contracts}")
        
        # Calculate TP/SL
        tp_price = round(entry_price * 1.015, 2)  # +1.5%
        sl_price = round(entry_price * 0.99, 2)   # -1%
        
        print(f"\n🎯 TP/SL Levels:")
        print(f"   TP: ${tp_price} (+1.5%)")
        print(f"   SL: ${sl_price} (-1%)")
        
        # Place TP order using OKX REST API directly
        print(f"\n🎯 Placing TP order...")
        import ccxt
        exchange = ccxt.okx({
            'apiKey': config['api_key'],
            'secret': config['secret'],
            'password': config['passphrase'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap'
            }
        })
        
        # Place TP algo order
        tp_response = exchange.private_post_trade_order_algo({
            'instId': 'SOL-USDT-SWAP',
            'tdMode': 'cross',
            'side': 'sell',
            'ordType': 'conditional',
            'sz': str(abs(contracts)),
            'tpTriggerPx': str(tp_price),
            'tpOrdPx': '-1',  # Market price
            'reduceOnly': True
        })
        print(f"✅ TP Response: {tp_response}")
        
        # Place SL algo order
        print(f"\n🛡️ Placing SL order...")
        sl_response = exchange.private_post_trade_order_algo({
            'instId': 'SOL-USDT-SWAP',
            'tdMode': 'cross',
            'side': 'sell',
            'ordType': 'conditional',
            'sz': str(abs(contracts)),
            'slTriggerPx': str(sl_price),
            'slOrdPx': '-1',  # Market price
            'reduceOnly': True
        })
        print(f"✅ SL Response: {sl_response}")
        
        # Send Telegram notification
        print("\n📱 Sending Telegram notification...")
        from telegram import Bot
        from datetime import datetime
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if token and chat_id:
            bot = Bot(token=token)
            message = f"""🚀 <b>LIVE TRADE CONFIRMED</b>

<b>Symbol:</b> SOL-USDT-SWAP
<b>Side:</b> LONG
<b>Size:</b> {contracts} SOL
<b>Entry:</b> ${entry_price}

<b>Risk Management:</b>
🎯 TP: ${tp_price} (+1.5%)
🛡️ SL: ${sl_price} (-1%)
📊 R/R: 1:1.5

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ <i>TP/SL orders placed successfully!</i>"""
            
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
            print("✅ Telegram notification sent!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(main())
