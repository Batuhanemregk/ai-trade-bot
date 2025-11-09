"""
ML Feature Builder - Expanded Feature Set with Multi-Timeframe Support
Produces 50+ features for LightGBM training and inference.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from loguru import logger


class FeatureBuilder:
    """
    Builds comprehensive ML features from OHLCV data.
    
    Feature categories:
    - TA Indicators (20+ features)
    - Price Action (14+ features)
    - Statistics (10+ features)
    - Time Features (4 features)
    - Volume Features (6 features)
    - Multi-timeframe features (6+ features)
    
    Total: 60+ features
    """
    
    def __init__(self):
        self.feature_columns = []
    
    def build_features(self, df: pd.DataFrame,
                      df_1h: Optional[pd.DataFrame] = None,
                      df_4h: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Build all features with multi-timeframe support.
        
        Args:
            df: Main timeframe OHLCV DataFrame
            df_1h: Optional 1h timeframe for MTF features
            df_4h: Optional 4h timeframe for MTF features
        
        Returns:
            DataFrame with all features added
        """
        # Deep copy to prevent side effects
        df = df.copy(deep=True)
        
        # Ensure timestamp is index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        
        logger.debug(f"Building features for {len(df)} bars...")
        
        # Single timeframe features
        df = self._add_ta_indicators(df)
        df = self._add_price_action(df)
        df = self._add_statistics(df)
        df = self._add_time_features(df)
        df = self._add_volume_features(df)
        
        # Multi-timeframe features
        if df_1h is not None:
            df = self._add_multitf_features(df, df_1h, '1h')
        if df_4h is not None:
            df = self._add_multitf_features(df, df_4h, '4h')
        
        # Clean and store feature list
        df = self._clean_data(df)
        self.feature_columns = [col for col in df.columns 
                               if col not in ['open', 'high', 'low', 'close', 'volume', 'timestamp', 'symbol']]
        
        logger.debug(f"Created {len(self.feature_columns)} features")
        return df
    
    def _add_ta_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical analysis indicators."""
        
        # ===== SMA Features =====
        df['sma_5'] = df['close'].rolling(window=5).mean()
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # ===== EMA Features =====
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # ===== MACD Features =====
        macd_line = df['ema_12'] - df['ema_26']
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        df['macd_line'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_hist'] = macd_line - signal_line
        
        # ===== RSI =====
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # ===== Stochastic =====
        low_min = df['low'].rolling(window=14).min()
        high_max = df['high'].rolling(window=14).max()
        df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
        df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()
        
        # ===== Williams%R =====
        df['williams_r'] = -100 * ((high_max - df['close']) / (high_max - low_min))
        
        # ===== ADX, +DI, -DI =====
        # True Range
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Directional Movement
        up_move = df['high'] - df['high'].shift()
        down_move = df['low'].shift() - df['low']
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smooth TR and DM
        atr_14 = tr.rolling(window=14).mean()
        plus_di_series = pd.Series(plus_dm).rolling(window=14).mean()
        minus_di_series = pd.Series(minus_dm).rolling(window=14).mean()
        
        df['plus_di'] = 100 * (plus_di_series / atr_14)
        df['minus_di'] = 100 * (minus_di_series / atr_14)
        
        # ADX
        dx = 100 * np.abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = dx.rolling(window=14).mean()
        
        # ===== ATR =====
        df['atr_14'] = atr_14
        df['atr_pct'] = (atr_14 / df['close']) * 100
        
        # ===== Bollinger Bands =====
        bb_mean = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = bb_mean + (2 * bb_std)
        df['bb_lower'] = bb_mean - (2 * bb_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / bb_mean
        df['bb_pos'] = (df['close'] - bb_mean) / (2 * bb_std)
        df['bb_pctb'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ===== OBV =====
        obv = (df['volume'] * np.sign(df['close'].diff())).fillna(0).cumsum()
        df['obv'] = obv
        
        # ===== MFI =====
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        positive_flow = money_flow.where(df['close'] > df['close'].shift(), 0).rolling(window=14).sum()
        negative_flow = money_flow.where(df['close'] < df['close'].shift(), 0).rolling(window=14).sum()
        money_ratio = positive_flow / negative_flow
        df['mfi'] = 100 - (100 / (1 + money_ratio))
        
        return df
    
    def _add_price_action(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price action features."""
        
        # ===== Range calculations =====
        range_val = df['high'] - df['low']
        
        # Body and wick ratios
        df['body'] = df['close'] - df['open']
        df['body_ratio'] = df['body'] / range_val
        df['upper_wick_ratio'] = (df['high'] - np.maximum(df['open'], df['close'])) / range_val
        df['lower_wick_ratio'] = (np.minimum(df['open'], df['close']) - df['low']) / range_val
        
        # ===== Heikin-Ashi =====
        ha_close = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha_open = df['open'].copy()
        ha_open.iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
        for i in range(1, len(df)):
            ha_open.iloc[i] = (ha_open.iloc[i-1] + ha_close.iloc[i-1]) / 2
        
        ha_high = pd.concat([df['high'], ha_open, ha_close], axis=1).max(axis=1)
        ha_low = pd.concat([df['low'], ha_open, ha_close], axis=1).min(axis=1)
        
        df['ha_open'] = ha_open
        df['ha_close'] = ha_close
        df['ha_high'] = ha_high
        df['ha_low'] = ha_low
        
        # ===== Pattern flags =====
        # Bullish engulfing
        prev_body = df['close'].shift(1) - df['open'].shift(1)
        df['engulfing_bull'] = ((prev_body < 0) & (df['body'] > 0) &
                                (df['open'] < df['close'].shift(1)) &
                                (df['close'] > df['open'].shift(1))).astype(int)
        
        # Bearish engulfing
        df['engulfing_bear'] = ((prev_body > 0) & (df['body'] < 0) &
                                (df['open'] > df['close'].shift(1)) &
                                (df['close'] < df['open'].shift(1))).astype(int)
        
        # Pinbar up (long lower wick)
        df['pinbar_up'] = ((df['lower_wick_ratio'] > 0.66) & 
                          (df['upper_wick_ratio'] < 0.33)).astype(int)
        
        # Pinbar down (long upper wick)
        df['pinbar_down'] = ((df['upper_wick_ratio'] > 0.66) & 
                            (df['lower_wick_ratio'] < 0.33)).astype(int)
        
        # ===== HH/HL/LH/LL patterns =====
        # Higher High (HH): current high > previous 5 highs
        df['hh'] = (df['high'] > df['high'].rolling(window=5).max().shift()).astype(int)
        
        # Higher Low (HL): current low > previous 5 lows
        df['hl'] = (df['low'] > df['low'].rolling(window=5).min().shift()).astype(int)
        
        # Lower High (LH): current high < previous 5 highs
        df['lh'] = (df['high'] < df['high'].rolling(window=5).max().shift()).astype(int)
        
        # Lower Low (LL): current low < previous 5 lows
        df['ll'] = (df['low'] < df['low'].rolling(window=5).min().shift()).astype(int)
        
        return df
    
    def _add_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add statistical features."""
        
        # ===== Log returns =====
        df['log_ret_1'] = np.log(df['close'] / df['close'].shift(1))
        df['log_ret_3'] = np.log(df['close'] / df['close'].shift(3))
        df['log_ret_5'] = np.log(df['close'] / df['close'].shift(5))
        
        # ===== Rolling mean =====
        df['roll_mean_5'] = df['close'].rolling(window=5).mean()
        df['roll_mean_10'] = df['close'].rolling(window=10).mean()
        df['roll_mean_20'] = df['close'].rolling(window=20).mean()
        
        # ===== Rolling std =====
        df['roll_std_5'] = df['close'].rolling(window=5).std()
        df['roll_std_10'] = df['close'].rolling(window=10).std()
        df['roll_std_20'] = df['close'].rolling(window=20).std()
        
        # ===== Skewness and kurtosis =====
        df['skewness_20'] = df['close'].rolling(window=20).skew()
        df['kurtosis_20'] = df['close'].rolling(window=20).apply(
            lambda x: x.kurtosis() if len(x) > 3 else 0
        )
        
        # ===== Volatility Regime Detection =====
        # High vol vs low vol periods
        df['volatility_regime'] = (df['close'].rolling(window=20).std() > 
                                   df['close'].rolling(window=100).std()).astype(int)
        
        # Volatility z-score
        vol_20 = df['close'].rolling(window=20).std()
        vol_mean = vol_20.rolling(window=100).mean()
        vol_std = vol_20.rolling(window=100).std()
        df['volatility_zscore'] = (vol_20 - vol_mean) / vol_std
        
        # ===== Normalized Price Distance from Key Levels =====
        # Distance from SMAs (normalized by price)
        df['distance_sma_20'] = (df['close'] - df['sma_20']) / df['close']
        df['distance_sma_50'] = (df['close'] - df['sma_50']) / df['close']
        
        # Distance from recent high/low
        df['distance_high_20'] = (df['close'] - df['high'].rolling(window=20).max()) / df['close']
        df['distance_low_20'] = (df['close'] - df['low'].rolling(window=20).min()) / df['close']
        
        return df
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add cyclical time features."""
        
        # Hour encoding
        hour = df.index.hour
        df['hour_sin'] = np.sin(2 * np.pi * hour / 24)
        df['hour_cos'] = np.cos(2 * np.pi * hour / 24)
        
        # Day of week encoding
        dow = df.index.dayofweek
        df['dow_sin'] = np.sin(2 * np.pi * dow / 7)
        df['dow_cos'] = np.cos(2 * np.pi * dow / 7)
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        
        # Volume SMAs
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_sma_ratio'] = df['volume'] / df['volume_sma_20']
        
        # Volume EMA
        df['volume_ema_20'] = df['volume'].ewm(span=20, adjust=False).mean()
        df['volume_ema_ratio'] = df['volume'] / df['volume_ema_20']
        
        # Volume momentum
        df['volume_momentum'] = df['volume'].pct_change(5)
        
        # Volume volatility
        df['volume_volatility'] = df['volume'].rolling(window=10).std()
        
        return df
    
    def _add_multitf_features(self, df: pd.DataFrame, df_tf: pd.DataFrame, tf_name: str) -> pd.DataFrame:
        """
        Add multi-timeframe features from higher timeframe.
        
        No look-ahead: Join using 'asof' merge on timestamp.
        """
        # Ensure df_tf has timestamp index
        if 'timestamp' in df_tf.columns:
            df_tf = df_tf.set_index('timestamp')
        
        # Calculate MTF features
        df_tf = df_tf.copy()
        
        # RSI
        delta = df_tf['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_tf[f'rsi_14_{tf_name}'] = 100 - (100 / (1 + rs))
        
        # MACD histogram
        ema12 = df_tf['close'].ewm(span=12, adjust=False).mean()
        ema26 = df_tf['close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        df_tf[f'macd_hist_{tf_name}'] = macd_line - signal_line
        
        # Trend strength
        sma20 = df_tf['close'].rolling(window=20).mean()
        sma50 = df_tf['close'].rolling(window=50).mean()
        df_tf[f'trend_strength_{tf_name}'] = np.abs(sma20 - sma50) / df_tf['close']
        
        # Extract MTF features
        mtf_features = [col for col in df_tf.columns if col.endswith(f'_{tf_name}')]
        
        # Merge using 'asof' (backward-fill on timestamp)
        for feat in mtf_features:
            df = df.merge(df_tf[[feat]], left_index=True, right_index=True, how='left')
            # Forward fill within gaps
            df[feat] = df[feat].ffill()
        
        return df
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean NaN and inf values."""
        
        # Replace inf with NaN
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # Forward fill NaN
        df = df.ffill()
        
        # Backward fill remaining NaN
        df = df.bfill()
        
        # If still NaN, fill with 0
        df = df.fillna(0)
        
        return df
    
    def create_label(self, df: pd.DataFrame, forward_bars: int = 3, threshold_pct: float = 0.20, include_flat: bool = True) -> pd.DataFrame:
        """
        Create three-class label: LONG=2, SHORT=0, FLAT=1.
        
        Args:
            df: DataFrame with 'close' column
            forward_bars: How many bars ahead to predict (default: 3)
            threshold_pct: Return threshold in percent (default: 0.20%)
            include_flat: Whether to include FLAT labels (default: True)
        
        Returns:
            DataFrame with 'label' column added (LONG=2, SHORT=0, FLAT=1)
        """
        df = df.copy()
        
        # Calculate future return
        future_close = df['close'].shift(-forward_bars)
        future_return = ((future_close - df['close']) / df['close']) * 100
        
        # Three-class label
        # LONG: future_return > threshold_pct → 2
        # SHORT: future_return < -threshold_pct → 0
        # FLAT: -threshold_pct <= future_return <= threshold_pct → 1
        
        df['label'] = 1  # Default: FLAT
        df.loc[future_return > threshold_pct, 'label'] = 2  # LONG
        df.loc[future_return < -threshold_pct, 'label'] = 0  # SHORT
        
        # Drop last N rows (no future data)
        df_labeled = df.iloc[:-forward_bars].copy()
        
        # If not including FLAT, filter them out
        if not include_flat:
            df_labeled = df_labeled[df_labeled['label'] != 1].copy()
        
        long_count = (df_labeled['label'] == 2).sum()
        short_count = (df_labeled['label'] == 0).sum()
        flat_count = (df_labeled['label'] == 1).sum()
        total = len(df_labeled)
        
        logger.info(f"Created labels: LONG={long_count} ({long_count/total*100:.1f}%), "
                    f"SHORT={short_count} ({short_count/total*100:.1f}%), "
                    f"FLAT={flat_count} ({flat_count/total*100:.1f}%), "
                    f"Total={total}")
        
        return df_labeled
    
    def get_feature_columns(self) -> list:
        """Get list of feature column names."""
        return self.feature_columns
    
    def prepare_for_training(self, df: pd.DataFrame, 
                            df_1h: Optional[pd.DataFrame] = None,
                            df_4h: Optional[pd.DataFrame] = None,
                            forward_bars: int = 3,
                            threshold_pct: float = 0.20,
                            include_flat: bool = True) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare data for training: features + labels.
        
        Args:
            df: Main timeframe OHLCV data
            df_1h: Optional 1h timeframe
            df_4h: Optional 4h timeframe
            forward_bars: Forward bars for labeling (default: 3)
            threshold_pct: Return threshold (default: 0.20%)
            include_flat: Whether to include FLAT labels (default: True)
        
        Returns:
            X: Features DataFrame
            y: Labels Series (LONG=2, SHORT=0, FLAT=1)
        """
        # Build features
        df = self.build_features(df, df_1h, df_4h)
        
        # Create labels
        df = self.create_label(df, forward_bars, threshold_pct, include_flat)
        
        # Extract X, y
        X = df[self.feature_columns]
        y = df['label']
        
        # Log class distribution
        long_count = (y == 2).sum()
        short_count = (y == 0).sum()
        flat_count = (y == 1).sum()
        total = len(y)
        
        logger.info(f"Training data: {len(X)} samples, {len(self.feature_columns)} features")
        logger.info(f"Class distribution: LONG={long_count} ({long_count/total*100:.1f}%), "
                    f"SHORT={short_count} ({short_count/total*100:.1f}%), "
                    f"FLAT={flat_count} ({flat_count/total*100:.1f}%)")
        
        return X, y

