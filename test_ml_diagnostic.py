"""ML Model Diagnostic Test - Simplified"""
import asyncio
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from scoring.ml_scorer import MLScorer
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_policy

async def test_ml():
    policy = load_policy()
    
    # Initialize ML scorer
    ml_scorer = MLScorer()
    print(f"Loaded models: {list(ml_scorer.models.keys())}")
    
    # Get real OHLCV data using sync-style adapter
    adapter = OKXCCXTAdapter(policy)
    
    print("\n--- Testing predictions ---")
    for symbol in ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP']:
        try:
            # Fetch 15m data
            ohlcv_15m = await adapter.fetch_ohlcv(symbol, '15m', limit=100)
            df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Fetch 1h data
            ohlcv_1h = await adapter.fetch_ohlcv(symbol, '1h', limit=100)
            df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Fetch 4h data  
            ohlcv_4h = await adapter.fetch_ohlcv(symbol, '4h', limit=100)
            df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            ohlcv_bundle = {'main': df_15m, '15m': df_15m, '1h': df_1h, '4h': df_4h}
            
            score, rationale, details = ml_scorer.score(symbol, ohlcv_bundle)
            p_up = details.get('p_up', 0)
            signal = details.get('signal_direction', 'N/A')
            print(f"{symbol}: score={score:.1f}, p_up={p_up:.4f}, signal={signal}")
            
        except Exception as e:
            import traceback
            print(f"{symbol}: ERROR - {e}")
            traceback.print_exc()
    
    await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_ml())
