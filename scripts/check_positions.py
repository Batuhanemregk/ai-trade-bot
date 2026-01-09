"""Check current positions and their contract sizes."""
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_env

load_env()

adapter = OKXCCXTAdapter()
positions = adapter.ccxt_client.fetch_positions()

print("=" * 60)
print("CURRENT POSITIONS")
print("=" * 60)

for pos in positions:
    contracts = abs(float(pos.get('contracts', 0)))
    if contracts > 0:
        symbol = pos.get('symbol', '')
        entry = pos.get('entryPrice', 0)
        side = pos.get('side', '')
        info = pos.get('info', {})
        okx_pos = info.get('pos', 'N/A')
        margin = info.get('margin', 'N/A')
        notional = info.get('notionalUsd', 'N/A')
        
        print(f"Symbol: {symbol}")
        print(f"  Side: {side}")
        print(f"  Contracts (CCXT): {contracts}")
        print(f"  OKX pos field: {okx_pos}")
        print(f"  Entry: {entry}")
        print(f"  Margin: {margin}")
        print(f"  Notional: {notional}")
        print("-" * 40)
