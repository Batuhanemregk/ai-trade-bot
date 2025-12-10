"""
Advanced Optuna Training with Feature Selection
- Label threshold: 1.0% (cleaner signals)
- 100 trials per symbol
- 5-fold CV with early stopping
- SHAP-based feature selection (top 35 features)
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
import shap

from ml.features.builder import FeatureBuilder


def select_top_features_shap(X, y, n_features: int = 35):
    """Select top features using SHAP importance."""
    logger.info(f"🔍 Running SHAP feature selection (selecting top {n_features})...")
    
    # Train a quick model for SHAP
    model = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.1,
        num_leaves=31,
        verbose=-1
    )
    
    # Use subset for speed
    sample_size = min(10000, len(X))
    X_sample = X.iloc[:sample_size]
    y_sample = y.iloc[:sample_size]
    
    model.fit(X_sample, y_sample)
    
    # SHAP values
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)
    
    # Handle binary classification SHAP output
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # Take positive class
    
    # Mean absolute SHAP value per feature
    mean_shap = np.abs(shap_values).mean(axis=0)
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': mean_shap
    }).sort_values('importance', ascending=False)
    
    # Select top N features
    top_features = feature_importance.head(n_features)['feature'].tolist()
    
    logger.info(f"📊 Top 10 features: {top_features[:10]}")
    logger.info(f"📊 Selected {len(top_features)} features")
    
    return top_features, feature_importance


def objective(trial, X, y, selected_features):
    """Optuna objective with early stopping and 5-fold CV."""
    
    X_selected = X[selected_features]
    
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'verbosity': -1,
        'n_jobs': -1,
        'force_col_wise': True,
        
        # Core parameters - wider search
        'n_estimators': trial.suggest_int('n_estimators', 200, 1000),
        'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.15, log=True),
        'num_leaves': trial.suggest_int('num_leaves', 10, 150),
        'max_depth': trial.suggest_int('max_depth', 3, 15),
        
        # Regularization - stronger
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-4, 50.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-4, 50.0, log=True),
        
        # Sampling
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.3, 1.0),
        'subsample': trial.suggest_float('subsample', 0.3, 1.0),
        'subsample_freq': trial.suggest_int('subsample_freq', 1, 10),
        
        # Min data
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 150),
        
        # Class weight for imbalanced data
        'scale_pos_weight': trial.suggest_float('scale_pos_weight', 1.0, 8.0),
    }
    
    # 5-fold TimeSeriesSplit
    tscv = TimeSeriesSplit(n_splits=5)
    auc_scores = []
    
    for train_idx, val_idx in tscv.split(X_selected):
        X_train, X_val = X_selected.iloc[train_idx], X_selected.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False)]
        )
        
        y_pred = model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, y_pred)
        auc_scores.append(auc)
    
    return np.mean(auc_scores)


def train_advanced(symbol: str, data_path: Path, output_dir: Path,
                   n_trials: int = 100, threshold_pct: float = 1.0, 
                   forward_bars: int = 3, n_features: int = 35):
    """Advanced training with all optimizations."""
    logger.info(f"🎯 Advanced Training for {symbol}")
    logger.info(f"   Threshold: {threshold_pct}%, Trials: {n_trials}, Top Features: {n_features}")
    
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
    
    # Create labels with higher threshold
    df_features = feature_builder.create_label(df_features, forward_bars=forward_bars, threshold_pct=threshold_pct)
    
    all_feature_cols = feature_builder.get_feature_columns()
    X = df_features[all_feature_cols].dropna()
    y = df_features.loc[X.index, 'label']
    
    logger.info(f"📊 Samples: {len(X)}, All Features: {len(all_feature_cols)}")
    logger.info(f"📊 Class: Up={y.sum()} ({y.mean()*100:.1f}%), Down={len(y)-y.sum()} (threshold={threshold_pct}%)")
    
    # Feature selection with SHAP
    selected_features, importance_df = select_top_features_shap(X, y, n_features)
    X_selected = X[selected_features]
    
    logger.info(f"📊 After feature selection: {len(selected_features)} features")
    
    # Optuna study
    sampler = TPESampler(seed=42)
    study = optuna.create_study(direction='maximize', sampler=sampler)
    
    logger.info(f"🔍 Starting Optuna optimization ({n_trials} trials, 5-fold CV)...")
    study.optimize(
        lambda trial: objective(trial, X, y, selected_features),
        n_trials=n_trials,
        show_progress_bar=True,
        n_jobs=1
    )
    
    best_params = study.best_params
    best_auc = study.best_value
    
    logger.info(f"✅ Best AUC (Optuna): {best_auc:.4f}")
    
    # Train final model with best params + early stopping
    logger.info("🏋️ Training final model with early stopping...")
    
    final_params = {
        'objective': 'binary',
        'metric': 'auc',
        'verbosity': -1,
        'n_jobs': -1,
        **best_params
    }
    
    # 5-fold validation for final metrics
    tscv = TimeSeriesSplit(n_splits=5)
    all_auc = []
    final_model = None
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X_selected)):
        X_train, X_test = X_selected.iloc[train_idx], X_selected.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        model = lgb.LGBMClassifier(**final_params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False)]
        )
        
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
    
    # Metadata with selected features
    metadata = {
        "symbol": symbol,
        "timeframe": "15m",
        "training_period": f"{df.index.min()} to {df.index.max()}",
        "training_samples": len(X),
        "n_features": len(selected_features),
        "feature_columns": selected_features,  # Only selected features!
        "all_features_count": len(all_feature_cols),
        "forward_bars": forward_bars,
        "threshold_pct": threshold_pct,
        "optuna_trials": n_trials,
        "best_params": best_params,
        "metrics": {
            "auc_mean": avg_auc,
            "auc_folds": all_auc,
            "optuna_best_auc": best_auc
        },
        "feature_importance": importance_df.head(20).to_dict('records'),
        "created_at": datetime.now().isoformat()
    }
    
    metadata_path = output_dir / f"{base_symbol}_15m_last18m_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    return avg_auc, best_auc, best_params, selected_features


def main():
    """Train all models with advanced optimization."""
    logger.info("🚀 Advanced Optuna Training Starting...")
    logger.info("   Threshold: 1.0%, Trials: 100, Features: Top 35, Early Stopping: Yes")
    
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
                avg_auc, best_auc, params, features = train_advanced(
                    symbol, data_path, output_dir,
                    n_trials=100,
                    threshold_pct=1.0,  # Higher threshold
                    forward_bars=3,
                    n_features=35  # Feature selection
                )
                results[symbol] = {
                    'final_auc': avg_auc,
                    'optuna_auc': best_auc,
                    'n_features': len(features)
                }
            except Exception as e:
                logger.error(f"❌ {symbol} failed: {e}")
                import traceback
                traceback.print_exc()
                results[symbol] = {'error': str(e)}
        else:
            logger.warning(f"⚠️ Data not found: {data_path}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 ADVANCED TRAINING SUMMARY")
    logger.info("=" * 60)
    for symbol, result in results.items():
        if 'final_auc' in result:
            logger.info(f"✅ {symbol}: Final AUC={result['final_auc']:.4f} (Optuna: {result['optuna_auc']:.4f}), Features: {result['n_features']}")
        else:
            logger.info(f"❌ {symbol}: {result.get('error', 'Failed')}")


if __name__ == "__main__":
    main()
