"""Check algo orders (TP/SL) for all positions."""
import asyncio
import json
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_env

async def main():
    load_env()
    adapter = OKXCCXTAdapter()
    
    orders = await adapter.fetch_algo_orders()
    
    # Save to file for checking
    with open('data/algo_orders_dump.json', 'w') as f:
        json.dump(orders, f, indent=2)
    
    print(f"Found {len(orders)} algo orders")
    for order in orders:
        symbol = order.get('instId', 'N/A')
        sz = order.get('sz', 'N/A')
        tp = order.get('tpTriggerPx', '')
        sl = order.get('slTriggerPx', '')
        print(f"{symbol}: sz={sz}, TP={tp}, SL={sl}")
    
    await adapter.close()

asyncio.run(main())
