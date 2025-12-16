"""Test limits vs info values in compute_required_amount"""
import asyncio
from dotenv import load_dotenv
load_dotenv()
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_policy

async def test_limits():
    policy = load_policy()
    adapter = OKXCCXTAdapter(policy)
    
    # We need to access ccxt_client directly for this test
    if hasattr(adapter, 'ccxt_client'):
        exchange = adapter.ccxt_client
    else:
        exchange = adapter.exchange if hasattr(adapter, 'exchange') else adapter
    
    # Load markets
    exchange.load_markets()
    
    symbols = ['ETH/USDT:USDT', 'BTC/USDT:USDT', 'SOL/USDT:USDT']
    
    for symbol in symbols:
        print(f"\n=== {symbol} ===")
        try:
            m = exchange.market(symbol)
            limits = m.get('limits', {}) or {}
            prec = m.get('precision', {}) or {}
            info = m.get('info', {}) or {}
            
            # Standard CCXT values
            print(f"limits.amount.min: {limits.get('amount', {}).get('min')}")
            print(f"limits.amount.step: {limits.get('amount', {}).get('step')}")
            print(f"precision.amount: {prec.get('amount')}")
            
            # Raw OKX info values
            print(f"info.minSz: {info.get('minSz')}")
            print(f"info.lotSz: {info.get('lotSz')}")
            print(f"info.ctVal: {info.get('ctVal')}")
            
            # Calculated real min
            min_sz = float(info.get('minSz', 0.01))
            ct_val = float(info.get('ctVal', 1))
            real_min = min_sz * ct_val
            print(f"CALCULATED real_min = minSz × ctVal = {min_sz} × {ct_val} = {real_min}")
            
        except Exception as e:
            print(f"  ERROR: {e}")
    
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_limits())
