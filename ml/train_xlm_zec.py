"""
Training script for XLM and ZEC using Binance data
HYPE excluded - too new, no 18 month history
CRO excluded - OKX data collection failed
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pickle
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score
import optuna
from optuna.samplers import TPESampler
from loguru import logger
import time as time_module

logger.add("logs/new_coin_training.log", rotation="10 MB", level="INFO")

# Only coins with 18 month history on Binance
COINS_TO_TRAIN = ['XLM', 'ZEC']


async def collect_ohlcv_data(symbol: str, timeframe: str = "15m", months: int = 18) -> pd.DataFrame:
    """Collect OHLCV data from Binance."""
    import ccxt
    
    try:
        exchange = ccxt.binance({'timeout': 30000})
        full_symbol = f"{symbol}/USDT"
        
        since_ts = int((datetime.now(timezone.utc) - timedelta(days=months * 30)).timestamp() * 1000)
        now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        logger.info(f"📊 Collecting {months}M of {timeframe} data for {symbol} from Binance...")
        
        all_bars = []
        current_since = since_ts
        request_count = 0
        max_requests = 200
        
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
                current_since = bars[-1][0] + 1
                
                if len(all_bars) % 5000 == 0:
                    logger.info(f"  Collected {len(all_bars)} bars...")
                
                time_module.sleep(0.2)
                request_count += 1
                
            except Exception as e:
                logger.warning(f"Batch fetch error: {e}")
                break
        
        if not all_bars:
            logger.error(f"❌ No data collected for {symbol}")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['symbol'] = symbol
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
        
        duration_days = (df['timestamp'].max() - df['timestamp'].min()).days
        logger.info(f"✅ Collected {len(df)} bars for {symbol} ({duration_days} days)")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Data collection failed for {symbol}: {e}")
        return pd.DataFrame()


async def train_coin_model(symbol: str, n_trials: int = 50) -> Dict:
    """Train model for a single coin."""
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Training model for {symbol}")
    logger.info(f"{'='*60}")
    
    result = {'symbol': symbol, 'success': False, 'metrics': {}}
    
    try:
        df = await collect_ohlcv_data(symbol, "15m", 18)
        
        if df.empty or len(df) < 1000:
            result['error'] = f"Insufficient data: {len(df) if not df.empty else 0} bars"
            return result
        
        from ml.features.builder import FeatureBuilder
        builder = FeatureBuilder()
        
        X, y = builder.prepare_for_training(df, forward_bars=3, threshold_pct=1.0)
        logger.info(f"📊 Training data: {len(X)} samples, {len(builder.feature_columns)} features")
        logger.info(f"📊 Class balance: {y.mean()*100:.1f}% positive")
        
        # Select top 35 features
        model_quick = lgb.LGBMClassifier(n_estimators=100, verbose=-1)
        model_quick.fit(X, y)
        feature_imp = pd.DataFrame({
            'feature': X.columns,
            'importance': model_quick.feature_importances_
        }).sort_values('importance', ascending=False)
        selected_features = feature_imp.head(35)['feature'].tolist()
        X_selected = X[selected_features]
        
        logger.info(f"🔧 Running {n_trials} Optuna trials...")
        
        def objective(trial):
            params = {
                'objective': 'binary',
                'metric': 'auc',
                'n_estimators': trial.suggest_int('n_estimators', 100, 400),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1),
                'num_leaves': trial.suggest_int('num_leaves', 16, 128),
                'max_depth': trial.suggest_int('max_depth', 4, 10),
                'verbose': -1
            }
            
            tscv = TimeSeriesSplit(n_splits=3)
            scores = []
            
            for train_idx, val_idx in tscv.split(X_selected):
                X_train, X_val = X_selected.iloc[train_idx], X_selected.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                
                model = lgb.LGBMClassifier(**params)
                model.fit(X_train, y_train)
                y_prob = model.predict_proba(X_val)[:, 1]
                scores.append(roc_auc_score(y_val, y_prob))
            
            return np.mean(scores)
        
        study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        best_auc = study.best_value
        best_params = study.best_params
        logger.info(f"✅ Best CV AUC: {best_auc:.4f}")
        
        final_params = {'objective': 'binary', 'verbose': -1, **best_params}
        final_model = lgb.LGBMClassifier(**final_params)
        final_model.fit(X_selected, y)
        
        # Holdout metrics
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
        }
        
        logger.info(f"📈 Holdout: AUC={metrics['auc']:.4f}, Acc={metrics['accuracy']:.4f}")
        
        # Save model
        output_dir = Path("models/lgbm")
        output_dir.mkdir(parents=True, exist_ok=True)
        model_path = output_dir / f"{symbol}_USDT_15m_last18m.pkl"
        
        with open(model_path, 'wb') as f:
            pickle.dump(final_model, f)
        
        metadata = {
            'symbol': f"{symbol}_USDT",
            'timeframe': '15m',
            'training_samples': len(X),
            'feature_columns': selected_features,
            'metrics': metrics,
            'data_source': 'binance',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        with open(output_dir / f"{symbol}_USDT_15m_last18m_metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"💾 Saved model to {model_path}")
        
        result.update({'success': True, 'model_path': str(model_path), 'metrics': metrics})
        return result
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        result['error'] = str(e)
        return result


async def main():
    print("="*60)
    print("ML MODEL TRAINING - XLM, ZEC (Binance data)")
    print("="*60)
    
    results = {}
    
    for symbol in COINS_TO_TRAIN:
        print(f"\n>>> Training {symbol}...")
        result = await train_coin_model(symbol, n_trials=50)
        results[symbol] = result
        
        if result['success']:
            m = result['metrics']
            print(f"✅ {symbol}: AUC={m['auc']:.4f} | Acc={m['accuracy']:.4f} | Prec={m['precision']:.4f}")
        else:
            print(f"❌ {symbol}: {result.get('error', 'Unknown error')}")
        
        await asyncio.sleep(2)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for symbol, result in results.items():
        if result['success']:
            m = result['metrics']
            print(f"{symbol}: AUC={m['auc']:.4f}")
        else:
            print(f"{symbol}: FAILED")
    
    with open("logs/xlm_zec_training_results.json", 'w') as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    asyncio.run(main())
