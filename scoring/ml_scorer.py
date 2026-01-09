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
    
    SIMPLIFIED: Only uses 15m timeframe models (9→3 reduction)
    - 3 models: BTC_15m, ETH_15m, SOL_15m
    - 1h and 4h data used as MTF features, not separate models
    - Falls back to TA-only scoring if model unavailable
    """
    
    def __init__(self):
        self.models = {}  # {model_key: model}
        self.metadata = {}  # {model_key: metadata}
        self.feature_builder = FeatureBuilder()
        
        # Shadow testing config
        self._shadow_testing_enabled = False
        self._shadow_log_path = None
        self._shadow_start_date = None
        
        # Tier-based model routing
        self._tier_models = {}  # {tier: model_key}
        self._dedicated_symbols = []  # Symbols with dedicated models
        
        self._load_all_models()
        self._load_shadow_config()
    
    def _load_shadow_config(self):
        """Load shadow testing configuration."""
        try:
            from application.coin_registry import get_coin_registry
            registry = get_coin_registry()
            shadow_config = registry._config.get('shadow_testing', {})
            
            self._shadow_testing_enabled = shadow_config.get('enabled', False)
            self._shadow_log_path = Path(shadow_config.get('log_file', 'logs/shadow_ml_predictions.jsonl'))
            
            if self._shadow_testing_enabled:
                # Ensure log directory exists
                self._shadow_log_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"🔍 Shadow testing enabled, logging to: {self._shadow_log_path}")
        except Exception as e:
            logger.warning(f"Could not load shadow testing config: {e}")
    
    def _log_shadow_prediction(self, symbol: str, model_key: str, p_up: float, 
                               ml_score: float, signal_dir: str, is_new_model: bool):
        """Log prediction for shadow testing analysis."""
        if not self._shadow_testing_enabled:
            return
        
        try:
            from datetime import datetime, timezone
            import json
            
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbol': symbol,
                'model_key': model_key,
                'p_up': round(p_up, 4),
                'ml_score': round(ml_score, 2),
                'signal_direction': signal_dir,
                'is_new_model': is_new_model,
                'model_type': 'dedicated' if not is_new_model else 'new_dedicated'
            }
            
            with open(self._shadow_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.debug(f"Shadow logging failed: {e}")
    
    def _load_all_models(self):
        """Load LightGBM models for ML-enabled symbols.
        
        Loads:
        1. Dedicated models for ml_enabled_symbols
        2. Tier-based models for tiers without dedicated models
        """
        # Get ML-enabled symbols from CoinRegistry
        try:
            from application.coin_registry import get_coin_registry
            registry = get_coin_registry()
            ml_symbols = registry.get_ml_enabled_symbols()
            tier_model_config = registry._config.get('tier_models', {})
        except Exception as e:
            logger.warning(f"Could not load CoinRegistry, using default ML symbols: {e}")
            ml_symbols = ['BTC', 'ETH', 'SOL']
            tier_model_config = {}
        
        self._dedicated_symbols = ml_symbols.copy()
        
        # Only 15m timeframe models
        timeframes = ['15m']
        
        logger.info(f"Loading LightGBM models for {len(ml_symbols)} symbols: {ml_symbols}")
        
        # 1. Load dedicated models for each symbol
        loaded_dedicated = 0
        for symbol in ml_symbols:
            for tf in timeframes:
                key = f"{symbol}_{tf}"
                
                # PRIORITY 1: Multi-class models (UP/NEUTRAL/DOWN - best quality)
                model_path = Path(f"models/lgbm/{symbol}_USDT_{tf}_multiclass.pkl")
                metadata_path = Path(f"models/lgbm/{symbol}_USDT_{tf}_multiclass_metadata.json")
                is_multiclass = True
                
                # PRIORITY 2: Regime v2 models
                if not model_path.exists():
                    model_path = Path(f"models/lgbm/{symbol}_USDT_{tf}_regime_v2.pkl")
                    metadata_path = Path(f"models/lgbm/{symbol}_USDT_{tf}_regime_v2_metadata.json")
                    is_multiclass = False
                
                # PRIORITY 3: Advanced 18m models
                if not model_path.exists():
                    model_path = Path(f"models/lgbm/{symbol}_USDT_{tf}_last18m.pkl")
                    metadata_path = Path(f"models/lgbm/{symbol}_USDT_{tf}_last18m_metadata.json")
                    is_multiclass = False
                
                # PRIORITY 4: Old format BTCUSDT_15m_last18m.pkl
                if not model_path.exists():
                    model_path = Path(f"models/lgbm/{symbol}USDT_{tf}_last18m.pkl")
                    metadata_path = Path(f"models/lgbm/{symbol}USDT_{tf}_last18m_metadata.json")
                    is_multiclass = False
                
                # PRIORITY 5: 6-month models
                if not model_path.exists():
                    model_path = Path(f"models/lgbm/{symbol}USDT_{tf}_last6m.pkl")
                    metadata_path = Path(f"models/lgbm/{symbol}USDT_{tf}_last6m_metadata.json")
                    is_multiclass = False
                
                try:
                    if not model_path.exists():
                        logger.warning(f"⚠️ Model not found: {model_path}, {symbol} will use tier model or TA-only")
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
                    
                    # Mark if multiclass
                    self.metadata[key]['is_multiclass'] = is_multiclass
                    
                    # Try to get metrics
                    metrics = self.metadata[key].get('metrics', {})
                    model_type = self.metadata[key].get('model_type', 'binary')
                    n_features = self.metadata[key].get('n_features', 'unknown')
                    
                    if model_type == 'multi-class' or is_multiclass:
                        f1 = metrics.get('f1_macro_mean', 'unknown')
                        logger.info(f"✅ Loaded MULTICLASS model: {key} (F1={f1}, Features={n_features})")
                    else:
                        auc = metrics.get('auc', metrics.get('auc_mean', 'unknown'))
                        logger.info(f"✅ Loaded LGBM model: {key} (AUC={auc}, Features={n_features})")
                    loaded_dedicated += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load {key}: {e}")
                    continue
        
        # 2. Load tier-based models
        for tier, model_key in tier_model_config.items():
            if model_key and model_key not in self.models:
                model_path = Path(f"models/lgbm/{model_key}.pkl")
                metadata_path = Path(f"models/lgbm/{model_key}_metadata.json")
                
                if model_path.exists():
                    try:
                        with open(model_path, 'rb') as f:
                            self.models[model_key] = pickle.load(f)
                        if metadata_path.exists():
                            with open(metadata_path, 'r') as f:
                                self.metadata[model_key] = json.load(f)
                        else:
                            self.metadata[model_key] = {}
                        
                        self._tier_models[tier] = model_key
                        logger.info(f"✅ Loaded tier model: {model_key} for {tier}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to load tier model {model_key}: {e}")
                else:
                    logger.debug(f"Tier model not found: {model_key} (will be trained later)")
        
        loaded_count = len(self.models)
        logger.info(f"Loaded {loaded_dedicated} dedicated + {len(self._tier_models)} tier models = {loaded_count} total")
        
        if loaded_count == 0:
            logger.warning("⚠️ No LightGBM models loaded, will use TA-only scoring")
    
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
            # Note: different training scripts use different keys
            model_features = self.metadata.get(model_key, {}).get('feature_columns', [])
            if not model_features:
                # Multi-class pipeline uses 'selected_features'
                model_features = self.metadata.get(model_key, {}).get('selected_features', [])
            if not model_features:
                # Try alternate key
                model_features = self.metadata.get(model_key, {}).get('features', [])
            if not model_features:
                # Fallback: use feature builder columns (NOT recommended for new models)
                logger.warning(f"No feature_columns in metadata for {model_key}, using all features")
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
            probs = model.predict_proba(latest_features_df)[0]
            
            # Check if multi-class model (3 classes: DOWN, NEUTRAL, UP)
            is_multiclass = self.metadata.get(model_key, {}).get('is_multiclass', False)
            
            if is_multiclass or len(probs) == 3:
                # MULTI-CLASS MODEL: [p_down, p_neutral, p_up]
                p_down = probs[0]
                p_neutral = probs[1] if len(probs) > 2 else 0
                p_up = probs[2] if len(probs) > 2 else probs[1]
                
                # ML Score = 50 + (p_up - p_down) * 50
                # This gives balanced scores: p_up > p_down → bullish, p_down > p_up → bearish
                net_bullish = p_up - p_down
                ml_score = round(50 + net_bullish * 50, 1)
                ml_score = max(0.0, min(100.0, ml_score))  # Clamp 0-100
                
                # Determine direction
                if ml_score >= 65:
                    signal_dir = "LONG"
                elif ml_score >= 55:
                    signal_dir = "LONG_WEAK"
                elif ml_score >= 45:
                    signal_dir = "NEUTRAL"
                elif ml_score >= 35:
                    signal_dir = "SHORT_WEAK"
                else:
                    signal_dir = "SHORT"
                
                # Confidence based on max probability
                max_prob = max(p_down, p_neutral, p_up)
                if max_prob >= 0.6:
                    confidence = "high"
                elif max_prob >= 0.45:
                    confidence = "medium"
                else:
                    confidence = "low"
                
                rationale = f"MULTICLASS {model_key}: p_up={p_up:.3f}, p_down={p_down:.3f} -> {ml_score:.1f}/100 ({signal_dir})"
                
                details = {
                    'model': model_key,
                    'p_up': float(p_up),
                    'p_down': float(p_down),
                    'p_neutral': float(p_neutral),
                    'ml_score': float(ml_score),
                    'signal_direction': signal_dir,
                    'confidence': confidence,
                    'model_type': 'MultiClass-LightGBM',
                    'n_features': len(model_features)
                }
            else:
                # BINARY MODEL: [p_down, p_up]
                p_up = probs[1]
                
                # Original binary scoring logic
                if p_up >= 0.70:
                    ml_score = round(70 + (p_up - 0.70) / 0.30 * 30, 1)
                    signal_dir = "LONG"
                elif p_up >= 0.55:
                    ml_score = round(60 + (p_up - 0.55) / 0.15 * 10, 1)
                    signal_dir = "LONG_WEAK"
                elif p_up >= 0.45:
                    ml_score = round(40 + (p_up - 0.45) / 0.10 * 20, 1)
                    signal_dir = "NEUTRAL"
                elif p_up >= 0.30:
                    ml_score = round(20 + (p_up - 0.30) / 0.15 * 20, 1)
                    signal_dir = "SHORT_WEAK"
                else:
                    ml_score = round((p_up / 0.30) * 20, 1)
                    signal_dir = "SHORT"
                
                confidence = self._calculate_confidence(p_up)
                rationale = f"LGBM {model_key}: p_up={p_up:.3f} -> {ml_score:.1f}/100 ({signal_dir}, confidence={confidence})"
                
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
            
            # Determine if this is a new model (not BTC/ETH/SOL)
            is_new_model = symbol_short not in ['BTC', 'ETH', 'SOL']
            
            # Shadow logging for all predictions
            self._log_shadow_prediction(symbol, model_key, p_up, ml_score, signal_dir, is_new_model)
            
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
    
    def _fallback_score(self, symbol: str) -> Tuple[Optional[float], str, Dict[str, Any]]:
        """
        Return None for coins without ML models - explicit TA-only mode.
        
        This is NOT a fallback score. Returning None signals the composite
        scorer to redistribute ML weight to TA scoring. No fake scores.
        """
        rationale = f"No ML model for {symbol}: TA-only mode active"
        logger.info(f"[ML_ROUTING] {rationale}")
        
        details = {
            'source': 'no_model',
            'ml_available': False,
            'ta_only_mode': True,
            'note': 'ML weight redistributed to TA scoring'
        }
        
        # Return None - composite scorer will handle weight redistribution
        return None, rationale, details


# Backward compatibility - keep old interface
def score_ml(symbol: str, ohlcv_data: Dict) -> Tuple[float, str, Dict]:
    """Legacy interface for ML scoring."""
    scorer = MLScorer()
    return scorer.score(symbol, ohlcv_data)
