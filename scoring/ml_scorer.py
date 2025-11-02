"""
ML Scorer - LightGBM-Based Scoring (LGBM-Only)
Uses trained LightGBM models for direction probability scoring.
"""

import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from loguru import logger

from ml.features import FeatureBuilder


class MLScorer:
    """
    ML-based scoring using trained LightGBM models.
    
    - Loads 9 separate models (3 symbols × 3 TFs)
    - Uses expanded feature set (60+ features) with multi-timeframe support
    - Generates p_up (probability of price going up)
    - Converts to score: 0-100 scale
    - Falls back to neutral if model unavailable
    """
    
    def __init__(self):
        self.models = {}  # {symbol_tf: model}
        self.metadata = {}  # {symbol_tf: metadata}
        self.feature_builder = FeatureBuilder()
        self._load_all_models()
    
    def _load_all_models(self):
        """Load all 9 LightGBM models (3 symbols × 3 TFs)."""
        symbols = ['BTC', 'ETH', 'SOL']
        timeframes = ['15m', '1h', '4h']
        
        logger.info("Loading LightGBM models...")
        
        for symbol in symbols:
            for tf in timeframes:
                key = f"{symbol}_{tf}"
                # Try 18-month model first (new), fallback to 6-month
                model_path = Path(f"models/lgbm/{symbol}USDT_{tf}_last18m.pkl")
                metadata_path = Path(f"models/lgbm/{symbol}USDT_{tf}_last18m_metadata.json")
                
                if not model_path.exists():
                    model_path = Path(f"models/lgbm/{symbol}USDT_{tf}_last6m.pkl")
                    metadata_path = Path(f"models/lgbm/{symbol}USDT_{tf}_last6m_metadata.json")
                
                try:
                    if not model_path.exists():
                        logger.debug(f"Model not found: {model_path}, will use fallback")
                        continue
                    
                    # Load model
                    with open(model_path, 'rb') as f:
                        self.models[key] = pickle.load(f)
                    
                    # Load metadata
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            self.metadata[key] = json.load(f)
                    else:
                        self.metadata[key] = {}
                    
                    # Try to get AUC from metrics
                    auc = self.metadata[key].get('metrics', {}).get('auc', 'unknown')
                    if auc == 'unknown':
                        auc = self.metadata[key].get('metrics', {}).get('auc_mean', 'unknown')
                    n_features = self.metadata[key].get('n_features', 'unknown')
                    
                    logger.info(f"✅ Loaded LGBM model: {key} (AUC={auc}, Features={n_features})")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load {key}: {e}")
                    continue
        
        loaded_count = len(self.models)
        logger.info(f"Loaded {loaded_count}/9 LightGBM models")
        
        if loaded_count == 0:
            logger.warning("⚠️ No LightGBM models loaded, will use fallback scoring")
    
    def score(self, symbol: str, ohlcv_bundle: Dict[str, pd.DataFrame]) -> Tuple[float, str, Dict[str, Any]]:
        """
        Compute ML score using appropriate LightGBM model.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT-SWAP')
            ohlcv_bundle: Dictionary with timeframes as keys and DataFrames as values
                         Expected keys: 'main' (or '15m'), '1h', '4h'
        
        Returns:
            Tuple of (score: float, rationale: str, details: dict)
            - score: 0-100 (0=strong down, 50=neutral, 100=strong up)
            - rationale: Explanation
            - details: Additional info (p_up, confidence, model_key)
        """
        try:
            # Extract symbol and timeframe
            symbol_short = self._extract_symbol(symbol)
            tf = self._extract_timeframe(ohlcv_bundle)
            
            if not symbol_short or not tf:
                logger.warning(f"Could not determine symbol/TF for {symbol}, using fallback")
                return self._fallback_score(symbol)
            
            model_key = f"{symbol_short}_{tf}"
            
            # Check if model exists
            if model_key not in self.models:
                logger.warning(f"No LGBM model for {model_key}, using fallback")
                return self._fallback_score(symbol)
            
            # Get OHLCV data
            df_main = ohlcv_bundle.get('main')
            if df_main is None:
                df_main = ohlcv_bundle.get(tf)
            if df_main is None:
                df_main = ohlcv_bundle.get('15m')  # Default to 15m
            
            if df_main is None or len(df_main) == 0:
                logger.warning(f"No data for ML scoring: {symbol}")
                return self._fallback_score(symbol)
            
            # Get multi-timeframe data
            df_1h = ohlcv_bundle.get('1h') if tf != '1h' else None
            df_4h = ohlcv_bundle.get('4h') if tf != '4h' else None
            
            # Build features
            df = self.feature_builder.build_features(df_main, df_1h, df_4h)
            
            if len(df) == 0:
                logger.warning(f"Empty features for {symbol}")
                return self._fallback_score(symbol)
            
            # Get feature columns from model metadata
            model_features = self.metadata.get(model_key, {}).get('features', [])
            if not model_features:
                # Fallback: use feature builder columns
                model_features = self.feature_builder.feature_columns
            
            if not model_features:
                logger.warning(f"No feature columns for {model_key}")
                return self._fallback_score(symbol)
            
            # Filter features to only those available in df
            available_features = [f for f in model_features if f in df.columns]
            missing_features = [f for f in model_features if f not in df.columns]
            
            if missing_features:
                logger.warning(f"Missing features for {model_key}: {missing_features[:5]}")
                logger.debug(f"Available features: {len(available_features)}, Missing: {len(missing_features)}")
            
            if len(available_features) == 0:
                logger.error(f"No available features for {model_key}")
                return self._fallback_score(symbol)
            
            # Get latest features as DataFrame (preserve feature names)
            latest_features_df = df[available_features].iloc[-1:]
            
            # Check for NaN/inf
            if latest_features_df.isnull().any().any() or np.isinf(latest_features_df.values).any():
                logger.warning(f"Invalid features for {symbol}, using fallback")
                return self._fallback_score(symbol)
            
            # Predict with DataFrame (preserves feature names)
            model = self.models[model_key]
            p_up = model.predict_proba(latest_features_df)[0, 1]
            
            # Convert to 0-100 score (bidirectional mapping for SHORT/LONG)
            # p_up >= 0.65: Strong LONG (70-100)
            # 0.50 < p_up < 0.65: Moderate LONG (60-69)
            # 0.35 < p_up < 0.50: Weak/NEUTRAL (40-59)
            # 0.20 < p_up <= 0.35: Moderate SHORT (20-39)
            # p_up <= 0.20: Strong SHORT (0-19)
            if p_up >= 0.65:
                ml_score = round(70 + (p_up - 0.65) / 0.35 * 30, 1)  # 70-100
                signal_dir = "LONG"
            elif p_up >= 0.50:
                ml_score = round(60 + (p_up - 0.50) / 0.15 * 10, 1)  # 60-70
                signal_dir = "LONG_WEAK"
            elif p_up >= 0.35:
                ml_score = round(40 + (p_up - 0.35) / 0.15 * 20, 1)  # 40-60
                signal_dir = "NEUTRAL"
            elif p_up >= 0.20:
                ml_score = round(20 + (p_up - 0.20) / 0.15 * 20, 1)  # 20-40
                signal_dir = "SHORT_WEAK"
            else:
                ml_score = round((p_up / 0.20) * 20, 1)  # 0-20
                signal_dir = "SHORT"
            
            # Determine confidence
            confidence = self._calculate_confidence(p_up)
            
            # Rationale
            rationale = f"LGBM {model_key}: p_up={p_up:.3f} -> {ml_score:.1f}/100 ({signal_dir}, confidence={confidence})"
            
            # Details
            auc = self.metadata[model_key].get('metrics', {}).get('auc', 0)
            if not auc:
                auc = self.metadata[model_key].get('metrics', {}).get('auc_mean', 0)
            
            details = {
                'model': model_key,
                'p_up': float(p_up),
                'p_down': float(1 - p_up),
                'ml_score': float(ml_score),
                'signal_direction': signal_dir,
                'confidence': confidence,
                'model_type': 'LightGBM',
                'auc': float(auc) if auc else None,
                'n_features': len(model_features)
            }
            
            logger.debug(f"✅ ML scoring for {symbol} ({model_key}): p_up={p_up:.3f}, score={ml_score:.1f}")
            
            return ml_score, rationale, details
            
        except Exception as e:
            logger.error(f"❌ ML scoring failed for {symbol}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return self._fallback_score(symbol)
    
    def _extract_symbol(self, symbol: str) -> Optional[str]:
        """Extract short symbol from full symbol string."""
        # Examples: 'BTC-USDT-SWAP' -> 'BTC', 'BTCUSDT' -> 'BTC'
        if '-' in symbol:
            parts = symbol.split('-')
            return parts[0]
        elif 'USDT' in symbol:
            return symbol.replace('USDT', '').replace('_USDT', '')
        else:
            return symbol[:3]  # Assume first 3 chars are symbol
    
    def _extract_timeframe(self, ohlcv_bundle: Dict) -> Optional[str]:
        """Extract timeframe from OHLCV bundle."""
        # Priority: main, then explicit TF, then default to 15m
        if 'main' in ohlcv_bundle:
            # Assume main is 15m (could be improved with metadata)
            return '15m'
        elif '15m' in ohlcv_bundle:
            return '15m'
        elif '1h' in ohlcv_bundle:
            return '1h'
        elif '4h' in ohlcv_bundle:
            return '4h'
        else:
            # Default to 15m
            return '15m'
    
    def _calculate_confidence(self, p_up: float) -> str:
        """
        Determine confidence level from probability.
        
        - [0.48, 0.52]: neutral band → low confidence
        - [0.55, 0.70]: moderate confidence
        - >= 0.70: high confidence
        - <= 0.30: high confidence (strong down)
        """
        if 0.48 <= p_up <= 0.52:
            return 'low'
        elif 0.52 < p_up < 0.55 or 0.45 < p_up < 0.48:
            return 'medium_low'
        elif 0.55 <= p_up < 0.70 or 0.30 < p_up <= 0.45:
            return 'medium'
        else:  # p_up >= 0.70 or p_up <= 0.30
            return 'high'
    
    def _fallback_score(self, symbol: str) -> Tuple[float, str, Dict[str, Any]]:
        """
        Fallback scoring when model unavailable.
        
        Returns neutral score with slight randomness to avoid constant 50.
        """
        import random
        import time
        
        # Add some variation but keep near neutral
        base = 50.0
        variation = random.uniform(-5, 5)  # ±5 points
        time_var = (time.time() % 10) - 5  # ±5 points based on time
        
        score = base + variation + time_var
        score = max(35.0, min(65.0, score))  # Clamp to 35-65 range
        
        rationale = f"ML fallback: model unavailable, using neutral score with variation"
        
        details = {
            'source': 'fallback',
            'p_up': score / 100.0,
            'p_down': 1 - (score / 100.0),
            'ml_score': score,
            'confidence': 'low',
            'model_type': 'fallback'
        }
        
        return score, rationale, details


# Backward compatibility - keep old interface
def score_ml(symbol: str, ohlcv_data: Dict) -> Tuple[float, str, Dict]:
    """Legacy interface for ML scoring."""
    scorer = MLScorer()
    return scorer.score(symbol, ohlcv_data)
