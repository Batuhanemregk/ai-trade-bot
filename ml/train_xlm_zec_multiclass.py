"""
Multiclass training for XLM and ZEC (UP / NEUTRAL / DOWN)
Same as other coins - 3 class, 16 forward bars, ±1% threshold
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import f1_score, accuracy_score
import optuna
from optuna.samplers import TPESampler
from loguru import logger
import time as time_module
import ccxt

logger.add("logs/multiclass_training.log", rotation="10 MB", level="INFO")

# Configuration - same as multiclass_pipeline.py
THRESHOLD_PCT = 1.0  # +1% = UP, -1% = DOWN
FORWARD_BARS = 16    # 16 bars = 4 hours (same as other coins)
N_OPTUNA_TRIALS = 50
N_TOP_FEATURES = 40

CLASS_DOWN = 0
CLASS_NEUTRAL = 1
CLASS_UP = 2

COINS_TO_TRAIN = ['XLM', 'ZEC']


def collect_ohlcv_data(symbol: str, months: int = 18) -> pd.DataFrame:
    """Collect OHLCV data from Binance."""
    exchange = ccxt.binance({'timeout': 30000})
    full_symbol = f"{symbol}/USDT"
    
    since_ts = int((datetime.now(timezone.utc) - timedelta(days=months * 30)).timestamp() * 1000)
    now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    logger.info(f"📊 Collecting {months}M of 15m data for {symbol}...")
    
    all_bars = []
    current_since = since_ts
    
    while current_since < now_ts:
        try:
            bars = exchange.fetch_ohlcv(full_symbol, '15m', current_since, 1000)
            if not bars:
                break
            all_bars.extend(bars)
            current_since = bars[-1][0] + 1
            if len(all_bars) % 5000 == 0:
                logger.info(f"  Collected {len(all_bars)} bars...")
            time_module.sleep(0.12)
        except Exception as e:
            logger.warning(f"Error: {e}")
            break
    
    df = pd.DataFrame(all_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    
    logger.info(f"✅ Collected {len(df)} bars for {symbol}")
    return df


def create_multiclass_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Create 3-class labels: DOWN (0), NEUTRAL (1), UP (2)"""
    df = df.copy()
    
    future_close = df['close'].shift(-FORWARD_BARS)
    future_return = ((future_close - df['close']) / df['close']) * 100
    
    conditions = [
        future_return <= -THRESHOLD_PCT,  # DOWN
        future_return >= THRESHOLD_PCT,   # UP
    ]
    choices = [CLASS_DOWN, CLASS_UP]
    df['label'] = np.select(conditions, choices, default=CLASS_NEUTRAL)
    
    df = df.iloc[:-FORWARD_BARS].copy()
    
    dist = df['label'].value_counts().to_dict()
    total = len(df)
    logger.info(f"  Labels: DOWN={dist.get(0,0)} ({dist.get(0,0)/total*100:.1f}%), "
               f"NEUTRAL={dist.get(1,0)} ({dist.get(1,0)/total*100:.1f}%), "
               f"UP={dist.get(2,0)} ({dist.get(2,0)/total*100:.1f}%)")
    
    return df


