"""Check availability of new coins on OKX and Binance."""
import ccxt

coins = ['TAO', 'FET', 'MNT', 'STX', 'JUP', 'SEI', 'GRT', 'RTX', 'MON', 'PENGU', 'AAVE', 'VIRTUAL', 'CAKE', 'RIVER']

print("Checking coin availability...")
print("=" * 60)

# Check OKX first (swap)
okx = ccxt.okx({'timeout': 30000})
okx_markets = okx.load_markets()

# Check Binance (spot)
binance = ccxt.binance({'timeout': 30000})
binance_markets = binance.load_markets()

results = []

for coin in coins:
    okx_symbol = f"{coin}/USDT:USDT"
    binance_symbol = f"{coin}/USDT"
    
    okx_available = okx_symbol in okx_markets
    binance_available = binance_symbol in binance_markets
    
    if okx_available:
        status = "OKX SWAP ✅"
        source = "okx"
    elif binance_available:
        status = "Binance SPOT ✅"
        source = "binance"
    else:
        status = "NOT FOUND ❌"
        source = None
    
    results.append({'coin': coin, 'status': status, 'source': source})
    print(f"{coin:8} | {status}")

print("\n" + "=" * 60)
available = [r for r in results if r['source']]
missing = [r for r in results if not r['source']]

print(f"Available: {len(available)} coins")
print(f"Missing: {len(missing)} coins - {[r['coin'] for r in missing]}")
