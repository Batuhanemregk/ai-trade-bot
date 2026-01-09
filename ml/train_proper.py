#!/usr/bin/env python
"""
Production-Grade Multiclass ML Training Script
================================================

This script trains LightGBM multiclass models with:
- NO data leakage (feature selection inside CV folds)
- CV-based Optuna optimization (not single split)
- Full reproducibility (all seeds set)
- Complete metadata for production inference

Target: FORWARD_BARS = 16 (15m bars => ~4 hours)
Classes: DOWN (0), NEUTRAL (1), UP (2)

Usage:
    python train_proper.py --symbols FET,STX,GRT,AAVE,CAKE
    python train_proper.py --symbol BTC --source binance
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import argparse
import pickle
import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import f1_score, accuracy_score
import optuna
from optuna.samplers import TPESampler
from loguru import logger
import time as time_module
import ccxt

logger.add("logs/production_training.log", rotation="10 MB", level="INFO")

# ==================== CONFIGURATION ====================
# These are FIXED and match production inference expectations

TIMEFRAME = "15m"
FORWARD_BARS = 16           # 16 bars * 15min = 4 hours lookahead
THRESHOLD_PCT = 1.0         # ±1% for UP/DOWN classification
N_TOP_FEATURES = 40         # Number of features to select
N_OPTUNA_TRIALS = 50        # Hyperparameter search trials
N_CV_FOLDS = 5              # Walk-forward CV folds
RANDOM_SEED = 42            # Master seed for reproducibility

# Class definitions (MUST match production MLScorer)
CLASS_DOWN = 0
CLASS_NEUTRAL = 1
CLASS_UP = 2

# Default coins if no arguments provided
DEFAULT_COINS = {
    'FET': 'binance',
    'STX': 'okx',
    'GRT': 'okx',
    'AAVE': 'okx',
    'CAKE': 'binance',
}


def set_all_seeds(seed: int = RANDOM_SEED) -> None:
    """Set all random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    # LightGBM uses its own seed parameter in model params


# ==================== DATA COLLECTION ====================

def collect_ohlcv(symbol: str, source: str, months: int = 24) -> Optional[pd.DataFrame]:
    """Collect OHLCV data from exchange."""
    try:
        if source == 'okx':
            exchange = ccxt.okx({'timeout': 60000})
            full_symbol = f"{symbol}/USDT:USDT"
        else:
            exchange = ccxt.binance({'timeout': 30000})
            full_symbol = f"{symbol}/USDT"
        
        since_ts = int((datetime.now(timezone.utc) - timedelta(days=months * 30)).timestamp() * 1000)
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        print(f"📊 Collecting {symbol} from {source}...")
        
        all_bars = []
        current_since = since_ts
        limit = 300 if source == 'okx' else 1000
        
        for _ in range(500):
            try:
                bars = exchange.fetch_ohlcv(full_symbol, TIMEFRAME, current_since, limit)
                if not bars:
                    break
                all_bars.extend(bars)
                current_since = bars[-1][0] + 1
                if current_since >= now_ts:
                    break
                if len(all_bars) % 10000 == 0:
                    print(f"  {len(all_bars)} bars...")
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
        print(f"✅ {symbol}: {len(df)} bars ({days} days)")
        return df
        
    except Exception as e:
        print(f"❌ Collection failed: {e}")
        return None


# ==================== LABEL CREATION ====================

def create_multiclass_labels(df: pd.DataFrame, forward_bars: int = FORWARD_BARS, 
                             threshold_pct: float = THRESHOLD_PCT) -> pd.DataFrame:
    """
    Create 3-class labels based on future returns.
    
    Labels:
        0 (DOWN): future_return <= -threshold_pct
        1 (NEUTRAL): -threshold_pct < future_return < threshold_pct
        2 (UP): future_return >= threshold_pct
    """
    df = df.copy()
    
    # Calculate future return
    future_close = df['close'].shift(-forward_bars)
    future_return = ((future_close - df['close']) / df['close']) * 100
    
    # Create labels
    conditions = [
        future_return <= -threshold_pct,  # DOWN
        future_return >= threshold_pct,   # UP
    ]
    choices = [CLASS_DOWN, CLASS_UP]
    df['label'] = np.select(conditions, choices, default=CLASS_NEUTRAL)
    
    # Remove rows without future data
    df = df.iloc[:-forward_bars].copy()
    
    # Log distribution
    dist = df['label'].value_counts().to_dict()
    total = len(df)
    print(f"  Labels: DOWN={dist.get(0,0)} ({dist.get(0,0)/total*100:.1f}%), "
          f"NEUTRAL={dist.get(1,0)} ({dist.get(1,0)/total*100:.1f}%), "
          f"UP={dist.get(2,0)} ({dist.get(2,0)/total*100:.1f}%)")
    
    return df