def train_multiclass_model(symbol: str) -> Dict:
    """Train multiclass model for a symbol."""
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Training MULTICLASS model for {symbol}")
    logger.info(f"   Classes: DOWN (ret<-{THRESHOLD_PCT}%), NEUTRAL, UP (ret>{THRESHOLD_PCT}%)")
    logger.info(f"   Forward: {FORWARD_BARS} bars (4 hours)")
    logger.info(f"{'='*60}")
    
    result = {'symbol': symbol, 'success': False}
    
    try:
        # 1. Collect data
        df = collect_ohlcv_data(symbol, 18)
        if len(df) < 5000:
            result['error'] = f"Insufficient data: {len(df)}"
            return result
        
        # 2. Build features
        from ml.features.builder import FeatureBuilder
        builder = FeatureBuilder()
        df_features = builder.build_features(df)
        
        # 3. Create multiclass labels
        df_labeled = create_multiclass_labels(df_features)
        
        feature_cols = builder.get_feature_columns()
        X = df_labeled[feature_cols]
        y = df_labeled['label']
        
        logger.info(f"📊 Training data: {len(X)} samples, {len(feature_cols)} features")
        
        # 4. Feature selection (top 40)
        model_quick = lgb.LGBMClassifier(
            n_estimators=100, objective='multiclass', num_class=3, verbose=-1
        )
        model_quick.fit(X, y)
        feature_imp = pd.DataFrame({
            'feature': X.columns,
            'importance': model_quick.feature_importances_
        }).sort_values('importance', ascending=False)
        selected_features = feature_imp.head(N_TOP_FEATURES)['feature'].tolist()
        X_selected = X[selected_features]
        
        # 5. Optuna HPO
        logger.info(f"🔧 Running {N_OPTUNA_TRIALS} Optuna trials...")
        
        def objective(trial):
            params = {
                'objective': 'multiclass',
                'num_class': 3,
                'metric': 'multi_logloss',
                'num_leaves': trial.suggest_int('num_leaves', 15, 63),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 0.95),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.6, 0.95),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
                'n_estimators': 300,
                'verbose': -1
            }
            
            split_idx = int(len(X_selected) * 0.8)
            X_train, X_val = X_selected.iloc[:split_idx], X_selected.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
            
            model = lgb.LGBMClassifier(**params)
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)],
                      callbacks=[lgb.early_stopping(50, verbose=False)])
            
            y_pred = model.predict(X_val)
            return f1_score(y_val, y_pred, average='macro')
        
        study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
        study.optimize(objective, n_trials=N_OPTUNA_TRIALS, show_progress_bar=True)
        
        best_params = study.best_params
        logger.info(f"✅ Best F1-macro: {study.best_value:.4f}")
        
        # 6. Walk-forward validation
        tscv = TimeSeriesSplit(n_splits=5)
        cv_scores = []
        
        for train_idx, val_idx in tscv.split(X_selected):
            X_train, X_val = X_selected.iloc[train_idx], X_selected.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            params = {
                'objective': 'multiclass', 'num_class': 3,
                'n_estimators': 500, 'verbose': -1, **best_params
            }
            model = lgb.LGBMClassifier(**params)
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)],
                      callbacks=[lgb.early_stopping(50, verbose=False)])
            
            y_pred = model.predict(X_val)
            cv_scores.append(f1_score(y_val, y_pred, average='macro'))
        
        mean_f1 = np.mean(cv_scores)
        logger.info(f"📈 Walk-forward F1-macro: {mean_f1:.4f} (+/- {np.std(cv_scores):.4f})")
        
        # 7. Train final model
        final_params = {
            'objective': 'multiclass', 'num_class': 3,
            'n_estimators': 500, 'verbose': -1, **best_params
        }
        final_model = lgb.LGBMClassifier(**final_params)
        final_model.fit(X_selected, y)
        
        # 8. Save
        output_dir = Path("models/lgbm")
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / f"{symbol}_USDT_15m_multiclass.pkl"
        
        with open(model_path, 'wb') as f:
            pickle.dump(final_model, f)
        
        metadata = {
            'symbol': symbol,
            'version': 'multiclass_v1',
            'model_type': 'multi-class',
            'classes': ['DOWN', 'NEUTRAL', 'UP'],
            'threshold_pct': THRESHOLD_PCT,
            'forward_bars': FORWARD_BARS,
            'selected_features': selected_features,
            'best_params': best_params,
            'metrics': {
                'f1_macro_mean': float(mean_f1),
                'f1_macro_std': float(np.std(cv_scores))
            },
            'trained_at': datetime.now(timezone.utc).isoformat()
        }
        
        with open(output_dir / f"{symbol}_USDT_15m_multiclass_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"💾 Saved: {model_path}")
        
        result.update({
            'success': True,
            'model_path': str(model_path),
            'f1_macro': mean_f1,
            'classes': ['DOWN', 'NEUTRAL', 'UP']
        })
        return result
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        result['error'] = str(e)
        return result


def main():
    print("="*60)
    print("MULTICLASS TRAINING: XLM, ZEC")
    print("Classes: DOWN (<-1%) | NEUTRAL | UP (>+1%)")
    print("Forward: 16 bars (4 hours)")
    print("="*60)
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    results = {}
    for symbol in COINS_TO_TRAIN:
        result = train_multiclass_model(symbol)
        results[symbol] = result
        
        if result['success']:
            print(f"✅ {symbol}: F1-macro={result['f1_macro']:.4f}")
        else:
            print(f"❌ {symbol}: {result.get('error', 'Unknown')}")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for symbol, result in results.items():
        if result['success']:
            print(f"{symbol}: F1-macro={result['f1_macro']:.4f} - {result['classes']}")
    
    with open("logs/xlm_zec_multiclass_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
