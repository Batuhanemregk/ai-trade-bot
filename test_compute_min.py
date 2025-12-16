"""Test compute_required_amount with ctVal fix"""
import asyncio
from dotenv import load_dotenv
load_dotenv()
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_policy
from execution.prevalidation import compute_required_amount

async def test_compute():
    policy = load_policy()
    adapter = OKXCCXTAdapter(policy)
    
    # Use ccxt_client
    if hasattr(adapter, 'ccxt_client'):
        exchange = adapter.ccxt_client
    else:
        exchange = adapter.exchange if hasattr(adapter, 'exchange') else adapter
    
    symbols = ['ETH/USDT:USDT', 'BTC/USDT:USDT', 'SOL/USDT:USDT']
    prices = [3100, 90000, 130]
    
    for symbol, price in zip(symbols, prices):
        print(f"\n=== {symbol} (price=${price}) ===")
        result = await compute_required_amount(exchange, symbol, price)
        print(f"  amount_min: {result.get('amount_min')}")
        print(f"  amount_step: {result.get('amount_step')}")
        print(f"  required_amount: {result.get('required_amount')}")
        print(f"  raw_info: {result.get('raw_info')}")
    
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_compute())
