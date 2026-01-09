#!/usr/bin/env python
"""
Advanced ML Pipeline v2 - Regime Detection + Optuna + Threshold Optimizer
=========================================================================

Özellikler:
- 15 sembol için 18 aylık Binance verisi
- SHAP-based feature selection (top 35)
- Optuna hiperparametre optimizasyonu (50 trial)
- Walk-forward validation
- Threshold optimization (enter_long, exit_long, enter_short, exit_short)
- Regime-adaptive thresholds

Çıktılar:
- Veri: data/ml_training/{SYMBOL}_15m_regime_v2.csv
- Model: models/lgbm/{SYMBOL}_USDT_15m_regime_v2.pkl
- Thresholds: models/lgbm/recommended_thresholds.json

Kullanım:
    python ml/full_regime_pipeline.py

Süre: ~4-6 saat (tüm semboller)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import ccxt
import pandas as pd
import numpy as np
import pickle
import json
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score, accuracy_score
from sklearn.calibration import CalibratedClassifierCV
import lightgbm as lgb
import optuna
from optuna.samplers import TPESampler
import shap
from loguru import logger

from ml.features.builder import FeatureBuilder


# ==================== CONFIGURATION ====================

ALL_SYMBOLS = [
    'BTC', 'ETH', 'SOL',
    'ARB', 'ATOM', 'AVAX', 'DOGE', 'NEAR', 'OP',
    'RENDER', 'SUI', 'UNI', 'VET', 'WLD', 'XRP'
]

DATA_SUFFIX = "_regime_v2"
MODEL_SUFFIX = "_regime_v2"

MONTHS_TO_FETCH = 18
THRESHOLD_PCT = 1.0
FORWARD_BARS = 3
N_OPTUNA_TRIALS = 50
N_TOP_FEATURES = 35
N_WALK_FORWARD_SPLITS = 5


# ==================== DATA COLLECTION ====================

class BinanceRegimeCollector:
    """Binance'den 18 aylık veri toplayan collector."""
    
    def __init__(self):
        self.exchange = ccxt.binance({'sandbox': False, 'rateLimit': 100})
        self.data_dir = Path("data/ml_training")
        self.data_dir.mkdir(exist_ok=True)
        
    def fetch_symbol(self, symbol: str, months: int = 18) -> Optional[pd.DataFrame]:
        """Tek sembol için veri çek."""
        pair = f"{symbol}/USDT"
        logger.info(f"📥 Fetching {months} months for {pair}...")
        
        since = int((datetime.now(timezone.utc) - timedelta(days=months*30)).timestamp() * 1000)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        
        all_ohlcv = []
        current_since = since
        
        while current_since < now:
            try:
                ohlcv = self.exchange.fetch_ohlcv(pair, '15m', current_since, 1000)
                if not ohlcv:
                    break
                all_ohlcv.extend(ohlcv)
                current_since = ohlcv[-1][0] + 1
                time.sleep(0.15)
            except Exception as e:
                logger.error(f"  Error: {e}")
                break
        
        if all_ohlcv:
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            logger.info(f"  ✅ {symbol}: {len(df)} bars")
            return df
        return None
    
    def collect_all(self, symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """Tüm semboller için veri topla."""
        results = {}
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{len(symbols)}] {symbol}")
            df = self.fetch_symbol(symbol, MONTHS_TO_FETCH)
            if df is not None and len(df) > 1000:
                filepath = self.data_dir / f"{symbol}_15m{DATA_SUFFIX}.csv"
                df.to_csv(filepath, index=False)
                results[symbol] = df
            time.sleep(1)
        return results


# ==================== SHAP FEATURE SELECTION ====================

def select_top_features_shap(X: pd.DataFrame, y: pd.Series, n_features: int = 35) -> List[str]:
    """SHAP ile en önemli n feature'ı seç."""
    logger.info(f"  SHAP feature selection ({n_features} features)...")
    
    # Quick model for SHAP
    model = lgb.LGBMClassifier(n_estimators=100, num_leaves=31, learning_rate=0.1, verbose=-1)
    model.fit(X, y)
    
    # SHAP values
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X[:1000])  # Sample for speed
    
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    
    # Feature importance
    importance = np.abs(shap_values).mean(axis=0)
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    selected = feature_importance.head(n_features)['feature'].tolist()
    logger.info(f"  Top 5: {selected[:5]}")
    return selected


# ==================== OPTUNA OPTIMIZATION ====================

def optuna_objective(trial, X_train, y_train, X_val, y_val):
    """Optuna objective for LightGBM."""
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'num_leaves': trial.suggest_int('num_leaves', 15, 63),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
        'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 0.95),
        'bagging_fraction': trial.suggest_float('bagging_fraction', 0.6, 0.95),
        'bagging_freq': trial.suggest_int('bagging_freq', 1, 7),
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 50),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'n_estimators': 500,
        'verbose': -1
    }
    
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)],
              callbacks=[lgb.early_stopping(50)])
    
    y_pred = model.predict_proba(X_val)[:, 1]
    return roc_auc_score(y_val, y_pred)


