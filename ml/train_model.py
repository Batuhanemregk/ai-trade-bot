"""
ML Model Training Pipeline
Trains RandomForest model for direction prediction (up/down).
"""

import pandas as pd
import numpy as np
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple
from loguru import logger

from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, 
    brier_score_loss, 
    precision_recall_fscore_support,
    classification_report,
    confusion_matrix
)
from sklearn.model_selection import TimeSeriesSplit

from ml.feature_engineering import FeatureEngineer


class MLModelTrainer:
    """Trains and evaluates ML models for trading signals."""
    
    def __init__(self, model_version: str = "rf_v1"):
        self.model_version = model_version
        self.feature_engineer = FeatureEngineer()
        self.model = None
        self.calibrated_model = None
        self.metadata = {}
    
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
    
    def train_test_split(self, X: pd.DataFrame, y: pd.Series, train_ratio: float = 0.8) -> Tuple:
        """
        Time-ordered train/test split.
        
        Args:
            X: Features
            y: Labels  
            train_ratio: Ratio for training set (default: 0.8 = 80%)
            
        Returns:
            X_train, X_test, y_train, y_test
        """
        split_idx = int(len(X) * train_ratio)
        
        X_train = X.iloc[:split_idx]
        X_test = X.iloc[split_idx:]
        y_train = y.iloc[:split_idx]
        y_test = y.iloc[split_idx:]
        
        logger.info(f"Train set: {len(X_train)} samples ({y_train.sum()/len(y_train)*100:.1f}% up)")
        logger.info(f"Test set: {len(X_test)} samples ({y_test.sum()/len(y_test)*100:.1f}% up)")
        
        return X_train, X_test, y_train, y_test
    
    def train_model(self, X_train: pd.DataFrame, y_train: pd.Series) -> RandomForestClassifier:
        """
        Train RandomForestClassifier.
        
        Parameters (as per plan):
        - n_estimators: 200
        - max_depth: 8-16 (using 12 as middle)
        - class_weight: 'balanced'
        - random_state: 42 (reproducibility)
        """
        logger.info("Training RandomForestClassifier...")
        
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1,
            verbose=0
        )
        
        self.model.fit(X_train, y_train)
        
        logger.info(f"[OK] Model trained with {len(X_train.columns)} features")
        
        return self.model
    
    def calibrate_model(self, X_train: pd.DataFrame, y_train: pd.Series, method: str = 'isotonic') -> CalibratedClassifierCV:
        """
        Calibrate model probabilities (Platt or Isotonic).
        
        Args:
            method: 'sigmoid' (Platt) or 'isotonic' (default)
        """
        logger.info(f"Calibrating model with {method} method...")
        
        self.calibrated_model = CalibratedClassifierCV(
            self.model,
            method=method,
            cv='prefit'  # Model already fitted
        )
        
        # Use last 20% of train data for calibration
        split_idx = int(len(X_train) * 0.8)
        X_cal = X_train.iloc[split_idx:]
        y_cal = y_train.iloc[split_idx:]
        
        self.calibrated_model.fit(X_cal, y_cal)
        
        logger.info("[OK] Model calibrated")
        
        return self.calibrated_model
    
    def evaluate_model(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, Any]:
        """
        Evaluate model performance.
        
        Metrics (as per plan):
        - AUC (ROC curve)
        - Brier score (calibration quality)
        - Precision/Recall at 0.5 threshold
        - Confusion matrix
        """
        logger.info("Evaluating model...")
        
        # Use calibrated model if available
        model = self.calibrated_model if self.calibrated_model else self.model
        
        # Predictions
        y_pred_proba = model.predict_proba(X_test)[:, 1]  # Probability of class 1 (up)
        y_pred = (y_pred_proba >= 0.5).astype(int)
        
        # AUC
        auc = roc_auc_score(y_test, y_pred_proba)
        
        # Brier score (lower is better)
        brier = brier_score_loss(y_test, y_pred_proba)
        
        # Precision, Recall, F1
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='binary', zero_division=0
        )
        
        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        
        # Accuracy
        accuracy = (y_pred == y_test).sum() / len(y_test)
        
        metrics = {
            'auc': float(auc),
            'brier_score': float(brier),
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'confusion_matrix': cm.tolist(),
            'test_samples': len(y_test),
            'calibrated': self.calibrated_model is not None
        }
        
        # Log results
        logger.info(f"[METRICS]")
        logger.info(f"  AUC: {auc:.4f}")
        logger.info(f"  Brier Score: {brier:.4f}")
        logger.info(f"  Accuracy: {accuracy:.4f}")
        logger.info(f"  Precision: {precision:.4f}")
        logger.info(f"  Recall: {recall:.4f}")
        logger.info(f"  F1 Score: {f1:.4f}")
        logger.info(f"  Confusion Matrix:")
        logger.info(f"    TN={cm[0,0]}, FP={cm[0,1]}")
        logger.info(f"    FN={cm[1,0]}, TP={cm[1,1]}")
        
        return metrics
    
    def save_model(self, output_dir: str = "models"):
        """
        Save model and metadata.
        
        Files:
        - models/rf_v1.pkl (pickled model)
        - models/rf_v1_version.json (metadata)
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_file = output_path / f"{self.model_version}.pkl"
        model_to_save = self.calibrated_model if self.calibrated_model else self.model
        
        with open(model_file, 'wb') as f:
            pickle.dump(model_to_save, f)
        
        logger.info(f"[OK] Model saved to {model_file}")
        
        # Save metadata
        metadata_file = output_path / f"{self.model_version}_version.json"
        
        metadata = {
            'version': self.model_version,
            'created_at': datetime.now().isoformat(),
            'model_type': 'RandomForestClassifier',
            'calibrated': self.calibrated_model is not None,
            'calibration_method': 'isotonic' if self.calibrated_model else None,
            'features': self.feature_engineer.get_feature_columns(),
            'n_features': len(self.feature_engineer.get_feature_columns()),
            'training_period': self.metadata.get('training_period'),
            'symbols': self.metadata.get('symbols', []),
            'metrics': self.metadata.get('metrics', {}),
            'hyperparameters': {
                'n_estimators': 200,
                'max_depth': 12,
                'min_samples_split': 10,
                'min_samples_leaf': 5,
                'class_weight': 'balanced'
            }
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"[OK] Metadata saved to {metadata_file}")
        
        return model_file, metadata_file


async def main():
    """Train ML model pipeline."""
    
    print("\n" + "="*60)
    print("ML MODEL TRAINING PIPELINE")
    print("="*60 + "\n")
    
    # Initialize trainer
    trainer = MLModelTrainer(model_version="rf_v1")
    
    # Load data
    data_file = "backtests/data/BTC-USDTUSDT_15m.csv"
    df = trainer.load_data(data_file)
    
    # Prepare data (features + labels)
    X, y = trainer.prepare_data(df, forward_bars=1)
    
    # Train/Test split (80/20)
    X_train, X_test, y_train, y_test = trainer.train_test_split(X, y, train_ratio=0.8)
    
    # Train model
    model = trainer.train_model(X_train, y_train)
    
    # Calibrate model
    calibrated_model = trainer.calibrate_model(X_train, y_train, method='isotonic')
    
    # Evaluate
    metrics = trainer.evaluate_model(X_test, y_test)
    
    # Store metadata
    trainer.metadata = {
        'training_period': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
        'symbols': ['BTC-USDT'],
        'metrics': metrics
    }
    
    # Save model
    model_file, metadata_file = trainer.save_model()
    
    print("\n" + "="*60)
    print(f"[OK] ML Model Training Complete!")
    print("="*60)
    print(f"Model: {model_file}")
    print(f"AUC: {metrics['auc']:.4f}")
    print(f"Brier: {metrics['brier_score']:.4f}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1: {metrics['f1_score']:.4f}")
    print("="*60 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

