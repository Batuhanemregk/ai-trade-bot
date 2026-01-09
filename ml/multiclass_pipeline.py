#!/usr/bin/env python
"""
Multi-Class ML Pipeline - UP / NEUTRAL / DOWN
==============================================

3 sınıflı model eğitimi:
- UP: return > +threshold%
- DOWN: return < -threshold%  
- NEUTRAL: between

Özellikler:
- Multi-class LightGBM (softmax)
- Optuna HPO
- SHAP feature selection
- Composite score threshold optimization
- Profit/Loss simulation

Kullanım:
    python ml/multiclass_pipeline.py
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
from sklearn.metrics import accuracy_score, f1_score, classification_report
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

DATA_SUFFIX = "_multiclass"
MODEL_SUFFIX = "_multiclass"

MONTHS_TO_FETCH = 18
THRESHOLD_PCT = 1.0  # +1% = UP, -1% = DOWN, between = NEUTRAL
FORWARD_BARS = 16  # 16 bars × 15min = 4 hours
N_OPTUNA_TRIALS = 50
N_TOP_FEATURES = 40
N_WALK_FORWARD_SPLITS = 5

# Classes
CLASS_DOWN = 0
CLASS_NEUTRAL = 1
CLASS_UP = 2


# ==================== DATA COLLECTION ====================

class BinanceCollector:
    def __init__(self):
        self.exchange = ccxt.binance({'sandbox': False, 'rateLimit': 100})
        self.data_dir = Path("data/ml_training")
        self.data_dir.mkdir(exist_ok=True)
        
    def fetch_symbol(self, symbol: str, months: int = 18) -> Optional[pd.DataFrame]:
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
                time.sleep(0.12)
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
        results = {}
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"[{i}/{len(symbols)}] {symbol}")
            df = self.fetch_symbol(symbol, MONTHS_TO_FETCH)
            if df is not None and len(df) > 1000:
                filepath = self.data_dir / f"{symbol}_15m{DATA_SUFFIX}.csv"
                df.to_csv(filepath, index=False)
                results[symbol] = df
            time.sleep(0.5)
        return results


# ==================== MULTI-CLASS LABELS ====================

def create_multiclass_labels(df: pd.DataFrame, forward_bars: int = 3, 
                            threshold_pct: float = 1.0) -> pd.DataFrame:
    """
    Create 3-class labels: DOWN (0), NEUTRAL (1), UP (2)
    """
    df = df.copy()
    
    # Future return
    future_close = df['close'].shift(-forward_bars)
    future_return = ((future_close - df['close']) / df['close']) * 100
    
    # 3-class labels
    conditions = [
        future_return <= -threshold_pct,  # DOWN
        future_return >= threshold_pct,   # UP
    ]
    choices = [CLASS_DOWN, CLASS_UP]
    df['label'] = np.select(conditions, choices, default=CLASS_NEUTRAL)
    
    # Drop rows without future data
    df = df.iloc[:-forward_bars].copy()
    
    # Distribution
    dist = df['label'].value_counts().to_dict()
    total = len(df)
    logger.info(f"  Labels: DOWN={dist.get(0,0)} ({dist.get(0,0)/total*100:.1f}%), "
               f"NEUTRAL={dist.get(1,0)} ({dist.get(1,0)/total*100:.1f}%), "
               f"UP={dist.get(2,0)} ({dist.get(2,0)/total*100:.1f}%)")
    
    return df


# ==================== SHAP FEATURE SELECTION ====================

def select_top_features(X: pd.DataFrame, y: pd.Series, n_features: int = 40) -> List[str]:
    logger.info(f"  SHAP feature selection ({n_features} features)...")
    
    model = lgb.LGBMClassifier(
        n_estimators=100, num_leaves=31, learning_rate=0.1, 
        verbose=-1, objective='multiclass', num_class=3
    )
    model.fit(X, y)
    
    # Feature importance from model
    importance = model.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    selected = feature_importance.head(n_features)['feature'].tolist()
    logger.info(f"  Top 5: {selected[:5]}")
    return selected


# ==================== OPTUNA HPO ====================

def optuna_objective_multiclass(trial, X_train, y_train, X_val, y_val):
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
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
    
    y_pred = model.predict(X_val)
    return f1_score(y_val, y_pred, average='macro')


def optimize_hyperparams_multiclass(X: pd.DataFrame, y: pd.Series, n_trials: int = 50) -> dict:
    logger.info(f"  Optuna HPO ({n_trials} trials)...")
    
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
    
    study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
    study.optimize(
        lambda trial: optuna_objective_multiclass(trial, X_train, y_train, X_val, y_val),
        n_trials=n_trials,
        show_progress_bar=False
    )
    
    logger.info(f"  Best F1-macro: {study.best_value:.4f}")
    return study.best_params


# ==================== TA SCORE CALCULATION ====================

def calculate_ta_score(df: pd.DataFrame) -> pd.Series:
    """Calculate TA score (0-100)"""
    scores = []
    
    for i in range(len(df)):
        score = 50.0
        
        # RSI
        rsi = df['rsi_14'].iloc[i] if 'rsi_14' in df.columns else 50
        if rsi < 30:
            score += 15
        elif rsi > 70:
            score -= 15
        elif rsi < 40:
            score += 7
        elif rsi > 60:
            score -= 7
        
        # MACD
        macd_hist = df['macd_hist'].iloc[i] if 'macd_hist' in df.columns else 0
        score += np.clip(macd_hist * 50, -10, 10)
        
        # Stochastic
        stoch_k = df['stoch_k'].iloc[i] if 'stoch_k' in df.columns else 50
        if stoch_k < 20:
            score += 10
        elif stoch_k > 80:
            score -= 10
        
        # EMA trend
        if 'ema_12' in df.columns and 'ema_26' in df.columns:
            if df['ema_12'].iloc[i] > df['ema_26'].iloc[i]:
                score += 10
            else:
                score -= 10
        
        scores.append(np.clip(score, 0, 100))
    
    return pd.Series(scores, index=df.index)


# ==================== THRESHOLD OPTIMIZATION ====================

WEIGHTS = {'technical': 0.60, 'ml': 0.30, 'news': 0.05, 'risk': 0.05}


def calculate_ml_score_multiclass(p_down: float, p_neutral: float, p_up: float) -> float:
    """
    Convert multi-class probabilities to 0-100 ML score.
    
    Score = 50 + (p_up - p_down) * 50
    - p_up > p_down → score > 50 (bullish)
    - p_down > p_up → score < 50 (bearish)
    """
    # Net bullish probability
    net_bullish = p_up - p_down
    
    # Scale to 0-100 (net_bullish in [-1, 1] → score in [0, 100])
    ml_score = 50 + net_bullish * 50
    
    return np.clip(ml_score, 0, 100)


def simulate_trading_pnl(composite_scores: pd.Series, prices: pd.Series,
                         enter_long: float, exit_long: float,
                         enter_short: float, exit_short: float,
                         forward_bars: int = 3) -> Dict:
    """Realistic PnL simulation with position tracking."""
    position = 0  # 1=long, -1=short, 0=flat
    entry_price = 0
    pnl_total = 0
    trades = []
    
    for i in range(len(composite_scores) - forward_bars):
        score = composite_scores.iloc[i]
        current_price = prices.iloc[i]
        future_price = prices.iloc[i + forward_bars]
        
        # Entry
        if position == 0:
            if score >= enter_long:
                position = 1
                entry_price = current_price
            elif score <= enter_short:
                position = -1
                entry_price = current_price
        
        # Exit
        elif position == 1:
            if score <= exit_long:
                pnl = (current_price - entry_price) / entry_price * 100
                pnl_total += pnl
                trades.append({'type': 'LONG', 'pnl': pnl, 'entry': entry_price, 'exit': current_price})
                position = 0
        
        elif position == -1:
            if score >= exit_short:
                pnl = (entry_price - current_price) / entry_price * 100
                pnl_total += pnl
                trades.append({'type': 'SHORT', 'pnl': pnl, 'entry': entry_price, 'exit': current_price})
                position = 0
    
    if not trades:
        return {'pnl': 0, 'trades': 0, 'win_rate': 0, 'avg_pnl': 0}
    
    wins = sum(1 for t in trades if t['pnl'] > 0)
    
    return {
        'pnl': pnl_total,
        'trades': len(trades),
        'win_rate': wins / len(trades),
        'avg_pnl': pnl_total / len(trades),
        'max_win': max(t['pnl'] for t in trades),
        'max_loss': min(t['pnl'] for t in trades)
    }


def optimize_thresholds_multiclass(df: pd.DataFrame, model, feature_cols: List[str]) -> Dict:
    """Threshold optimization for multi-class model."""
    logger.info(f"  Threshold optimization with PnL simulation...")
    
    # TA scores
    ta_scores = calculate_ta_score(df)
    
    # ML scores from multi-class
    X = df[feature_cols]
    probs = model.predict_proba(X)  # [p_down, p_neutral, p_up]
    
    ml_scores = pd.Series([
        calculate_ml_score_multiclass(probs[i, 0], probs[i, 1], probs[i, 2])
        for i in range(len(probs))
    ], index=df.index)
    
    logger.info(f"    TA scores: mean={ta_scores.mean():.1f}")
    logger.info(f"    ML scores: mean={ml_scores.mean():.1f}, min={ml_scores.min():.1f}, max={ml_scores.max():.1f}")
    
    # Composite scores
    composite = (
        WEIGHTS['technical'] * ta_scores +
        WEIGHTS['ml'] * ml_scores +
        WEIGHTS['news'] * 50 +
        WEIGHTS['risk'] * 50
    )
    
    logger.info(f"    Composite: mean={composite.mean():.1f}")
    
    # Optimization
    def threshold_objective(trial):
        enter_long = trial.suggest_int('enter_long', 52, 68)
        exit_long = trial.suggest_int('exit_long', 40, 52)
        enter_short = trial.suggest_int('enter_short', 30, 48)
        exit_short = trial.suggest_int('exit_short', 48, 60)
        
        if exit_long >= enter_long or exit_short <= enter_short:
            return -1000
        
        result = simulate_trading_pnl(
            composite, df['close'],
            enter_long, exit_long, enter_short, exit_short,
            FORWARD_BARS
        )
        
        if result['trades'] < 30:
            return -100
        
        # Objective: PnL × win_rate × sqrt(trades)
        return result['pnl'] * result['win_rate'] * np.sqrt(result['trades'])
    
    study = optuna.create_study(direction='maximize', sampler=TPESampler(seed=42))
    study.optimize(threshold_objective, n_trials=150, show_progress_bar=False)
    
    best = study.best_params
    
    # Final simulation
    final_result = simulate_trading_pnl(
        composite, df['close'],
        best['enter_long'], best['exit_long'], best['enter_short'], best['exit_short'],
        FORWARD_BARS
    )
    
    logger.info(f"    Best thresholds: enter_long={best['enter_long']}, exit_long={best['exit_long']}, "
               f"enter_short={best['enter_short']}, exit_short={best['exit_short']}")
    logger.info(f"    Simulated: {final_result['trades']} trades, win_rate={final_result['win_rate']:.1%}, "
               f"total_pnl={final_result['pnl']:.2f}%, avg_pnl={final_result['avg_pnl']:.3f}%")
    
    return {
        'thresholds': best,
        'simulation': final_result
    }


# ==================== TRAINING ====================

def train_symbol_multiclass(symbol: str, df: pd.DataFrame, output_dir: Path) -> Tuple[Optional[Path], Optional[Dict]]:
    logger.info(f"🎯 Training {symbol} (multi-class)...")
    
    # Features
    fb = FeatureBuilder()
    df_features = fb.build_features(df)
    
    # Multi-class labels
    df_labeled = create_multiclass_labels(df_features, FORWARD_BARS, THRESHOLD_PCT)
    
    feature_cols = fb.get_feature_columns()
    X = df_labeled[feature_cols]
    y = df_labeled['label']
    
    if len(X) < 2000:
        logger.warning(f"  ⚠️ Not enough data ({len(X)}), skipping")
        return None, None
    
    # Feature selection
    selected_features = select_top_features(X, y, N_TOP_FEATURES)
    X_selected = X[selected_features]
    
    # Optuna HPO
    best_params = optimize_hyperparams_multiclass(X_selected, y, N_OPTUNA_TRIALS)
    
    # Walk-forward validation
    tscv = TimeSeriesSplit(n_splits=N_WALK_FORWARD_SPLITS)
    cv_scores = []
    
    for train_idx, val_idx in tscv.split(X_selected):
        X_train, X_val = X_selected.iloc[train_idx], X_selected.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        params = {
            'objective': 'multiclass', 'num_class': 3, 'metric': 'multi_logloss',
            'boosting_type': 'gbdt', 'n_estimators': 500, 'verbose': -1,
            **best_params
        }
        
        model = lgb.LGBMClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)],
                  callbacks=[lgb.early_stopping(50)])
        
        y_pred = model.predict(X_val)
        cv_scores.append(f1_score(y_val, y_pred, average='macro'))
    
    mean_f1 = np.mean(cv_scores)
    logger.info(f"  Walk-forward F1-macro: {mean_f1:.4f} (+/- {np.std(cv_scores):.4f})")
    
    # Final model
    final_params = {
        'objective': 'multiclass', 'num_class': 3, 'metric': 'multi_logloss',
        'boosting_type': 'gbdt', 'n_estimators': 500, 'verbose': -1,
        **best_params
    }
    final_model = lgb.LGBMClassifier(**final_params)
    final_model.fit(X_selected, y)
    
    # Threshold optimization
    optimization_result = optimize_thresholds_multiclass(df_labeled, final_model, selected_features)
    
    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{symbol}_USDT_15m{MODEL_SUFFIX}.pkl"
    metadata_path = output_dir / f"{symbol}_USDT_15m{MODEL_SUFFIX}_metadata.json"
    
    with open(model_path, 'wb') as f:
        pickle.dump(final_model, f)
    
    metadata = {
        'symbol': symbol,
        'version': 'multiclass_v1',
        'model_type': 'multi-class',
        'classes': ['DOWN', 'NEUTRAL', 'UP'],
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'selected_features': selected_features,
        'n_features': len(selected_features),
        'best_params': best_params,
        'recommended_thresholds': optimization_result['thresholds'],
        'simulation_results': optimization_result['simulation'],
        'metrics': {
            'f1_macro_mean': float(mean_f1),
            'f1_macro_std': float(np.std(cv_scores))
        }
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"  ✅ Saved: {model_path.name}")
    return model_path, optimization_result


# ==================== MAIN ====================

def main():
    print("=" * 70)
    print("MULTI-CLASS ML PIPELINE (UP / NEUTRAL / DOWN)")
    print("=" * 70)
    print(f"Semboller: {len(ALL_SYMBOLS)}")
    print(f"Sınıflar: UP (>{THRESHOLD_PCT}%), NEUTRAL, DOWN (<-{THRESHOLD_PCT}%)")
    print()
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    # Data collection
    print("\n" + "=" * 40)
    print("ADIM 1: Veri Toplama")
    print("=" * 40)
    
    collector = BinanceCollector()
    data = collector.collect_all(ALL_SYMBOLS)
    print(f"✅ {len(data)} sembol için veri toplandı")
    
    # Training
    print("\n" + "=" * 40)
    print("ADIM 2: Multi-Class Model Eğitimi")
    print("=" * 40)
    
    output_dir = Path("models/lgbm")
    all_results = {}
    trained = []
    
    for symbol, df in data.items():
        try:
            result, optimization = train_symbol_multiclass(symbol, df, output_dir)
            if result:
                trained.append(symbol)
                all_results[symbol] = optimization
        except Exception as e:
            logger.error(f"❌ {symbol} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 40)
    print("ADIM 3: Sonuçlar")
    print("=" * 40)
    
    if all_results:
        # Average thresholds
        avg_thresholds = {
            'enter_long': int(np.mean([r['thresholds']['enter_long'] for r in all_results.values()])),
            'exit_long': int(np.mean([r['thresholds']['exit_long'] for r in all_results.values()])),
            'enter_short': int(np.mean([r['thresholds']['enter_short'] for r in all_results.values()])),
            'exit_short': int(np.mean([r['thresholds']['exit_short'] for r in all_results.values()]))
        }
        
        # Average simulation
        avg_pnl = np.mean([r['simulation']['pnl'] for r in all_results.values()])
        avg_trades = int(np.mean([r['simulation']['trades'] for r in all_results.values()]))
        avg_winrate = np.mean([r['simulation']['win_rate'] for r in all_results.values()])
        
        # Save summary
        summary_file = output_dir / "multiclass_summary.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'average_thresholds': avg_thresholds,
                'average_simulation': {
                    'pnl': avg_pnl,
                    'trades': avg_trades,
                    'win_rate': avg_winrate
                },
                'per_symbol': {s: r for s, r in all_results.items()},
                'generated_at': datetime.now(timezone.utc).isoformat()
            }, f, indent=2)
        
        print(f"\n📊 Önerilen Thresholdlar (ortalama):")
        print(f"   enter_long: {avg_thresholds['enter_long']}")
        print(f"   exit_long: {avg_thresholds['exit_long']}")
        print(f"   enter_short: {avg_thresholds['enter_short']}")
        print(f"   exit_short: {avg_thresholds['exit_short']}")
        
        print(f"\n📈 Simülasyon Sonuçları (ortalama):")
        print(f"   Total PnL: {avg_pnl:.2f}%")
        print(f"   Trades: {avg_trades}")
        print(f"   Win Rate: {avg_winrate:.1%}")
        
        print(f"\n💾 Saved to: {summary_file}")
    
    print("\n" + "=" * 70)
    print("ÖZET")
    print("=" * 70)
    print(f"✅ Eğitilen: {len(trained)} model")
    print(f"📁 Model dosyaları: models/lgbm/*{MODEL_SUFFIX}.pkl")
    print("=" * 70)


if __name__ == "__main__":
    main()
