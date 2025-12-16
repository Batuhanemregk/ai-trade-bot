"""
Training Pipeline for New Coin Models

Usage:
    # Train single coin
    python ml/train_new_coins.py --symbols XRP
    
    # Train multiple coins
    python ml/train_new_coins.py --symbols XRP,DOGE,AVAX
    
    # Train all new coins
    python ml/train_new_coins.py --all
"""

import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import argparse
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score
import optuna
from optuna.samplers import TPESampler
from loguru import logger

# Configure loguru
logger.add("logs/model_training.log", rotation="10 MB", level="INFO")

# Our ML symbols to train
NEW_COINS = ['XRP', 'DOGE', 'AVAX', 'VET', 'OP', 'RENDER', 'WLD', 'SUI', 'UNI', 'ARB', 'ATOM', 'NEAR']
EXISTING_COINS = ['BTC', 'ETH', 'SOL']


async def collect_ohlcv_data(symbol: str, timeframe: str = "15m", months: int = 18) -> pd.DataFrame:
    """
    Collect OHLCV data from Binance (public API - no key needed).
    
    Args:
        symbol: Coin symbol (e.g., 'XRP')
        timeframe: OHLCV timeframe
        months: Number of months of history
        
    Returns:
        DataFrame with OHLCV data
    """
    import ccxt
    import time as time_module
    
    try:
        # Use Binance public API (no API key required)
        exchange = ccxt.binance({
            'sandbox': False,
            'rateLimit': 100,
        })
        
        full_symbol = f"{symbol}/USDT"  # Binance spot format
        since_ts = int((datetime.now(timezone.utc) - timedelta(days=months * 30)).timestamp() * 1000)
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"📊 Collecting {months}M of {timeframe} data for {symbol} from Binance...")
        
        all_bars = []
        current_since = since_ts
        request_count = 0
        max_requests = 200  # ~52k bars for 18 months of 15m
        
        while current_since < now_ts and request_count < max_requests:
            try:
                bars = exchange.fetch_ohlcv(
                    symbol=full_symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=1000
                )
                
                if not bars or len(bars) == 0:
                    break
                
                all_bars.extend(bars)
                current_since = bars[-1][0] + 1  # Next millisecond
                
                # Progress logging
                if len(all_bars) % 5000 == 0:
                    logger.info(f"  Collected {len(all_bars)} bars...")
                
                # Rate limit protection
                time_module.sleep(0.2)
                request_count += 1
                
            except Exception as e:
                logger.warning(f"Batch fetch error: {e}, stopping")
                break
        
        if not all_bars:
            logger.error(f"❌ No data collected for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        duration_days = (df['timestamp'].max() - df['timestamp'].min()).days
        logger.info(f"✅ Collected {len(df)} bars for {symbol} ({duration_days} days)")
        logger.info(f"   Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Data collection failed for {symbol}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return pd.DataFrame()


def select_top_features_shap(X: pd.DataFrame, y: pd.Series, n_features: int = 35) -> List[str]:
    """Select top features using SHAP importance."""
    try:
        import shap
        
        logger.info(f"🔍 Selecting top {n_features} features using SHAP...")
        
        # Train quick model for SHAP
        model = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.1,
            num_leaves=31,
            max_depth=6,
            n_jobs=-1,
            verbose=-1
        )
        model.fit(X, y)
        
        # SHAP values
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        
        # Handle binary classification
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        
        # Mean absolute SHAP importance
        mean_shap = np.abs(shap_values).mean(axis=0)
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': mean_shap
        }).sort_values('importance', ascending=False)
        
        top_features = feature_importance.head(n_features)['feature'].tolist()
        logger.info(f"✅ Selected features: {top_features[:10]}...")
        
        return top_features
        
    except Exception as e:
        logger.warning(f"SHAP selection failed: {e}, using all features")
        return X.columns.tolist()[:n_features]


def objective(trial, X: pd.DataFrame, y: pd.Series, feature_cols: List[str]) -> float:
    """Optuna objective with 5-fold time series CV."""
    
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1),
        'num_leaves': trial.suggest_int('num_leaves', 16, 256),
        'max_depth': trial.suggest_int('max_depth', 4, 12),
        'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'min_child_samples': trial.suggest_int('min_child_samples', 20, 200),
        'n_jobs': -1,
        'verbose': -1
    }
    
    # 5-fold time series cross-validation
    tscv = TimeSeriesSplit(n_splits=5)
    scores = []
    
    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X.iloc[train_idx][feature_cols], X.iloc[val_idx][feature_cols]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False)]
        )
        
        y_prob = model.predict_proba(X_val)[:, 1]
        score = roc_auc_score(y_val, y_prob)
        scores.append(score)
    
    return np.mean(scores)


