"""
Model Performance Tester
Tests ML model performance and compares with fallback.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple
from loguru import logger

from ml.model_version_manager import MLModelVersionManager
from ml.feature_engineering import FeatureEngineer
from scoring.ml_scorer import MLScorer


class ModelPerformanceTester:
    """Tests ML model performance."""
    
    def __init__(self):
        self.version_manager = MLModelVersionManager()
        self.feature_engineer = FeatureEngineer()
        self.ml_scorer = MLScorer()
    
    def test_model_performance(self, symbol: str, ohlcv_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Test model performance for a symbol."""
        results = {
            "symbol": symbol,
            "timestamp": pd.Timestamp.now().isoformat(),
            "tests": {}
        }
        
        # Test 1: Current model performance
        try:
            ml_score, rationale, details = self.ml_scorer.score(symbol, ohlcv_data)
            results["tests"]["current_model"] = {
                "score": ml_score,
                "rationale": rationale,
                "details": details,
                "status": "success"
            }
        except Exception as e:
            results["tests"]["current_model"] = {
                "error": str(e),
                "status": "failed"
            }
        
        # Test 2: Fallback performance
        try:
            fallback_score, fallback_rationale, fallback_details = self.ml_scorer._fallback_score(symbol)
            results["tests"]["fallback"] = {
                "score": fallback_score,
                "rationale": fallback_rationale,
                "details": fallback_details,
                "status": "success"
            }
        except Exception as e:
            results["tests"]["fallback"] = {
                "error": str(e),
                "status": "failed"
            }
        
        # Test 3: Feature engineering
        try:
            df_15m = ohlcv_data.get('15m', pd.DataFrame())
            if not df_15m.empty:
                features_df = self.feature_engineer.create_features(df_15m)
                results["tests"]["feature_engineering"] = {
                    "features_created": len(self.feature_engineer.feature_columns),
                    "feature_names": self.feature_engineer.feature_columns,
                    "data_shape": features_df.shape,
                    "status": "success"
                }
            else:
                results["tests"]["feature_engineering"] = {
                    "error": "No 15m data available",
                    "status": "failed"
                }
        except Exception as e:
            results["tests"]["feature_engineering"] = {
                "error": str(e),
                "status": "failed"
            }
        
        return results
    
    def run_comprehensive_test(self, symbols: list) -> Dict[str, Any]:
        """Run comprehensive test on multiple symbols."""
        logger.info(f"Running comprehensive ML test on {len(symbols)} symbols")
        
        all_results = {
            "test_timestamp": pd.Timestamp.now().isoformat(),
            "symbols_tested": symbols,
            "results": {}
        }
        
        for symbol in symbols:
            logger.info(f"Testing {symbol}...")
            # This would need actual OHLCV data
            # For now, just test the structure
            all_results["results"][symbol] = {
                "status": "pending_data",
                "note": "Requires actual OHLCV data to test"
            }
        
        return all_results


def test_ml_system():
    """Quick test of ML system."""
    tester = ModelPerformanceTester()
    
    # Test version manager
    logger.info("Testing Model Version Manager...")
    versions = tester.version_manager.available_versions
    logger.info(f"Available versions: {versions}")
    
    # Test feature engineering
    logger.info("Testing Feature Engineering...")
    # Create dummy data for testing
    dummy_data = pd.DataFrame({
        'timestamp': pd.date_range('2025-01-01', periods=100, freq='15T'),
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 105,
        'low': np.random.randn(100).cumsum() + 95,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    features_df = tester.feature_engineer.create_features(dummy_data)
    logger.info(f"Created {len(tester.feature_engineer.feature_columns)} features")
    
    return True


if __name__ == "__main__":
    test_ml_system()