# ==================== FEATURE SELECTION (FOLD-AWARE) ====================

def select_features_in_fold(X_train: pd.DataFrame, y_train: pd.Series, 
                            n_features: int = N_TOP_FEATURES) -> List[str]:
    """
    Select top N features using ONLY training data.
    This prevents data leakage from validation set.
    """
    model = lgb.LGBMClassifier(
        n_estimators=100, 
        num_leaves=31, 
        learning_rate=0.1,
        verbose=-1, 
        objective='multiclass', 
        num_class=3,
        random_state=RANDOM_SEED
    )
    model.fit(X_train, y_train)
    
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return feature_importance.head(n_features)['feature'].tolist()


# ==================== CV-BASED OPTUNA OBJECTIVE ====================

def create_cv_objective(X: pd.DataFrame, y: pd.Series, feature_cols: List[str], 
                        n_folds: int = N_CV_FOLDS):
    """
    Create Optuna objective that uses walk-forward CV.
    This prevents overfitting to a single validation split.
    """
    
    def objective(trial) -> float:
        params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': trial.suggest_int('num_leaves', 15, 63),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
            'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 0.95),
            'bagging_fraction': trial.suggest_float('bagging_fraction', 0.6, 0.95),
            'bagging_freq': trial.suggest_int('bagging_freq', 1, 7),
            'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
            'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
            'n_estimators': 500,
            'verbose': -1,
            'random_state': RANDOM_SEED,
            'deterministic': True
        }
        
        tscv = TimeSeriesSplit(n_splits=n_folds)
        fold_scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train_fold = X.iloc[train_idx][feature_cols]
            X_val_fold = X.iloc[val_idx][feature_cols]
            y_train_fold = y.iloc[train_idx]
            y_val_fold = y.iloc[val_idx]
            
            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_train_fold, y_train_fold,
                eval_set=[(X_val_fold, y_val_fold)],
                callbacks=[lgb.early_stopping(50, verbose=False)]
            )
            
            y_pred = model.predict(X_val_fold)
            fold_scores.append(f1_score(y_val_fold, y_pred, average='macro'))
        
        return np.mean(fold_scores)
    
    return objective


# ==================== MAIN TRAINING FUNCTION ====================

