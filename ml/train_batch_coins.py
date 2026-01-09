"""
Multiclass training for new coins
TAO, FET, STX, JUP, SEI, GRT, MON, PENGU, AAVE, VIRTUAL, CAKE
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import f1_score
import optuna
from optuna.samplers import TPESampler
from loguru import logger
import time as time_module
import ccxt

logger.add("logs/new_coins_batch_training.log", rotation="10 MB", level="INFO")

# Configuration
THRESHOLD_PCT = 1.0
FORWARD_BARS = 16
N_OPTUNA_TRIALS = 30
N_TOP_FEATURES = 35

CLASS_DOWN = 0
CLASS_NEUTRAL = 1
CLASS_UP = 2

# Coins and their sources
COINS_CONFIG = {
    'TAO': 'okx',
    'FET': 'binance',
    'STX': 'okx',
    'JUP': 'okx',
    'SEI': 'okx',
    'GRT': 'okx',
    'MON': 'okx',
    'PENGU': 'okx',
    'AAVE': 'okx',
    'VIRTUAL': 'okx',
    'CAKE': 'binance',
}


def collect_ohlcv(symbol: str, source: str, months: int = 24) -> Optional[pd.DataFrame]:
    """Collect OHLCV data from specified source."""
    try:
        if source == 'okx':
            exchange = ccxt.okx({'timeout': 60000})
            full_symbol = f"{symbol}/USDT:USDT"
        else:
            exchange = ccxt.binance({'timeout': 30000})
            full_symbol = f"{symbol}/USDT"
        
        since_ts = int((datetime.now(timezone.utc) - timedelta(days=months * 30)).timestamp() * 1000)
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"📊 Collecting data for {symbol} from {source}...")
        
        all_bars = []
        current_since = since_ts
        limit = 300 if source == 'okx' else 1000
        
        for _ in range(500):
            try:
                bars = exchange.fetch_ohlcv(full_symbol, '15m', current_since, limit)
                if not bars:
                    break
                all_bars.extend(bars)
                current_since = bars[-1][0] + 1
                if current_since >= now_ts:
                    break
                if len(all_bars) % 5000 == 0:
                    logger.info(f"  {len(all_bars)} bars...")
                time_module.sleep(0.15)
            except Exception as e:
                logger.warning(f"Fetch error: {e}")
                break
        
        if not all_bars:
            return None
        
        df = pd.DataFrame(all_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        days = (df['timestamp'].max() - df['timestamp'].min()).days
        logger.info(f"✅ {symbol}: {len(df)} bars ({days} days)")
        return df
        
    except Exception as e:
        logger.error(f"Collection failed for {symbol}: {e}")
        return None


def create_multiclass_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Create 3-class labels."""
    df = df.copy()
    future_close = df['close'].shift(-FORWARD_BARS)
    future_return = ((future_close - df['close']) / df['close']) * 100
    
    conditions = [future_return <= -THRESHOLD_PCT, future_return >= THRESHOLD_PCT]
    choices = [CLASS_DOWN, CLASS_UP]
    df['label'] = np.select(conditions, choices, default=CLASS_NEUTRAL)
    df = df.iloc[:-FORWARD_BARS].copy()
    
    dist = df['label'].value_counts().to_dict()
    total = len(df)
    logger.info(f"  Labels: D={dist.get(0,0)/total*100:.0f}% N={dist.get(1,0)/total*100:.0f}% U={dist.get(2,0)/total*100:.0f}%")
    return df


