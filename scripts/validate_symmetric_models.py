"""Validate symmetric models on recent data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from loguru import logger
from scoring.ml_scorer import MLScorer

def test_model_predictions():
    """Test if models produce proper SHORT and LONG signals."""
    
    logger.info("Testing symmetric model predictions...")
    
    scorer = MLScorer()
    
    # Load recent data
    test_data = {}
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    for symbol_full in symbols:
        symbol_map = {
            'BTCUSDT': 'BTC-USDT-SWAP',
            'ETHUSDT': 'ETH-USDT-SWAP',
            'SOLUSDT': 'SOL-USDT-SWAP'
        }
        symbol = symbol_map[symbol_full]
        
        try:
            df = pd.read_csv(f'data/ml_training/{symbol_full}_15m_18months_binance.csv')
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
            test_data[symbol] = df.tail(200)
        except FileNotFoundError:
            logger.warning(f"Could not load data for {symbol}, skipping")
            continue
    
    results = {'LONG': 0, 'SHORT': 0, 'FLAT': 0}
    
    for symbol, df in test_data.items():
        try:
            ohlcv_bundle = {'main': df}
            score, rationale, details = scorer.score(symbol, ohlcv_bundle)
            
            direction = details.get('signal_direction', 'UNKNOWN')
            logger.info(f"{symbol}: Score={score:.1f}, Direction={direction}")
            
            if 'LONG' in direction:
                results['LONG'] += 1
            elif 'SHORT' in direction:
                results['SHORT'] += 1
            else:
                results['FLAT'] += 1
        except Exception as e:
            logger.error(f"Error testing {symbol}: {e}")
    
    logger.info(f"\nSignal Distribution: {results}")
    
    if results['SHORT'] > 0:
        logger.success("✅ Models producing SHORT signals (symmetric learning confirmed)")
    else:
        logger.warning("⚠️ No SHORT signals detected")

if __name__ == '__main__':
    test_model_predictions()

