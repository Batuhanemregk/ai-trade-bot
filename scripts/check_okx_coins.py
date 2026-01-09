"""Check OKX for HYPE and CRO availability."""
import ccxt

okx = ccxt.okx({'timeout': 30000})

coins = ['HYPE', 'CRO', 'XMR', 'XLM', 'ZEC']

print("OKX Coin Availability Check:")
print("=" * 50)

for coin in coins:
    swap_symbol = f'{coin}/USDT:USDT'
    spot_symbol = f'{coin}/USDT'
    
    # Check swap first (what bot uses)
    try:
        ticker = okx.fetch_ticker(swap_symbol)
        print(f"{coin}: SWAP OK - price={ticker['last']}")
        continue
    except:
        pass
    
    # Try spot
    try:
        ticker = okx.fetch_ticker(spot_symbol)
        print(f"{coin}: SPOT ONLY - price={ticker['last']}")
    except:
        print(f"{coin}: NOT AVAILABLE on OKX")
