#!/usr/bin/env python
"""
ML Model Retrain Script with Regime Detection
Kullanımı: python ml/retrain_with_regime.py

Bu script:
1. Son 6 aylık veriyi yükler
2. market_trend_regime feature'ı ile balanced eğitim yapar
3. Bull/Bear dönemlerinden eşit örnek alarak model bias'ını azaltır
4. Probability calibration uygular
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime, timezone
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.calibration import CalibratedClassifierCV
import lightgbm as lgb
from loguru import logger

from ml.features.builder import FeatureBuilder


def load_data(symbol: str, data_dir: Path = Path("data/ml_training")) -> pd.DataFrame:
    """Load training data for symbol."""
    # Try different file patterns
    patterns = [
        f"{symbol}USDT_15m_*.csv",
        f"{symbol}_USDT_15m_*.csv",
        f"{symbol.upper()}USDT_15m_*.csv"
    ]
    
    for pattern in patterns:
        files = list(data_dir.glob(pattern))
        if files:
            # Get most recent file
            latest = sorted(files)[-1]
            logger.info(f"Loading data from {latest}")
            return pd.read_csv(latest)
    
    raise FileNotFoundError(f"No data found for {symbol} in {data_dir}")


def balanced_sample(X: pd.DataFrame, y: pd.Series, regime: pd.Series, 
                    min_samples_per_regime: int = 1000) -> tuple:
    """
    Create balanced sample across regime types.
    Ensures model sees equal bullish and bearish periods.
    """
    # Combine into single DataFrame
    df = X.copy()
    df['_label'] = y
    df['_regime'] = regime
    
    sampled = []
    
    for regime_val in [-1, 0, 1]:  # BEARISH, SIDEWAYS, BULLISH
        regime_df = df[df['_regime'] == regime_val]
        if len(regime_df) > 0:
            # Sample equally from each regime
            n_samples = min(len(regime_df), min_samples_per_regime)
            sampled.append(regime_df.sample(n=n_samples, random_state=42))
    
    if not sampled:
        logger.warning("No samples found, using original data")
        return X, y
    
    balanced_df = pd.concat(sampled, ignore_index=True)
    
    # Shuffle
    balanced_df = balanced_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Extract X, y
    y_balanced = balanced_df['_label']
    X_balanced = balanced_df.drop(['_label', '_regime'], axis=1)
    
    logger.info(f"Balanced sampling: {len(X)} -> {len(X_balanced)} samples")
    logger.info(f"Regime distribution: BEAR={sum(balanced_df['_regime']==-1)}, "
               f"SIDE={sum(balanced_df['_regime']==0)}, BULL={sum(balanced_df['_regime']==1)}")
    
    return X_balanced, y_balanced


def train_with_regime(symbol: str, output_dir: Path = Path("models/lgbm"),
                     n_splits: int = 5, threshold_pct: float = 1.0):
    """
    Train model with balanced regime sampling.
    
    Args:
        symbol: Trading symbol (e.g., 'BTC')
        output_dir: Where to save model
        n_splits: CV folds
        threshold_pct: Label threshold (1% default for cleaner signals)
    """
    logger.info(f"=== Training {symbol} with Regime Detection ===")
    
    # Load data
    df = load_data(symbol)
    
    # Build features
    feature_builder = FeatureBuilder()
    df_features = feature_builder.build_features(df)
    
    # Create label
    df_labeled = feature_builder.create_label(df_features, forward_bars=3, threshold_pct=threshold_pct)
    
    # Get features and labels
    feature_cols = feature_builder.get_feature_columns()
    X = df_labeled[feature_cols]
    y = df_labeled['label']
    
    # Get regime column
    if 'market_trend_regime' in df_labeled.columns:
        regime = df_labeled['market_trend_regime']
    else:
        # Fallback: calculate here
        logger.warning("market_trend_regime not found, calculating...")
        ema_20 = df_labeled['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df_labeled['close'].ewm(span=50, adjust=False).mean()
        adx = df_labeled.get('adx', 25)
        conditions = [
            (ema_20 > ema_50) & (adx > 20),
            (ema_20 < ema_50) & (adx > 20),
        ]
        regime = np.select(conditions, [1, -1], default=0)
    
    # Balanced sampling
    X_balanced, y_balanced = balanced_sample(X, y, regime, min_samples_per_regime=2000)
    
    # Train model
    logger.info("Training LightGBM model...")
    
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'n_estimators': 500,
        'early_stopping_round': 50
    }
    
    # Cross-validation
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_scores = []
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(X_balanced, y_balanced)):
        X_train, X_val = X_balanced.iloc[train_idx], X_balanced.iloc[val_idx]
        y_train, y_val = y_balanced.iloc[train_idx], y_balanced.iloc[val_idx]
        
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=50)]
        )
        
        y_pred = model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, y_pred)
        cv_scores.append(auc)
        logger.info(f"Fold {fold+1}: AUC = {auc:.4f}")
    
    logger.info(f"Mean CV AUC: {np.mean(cv_scores):.4f} (+/- {np.std(cv_scores):.4f})")
    
    # Train final model on all data
    final_model = lgb.LGBMClassifier(**params)
    final_model.fit(X_balanced, y_balanced)
    
    # Calibration (optional but recommended)
    logger.info("Applying probability calibration...")
    calibrated_model = CalibratedClassifierCV(final_model, method='isotonic', cv=3)
    calibrated_model.fit(X_balanced, y_balanced)
    
    # Test calibration
    test_probs = calibrated_model.predict_proba(X_balanced)[:, 1]
    logger.info(f"Calibrated p_up range: [{test_probs.min():.3f}, {test_probs.max():.3f}]")
    logger.info(f"Calibrated p_up mean: {test_probs.mean():.3f}")
    
    # Save model
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{symbol}_USDT_15m_regime.pkl"
    metadata_path = output_dir / f"{symbol}_USDT_15m_regime_metadata.json"
    
    with open(model_path, 'wb') as f:
        pickle.dump(calibrated_model, f)
    
    metadata = {
        'symbol': symbol,
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'feature_columns': feature_cols,
        'n_features': len(feature_cols),
        'metrics': {
            'auc_mean': float(np.mean(cv_scores)),
            'auc_std': float(np.std(cv_scores)),
            'n_samples': len(X_balanced)
        },
        'training_config': {
            'threshold_pct': threshold_pct,
            'balanced_sampling': True,
            'calibrated': True
        }
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"✅ Model saved to {model_path}")
    logger.info(f"✅ Metadata saved to {metadata_path}")
    
    return model_path


def main():
    """Train all ML-enabled symbols with regime detection."""
    symbols = ['BTC', 'ETH', 'SOL']
    
    print("=" * 60)
    print("ML Model Retrain with Regime Detection")
    print("=" * 60)
    print()
    print("Bu script modelleri balanced regime sampling ile yeniden eğitir.")
    print("Bullish ve bearish dönemlerden eşit örnek alarak bias azaltır.")
    print()
    
    for symbol in symbols:
        try:
            train_with_regime(symbol)
            print()
        except FileNotFoundError as e:
            logger.warning(f"Skipping {symbol}: {e}")
            continue
        except Exception as e:
            logger.error(f"Failed to train {symbol}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("=" * 60)
    print("Eğitim tamamlandı!")
    print()
    print("Yeni modelleri aktif etmek için:")
    print("1. models/lgbm/ klasöründeki yeni *_regime.pkl dosyalarını")
    print("   *_last18m.pkl olarak yeniden adlandırın")
    print("2. Veya ml_scorer.py'de model yollarını güncelleyin")
    print("=" * 60)


if __name__ == "__main__":
    main()