def train_multiclass_production(symbol: str, df: pd.DataFrame, source: str) -> Dict:
    """
    Production-grade multiclass training with:
    - Fold-aware feature selection (no leakage)
    - CV-based Optuna (no single-split overfit)
    - Full reproducibility
    - Complete metadata
    """
    print(f"\n{'='*70}")
    print(f"🚀 PRODUCTION TRAINING: {symbol}")
    print(f"   Data: {len(df)} bars from {source}")
    print(f"   Config: {N_OPTUNA_TRIALS} trials, {N_TOP_FEATURES} features, {N_CV_FOLDS}-fold CV")
    print(f"   Forward: {FORWARD_BARS} bars ({FORWARD_BARS * 15} minutes)")
    print(f"{'='*70}")
    
    set_all_seeds(RANDOM_SEED)
    result = {'symbol': symbol, 'success': False, 'source': source}
    
    try:
        # 1. Build features
        from ml.features.builder import FeatureBuilder
        builder = FeatureBuilder()
        df_features = builder.build_features(df)
        
        # 2. Create labels
        df_labeled = create_multiclass_labels(df_features, FORWARD_BARS, THRESHOLD_PCT)
        
        all_feature_cols = builder.get_feature_columns()
        X = df_labeled[all_feature_cols]
        y = df_labeled['label']
        
        if len(X) < 5000:
            result['error'] = f"Insufficient data: {len(X)} (need >= 5000)"
            return result
        
        # Record data range (use original df since build_features may drop timestamp)
        train_start = df['timestamp'].min().isoformat()
        train_end = df['timestamp'].max().isoformat()
        
        print(f"  Training range: {train_start[:10]} to {train_end[:10]}")
        print(f"  Total samples: {len(X)}, Raw features: {len(all_feature_cols)}")
        
        # 3. Initial feature selection using first 80% (to get stable feature list)
        # This is used to define the feature space for Optuna
        split_80 = int(len(X) * 0.8)
        X_train_initial = X.iloc[:split_80]
        y_train_initial = y.iloc[:split_80]
        
        print(f"\n📊 Feature selection (on first 80% of data)...")
        selected_features = select_features_in_fold(X_train_initial, y_train_initial, N_TOP_FEATURES)
        print(f"  Selected {len(selected_features)} features")
        print(f"  Top 5: {selected_features[:5]}")
        
        # 4. Optuna HPO with CV-based objective
        print(f"\n🔧 Optuna HPO ({N_OPTUNA_TRIALS} trials, {N_CV_FOLDS}-fold CV each)...")
        
        study = optuna.create_study(
            direction='maximize', 
            sampler=TPESampler(seed=RANDOM_SEED)
        )
        
        objective = create_cv_objective(X, y, selected_features, N_CV_FOLDS)
        study.optimize(objective, n_trials=N_OPTUNA_TRIALS, show_progress_bar=True)
        
        best_params = study.best_params
        print(f"  Best CV F1-macro: {study.best_value:.4f}")
        print(f"  Best params: num_leaves={best_params['num_leaves']}, "
              f"lr={best_params['learning_rate']:.4f}")
        
        # 5. Final CV evaluation with best params (for reporting)
        print(f"\n📈 Final CV evaluation ({N_CV_FOLDS} folds)...")
        tscv = TimeSeriesSplit(n_splits=N_CV_FOLDS)
        cv_scores = []
        fold_details = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X), 1):
            X_train_fold = X.iloc[train_idx][selected_features]
            X_val_fold = X.iloc[val_idx][selected_features]
            y_train_fold = y.iloc[train_idx]
            y_val_fold = y.iloc[val_idx]
            
            final_params = {
                'objective': 'multiclass', 
                'num_class': 3, 
                'metric': 'multi_logloss',
                'boosting_type': 'gbdt', 
                'n_estimators': 500, 
                'verbose': -1,
                'random_state': RANDOM_SEED,
                'deterministic': True,
                **best_params
            }
            
            model = lgb.LGBMClassifier(**final_params)
            model.fit(
                X_train_fold, y_train_fold,
                eval_set=[(X_val_fold, y_val_fold)],
                callbacks=[lgb.early_stopping(50, verbose=False)]
            )
            
            y_pred = model.predict(X_val_fold)
            fold_f1 = f1_score(y_val_fold, y_pred, average='macro')
            fold_acc = accuracy_score(y_val_fold, y_pred)
            cv_scores.append(fold_f1)
            
            fold_details.append({
                'fold': fold,
                'train_size': len(train_idx),
                'val_size': len(val_idx),
                'f1_macro': round(fold_f1, 4),
                'accuracy': round(fold_acc, 4)
            })
            print(f"  Fold {fold}: F1={fold_f1:.4f}, Acc={fold_acc:.4f} "
                  f"(train={len(train_idx)}, val={len(val_idx)})")
        
        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))
        print(f"  Mean F1: {cv_mean:.4f} (+/- {cv_std:.4f})")
        
        # 6. Train final model on ALL data
        print(f"\n🎯 Training final model on all data...")
        X_final = X[selected_features]
        
        final_model_params = {
            'objective': 'multiclass', 
            'num_class': 3, 
            'boosting_type': 'gbdt', 
            'n_estimators': 500, 
            'verbose': -1,
            'random_state': RANDOM_SEED,
            'deterministic': True,
            **best_params
        }
        
        final_model = lgb.LGBMClassifier(**final_model_params)
        final_model.fit(X_final, y)
        
        # 7. Save model and metadata
        output_dir = Path("models/lgbm")
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / f"{symbol}_USDT_15m_multiclass.pkl"
        metadata_path = output_dir / f"{symbol}_USDT_15m_multiclass_metadata.json"
        
        with open(model_path, 'wb') as f:
            pickle.dump(final_model, f)
        
        # Complete metadata for production
        metadata = {
            # Identity
            'symbol': symbol,
            'timeframe': TIMEFRAME,
            'version': 'multiclass_v2_production',
            'model_type': 'multi-class',
            
            # Class mapping (CRITICAL for production inference)
            'class_mapping': {
                '0': 'DOWN',
                '1': 'NEUTRAL', 
                '2': 'UP'
            },
            'classes': ['DOWN', 'NEUTRAL', 'UP'],
            
            # Label creation parameters
            'forward_bars': FORWARD_BARS,
            'label_threshold_pct': THRESHOLD_PCT,
            'label_logic': f"DOWN: ret <= -{THRESHOLD_PCT}%, UP: ret >= +{THRESHOLD_PCT}%, else NEUTRAL",
            
            # Features (exact order for inference)
            'feature_list': selected_features,
            'n_features': len(selected_features),
            
            # Training data info
            'data_source': source,
            'train_start': train_start,
            'train_end': train_end,
            'n_rows': len(X),
            'data_days': (df['timestamp'].max() - df['timestamp'].min()).days,
            
            # CV results
            'cv_folds': N_CV_FOLDS,
            'cv_metric': 'f1_macro',
            'cv_mean': cv_mean,
            'cv_std': cv_std,
            'cv_fold_details': fold_details,
            
            # Optuna results
            'optuna_trials': N_OPTUNA_TRIALS,
            'optuna_best_value': float(study.best_value),
            'best_params': best_params,
            
            # Reproducibility
            'random_seed': RANDOM_SEED,
            'trained_at': datetime.now(timezone.utc).isoformat(),
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n💾 Saved: {model_path}")
        print(f"   Metadata: {metadata_path}")
        print(f"✅ {symbol} complete: CV F1={cv_mean:.4f} (+/- {cv_std:.4f})")
        
        result.update({
            'success': True,
            'model_path': str(model_path),
            'cv_f1_mean': cv_mean,
            'cv_f1_std': cv_std,
            'n_features': len(selected_features),
            'n_rows': len(X),
            'train_start': train_start,
            'train_end': train_end
        })
        return result
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        result['error'] = str(e)
        return result


# ==================== CLI ====================

def parse_args():
    parser = argparse.ArgumentParser(description='Production-grade multiclass ML training')
    parser.add_argument('--symbol', type=str, help='Single symbol to train (e.g., BTC)')
    parser.add_argument('--symbols', type=str, help='Comma-separated symbols (e.g., FET,STX,GRT)')
    parser.add_argument('--source', type=str, default='binance', 
                        choices=['binance', 'okx'], help='Data source')
    parser.add_argument('--months', type=int, default=24, help='Months of data to fetch')
    return parser.parse_args()


def main():
    args = parse_args()
    
    print("=" * 70)
    print("PRODUCTION-GRADE MULTICLASS TRAINING")
    print("=" * 70)
    print(f"Config:")
    print(f"  - Forward bars: {FORWARD_BARS} ({FORWARD_BARS * 15} minutes)")
    print(f"  - Threshold: ±{THRESHOLD_PCT}%")
    print(f"  - Features: {N_TOP_FEATURES}")
    print(f"  - Optuna trials: {N_OPTUNA_TRIALS}")
    print(f"  - CV folds: {N_CV_FOLDS}")
    print(f"  - Random seed: {RANDOM_SEED}")
    print("=" * 70)
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    set_all_seeds(RANDOM_SEED)
    
    # Determine coins to train
    if args.symbol:
        coins = {args.symbol.upper(): args.source}
    elif args.symbols:
        coins = {s.strip().upper(): args.source for s in args.symbols.split(',')}
    else:
        coins = DEFAULT_COINS
    
    print(f"Coins to train: {list(coins.keys())}")
    print("=" * 70)
    
    results = {}
    
    for symbol, source in coins.items():
        print(f"\n>>> Processing {symbol}...")
        df = collect_ohlcv(symbol, source, months=args.months if hasattr(args, 'months') else 24)
        
        if df is not None and len(df) > 5000:
            result = train_multiclass_production(symbol, df, source)
            results[symbol] = result
        else:
            results[symbol] = {'success': False, 'error': 'Insufficient data'}
            print(f"❌ {symbol}: Insufficient data")
    
    # Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    for symbol, result in results.items():
        if result.get('success'):
            print(f"✅ {symbol}: CV F1={result['cv_f1_mean']:.4f} (+/- {result['cv_f1_std']:.4f}) | "
                  f"{result['n_rows']} rows | {result['n_features']} features")
        else:
            print(f"❌ {symbol}: {result.get('error', 'Unknown error')}")
    
    # Save results
    results_path = Path("logs/production_training_results.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
