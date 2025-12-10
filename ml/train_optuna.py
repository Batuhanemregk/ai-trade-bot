"""
Optuna-Optimized Model Training
Hyperparameter tuning with Optuna for maximizing AUC
"""

import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from datetime import datetime
from loguru import logger
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.calibration import CalibratedClassifierCV
import optuna
from optuna.samplers import TPESampler

from ml.features.builder import FeatureBuilder


def objective(trial, X, y):
    """Optuna objective function for LightGBM optimization."""
    
    # Hyperparameter search space
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'verbosity': -1,
        'n_jobs': -1,
        'force_col_wise': True,
        
        # Core parameters
        'n_estimators': trial.suggest_int('n_estimators', 100, 800),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 15, 127),
        'max_depth': trial.suggest_int('max_depth', 3, 12),
        
        # Regularization
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-4, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-4, 10.0, log=True),
        
        # Sampling
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.4, 1.0),
        'subsample': trial.suggest_float('subsample', 0.4, 1.0),
        'subsample_freq': trial.suggest_int('subsample_freq', 1, 7),
        
        # Min data
        'min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
        
        # Class weight for imbalanced data
        'scale_pos_weight': trial.suggest_float('scale_pos_weight', 1.0, 5.0),
    }
    
    # TimeSeriesSplit cross-validation
    tscv = TimeSeriesSplit(n_splits=3)  # 3 for speed
    auc_scores = []
    
    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(30, verbose=False)]
        )
        
        y_pred = model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, y_pred)
        auc_scores.append(auc)
    
    return np.mean(auc_scores)


def train_with_optuna(symbol: str, data_path: Path, output_dir: Path, 
                       n_trials: int = 50, forward_bars: int = 3):
    """Train model with Optuna hyperparameter optimization."""
    logger.info(f"🎯 Optuna Training for {symbol} ({n_trials} trials)...")
    
    # Load data
    df = pd.read_csv(data_path)
    logger.info(f"📊 Loaded {len(df)} bars")
    
    # Process timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
    elif 'Unnamed: 0' in df.columns:
        df['timestamp'] = pd.to_datetime(df['Unnamed: 0'])
        df = df.set_index('timestamp')
        df = df.drop('Unnamed: 0', axis=1, errors='ignore')
    
    # Build features
    feature_builder = FeatureBuilder()
    df_features = feature_builder.build_features(df)
    df_features = feature_builder.create_label(df_features, forward_bars=forward_bars)
    
    feature_cols = feature_builder.get_feature_columns()
    X = df_features[feature_cols].dropna()
    y = df_features.loc[X.index, 'label']
    
    logger.info(f"📊 Samples: {len(X)}, Features: {len(feature_cols)}")
    logger.info(f"📊 Class: Up={y.sum()} ({y.mean()*100:.1f}%), Down={len(y)-y.sum()}")
    
    # Optuna study
    sampler = TPESampler(seed=42)
    study = optuna.create_study(direction='maximize', sampler=sampler)
    
    logger.info(f"🔍 Starting Optuna optimization ({n_trials} trials)...")
    study.optimize(
        lambda trial: objective(trial, X, y),
        n_trials=n_trials,
        show_progress_bar=True,
        n_jobs=1
    )
    
    best_params = study.best_params
    best_auc = study.best_value
    
    logger.info(f"✅ Best AUC: {best_auc:.4f}")
    logger.info(f"📊 Best params: {best_params}")
    
    # Train final model with best params
    logger.info("🏋️ Training final model with best parameters...")
    
    final_params = {
        'objective': 'binary',
        'metric': 'auc',
        'verbosity': -1,
        'n_jobs': -1,
        **best_params
    }
    
    # Full 5-fold validation for final metrics
    tscv = TimeSeriesSplit(n_splits=5)
    all_auc = []
    final_model = None
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        model = lgb.LGBMClassifier(**final_params)
        model.fit(X_train, y_train)
        
        y_pred = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_pred)
        acc = accuracy_score(y_test, (y_pred > 0.5).astype(int))
        
        logger.info(f"   Fold {fold+1}/5: AUC={auc:.4f}, Acc={acc:.3f}")
        all_auc.append(auc)
        final_model = model
    
    avg_auc = np.mean(all_auc)
    logger.info(f"📊 Final Average AUC: {avg_auc:.4f}")
    
    # Calibrate
    logger.info("🔧 Calibrating model...")
    calibrated = CalibratedClassifierCV(final_model, method='isotonic', cv='prefit')
    calibrated.fit(X_test, y_test)
    
    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    base_symbol = symbol.replace('/', '_').replace('-', '_')
    
    model_path = output_dir / f"{base_symbol}_15m_last18m.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(calibrated, f)
    logger.info(f"💾 Saved: {model_path}")
    
    # Metadata
    metadata = {
        "symbol": symbol,
        "timeframe": "15m",
        "training_period": f"{df.index.min()} to {df.index.max()}",
        "training_samples": len(X),
        "n_features": len(feature_cols),
        "feature_columns": feature_cols,
        "forward_bars": forward_bars,
        "optuna_trials": n_trials,
        "best_params": best_params,
        "metrics": {
            "auc_mean": avg_auc,
            "auc_folds": all_auc,
            "optuna_best_auc": best_auc
        },
        "created_at": datetime.now().isoformat()
    }
    
    metadata_path = output_dir / f"{base_symbol}_15m_last18m_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    return avg_auc, best_params


def main():
    """Train all models with Optuna optimization."""
    logger.info("🚀 Optuna-Optimized ML Training Starting...")
    
    # Suppress Optuna logs
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    data_dir = Path("data/ml_training")
    output_dir = Path("models/lgbm")
    
    symbols = {
        'BTC_USDT': data_dir / 'BTC_USDT_15m_6months_binance.csv',
        'ETH_USDT': data_dir / 'ETH_USDT_15m_6months_binance.csv',
        'SOL_USDT': data_dir / 'SOL_USDT_15m_6months_binance.csv',
    }
    
    results = {}
    
    for symbol, data_path in symbols.items():
        if data_path.exists():
            try:
                auc, params = train_with_optuna(
                    symbol, data_path, output_dir,
                    n_trials=50,  # 50 trials per symbol
                    forward_bars=3
                )
                results[symbol] = {'auc': auc, 'params': params}
            except Exception as e:
                logger.error(f"❌ {symbol} failed: {e}")
                import traceback
                traceback.print_exc()
                results[symbol] = {'error': str(e)}
        else:
            logger.warning(f"⚠️ Data not found: {data_path}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 OPTUNA TRAINING SUMMARY")
    logger.info("=" * 60)
    for symbol, result in results.items():
        if 'auc' in result:
            logger.info(f"✅ {symbol}: AUC={result['auc']:.4f}")
        else:
            logger.info(f"❌ {symbol}: {result.get('error', 'Failed')}")


if __name__ == "__main__":
    main()
