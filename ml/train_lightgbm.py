"""
LightGBM Model Training Pipeline
Trains LightGBM model for direction prediction (up/down).
"""

import pandas as pd
import numpy as np
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple
from loguru import logger

import lightgbm as lgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, 
    accuracy_score, 
    precision_score, 
    recall_score, 
    f1_score,
    confusion_matrix
)
from sklearn.model_selection import TimeSeriesSplit

from ml.feature_engineering import FeatureEngineer
from ml.model_version_manager import MLModelVersionManager

class LightGBMTrainer:
    """Trains and evaluates LightGBM models for trading signals."""
    
    def __init__(self, model_version: str = "lgb_v1"):
        self.model_version = model_version
        self.feature_engineer = FeatureEngineer()
        self.model = None
        self.calibrated_model = None
        self.metadata = {}
        self.model_manager = MLModelVersionManager()
    
    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load OHLCV data from CSV."""
        logger.info(f"Loading data from {filepath}")
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} bars")
        return df
    
    def prepare_data(self, df: pd.DataFrame, forward_bars: int = 1) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and labels."""
        X, y = self.feature_engineer.prepare_for_training(df, forward_bars)
        return X, y
    
    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series) -> Any:
        """Trains the LightGBM model."""
        logger.info(f"Training LightGBM model with {len(X_train)} samples and {len(X_train.columns)} features...")
        
        # LightGBM parameters (can be tuned)
        lgb_params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'n_estimators': 500,
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': -1,
            'seed': 42,
            'n_jobs': -1,
            'verbose': -1, # Suppress verbose output
            'colsample_bytree': 0.7,
            'subsample': 0.7,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
        }
        
        model = lgb.LGBMClassifier(**lgb_params)
        model.fit(X_train, y_train)
        
        logger.info("✅ LightGBM model trained.")
        return model
    
    def calibrate_model(self, model: Any, X_cal: pd.DataFrame, y_cal: pd.Series) -> Any:
        """Calibrates the model probabilities."""
        logger.info("Calibrating model probabilities (Isotonic)...")
        calibrated_model = CalibratedClassifierCV(model, method='isotonic', cv='prefit')
        calibrated_model.fit(X_cal, y_cal)
        logger.info("✅ Model calibrated.")
        return calibrated_model
        
    def evaluate_model(self, model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """Evaluates the model and returns performance metrics."""
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        metrics = {
            "auc": roc_auc_score(y_test, y_pred_proba),
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred),
            "recall": recall_score(y_test, y_pred),
            "f1_score": f1_score(y_test, y_pred),
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
            "test_samples": len(y_test)
        }
        logger.info(f"📊 Model Evaluation: AUC={metrics['auc']:.3f}, Accuracy={metrics['accuracy']:.3f}")
        return metrics
        
    def run_training_pipeline(self, df: pd.DataFrame, forward_bars: int = 1) -> Dict[str, Any]:
        """Runs the complete training pipeline."""
        X, y = self.prepare_data(df, forward_bars)
        
        if len(X) < 100:
            logger.warning("Insufficient data for training after feature engineering. Skipping training.")
            return {"status": "SKIPPED", "reason": "Insufficient data"}

        # TimeSeriesSplit for robust evaluation
        tscv = TimeSeriesSplit(n_splits=5)
        
        all_metrics = []
        final_model = None
        
        for fold, (train_index, test_index) in enumerate(tscv.split(X)):
            logger.info(f"--- Fold {fold+1}/{tscv.n_splits} ---")
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            # Train
            model = self.train_model(X_train, y_train)
            
            # Calibrate
            calibrated_model = self.calibrate_model(model, X_test, y_test) # Use test set for calibration
            
            # Evaluate
            metrics = self.evaluate_model(calibrated_model, X_test, y_test)
            all_metrics.append(metrics)
            final_model = calibrated_model # Keep the last calibrated model

        # Average metrics
        avg_metrics = {k: np.mean([m[k] for m in all_metrics if k in m]) for k in all_metrics[0]}
        logger.info(f"--- Average Metrics: AUC={avg_metrics['auc']:.3f}, Accuracy={avg_metrics['accuracy']:.3f} ---")

        # Save the final model and metadata
        metadata = {
            "version": self.model_version,
            "created_at": datetime.now().isoformat(),
            "model_type": "LightGBMClassifier",
            "calibrated": True,
            "calibration_method": "isotonic",
            "features": self.feature_engineer.feature_columns,
            "n_features": len(self.feature_engineer.feature_columns),
            "training_period": f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            "symbols": list(df['symbol'].unique()) if 'symbol' in df.columns else ["unknown"],
            "metrics": avg_metrics,
            "hyperparameters": {
                'objective': 'binary', 'metric': 'auc', 'boosting_type': 'gbdt',
                'n_estimators': 500, 'learning_rate': 0.05, 'num_leaves': 31,
                'max_depth': -1, 'seed': 42, 'n_jobs': -1, 'colsample_bytree': 0.7,
                'subsample': 0.7, 'reg_alpha': 0.1, 'reg_lambda': 0.1,
            }
        }
        self.model_manager.save_model(final_model, metadata, self.model_version)
        
        return {"status": "SUCCESS", "metrics": avg_metrics, "model_version": self.model_version}

if __name__ == "__main__":
    # Example usage with dummy data
    logger.info("Running LightGBM Trainer with dummy data for testing...")
    dummy_data = {
        'timestamp': pd.date_range('2025-01-01', periods=1000, freq='15T'),
        'open': np.random.rand(1000) * 100 + 1000,
        'high': np.random.rand(1000) * 10 + 1000,
        'low': np.random.rand(1000) * 10 + 1000,
        'close': np.random.rand(1000) * 10 + 1000,
        'volume': np.random.rand(1000) * 1000 + 10000
    }
    dummy_df = pd.DataFrame(dummy_data)
    dummy_df['symbol'] = 'DUMMY-USDT' # Add symbol column
    
    trainer = LightGBMTrainer()
    results = trainer.run_training_pipeline(dummy_df)
    logger.info(f"Dummy training results: {results}")