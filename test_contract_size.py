"""Test what amount format OKX expects via CCXT"""
import asyncio
from dotenv import load_dotenv
load_dotenv()
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_policy

async def test_contract_size():
    policy = load_policy()
    adapter = OKXCCXTAdapter(policy)
    
    # Load markets
    adapter.load_markets()
    
    symbols = [
        ('ETH/USDT:USDT', 'ETH-USDT-SWAP'),
        ('BTC/USDT:USDT', 'BTC-USDT-SWAP'),
        ('SOL/USDT:USDT', 'SOL-USDT-SWAP'),
    ]
    
    for ccxt_sym, okx_sym in symbols:
        print(f"\n=== {okx_sym} ===")
        m = adapter.exchange.market(ccxt_sym)
        
        ct_val = float(m.get('info', {}).get('ctVal', 1))
        contract_size = m.get('contractSize', 1)
        precision = m.get('precision', {}).get('amount', 0.01)
        limits_min = m.get('limits', {}).get('amount', {}).get('min', 0.01)
        
        print(f"  ctVal: {ct_val}")
        print(f"  contractSize: {contract_size}")
        print(f"  precision.amount: {precision}")
        print(f"  limits.amount.min: {limits_min}")
        
        # Test: If I want 0.001 ETH position, what should I send?
        base_amount = 0.001 if 'ETH' in okx_sym else 0.0001 if 'BTC' in okx_sym else 0.01
        contracts = base_amount / ct_val if ct_val else base_amount
        print(f"  To get {base_amount} base amount:")
        print(f"    Send as contracts: {contracts}")
        print(f"    Or send base_amount directly: {base_amount}")
    
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_contract_size())
