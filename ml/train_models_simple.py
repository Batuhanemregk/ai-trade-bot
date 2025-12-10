"""
Simple Model Training Script - Trains one model per symbol
For 15m timeframe only (per ML simplification)
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

from ml.features.builder import FeatureBuilder


def train_symbol_model(symbol: str, data_path: Path, output_dir: Path, forward_bars: int = 3):
    """Train a single model for one symbol."""
    logger.info(f"🎯 Training model for {symbol}...")
    
    # Load data
    df = pd.read_csv(data_path)
    logger.info(f"📊 Loaded {len(df)} bars for {symbol}")
    
    # Ensure timestamp column
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
    elif df.index.name == 'timestamp' or 'Unnamed: 0' in df.columns:
        if 'Unnamed: 0' in df.columns:
            df['timestamp'] = pd.to_datetime(df['Unnamed: 0'])
            df = df.set_index('timestamp')
            df = df.drop('Unnamed: 0', axis=1, errors='ignore')
    
    # Build features
    feature_builder = FeatureBuilder()
    df_features = feature_builder.build_features(df)
    
    # Create labels
    df_features = feature_builder.create_label(df_features, forward_bars=forward_bars)
    
    # Get feature columns
    feature_cols = feature_builder.get_feature_columns()
    
    # Prepare X, y
    X = df_features[feature_cols].dropna()
    y = df_features.loc[X.index, 'label']
    
    logger.info(f"📊 Training samples: {len(X)}, Features: {len(feature_cols)}")
    logger.info(f"📊 Class distribution: Up={y.sum()} ({y.mean()*100:.1f}%), Down={len(y)-y.sum()}")
    
    # TimeSeriesSplit for validation
    tscv = TimeSeriesSplit(n_splits=5)
    
    all_auc = []
    final_model = None
    
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        logger.info(f"--- Fold {fold+1}/5 ---")
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        
        # Train LightGBM
        model = lgb.LGBMClassifier(
            objective='binary',
            metric='auc',
            n_estimators=300,
            learning_rate=0.05,
            num_leaves=31,
            colsample_bytree=0.7,
            subsample=0.7,
            reg_alpha=0.1,
            reg_lambda=0.1,
            verbose=-1
        )
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_pred_proba)
        acc = accuracy_score(y_test, (y_pred_proba > 0.5).astype(int))
        
        logger.info(f"   AUC={auc:.3f}, Accuracy={acc:.3f}")
        all_auc.append(auc)
        final_model = model
    
    avg_auc = np.mean(all_auc)
    logger.info(f"📊 Average AUC: {avg_auc:.3f}")
    
    # Calibrate final model on last fold
    logger.info("🔧 Calibrating model...")
    calibrated = CalibratedClassifierCV(final_model, method='isotonic', cv='prefit')
    calibrated.fit(X_test, y_test)
    
    # Save model
    output_dir.mkdir(parents=True, exist_ok=True)
    base_symbol = symbol.replace('/', '_').replace('-', '_')
    
    model_path = output_dir / f"{base_symbol}_15m_last18m.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump(calibrated, f)
    logger.info(f"💾 Saved model: {model_path}")
    
    # Save metadata
    metadata = {
        "symbol": symbol,
        "timeframe": "15m",
        "training_period": f"{df.index.min()} to {df.index.max()}",
        "training_samples": len(X),
        "n_features": len(feature_cols),
        "feature_columns": feature_cols,
        "forward_bars": forward_bars,
        "metrics": {
            "auc_mean": avg_auc,
            "auc_folds": all_auc
        },
        "created_at": datetime.now().isoformat()
    }
    
    metadata_path = output_dir / f"{base_symbol}_15m_last18m_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info(f"💾 Saved metadata: {metadata_path}")
    
    return avg_auc


def main():
    """Train all 3 models."""
    logger.info("🚀 Starting ML Model Training (15m only, 18 months data)...")
    
    data_dir = Path("data/ml_training")
    output_dir = Path("models/lgbm")
    
    # Symbol-file mapping
    symbols = {
        'BTC_USDT': data_dir / 'BTC_USDT_15m_6months_binance.csv',
        'ETH_USDT': data_dir / 'ETH_USDT_15m_6months_binance.csv',
        'SOL_USDT': data_dir / 'SOL_USDT_15m_6months_binance.csv',
    }
    
    results = {}
    for symbol, data_path in symbols.items():
        if data_path.exists():
            try:
                auc = train_symbol_model(symbol, data_path, output_dir, forward_bars=3)
                results[symbol] = {'status': 'SUCCESS', 'auc': auc}
            except Exception as e:
                logger.error(f"❌ Failed to train {symbol}: {e}")
                results[symbol] = {'status': 'FAILED', 'error': str(e)}
        else:
            logger.warning(f"⚠️ Data not found: {data_path}")
            results[symbol] = {'status': 'SKIPPED', 'reason': 'data_not_found'}
    
    # Summary
    logger.info("=" * 60)
    logger.info("📊 TRAINING SUMMARY")
    logger.info("=" * 60)
    for symbol, result in results.items():
        if result['status'] == 'SUCCESS':
            logger.info(f"✅ {symbol}: AUC={result['auc']:.3f}")
        else:
            logger.info(f"❌ {symbol}: {result['status']}")
    
    return results


if __name__ == "__main__":
    main()
