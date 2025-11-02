"""
Train LightGBM with Optuna hyperparameter optimization for 18-month data.
"""

import pandas as pd
import numpy as np
import pickle
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
from loguru import logger

import lightgbm as lgb
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score, balanced_accuracy_score
from sklearn.model_selection import TimeSeriesSplit

import optuna
from optuna.visualization import plot_optimization_history

from ml.features import FeatureBuilder


class LGBMTrainerOptuna:
    """Trains LightGBM with Optuna optimization."""
    
    def __init__(self):
        self.feature_builder = FeatureBuilder()
        self.results = {}
        
    def load_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load 18-month data."""
        # Try 18-month file first
        filepath_18m = Path(f"data/ml_training/{symbol}_{timeframe}_18months_binance.csv")
        if filepath_18m.exists():
            logger.info(f"Loading 18-month data from {filepath_18m.name}")
            df = pd.read_csv(filepath_18m)
        else:
            # Fallback to 6-month
            filepath_6m = Path(f"data/ml_training/{symbol}_USDT_{timeframe}_6months_binance.csv")
            logger.info(f"Loading 6-month data from {filepath_6m.name}")
            df = pd.read_csv(filepath_6m)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        logger.info(f"Loaded {len(df)} bars")
        return df
    
    def train_with_optuna(
        self, 
        symbol: str, 
        timeframe: str,
        n_trials: int = 50
    ) -> Dict[str, Any]:
        """
        Train model with Optuna optimization.
        
        Args:
            symbol: Symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '15m')
            n_trials: Number of Optuna trials
        
        Returns:
            Dictionary with best model and metrics
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Optuna Optimization for {symbol}_{timeframe} ({n_trials} trials)")
        logger.info(f"{'='*80}")
        
        # Load data
        df_main = self.load_data(symbol, timeframe)
        
        # Load MTF data if available
        df_1h = None
        df_4h = None
        
        if timeframe != '1h':
            df_1h = self._load_mtf_data(symbol, '1h')
        if timeframe != '4h':
            df_4h = self._load_mtf_data(symbol, '4h')
        
        # Build features
        df = self.feature_builder.build_features(df_main, df_1h, df_4h)
        
        # Create labels
        df = self.feature_builder.create_label(df, forward_bars=1, threshold_pct=0.15)
        
        # Prepare X, y
        X = df[self.feature_builder.feature_columns]
        y = df['label']
        
        logger.info(f"Training data: {len(X)} samples, {len(self.feature_builder.feature_columns)} features")
        logger.info(f"Label distribution: Pos={y.sum()} ({y.sum()/len(y)*100:.1f}%), Neg={len(y)-y.sum()} ({(len(y)-y.sum())/len(y)*100:.1f}%)")
        
        # Time-series split for validation
        tscv = TimeSeriesSplit(n_splits=5)
        
        def objective(trial):
            """Optuna objective function."""
            # Suggest hyperparameters
            params = {
                'objective': 'binary',
                'metric': 'auc',
                'boosting_type': 'gbdt',
                'n_estimators': trial.suggest_int('n_estimators', 500, 2000),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 31, 127),
                'max_depth': trial.suggest_int('max_depth', 5, 15),
                'min_child_samples': trial.suggest_int('min_child_samples', 20, 100),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.01, 1.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.01, 1.0, log=True),
                'class_weight': 'balanced',
                'random_state': 42,
                'n_jobs': -1,
                'verbose': -1
            }
            
            # Cross-validation
            auc_scores = []
            
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                
                # Train model
                model = lgb.LGBMClassifier(**params)
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    eval_metric='auc',
                    callbacks=[lgb.early_stopping(50, verbose=False)]
                )
                
                # Predict
                y_pred_proba = model.predict_proba(X_val)[:, 1]
                auc = roc_auc_score(y_val, y_pred_proba)
                auc_scores.append(auc)
            
            # Return mean AUC
            return np.mean(auc_scores)
        
        # Run optimization
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        # Get best params
        best_params = study.best_params
        best_auc = study.best_value
        
        logger.info(f"\nBest AUC: {best_auc:.4f}")
        logger.info(f"Best params: {best_params}")
        
        # Train final model with best params
        model = lgb.LGBMClassifier(**best_params)
        
        # Final train/test split
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            eval_metric='auc',
            callbacks=[lgb.early_stopping(50, verbose=False)]
        )
        
        # Evaluate
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        auc = roc_auc_score(y_test, y_pred_proba)
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        balanced_acc = balanced_accuracy_score(y_test, y_pred)
        
        logger.info(f"\nFinal Metrics:")
        logger.info(f"  AUC: {auc:.4f}")
        logger.info(f"  Accuracy: {accuracy:.4f}")
        logger.info(f"  F1: {f1:.4f}")
        logger.info(f"  Balanced Accuracy: {balanced_acc:.4f}")
        
        # Save model
        model_dir = Path("models/lgbm")
        model_dir.mkdir(exist_ok=True)
        
        model_path = model_dir / f"{symbol}_{timeframe}_last18m.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Save metadata
        metadata = {
            'symbol': symbol,
            'timeframe': timeframe,
            'features': self.feature_builder.feature_columns,
            'n_features': len(self.feature_builder.feature_columns),
            'metrics': {
                'auc': float(auc),
                'accuracy': float(accuracy),
                'f1': float(f1),
                'balanced_accuracy': float(balanced_acc)
            },
            'training_date': datetime.now().isoformat(),
            'label_config': {
                'forward_bars': 1,
                'threshold_pct': 0.15
            },
            'hyperparameters': best_params,
            'optuna_trials': n_trials,
            'optuna_best_value': float(best_auc)
        }
        
        metadata_path = model_dir / f"{symbol}_{timeframe}_last18m_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved model to {model_path}")
        logger.info(f"Saved metadata to {metadata_path}")
        
        self.results[f"{symbol}_{timeframe}"] = metadata
        
        return metadata
    
    def _load_mtf_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load multi-timeframe data."""
        filepath_18m = Path(f"data/ml_training/{symbol}_{timeframe}_18months_binance.csv")
        if filepath_18m.exists():
            df = pd.read_csv(filepath_18m)
        else:
            filepath_6m = Path(f"data/ml_training/{symbol}_USDT_{timeframe}_6months_binance.csv")
            df = pd.read_csv(filepath_6m)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        return df
    
    def train_all_models(self, n_trials: int = 50) -> Dict[str, Dict]:
        """Train all 9 models with Optuna."""
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        timeframes = ['15m', '1h', '4h']
        
        logger.info("="*80)
        logger.info(f"OPTUNA TRAINING: 9 MODELS × {n_trials} TRIALS EACH")
        logger.info("="*80)
        
        for symbol in symbols:
            for tf in timeframes:
                try:
                    self.train_with_optuna(symbol, tf, n_trials=n_trials)
                except Exception as e:
                    logger.error(f"Failed to train {symbol}_{tf}: {e}")
        
        # Print summary
        self._print_summary()
        
        return self.results
    
    def _print_summary(self):
        """Print training summary."""
        logger.info("\n" + "="*80)
        logger.info("TRAINING SUMMARY")
        logger.info("="*80)
        
        for key, result in self.results.items():
            auc = result['metrics']['auc']
            logger.info(f"{key}: AUC = {auc:.4f}")
        
        avg_auc = np.mean([r['metrics']['auc'] for r in self.results.values()])
        logger.info(f"\nAverage AUC: {avg_auc:.4f}")
        logger.info("="*80)


def main():
    """Main training function."""
    trainer = LGBMTrainerOptuna()
    
    # Train all models
    results = trainer.train_all_models(n_trials=50)
    
    logger.info("\n✅ Training complete!")
    return results


if __name__ == '__main__':
    main()


