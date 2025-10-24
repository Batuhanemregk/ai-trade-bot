"""
ML Scorer - Real Machine Learning Predictions
Uses trained RandomForest model for direction probability scoring.
"""

import pickle
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from loguru import logger

from ml.feature_engineering import FeatureEngineer


class MLScorer:
    """
    ML-based scoring using trained RandomForest model.
    
    - Loads model from models/rf_v1.pkl
    - Generates p_up (probability of price going up)
    - Converts to score: 0-100 scale
    - Falls back to neutral if model unavailable
    """
    
    def __init__(self):
        self.model = None
        self.model_version = None
        self.metadata = {}
        self.feature_engineer = None  # Will be created when needed
        self._load_model()
    
    def _load_model(self):
        """Load trained ML model if available."""
        try:
            # Use Model Version Manager to get active model
            from ml.model_version_manager import MLModelVersionManager
            manager = MLModelVersionManager()
            
            # Get active model
            active_version = manager.get_active_model_version()
            if not active_version:
                logger.info("ℹ️ No active ML model found, will use fallback scoring")
                self.model = None
                return
            
            # Load active model
            self.model = manager.get_active_model()
            if not self.model:
                logger.info("ℹ️ Active ML model could not be loaded, will use fallback scoring")
                self.model = None
                return
            
            # Get metadata
            self.metadata = manager.get_model_metadata(active_version)
            self.model_version = active_version
            
            logger.info(f"✅ ML model loaded: {self.model_version}")
            logger.info(f"   Features: {self.metadata.get('n_features', 'unknown')}")
            logger.info(f"   AUC: {self.metadata.get('metrics', {}).get('auc', 'unknown')}")
            logger.info(f"   Calibrated: {self.metadata.get('calibrated', False)}")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to load ML model: {e}")
            self.model = None
    
    def score(self, symbol: str, ohlcv_bundle: Dict[str, pd.DataFrame]) -> Tuple[float, str, Dict[str, Any]]:
        """
        Compute ML score for a symbol.
        
        Args:
            symbol: Trading symbol
            ohlcv_bundle: Dictionary with timeframes as keys and DataFrames as values
            
        Returns:
            Tuple of (score: float, rationale: str, details: dict)
            - score: 0-100 (0=strong down, 50=neutral, 100=strong up)
            - rationale: Explanation
            - details: Additional info (p_up, confidence, source)
        """
        try:
            # If no model, use fallback
            if self.model is None:
                return self._fallback_score(symbol)
            
            # Initialize feature engineer if not done yet
            if self.feature_engineer is None:
                self.feature_engineer = FeatureEngineer()
            
            # Get main timeframe data (use 'is None' to avoid DataFrame ambiguity)
            main_df = ohlcv_bundle.get('main')
            if main_df is None:
                main_df = ohlcv_bundle.get('15m')
            if main_df is None:
                logger.warning(f"No data for ML scoring: {symbol}")
                return self._fallback_score(symbol)
            if len(main_df) == 0:
                logger.warning(f"Empty data for ML scoring: {symbol}")
                return self._fallback_score(symbol)
            
            # Create features (same pipeline as training)
            df_with_features = self.feature_engineer.create_features(main_df)
            
            # Get latest row features
            if len(df_with_features) == 0:
                return self._fallback_score(symbol)
            
            # Get feature columns AFTER creating features (they're set during create_features)
            feature_cols = self.feature_engineer.get_feature_columns()
            if feature_cols is None or len(feature_cols) == 0:
                logger.warning(f"No feature columns available for {symbol}")
                return self._fallback_score(symbol)
            
            latest_features = df_with_features[feature_cols].iloc[-1:]
            
            # Ensure no NaN/inf in features
            has_nan = latest_features.isnull().values.any()
            has_inf = np.isinf(latest_features.values).any()
            if has_nan or has_inf:
                logger.warning(f"Invalid features for {symbol}, using fallback")
                return self._fallback_score(symbol)
            
            # Predict probability
            p_up = self.model.predict_proba(latest_features)[0, 1]  # Probability of UP
            
            # Convert to 0-100 score
            ml_score = round(p_up * 100, 1)
            
            # Determine confidence
            confidence = self._calculate_confidence(p_up)
            
            # Rationale
            rationale = f"ML prediction: {p_up:.3f} -> {ml_score:.1f}/100 (confidence={confidence})"
            
            # Details
            details = {
                'source': self.model_version,
                'p_up': float(p_up),
                'p_down': float(1 - p_up),
                'ml_score': float(ml_score),
                'confidence': confidence,
                'model_type': 'RandomForest',
                'calibrated': self.metadata.get('calibrated', False)
            }
            
            logger.debug(f"✅ ML scoring for {symbol}: p_up={p_up:.3f}, score={ml_score:.1f}")
            
            return ml_score, rationale, details
            
        except Exception as e:
            logger.error(f"❌ ML scoring failed for {symbol}: {e}")
            return self._fallback_score(symbol)
    
    def _calculate_confidence(self, p_up: float) -> str:
        """
        Determine confidence level from probability.
        
        As per plan:
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
