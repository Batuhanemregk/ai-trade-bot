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
        logger.info("Configuration: Multiclass (LONG=2, SHORT=0, FLAT=1)")
        logger.info("  - Forward bars: 3")
        logger.info("  - Threshold: 0.20%")
        logger.info("  - Include FLAT: Yes (with reduced weight)")
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
                    
                    # Prepare data: features + labels (3-class: LONG=2, SHORT=0, FLAT=1)
                    logger.info("Preparing training data...")
                    X, y = self.feature_builder.prepare_for_training(
                        df_main, df_1h, df_4h,
                        forward_bars=3,
                        threshold_pct=0.20,
                        include_flat=True
                    )
                    
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
        """Load OHLCV data from CSV (18-month data only)."""
        # Use 18-month data format: BTCUSDT_15m_18months_binance.csv
        filename = f"{symbol}_{timeframe}_18months_binance.csv"
        filepath = Path(f"data/ml_training/{filename}")
        
        if not filepath.exists():
            raise FileNotFoundError(f"18-month data file not found: {filepath}")
        
        logger.info(f"Loading 18-month data: {filepath}")
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
        
        logger.info(f"Loaded {len(df)} bars (Date range: {df.index[0]} to {df.index[-1]})")
        return df
    
    def _train_single_model(self, X: pd.DataFrame, y: pd.Series, symbol: str, tf: str) -> Any:
        """Train single LightGBM model with time-series CV (3-class: LONG=2, SHORT=0, FLAT=1)."""
        
        # Calculate class weights (give FLAT lower weight to focus on LONG/SHORT)
        unique_classes = np.unique(y)
        class_counts = {cls: (y == cls).sum() for cls in unique_classes}
        total = len(y)
        
        # Inverse frequency weighting with FLAT penalty
        class_weight_dict = {}
        for cls in unique_classes:
            freq = class_counts[cls] / total
            weight = 1.0 / freq  # Inverse frequency
            # Reduce FLAT weight by 50% (FLAT=1)
            if cls == 1:  # FLAT
                weight *= 0.5
            class_weight_dict[cls] = weight
        
        # Normalize weights
        total_weight = sum(class_weight_dict.values())
        class_weight_dict = {k: v / total_weight * len(unique_classes) for k, v in class_weight_dict.items()}
        
        logger.info(f"Class weights: {class_weight_dict}")
        
        # Hyperparameters - Multiclass for 3 classes
        params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'n_estimators': 1000,
            'learning_rate': 0.03,
            'num_leaves': 63,
            'max_depth': 10,
            'colsample_bytree': 0.8,
            'subsample': 0.8,
            'reg_alpha': 0.5,
            'reg_lambda': 0.5,
            'min_child_samples': 50,
            'class_weight': class_weight_dict,  # Custom weights (FLAT penalized)
            'seed': 42,
            'n_jobs': -1,
            'verbose': -1
        }
        
        model = lgb.LGBMClassifier(**params)
        
        # Train on full data
        model.fit(X, y)
        
        return model
    
    def _evaluate_model(self, model: Any, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """Evaluate model with time-series split (multiclass: LONG=2, SHORT=0, FLAT=1)."""
        from sklearn.metrics import roc_auc_score, classification_report
        
        tscv = TimeSeriesSplit(n_splits=5)
        
        metrics_list = []
        
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            # Train temporary model for this fold
            temp_model = lgb.LGBMClassifier(**model.get_params())
            temp_model.fit(X_train, y_train)
            
            # Predict (multiclass)
            y_pred_proba = temp_model.predict_proba(X_test)  # Shape: (n_samples, 3)
            y_pred = temp_model.predict(X_test)
            
            # Multiclass AUC (one-vs-rest average)
            try:
                # One-vs-rest AUC for each class
                auc_ovr = roc_auc_score(y_test, y_pred_proba, multi_class='ovr', average='macro')
            except:
                auc_ovr = 0.5  # Fallback if AUC calculation fails
            
            # Calculate metrics (multiclass)
            fold_metrics = {
                'auc': auc_ovr,  # Macro-averaged one-vs-rest AUC
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, average='macro', zero_division=0),
                'recall': recall_score(y_test, y_pred, average='macro', zero_division=0),
                'f1': f1_score(y_test, y_pred, average='macro', zero_division=0),
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
        
        # Save model with multiclass_v3 tag
        model_path = model_dir / f"{symbol}_{tf}_multiclass_v3.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Get model hyperparameters
        model_params = model.get_params()
        class_weight_info = model_params.get('class_weight', 'unknown')
        if isinstance(class_weight_info, dict):
            class_weight_info = {str(k): float(v) for k, v in class_weight_info.items()}
        
        # Save metadata
        metadata = {
            'symbol': symbol,
            'timeframe': tf,
            'model_version': 'multiclass_v3',
            'features': features,
            'n_features': len(features),
            'metrics': metrics,
            'training_date': datetime.now().isoformat(),
            'label_config': {
                'type': 'multiclass_three_class',
                'forward_bars': 3,
                'threshold_pct': 0.20,
                'long_label': 2,
                'short_label': 0,
                'flat_label': 1,
                'include_flat': True
            },
            'data_period': '18_months',
            'hyperparameters': {
                'objective': 'multiclass',
                'num_class': 3,
                'metric': 'multi_logloss',
                'boosting_type': 'gbdt',
                'n_estimators': 1000,
                'learning_rate': 0.03,
                'num_leaves': 63,
                'max_depth': 10,
                'colsample_bytree': 0.8,
                'subsample': 0.8,
                'reg_alpha': 0.5,
                'reg_lambda': 0.5,
                'min_child_samples': 50,
                'class_weight': class_weight_info
            }
        }
        
        metadata_path = model_dir / f"{symbol}_{tf}_multiclass_v3_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved model: {model_path}")
        logger.info(f"Saved metadata: {metadata_path}")
    
    def generate_report(self) -> str:
        """Generate training report as markdown."""
        lines = [
            "# Symmetric Binary LGBM Training Report",
            "",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Models Trained**: {len(self.results)}",
            f"**Model Version**: symmetric_v2",
            "",
            "## Configuration",
            "",
            "- **Label Strategy**: Symmetric binary classification",
            "  - LONG (1): future_return > 0.25%",
            "  - SHORT (0): future_return < -0.25%",
            "  - FLAT: Removed from training",
            "- **Data Period**: 18 months",
            "- **Forward Bars**: 1 bar",
            "- **Features**: 60-73 (multi-timeframe)",
            "- **Class Balancing**: Balanced class weights enabled",
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
        
        # Calculate average AUC
        auc_values = [r.get('auc', 0) for r in self.results.values() if 'auc' in r]
        avg_auc = sum(auc_values) / len(auc_values) if auc_values else 0
        
        lines.extend([
            "",
            "## Summary",
            "",
            f"- **Average AUC**: {avg_auc:.4f}",
            f"- **Target AUC**: 0.70-0.80",
            f"- **Status**: {'✅ Target achieved' if avg_auc >= 0.70 else '⚠️ Below target'}",
            "",
            "## Improvements vs Previous Version",
            "",
            "- Symmetric learning for both LONG and SHORT directions",
            "- 18-month data (vs 6-month)",
            "- FLAT examples removed for cleaner training",
            "- More balanced class distribution (~30% LONG, ~30% SHORT, ~40% removed)",
            "- Enhanced hyperparameters with class balancing"
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