def train_multiclass(symbol: str, df: pd.DataFrame, source: str) -> Dict:
    """Train multiclass model."""
    logger.info(f"\n{'='*50}")
    logger.info(f"🚀 Training {symbol} ({source}, {len(df)} bars)")
    logger.info(f"{'='*50}")
    
    result = {'symbol': symbol, 'success': False, 'source': source}
    
    try:
        from ml.features.builder import FeatureBuilder
        builder = FeatureBuilder()
        df_features = builder.build_features(df)
        df_labeled = create_multiclass_labels(df_features)
        
        feature_cols = builder.get_feature_columns()
        X = df_labeled[feature_cols]
        y = df_labeled['label']
        
        if len(X) < 500:
            result['error'] = f"Insufficient: {len(X)}"
            return result
        
        # Feature selection
        model_q = lgb.LGBMClassifier(n_estimators=100, objective='multiclass', num_class=3, verbose=-1)
        model_q.fit(X, y)
        fi = pd.DataFrame({'f': X.columns, 'i': model_q.feature_importances_}).sort_values('i', ascending=False)
        sel_feat = fi.head(N_TOP_FEATURES)['f'].tolist()
        X_sel = X[sel_feat]
        
        # Optuna
        def objective(trial):
            params = {
                'objective': 'multiclass', 'num_class': 3,
                'num_leaves': trial.suggest_int('num_leaves', 15, 50),
                'learning_rate': trial.suggest_float('learning_rate', 0.02, 0.1),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 0.9),
                'n_estimators': 200, 'verbose': -1
            }
            split_idx = int(len(X_sel) * 0.8)
            X_tr, X_val = X_sel.iloc[:split_idx], X_sel.iloc[split_idx:]
            y_tr, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
            model = lgb.LGBMClassifier(**params)
            model.fit(X_tr, y_tr)
            return f1_score(y_val, model.predict(X_val), average='macro')
        
        study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
        study.optimize(objective, n_trials=N_OPTUNA_TRIALS, show_progress_bar=False)
        best_params = study.best_params
        
        # CV
        n_splits = max(2, min(3, len(X_sel) // 500))
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = []
        for tr_idx, val_idx in tscv.split(X_sel):
            model = lgb.LGBMClassifier(objective='multiclass', num_class=3, n_estimators=300, verbose=-1, **best_params)
            model.fit(X_sel.iloc[tr_idx], y.iloc[tr_idx])
            cv_scores.append(f1_score(y.iloc[val_idx], model.predict(X_sel.iloc[val_idx]), average='macro'))
        mean_f1 = np.mean(cv_scores)
        
        # Final
        final_model = lgb.LGBMClassifier(objective='multiclass', num_class=3, n_estimators=300, verbose=-1, **best_params)
        final_model.fit(X_sel, y)
        
        # Save
        out_dir = Path("models/lgbm")
        out_dir.mkdir(parents=True, exist_ok=True)
        model_path = out_dir / f"{symbol}_USDT_15m_multiclass.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(final_model, f)
        
        days = (df['timestamp'].max() - df['timestamp'].min()).days
        meta = {
            'symbol': symbol, 'version': 'multiclass_v1', 'model_type': 'multi-class',
            'classes': ['DOWN', 'NEUTRAL', 'UP'], 'data_source': source, 'data_days': days,
            'selected_features': sel_feat, 'best_params': best_params,
            'metrics': {'f1_macro': float(mean_f1)},
            'trained_at': datetime.now(timezone.utc).isoformat()
        }
        with open(out_dir / f"{symbol}_USDT_15m_multiclass_metadata.json", 'w') as f:
            json.dump(meta, f, indent=2)
        
        logger.info(f"💾 Saved {symbol} - F1={mean_f1:.4f}")
        result.update({'success': True, 'f1': mean_f1, 'days': days, 'bars': len(df)})
        return result
    except Exception as e:
        logger.error(f"Failed {symbol}: {e}")
        import traceback
        traceback.print_exc()
        result['error'] = str(e)
        return result


def main():
    print("=" * 60)
    print("BATCH MULTICLASS TRAINING - 11 COINS")
    print("=" * 60)
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    results = {}
    
    for symbol, source in COINS_CONFIG.items():
        print(f"\n>>> {symbol} ({source})...")
        df = collect_ohlcv(symbol, source, months=24)
        
        if df is not None and len(df) > 500:
            result = train_multiclass(symbol, df, source)
            results[symbol] = result
            if result['success']:
                print(f"✅ {symbol}: F1={result['f1']:.4f} | {result['days']} days")
            else:
                print(f"❌ {symbol}: {result.get('error', 'Unknown')}")
        else:
            results[symbol] = {'success': False, 'error': 'No data'}
            print(f"❌ {symbol}: No data available")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    success = [s for s, r in results.items() if r.get('success')]
    failed = [s for s, r in results.items() if not r.get('success')]
    print(f"✅ Success: {len(success)} - {success}")
    print(f"❌ Failed: {len(failed)} - {failed}")
    
    with open("logs/batch_training_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
