"""Check real OKX minimum order values"""
import asyncio
from dotenv import load_dotenv
load_dotenv()
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_policy

async def check_minimums():
    policy = load_policy()
    adapter = OKXCCXTAdapter(policy)
    
    # Load markets (sync method)
    if not hasattr(adapter.ccxt_client, 'markets') or not adapter.ccxt_client.markets:
        adapter.ccxt_client.load_markets()
    
    for symbol in ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']:
        ccxt_symbol = symbol.replace('-', '/').replace('/SWAP', ':USDT')
        m = adapter.ccxt_client.market(ccxt_symbol)
        
        limits = m.get('limits', {})
        info = m.get('info', {})
        precision = m.get('precision', {})
        
        print(f'\n=== {symbol} ===')
        print(f'limits.amount.min: {limits.get("amount", {}).get("min")}')
        print(f'limits.amount.step: {limits.get("amount", {}).get("step")}')
        print(f'limits.cost.min: {limits.get("cost", {}).get("min")}')
        print(f'precision.amount: {precision.get("amount")}')
        print(f'info.minSz: {info.get("minSz")}')
        print(f'info.lotSz: {info.get("lotSz")}')
        print(f'info.ctVal: {info.get("ctVal")}')  # Contract value per contract
        print(f'info.ctMult: {info.get("ctMult")}')  # Contract multiplier
    
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(check_minimums())
