"""Check raw position data from OKX"""
import asyncio
from dotenv import load_dotenv
load_dotenv()
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_policy

async def check():
    policy = load_policy()
    adapter = OKXCCXTAdapter(policy)
    positions = await adapter.fetch_positions()
    
    for pos in positions:
        c = float(pos.get('contracts', 0) or pos.get('info', {}).get('pos', 0) or 0)
        if c != 0:
            print('='*50)
            print('Symbol:', pos.get('symbol'))
            print('Side:', pos.get('side'))
            print('Contracts:', pos.get('contracts'))
            print('Entry:', pos.get('entryPrice'))
            print('Notional:', pos.get('notional'))
            print('InitialMargin:', pos.get('initialMargin'))
            print('---RAW INFO---')
            info = pos.get('info', {})
            print('pos:', info.get('pos'))
            print('notionalUsd:', info.get('notionalUsd'))
            print('margin:', info.get('margin'))
            print('lever:', info.get('lever'))
            print('mgnMode:', info.get('mgnMode'))
    
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(check())
