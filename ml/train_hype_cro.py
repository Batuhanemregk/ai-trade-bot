"""
Multiclass training for HYPE and CRO
- HYPE: OKX swap, use whatever data is available (~2 months)
- CRO: Try OKX first, fallback to Binance with max available data
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
from typing import List, Dict, Optional
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import f1_score
import optuna
from optuna.samplers import TPESampler
from loguru import logger
import time as time_module
import ccxt

logger.add("logs/hype_cro_training.log", rotation="10 MB", level="INFO")

# Configuration
THRESHOLD_PCT = 1.0
FORWARD_BARS = 16
N_OPTUNA_TRIALS = 30  # Reduced for less data
N_TOP_FEATURES = 35

CLASS_DOWN = 0
CLASS_NEUTRAL = 1
CLASS_UP = 2


def collect_ohlcv_okx(symbol: str, months: int = 24) -> Optional[pd.DataFrame]:
    """Collect OHLCV from OKX swap."""
    try:
        exchange = ccxt.okx({'timeout': 60000})
        full_symbol = f"{symbol}/USDT:USDT"
        
        since_ts = int((datetime.now(timezone.utc) - timedelta(days=months * 30)).timestamp() * 1000)
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"📊 Collecting data for {symbol} from OKX...")
        
        all_bars = []
        current_since = since_ts
        max_requests = 300
        
        for _ in range(max_requests):
            try:
                bars = exchange.fetch_ohlcv(full_symbol, '15m', current_since, 300)
                if not bars:
                    break
                all_bars.extend(bars)
                current_since = bars[-1][0] + 1
                if current_since >= now_ts:
                    break
                time_module.sleep(0.2)
            except Exception as e:
                logger.warning(f"OKX fetch error: {e}")
                break
        
        if not all_bars:
            return None
        
        df = pd.DataFrame(all_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        days = (df['timestamp'].max() - df['timestamp'].min()).days
        logger.info(f"✅ OKX {symbol}: {len(df)} bars ({days} days)")
        return df
        
    except Exception as e:
        logger.error(f"OKX collection failed for {symbol}: {e}")
        return None


def collect_ohlcv_binance(symbol: str, months: int = 60) -> Optional[pd.DataFrame]:
    """Collect OHLCV from Binance spot with max available data."""
    try:
        exchange = ccxt.binance({'timeout': 30000})
        full_symbol = f"{symbol}/USDT"
        
        # Try to get as much data as possible
        since_ts = int((datetime.now(timezone.utc) - timedelta(days=months * 30)).timestamp() * 1000)
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"📊 Collecting data for {symbol} from Binance (max {months} months)...")
        
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
                logger.warning(f"Binance error: {e}")
                break
        
        if not all_bars:
            return None
        
        df = pd.DataFrame(all_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        days = (df['timestamp'].max() - df['timestamp'].min()).days
        logger.info(f"✅ Binance {symbol}: {len(df)} bars ({days} days)")
        return df
        
    except Exception as e:
        logger.error(f"Binance collection failed for {symbol}: {e}")
        return None


def create_multiclass_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Create 3-class labels."""
    df = df.copy()
    
    future_close = df['close'].shift(-FORWARD_BARS)
    future_return = ((future_close - df['close']) / df['close']) * 100
    
    conditions = [
        future_return <= -THRESHOLD_PCT,
        future_return >= THRESHOLD_PCT,
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


def train_multiclass(symbol: str, df: pd.DataFrame, source: str) -> Dict:
    """Train multiclass model."""
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Training MULTICLASS for {symbol} ({source})")
    logger.info(f"   Data: {len(df)} bars")
    logger.info(f"{'='*60}")
    
    result = {'symbol': symbol, 'success': False, 'source': source}
    
    try:
        from ml.features.builder import FeatureBuilder
        builder = FeatureBuilder()
        df_features = builder.build_features(df)
        df_labeled = create_multiclass_labels(df_features)
        
        feature_cols = builder.get_feature_columns()
        X = df_labeled[feature_cols]
        y = df_labeled['label']
        
        if len(X) < 1000:
            result['error'] = f"Insufficient data after features: {len(X)}"
            return result
        
        logger.info(f"📊 Training data: {len(X)} samples")
        
        # Feature selection
        model_quick = lgb.LGBMClassifier(
            n_estimators=100, objective='multiclass', num_class=3, verbose=-1
        )
        model_quick.fit(X, y)
        feature_imp = pd.DataFrame({
            'feature': X.columns,
            'importance': model_quick.feature_importances_
        }).sort_values('importance', ascending=False)
        
        n_features = min(N_TOP_FEATURES, len(X.columns))
        selected_features = feature_imp.head(n_features)['feature'].tolist()
        X_selected = X[selected_features]
        
        # Optuna HPO
        logger.info(f"🔧 Running {N_OPTUNA_TRIALS} Optuna trials...")
        
        def objective(trial):
            params = {
                'objective': 'multiclass',
                'num_class': 3,
                'num_leaves': trial.suggest_int('num_leaves', 15, 50),
                'learning_rate': trial.suggest_float('learning_rate', 0.02, 0.1),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 0.9),
                'n_estimators': 200,
                'verbose': -1
            }
            
            split_idx = int(len(X_selected) * 0.8)
            X_train, X_val = X_selected.iloc[:split_idx], X_selected.iloc[split_idx:]
            y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
            
            model = lgb.LGBMClassifier(**params)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            return f1_score(y_val, y_pred, average='macro')
        
        study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
        study.optimize(objective, n_trials=N_OPTUNA_TRIALS, show_progress_bar=True)
        
        best_params = study.best_params
        logger.info(f"✅ Best F1-macro: {study.best_value:.4f}")
        
        # Walk-forward CV (fewer splits for less data)
        n_splits = min(3, len(X_selected) // 500)
        n_splits = max(2, n_splits)
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = []
        
        for train_idx, val_idx in tscv.split(X_selected):
            X_train, X_val = X_selected.iloc[train_idx], X_selected.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model = lgb.LGBMClassifier(
                objective='multiclass', num_class=3,
                n_estimators=300, verbose=-1, **best_params
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)
            cv_scores.append(f1_score(y_val, y_pred, average='macro'))
        
        mean_f1 = np.mean(cv_scores)
        logger.info(f"📈 Walk-forward F1-macro: {mean_f1:.4f}")
        
        # Final model
        final_model = lgb.LGBMClassifier(
            objective='multiclass', num_class=3,
            n_estimators=300, verbose=-1, **best_params
        )
        final_model.fit(X_selected, y)
        
        # Save
        output_dir = Path("models/lgbm")
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / f"{symbol}_USDT_15m_multiclass.pkl"
        
        with open(model_path, 'wb') as f:
            pickle.dump(final_model, f)
        
        days = (df['timestamp'].max() - df['timestamp'].min()).days
        
        metadata = {
            'symbol': symbol,
            'version': 'multiclass_v1',
            'model_type': 'multi-class',
            'classes': ['DOWN', 'NEUTRAL', 'UP'],
            'data_source': source,
            'data_days': days,
            'data_bars': len(df),
            'training_samples': len(X),
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
            'data_days': days,
            'data_bars': len(df)
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
    print("MULTICLASS TRAINING: HYPE, CRO")
    print("="*60)
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    results = {}
    
    # HYPE - OKX only (new coin, use whatever is available)
    print("\n>>> HYPE - Collecting from OKX...")
    df_hype = collect_ohlcv_okx('HYPE', months=6)
    if df_hype is not None and len(df_hype) > 500:
        result = train_multiclass('HYPE', df_hype, 'OKX')
        results['HYPE'] = result
    else:
        results['HYPE'] = {'success': False, 'error': 'No data from OKX'}
    
    # CRO - Try OKX first, then Binance
    print("\n>>> CRO - Trying OKX first...")
    df_cro = collect_ohlcv_okx('CRO', months=24)
    
    if df_cro is None or len(df_cro) < 1000:
        print("    OKX failed, trying Binance...")
        df_cro = collect_ohlcv_binance('CRO', months=60)
    
    if df_cro is not None and len(df_cro) > 500:
        source = 'OKX' if 'USDT:USDT' in str(df_cro.columns) else 'Binance'
        result = train_multiclass('CRO', df_cro, source)
        results['CRO'] = result
    else:
        results['CRO'] = {'success': False, 'error': 'No data from OKX or Binance'}
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for symbol, result in results.items():
        if result['success']:
            print(f"✅ {symbol}: F1={result['f1_macro']:.4f} | {result['data_days']} days | {result['data_bars']} bars | {result.get('source', 'Unknown')}")
        else:
            print(f"❌ {symbol}: {result.get('error', 'Unknown')}")
    
    with open("logs/hype_cro_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