def optimize_hyperparams(X: pd.DataFrame, y: pd.Series, n_trials: int = 50) -> dict:
    """Optuna ile hiperparametre optimizasyonu."""
    logger.info(f"  Optuna HPO ({n_trials} trials)...")
    
    # Time-based split
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
    
    study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
    study.optimize(
        lambda trial: optuna_objective(trial, X_train, y_train, X_val, y_val),
        n_trials=n_trials,
        show_progress_bar=False,
        callbacks=[lambda study, trial: None]  # Suppress output
    )
    
    logger.info(f"  Best AUC: {study.best_value:.4f}")
    return study.best_params


# ==================== THRESHOLD OPTIMIZATION WITH COMPOSITE SCORE ====================

# Scoring weights (from policy.yaml defaults)
WEIGHTS = {
    'technical': 0.60,
    'ml': 0.30,
    'news': 0.05,
    'risk': 0.05
}


def calculate_ta_score(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Technical Analysis score (0-100) similar to strategy_service.
    Based on RSI, MACD, Stochastic, and trend indicators.
    """
    scores = pd.Series(index=df.index, dtype=float)
    
    for i in range(len(df)):
        score = 50.0  # Base neutral score
        
        # RSI contribution (±15 points)
        rsi = df['rsi_14'].iloc[i] if 'rsi_14' in df.columns else 50
        if rsi < 30:
            score += 15  # Oversold = bullish
        elif rsi > 70:
            score -= 15  # Overbought = bearish
        elif rsi < 40:
            score += 7
        elif rsi > 60:
            score -= 7
        
        # MACD contribution (±10 points)
        macd_hist = df['macd_hist'].iloc[i] if 'macd_hist' in df.columns else 0
        if macd_hist > 0:
            score += min(10, macd_hist * 100)  # Bullish
        else:
            score -= min(10, abs(macd_hist) * 100)  # Bearish
        
        # Stochastic contribution (±10 points)
        stoch_k = df['stoch_k'].iloc[i] if 'stoch_k' in df.columns else 50
        if stoch_k < 20:
            score += 10  # Oversold
        elif stoch_k > 80:
            score -= 10  # Overbought
        
        # Trend contribution (±10 points) - EMA cross
        if 'ema_12' in df.columns and 'ema_26' in df.columns:
            ema_12 = df['ema_12'].iloc[i]
            ema_26 = df['ema_26'].iloc[i]
            if ema_12 > ema_26:
                score += 10  # Bullish trend
            else:
                score -= 10  # Bearish trend
        
        # Bollinger Band contribution (±5 points)
        if 'bb_pos' in df.columns:
            bb_pos = df['bb_pos'].iloc[i]
            if bb_pos < -1:
                score += 5  # Below lower band = potential reversal up
            elif bb_pos > 1:
                score -= 5  # Above upper band = potential reversal down
        
        # Clamp to 0-100
        scores.iloc[i] = max(0, min(100, score))
    
    return scores


def calculate_composite_score(ta_scores: pd.Series, ml_scores: pd.Series,
                              weights: dict = None) -> pd.Series:
    """
    Calculate composite score using TA and ML with policy weights.
    News and Risk are neutral (50) since we don't have them in training data.
    """
    if weights is None:
        weights = WEIGHTS
    
    # News and Risk are neutral (50) in training simulation
    news_score = 50.0
    risk_score = 50.0
    
    composite = (
        weights['technical'] * ta_scores +
        weights['ml'] * ml_scores +
        weights['news'] * news_score +
        weights['risk'] * risk_score
    )
    
    return composite.clip(0, 100)


def simulate_trading_composite(composite_scores: pd.Series, actual_returns: pd.Series,
                               enter_long: float, exit_long: float,
                               enter_short: float, exit_short: float) -> Dict:
    """Trading simulation using composite scores."""
    position = 0
    pnl = 0
    trades = 0
    wins = 0
    max_drawdown = 0
    peak_pnl = 0
    
    for i in range(len(composite_scores)):
        score = composite_scores.iloc[i]
        ret = actual_returns.iloc[i] if i < len(actual_returns) else 0
        
        # Entry signals
        if position == 0:
            if score >= enter_long:
                position = 1
                trades += 1
            elif score <= enter_short:
                position = -1
                trades += 1
        
        # Exit signals
        elif position == 1:
            if score <= exit_long:
                trade_pnl = ret * position
                pnl += trade_pnl
                if trade_pnl > 0:
                    wins += 1
                position = 0
        
        elif position == -1:
            if score >= exit_short:
                trade_pnl = ret * position
                pnl += trade_pnl
                if trade_pnl > 0:
                    wins += 1
                position = 0
        
        # Track drawdown
        peak_pnl = max(peak_pnl, pnl)
        drawdown = peak_pnl - pnl
        max_drawdown = max(max_drawdown, drawdown)
    
    win_rate = wins / trades if trades > 0 else 0
    sharpe_like = pnl / (max_drawdown + 1) if max_drawdown > 0 else pnl
    
    return {
        'pnl': pnl,
        'trades': trades,
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'sharpe_like': sharpe_like
    }


def optimize_thresholds_composite(df: pd.DataFrame, model, feature_cols: List[str]) -> Dict:
    """
    Threshold optimization using COMPOSITE SCORE (TA + ML).
    This matches the actual trading system's scoring logic.
    """
    logger.info(f"  Composite score threshold optimization...")
    
    # 1. Calculate TA scores
    ta_scores = calculate_ta_score(df)
    logger.info(f"    TA scores: mean={ta_scores.mean():.1f}, std={ta_scores.std():.1f}")
    
    # 2. Calculate ML scores
    X = df[feature_cols]
    ml_probs = model.predict_proba(X)[:, 1]
    ml_scores = pd.Series(ml_probs * 100, index=df.index)
    logger.info(f"    ML scores: mean={ml_scores.mean():.1f}, std={ml_scores.std():.1f}")
    
    # 3. Calculate composite scores
    composite_scores = calculate_composite_score(ta_scores, ml_scores)
    logger.info(f"    Composite scores: mean={composite_scores.mean():.1f}, std={composite_scores.std():.1f}")
    
    # 4. Future returns for simulation
    returns = df['close'].pct_change(FORWARD_BARS).shift(-FORWARD_BARS) * 100
    returns = returns.fillna(0)
    
    # 5. Optuna optimization
    def threshold_objective(trial):
        enter_long = trial.suggest_int('enter_long', 52, 68)
        exit_long = trial.suggest_int('exit_long', 38, 52)
        enter_short = trial.suggest_int('enter_short', 28, 45)
        exit_short = trial.suggest_int('exit_short', 48, 62)
        
        # Ensure valid ranges
        if exit_long >= enter_long or exit_short <= enter_short:
            return -1000
        
        result = simulate_trading_composite(
            composite_scores, returns,
            enter_long, exit_long, enter_short, exit_short
        )
        
        # Objective: Sharpe-like ratio × win_rate
        if result['trades'] < 20:
            return -100
        
        return result['sharpe_like'] * result['win_rate'] * np.log1p(result['trades'])
    
    study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
    study.optimize(threshold_objective, n_trials=150, show_progress_bar=False)
    
    best = study.best_params
    
    # Test with best thresholds
    test_result = simulate_trading_composite(
        composite_scores, returns,
        best['enter_long'], best['exit_long'], best['enter_short'], best['exit_short']
    )
    
    logger.info(f"    Best thresholds (composite): enter_long={best['enter_long']}, exit_long={best['exit_long']}, "
               f"enter_short={best['enter_short']}, exit_short={best['exit_short']}")
    logger.info(f"    Simulated: {test_result['trades']} trades, win_rate={test_result['win_rate']:.1%}, "
               f"pnl={test_result['pnl']:.2f}")
    
    return best





# ==================== TRAINING ====================

def train_symbol_advanced(symbol: str, df: pd.DataFrame, output_dir: Path) -> Tuple[Optional[Path], Optional[Dict]]:
    """Advanced training with all optimizations."""
    logger.info(f"🎯 Training {symbol}...")
    
    # Features
    fb = FeatureBuilder()
    df_features = fb.build_features(df)
    df_labeled = fb.create_label(df_features, FORWARD_BARS, THRESHOLD_PCT)
    
    feature_cols = fb.get_feature_columns()
    X = df_labeled[feature_cols]
    y = df_labeled['label']
    
    if len(X) < 2000:
        logger.warning(f"  ⚠️ Not enough data ({len(X)}), skipping")
        return None, None
    
    # 1. SHAP Feature Selection
    selected_features = select_top_features_shap(X, y, N_TOP_FEATURES)
    X_selected = X[selected_features]
    
    # 2. Optuna HPO
    best_params = optimize_hyperparams(X_selected, y, N_OPTUNA_TRIALS)
    
    # 3. Walk-forward validation
    tscv = TimeSeriesSplit(n_splits=N_WALK_FORWARD_SPLITS)
    cv_scores = []
    
    for train_idx, val_idx in tscv.split(X_selected):
        X_train, X_val = X_selected.iloc[train_idx], X_selected.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        params = {
            'objective': 'binary', 'metric': 'auc', 'boosting_type': 'gbdt',
            'n_estimators': 500, 'verbose': -1, **best_params
        }
        
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)],
                  callbacks=[lgb.early_stopping(50)])
        
        y_pred = model.predict_proba(X_val)[:, 1]
        cv_scores.append(roc_auc_score(y_val, y_pred))
    
    mean_auc = np.mean(cv_scores)
    logger.info(f"  Walk-forward AUC: {mean_auc:.4f} (+/- {np.std(cv_scores):.4f})")
    
    # 4. Final model with calibration
    final_params = {
        'objective': 'binary', 'metric': 'auc', 'boosting_type': 'gbdt',
        'n_estimators': 500, 'verbose': -1, **best_params
    }
    final_model = lgb.LGBMClassifier(**final_params)
    final_model.fit(X_selected, y)
    
    calibrated = CalibratedClassifierCV(final_model, method='isotonic', cv=3)
    calibrated.fit(X_selected, y)
    
    # 5. Threshold optimization with COMPOSITE SCORE
    thresholds = optimize_thresholds_composite(df_labeled, calibrated, selected_features)
    
    # 6. Save
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{symbol}_USDT_15m{MODEL_SUFFIX}.pkl"
    metadata_path = output_dir / f"{symbol}_USDT_15m{MODEL_SUFFIX}_metadata.json"
    
    with open(model_path, 'wb') as f:
        pickle.dump(calibrated, f)
    
    metadata = {
        'symbol': symbol,
        'version': 'regime_v2_advanced',
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'selected_features': selected_features,
        'n_features': len(selected_features),
        'best_params': best_params,
        'recommended_thresholds': thresholds,
        'metrics': {
            'auc_mean': float(mean_auc),
            'auc_std': float(np.std(cv_scores))
        }
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"  ✅ Saved: {model_path.name}")
    return model_path, thresholds


# ==================== MAIN ====================

def main():
    print("=" * 70)
    print("ADVANCED ML PIPELINE v2")
    print("Optuna + SHAP + Threshold Optimizer + Walk-Forward Validation")
    print("=" * 70)
    print(f"Semboller: {len(ALL_SYMBOLS)}")
    print(f"Optuna trials: {N_OPTUNA_TRIALS}")
    print(f"Top features: {N_TOP_FEATURES}")
    print()
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    # Step 1: Data collection
    print("\n" + "=" * 40)
    print("ADIM 1: Veri Toplama")
    print("=" * 40)
    
    collector = BinanceRegimeCollector()
    data = collector.collect_all(ALL_SYMBOLS)
    print(f"✅ {len(data)} sembol için veri toplandı")
    
    # Step 2: Training
    print("\n" + "=" * 40)
    print("ADIM 2: Advanced Model Eğitimi")
    print("=" * 40)
    
    output_dir = Path("models/lgbm")
    all_thresholds = {}
    trained = []
    
    for symbol, df in data.items():
        try:
            result, thresholds = train_symbol_advanced(symbol, df, output_dir)
            if result:
                trained.append(symbol)
                all_thresholds[symbol] = thresholds
        except Exception as e:
            logger.error(f"❌ {symbol} failed: {e}")
    
    # Step 3: Save recommended thresholds
    print("\n" + "=" * 40)
    print("ADIM 3: Threshold Önerileri")
    print("=" * 40)
    
    # Average thresholds across all symbols
    if all_thresholds:
        avg_thresholds = {
            'enter_long': int(np.mean([t['enter_long'] for t in all_thresholds.values()])),
            'exit_long': int(np.mean([t['exit_long'] for t in all_thresholds.values()])),
            'enter_short': int(np.mean([t['enter_short'] for t in all_thresholds.values()])),
            'exit_short': int(np.mean([t['exit_short'] for t in all_thresholds.values()]))
        }
        
        threshold_file = output_dir / "recommended_thresholds.json"
        with open(threshold_file, 'w') as f:
            json.dump({
                'average': avg_thresholds,
                'per_symbol': all_thresholds,
                'generated_at': datetime.now(timezone.utc).isoformat()
            }, f, indent=2)
        
        print(f"\n📊 Önerilen Thresholdlar (ortalama):")
        print(f"   enter_long: {avg_thresholds['enter_long']}")
        print(f"   exit_long: {avg_thresholds['exit_long']}")
        print(f"   enter_short: {avg_thresholds['enter_short']}")
        print(f"   exit_short: {avg_thresholds['exit_short']}")
        print(f"\n💾 Saved to: {threshold_file}")
    
    # Summary
    print("\n" + "=" * 70)
    print("ÖZET")
    print("=" * 70)
    print(f"✅ Eğitilen: {len(trained)} model")
    print(f"📊 Threshold önerileri: recommended_thresholds.json")
    print()
    print("Policy.yaml'a uygulamak için:")
    print("  trading.scoring.decision_thresholds altındaki değerleri güncelleyin")
    print("=" * 70)


if __name__ == "__main__":
    main()
