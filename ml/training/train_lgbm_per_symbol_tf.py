"""
LightGBM Trainer - Train 9 Separate Models (3 symbols × 3 TFs)
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
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, f1_score, balanced_accuracy_score
from sklearn.model_selection import TimeSeriesSplit

from ml.features import FeatureBuilder


class LGBMTrainerPerSymbolTF:
    """Trains separate LightGBM models for each symbol-TF combination."""
    
    def __init__(self):
        self.feature_builder = FeatureBuilder()
        self.results = {}
        
    def train_all_models(self) -> Dict[str, Dict]:
        """
        Train 9 separate models (3 symbols × 3 TFs).
        
        Returns:
            Dictionary of results for each model
        """
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        timeframes = ['15m', '1h', '4h']
        
        logger.info("="*80)
        logger.info("STARTING TRAINING: 9 MODELS (3 SYMBOLS × 3 TFS)")
        logger.info("="*80)
        
        for symbol in symbols:
            for tf in timeframes:
                try:
                    logger.info(f"\n{'='*80}")
                    logger.info(f"Training {symbol}_{tf}")
                    logger.info(f"{'='*80}")
                    
                    # Load data
                    df_main = self._load_data(symbol, tf)
                    df_1h = self._load_data(symbol, '1h') if tf != '1h' else None
                    df_4h = self._load_data(symbol, '4h') if tf != '4h' else None
                    
                    # Build features
                    logger.info("Building features...")
                    df = self.feature_builder.build_features(df_main, df_1h, df_4h)
                    
                    # Create labels
                    logger.info("Creating labels...")
                    df = self.feature_builder.create_label(df, forward_bars=3, threshold_pct=0.25)
                    
                    # Extract X, y
                    X = df[self.feature_builder.feature_columns]
                    y = df['label']
                    
                    logger.info(f"Training data: {len(X)} samples, {len(X.columns)} features")
                    logger.info(f"Class distribution: {y.sum()} positives ({y.sum()/len(y)*100:.1f}%)")
                    
                    # Train
                    logger.info("Training model...")
                    model = self._train_single_model(X, y, symbol, tf)
                    
                    # Evaluate
                    logger.info("Evaluating model...")
                    metrics = self._evaluate_model(model, X, y)
                    
                    # Save
                    logger.info("Saving model...")
                    self._save_model(model, self.feature_builder.feature_columns, metrics, symbol, tf)
                    
                    self.results[f"{symbol}_{tf}"] = metrics
                    
                    logger.info(f"✅ {symbol}_{tf} training complete!")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to train {symbol}_{tf}: {e}")
                    self.results[f"{symbol}_{tf}"] = {'error': str(e)}
        
        logger.info("\n" + "="*80)
        logger.info("TRAINING COMPLETE")
        logger.info("="*80)
        
        return self.results
    
    def _load_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Load OHLCV data from CSV."""
        # Convert symbol format (BTCUSDT -> BTC)
        symbol_short = symbol.replace('USDT', '')
        filename = f"{symbol_short}_USDT_{timeframe}_6months_binance.csv"
        filepath = Path(f"data/ml_training/{filename}")
        
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")
        
        df = pd.read_csv(filepath)
        
        # Parse timestamp
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        elif 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['time'])
        else:
            df['timestamp'] = pd.to_datetime(df.iloc[:, 0])
        
        df = df.sort_values('timestamp').reset_index(drop=True)
        df = df.set_index('timestamp')
        
        logger.debug(f"Loaded {len(df)} bars from {filepath}")
        return df
    
    def _train_single_model(self, X: pd.DataFrame, y: pd.Series, symbol: str, tf: str) -> Any:
        """Train single LightGBM model with time-series CV."""
        
        # Hyperparameters
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'n_estimators': 500,
            'learning_rate': 0.05,
            'num_leaves': 31,
            'max_depth': -1,
            'colsample_bytree': 0.7,
            'subsample': 0.7,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
            'seed': 42,
            'n_jobs': -1,
            'verbose': -1
        }
        
        model = lgb.LGBMClassifier(**params)
        
        # Train on full data
        model.fit(X, y)
        
        return model
    
    def _evaluate_model(self, model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Evaluate model with time-series split."""
        tscv = TimeSeriesSplit(n_splits=5)
        
        metrics_list = []
        
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            # Train temporary model for this fold
            temp_model = lgb.LGBMClassifier(**model.get_params())
            temp_model.fit(X_train, y_train)
            
            # Predict
            y_pred_proba = temp_model.predict_proba(X_test)[:, 1]
            y_pred = (y_pred_proba > 0.5).astype(int)
            
            # Calculate metrics
            fold_metrics = {
                'auc': roc_auc_score(y_test, y_pred_proba),
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, zero_division=0),
                'recall': recall_score(y_test, y_pred, zero_division=0),
                'f1': f1_score(y_test, y_pred, zero_division=0),
                'balanced_accuracy': balanced_accuracy_score(y_test, y_pred)
            }
            
            metrics_list.append(fold_metrics)
        
        # Average across folds
        avg_metrics = {}
        for metric_name in metrics_list[0].keys():
            avg_metrics[metric_name] = np.mean([m[metric_name] for m in metrics_list])
        
        logger.info(f"CV Results: AUC={avg_metrics['auc']:.3f}, F1={avg_metrics['f1']:.3f}")
        
        return avg_metrics
    
    def _save_model(self, model: Any, features: List[str], metrics: Dict, symbol: str, tf: str):
        """Save model and metadata."""
        # Create directory
        model_dir = Path("models/lgbm")
        model_dir.mkdir(exist_ok=True)
        
        # Save model
        model_path = model_dir / f"{symbol}_{tf}_last6m.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Save metadata
        metadata = {
            'symbol': symbol,
            'timeframe': tf,
            'features': features,
            'n_features': len(features),
            'metrics': metrics,
            'training_date': datetime.now().isoformat(),
            'label_config': {
                'forward_bars': 3,
                'threshold_pct': 0.25
            },
            'hyperparameters': {
                'objective': 'binary',
                'metric': 'auc',
                'boosting_type': 'gbdt',
                'n_estimators': 500,
                'learning_rate': 0.05,
                'num_leaves': 31,
                'max_depth': -1,
                'colsample_bytree': 0.7,
                'subsample': 0.7,
                'reg_alpha': 0.1,
                'reg_lambda': 0.1
            }
        }
        
        metadata_path = model_dir / f"{symbol}_{tf}_last6m_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved model: {model_path}")
        logger.info(f"Saved metadata: {metadata_path}")
    
    def generate_report(self) -> str:
        """Generate training report as markdown."""
        lines = [
            "# LGBM Training Report",
            "",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Models Trained**: {len(self.results)}",
            "",
            "## Model Performance",
            "",
            "| Symbol_TF | AUC    | Accuracy | Precision | Recall | F1     | Balanced Acc |",
            "|-----------|--------|----------|-----------|--------|--------|--------------|"
        ]
        
        for key in sorted(self.results.keys()):
            metrics = self.results[key]
            if 'error' in metrics:
                lines.append(f"| {key} | ERROR | - | - | - | - | - |")
            else:
                lines.append(
                    f"| {key} | {metrics.get('auc', 0):.4f} | {metrics.get('accuracy', 0):.4f} | "
                    f"{metrics.get('precision', 0):.4f} | {metrics.get('recall', 0):.4f} | "
                    f"{metrics.get('f1', 0):.4f} | {metrics.get('balanced_accuracy', 0):.4f} |"
                )
        
        lines.extend([
            "",
            "## Summary",
            "",
            "- **Training Method**: Time-series cross-validation (5 folds)",
            "- **Label**: Binary (price up >0.25% in 3 bars)",
            "- **Features**: 60-73 (depending on MTF availability)",
            "- **Hyperparameters**: Standard LightGBM config with regularization"
        ])
        
        return "\n".join(lines)


def main():
    """Main training function."""
    trainer = LGBMTrainerPerSymbolTF()
    results = trainer.train_all_models()
    
    # Generate report
    report = trainer.generate_report()
    print("\n" + report)
    
    # Save report
    report_path = Path("docs/LGBM_TRAINING_REPORT.md")
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info(f"Training report saved to: {report_path}")


if __name__ == '__main__':
    main()

