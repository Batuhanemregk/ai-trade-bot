"""
ML Feature Engineering Pipeline
Creates features from OHLCV data for ML model training and inference.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger


class FeatureEngineer:
    """
    Creates ML features from OHLCV data.
    
    Features (as per plan):
    - TA: RSI(14), MACD_hist(12,26,9), ATR%, BB_pos
    - Returns: ret_1, ret_4, ret_16
    - Trend: SMA20-SMA50
    - Time: hour_sin/cos, dow_sin/cos
    """
    
    def __init__(self):
        self.feature_columns = []
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create all features from OHLCV DataFrame.
        
        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume]
            
        Returns:
            DataFrame with features added
        """
        df = df.copy()
        
        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        
        logger.info(f"Creating features for {len(df)} bars...")
        
        # 1. TA Features
        df = self._add_ta_features(df)
        
        # 2. Return Features
        df = self._add_return_features(df)
        
        # 3. Trend Features
        df = self._add_trend_features(df)
        
        # 4. Time Features
        df = self._add_time_features(df)
        
        # 5. Volume Features (NEW)
        df = self._add_volume_features(df)
        
        # 6. Market Regime Features (NEW)
        df = self._add_regime_features(df)
        
        # 7. Clean NaN/inf
        df = self._clean_data(df)
        
        # Store feature columns (excluding OHLCV)
        self.feature_columns = [col for col in df.columns 
                                if col not in ['open', 'high', 'low', 'close', 'volume', 'symbol']]
        
        logger.info(f"Created {len(self.feature_columns)} features")
        return df
    
    def _add_ta_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical analysis features."""
        
        # RSI(14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # MACD histogram
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        df['macd_hist'] = macd_line - signal_line
        
        # ATR%
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()
        df['atr_pct'] = (atr / df['close']) * 100
        
        # Bollinger Band Position
        sma20 = df['close'].rolling(window=20).mean()
        std20 = df['close'].rolling(window=20).std()
        bb_upper = sma20 + (2 * std20)
        bb_lower = sma20 - (2 * std20)
        bb_mid = sma20
        df['bb_pos'] = (df['close'] - bb_mid) / (2 * std20)
        
        return df
    
    def _add_return_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add return features."""
        
        # ret_1, ret_4, ret_16 (1-bar, 4-bar, 16-bar returns)
        df['ret_1'] = df['close'].pct_change(1) * 100  # Percentage
        df['ret_4'] = df['close'].pct_change(4) * 100
        df['ret_16'] = df['close'].pct_change(16) * 100
        
        return df
    
    def _add_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trend features."""
        
        # SMA20 - SMA50 (trend direction)
        sma20 = df['close'].rolling(window=20).mean()
        sma50 = df['close'].rolling(window=50).mean()
        df['sma_diff'] = ((sma20 - sma50) / sma50) * 100  # Percentage
        
        # SMA ratio (alternative)
        df['sma_ratio'] = sma20 / sma50
        
        return df
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add cyclical time features."""
        
        # Hour (0-23) -> sin/cos encoding
        hour = df.index.hour
        df['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        df['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        
        # Day of week (0-6) -> sin/cos encoding
        dow = df.index.dayofweek
        df['dow_sin'] = np.sin(2 * np.pi * dow / 7)
        df['dow_cos'] = np.cos(2 * np.pi * dow / 7)
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean NaN and inf values."""
        
        # Replace inf with NaN
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # Forward fill NaN (use previous valid value)
        df = df.ffill()
        
        # Backward fill remaining NaN (for first rows)
        df = df.bfill()
        
        # If still NaN, fill with 0
        df = df.fillna(0)
        
        return df
    
    def create_label(self, df: pd.DataFrame, forward_bars: int = 1) -> pd.DataFrame:
        """
        Create binary label: y=1 if close_{t+forward_bars} > close_t, else 0.
        
        Args:
            df: DataFrame with 'close' column
            forward_bars: How many bars ahead to predict (default: 1)
            
        Returns:
            DataFrame with 'label' column added
        """
        df = df.copy()
        
        # Shift close price backwards to get future price
        future_close = df['close'].shift(-forward_bars)
        
        # Label: 1 if price goes up, 0 if down/flat
        df['label'] = (future_close > df['close']).astype(int)
        
        # Drop last N rows (no future data)
        df = df.iloc[:-forward_bars]
        
        logger.info(f"Created labels: {df['label'].sum()} up ({df['label'].sum()/len(df)*100:.1f}%), {len(df)-df['label'].sum()} down")
        
        return df
    
    def get_feature_columns(self) -> list:
        """Get list of feature column names."""
        return self.feature_columns
    
    def prepare_for_training(self, df: pd.DataFrame, forward_bars: int = 1) -> tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data for training: features + labels.
        
        Returns:
            X: Features DataFrame
            y: Labels Series
        """
        # Create features
        df = self.create_features(df)
        
        # Create labels
        df = self.create_label(df, forward_bars)
        
        # Split X, y - exclude timestamp and other non-feature columns
        feature_cols = [col for col in self.feature_columns if col not in ['timestamp', 'timeframe']]
        X = df[feature_cols]
        y = df['label']
        
        logger.info(f"Training data: {len(X)} samples, {len(feature_cols)} features")
        logger.info(f"Class distribution: Up={y.sum()} ({y.sum()/len(y)*100:.1f}%), Down={len(y)-y.sum()} ({(len(y)-y.sum())/len(y)*100:.1f}%)")
        
        return X, y
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        # Volume SMA ratio
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_sma_ratio'] = df['volume'] / df['volume_sma_20']
        
        # Volume momentum
        df['volume_momentum'] = df['volume'].pct_change(5)
        
        # Volume volatility
        df['volume_volatility'] = df['volume'].rolling(10).std()
        
        return df
    
    def _add_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market regime features."""
        # Price momentum
        df['price_momentum_5'] = df['close'].pct_change(5)
        df['price_momentum_20'] = df['close'].pct_change(20)
        
        # Volatility regime
        df['volatility_20'] = df['close'].rolling(20).std()
        df['volatility_regime'] = (df['volatility_20'] > df['volatility_20'].rolling(50).mean()).astype(int)
        
        # Trend strength
        df['trend_strength'] = abs(df['close'].rolling(20).mean() - df['close'].rolling(50).mean()) / df['close']
        
        return df