async def train_coin_model(
    symbol: str,
    output_dir: Path = Path("models/lgbm"),
    n_trials: int = 100,
    threshold_pct: float = 1.0,
    forward_bars: int = 3,
    n_features: int = 35,
    months: int = 18
) -> Dict:
    """
    Train a dedicated model for a single coin.
    
    Args:
        symbol: Coin symbol
        output_dir: Output directory for model files
        n_trials: Optuna trials
        threshold_pct: Label threshold percentage
        forward_bars: Forward bars for label
        n_features: Number of features to select
        months: Months of training data
        
    Returns:
        Training results dict
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Training model for {symbol}")
    logger.info(f"{'='*60}")
    
    result = {
        'symbol': symbol,
        'success': False,
        'model_path': None,
        'metrics': {}
    }
    
    try:
        # 1. Collect data
        df = await collect_ohlcv_data(symbol, "15m", months)
        
        if df.empty or len(df) < 1000:
            logger.error(f"❌ Insufficient data for {symbol}: {len(df)} bars")
            result['error'] = f"Insufficient data: {len(df)} bars"
            return result
        
        # 2. Build features
        from ml.features.builder import FeatureBuilder
        builder = FeatureBuilder()
        
        X, y = builder.prepare_for_training(
            df, 
            forward_bars=forward_bars, 
            threshold_pct=threshold_pct
        )
        
        logger.info(f"📊 Training data: {len(X)} samples, {len(builder.feature_columns)} features")
        logger.info(f"📊 Class balance: {y.mean()*100:.1f}% positive")
        
        # 3. Feature selection
        selected_features = select_top_features_shap(X, y, n_features)
        X_selected = X[selected_features]
        
        # 4. Optuna optimization
        logger.info(f"🔧 Running {n_trials} Optuna trials...")
        
        study = optuna.create_study(
            direction="maximize",
            sampler=TPESampler(seed=42)
        )
        study.optimize(
            lambda trial: objective(trial, X_selected, y, selected_features),
            n_trials=n_trials,
            show_progress_bar=True
        )
        
        best_auc = study.best_value
        best_params = study.best_params
        
        logger.info(f"✅ Best AUC: {best_auc:.4f}")
        logger.info(f"✅ Best params: {best_params}")
        
        # 5. Train final model with best params
        final_params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'n_jobs': -1,
            'verbose': -1,
            **best_params
        }
        
        final_model = lgb.LGBMClassifier(**final_params)
        final_model.fit(X_selected, y)
        
        # 6. Calculate final metrics on last 20% (holdout)
        split_idx = int(len(X_selected) * 0.8)
        X_holdout = X_selected.iloc[split_idx:]
        y_holdout = y.iloc[split_idx:]
        
        y_prob = final_model.predict_proba(X_holdout)[:, 1]
        y_pred = final_model.predict(X_holdout)
        
        metrics = {
            'auc': float(roc_auc_score(y_holdout, y_prob)),
            'accuracy': float(accuracy_score(y_holdout, y_pred)),
            'precision': float(precision_score(y_holdout, y_pred)),
            'recall': float(recall_score(y_holdout, y_pred)),
            'optuna_best_auc': float(best_auc)
        }
        
        logger.info(f"📈 Holdout metrics: AUC={metrics['auc']:.4f}, Acc={metrics['accuracy']:.4f}")
        
        # 7. Save model
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / f"{symbol}_USDT_15m_last18m.pkl"
        metadata_path = output_dir / f"{symbol}_USDT_15m_last18m_metadata.json"
        
        with open(model_path, 'wb') as f:
            pickle.dump(final_model, f)
        
        # 8. Save metadata
        metadata = {
            'symbol': f"{symbol}_USDT",
            'timeframe': '15m',
            'training_period': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            'training_samples': len(X),
            'n_features': len(selected_features),
            'feature_columns': selected_features,
            'forward_bars': forward_bars,
            'threshold_pct': threshold_pct,
            'optuna_trials': n_trials,
            'best_params': best_params,
            'metrics': metrics,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"💾 Saved model to {model_path}")
        
        result.update({
            'success': True,
            'model_path': str(model_path),
            'metrics': metrics,
            'training_samples': len(X)
        })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Training failed for {symbol}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        result['error'] = str(e)
        return result


async def train_all_new_coins(
    symbols: List[str] = None,
    n_trials: int = 100
) -> Dict[str, Dict]:
    """Train models for all new coins."""
    
    if symbols is None:
        symbols = NEW_COINS
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Training {len(symbols)} coin models")
    logger.info(f"{'='*60}")
    
    results = {}
    
    for i, symbol in enumerate(symbols, 1):
        logger.info(f"\n[{i}/{len(symbols)}] Processing {symbol}...")
        
        result = await train_coin_model(
            symbol=symbol,
            n_trials=n_trials
        )
        
        results[symbol] = result
        
        if result['success']:
            logger.info(f"✅ {symbol}: AUC={result['metrics']['auc']:.4f}")
        else:
            logger.error(f"❌ {symbol}: {result.get('error', 'Unknown error')}")
        
        # Rate limit between coins
        await asyncio.sleep(1)
    
    # Summary
    successful = [s for s, r in results.items() if r['success']]
    failed = [s for s, r in results.items() if not r['success']]
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 Training Summary")
    logger.info(f"{'='*60}")
    logger.info(f"✅ Successful: {len(successful)} - {successful}")
    logger.info(f"❌ Failed: {len(failed)} - {failed}")
    
    if successful:
        avg_auc = np.mean([results[s]['metrics']['auc'] for s in successful])
        logger.info(f"📈 Average AUC: {avg_auc:.4f}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Train ML models for new coins")
    parser.add_argument('--symbols', type=str, help='Comma-separated list of symbols')
    parser.add_argument('--all', action='store_true', help='Train all new coins')
    parser.add_argument('--trials', type=int, default=100, help='Optuna trials')
    
    args = parser.parse_args()
    
    if args.all:
        symbols = NEW_COINS
    elif args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        print("Usage: python train_new_coins.py --symbols XRP,DOGE or --all")
        return
    
    # Run training
    results = asyncio.run(train_all_new_coins(symbols, n_trials=args.trials))
    
    # Save results
    results_path = Path("logs/training_results.json")
    results_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
