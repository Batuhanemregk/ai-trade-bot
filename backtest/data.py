"""
Backtest Data Loader.

Loads OHLCV data from CSV files with:
- Date filtering
- 15m → 1h aggregation
- Multi-timeframe support
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from loguru import logger


class BacktestDataLoader:
    """
    Loads and manages OHLCV data for backtesting.
    
    Features:
    - Load from CSV files
    - Automatic timestamp parsing (ISO or Unix ms)
    - Date range filtering
    - 15m → 1h aggregation for HTF filters
    """
    
    def __init__(self, data_dir: str = "data/backtest_ohlcv"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Cached data
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def load_ohlcv(
        self,
        symbol: str,
        timeframe: str = "15m",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Load OHLCV data from CSV file.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC-USDT-SWAP')
            timeframe: Timeframe (e.g., '15m', '1h')
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        cache_key = f"{symbol}_{timeframe}"
        
        if cache_key in self._cache:
            df = self._cache[cache_key].copy()
        else:
            # Build file path
            file_path = self.data_dir / f"{symbol}_{timeframe}.csv"
            
            if not file_path.exists():
                # Try alternative naming conventions
                alt_paths = [
                    self.data_dir / f"{symbol.replace('-SWAP', '')}_{timeframe}.csv",
                    self.data_dir / f"{symbol.split('-')[0]}_{timeframe}.csv",
                    self.data_dir / f"{symbol}_{timeframe.lower()}.csv",
                ]
                
                for alt in alt_paths:
                    if alt.exists():
                        file_path = alt
                        break
                else:
                    # If 1h missing but 15m exists, aggregate
                    if timeframe == '1h':
                        df_15m = self.load_ohlcv(symbol, '15m', start_date, end_date)
                        if not df_15m.empty:
                            logger.info(f"[DATA] Aggregating 15m → 1h for {symbol}")
                            return self._aggregate_to_1h(df_15m)
                    
                    raise FileNotFoundError(
                        f"OHLCV file not found: {file_path}\n"
                        f"Please create CSV with columns: timestamp,open,high,low,close,volume"
                    )
            
            logger.info(f"[DATA] Loading {file_path}")
            df = self._load_csv(file_path)
            self._cache[cache_key] = df.copy()
        
        # Apply date filters
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        logger.info(f"[DATA] Loaded {len(df)} bars for {symbol} {timeframe} "
                   f"({df.index.min()} to {df.index.max()})")
        
        return df
    
    def _load_csv(self, file_path: Path) -> pd.DataFrame:
        """Load and parse CSV file."""
        df = pd.read_csv(file_path)
        
        # Validate columns
        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        # Accept case-insensitive
        df.columns = df.columns.str.lower()
        
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns in {file_path}: {missing}")
        
        # Parse timestamp
        df = self._parse_timestamp(df)
        
        # Set index
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        
        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop NaN rows
        df.dropna(inplace=True)
        
        return df
    
    def _parse_timestamp(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse timestamp column (ISO or Unix ms)."""
        ts_col = df['timestamp']
        
        # Check if numeric (Unix timestamp)
        if pd.api.types.is_numeric_dtype(ts_col):
            # Assume milliseconds if > 1e12
            if ts_col.iloc[0] > 1e12:
                df['timestamp'] = pd.to_datetime(ts_col, unit='ms')
            else:
                df['timestamp'] = pd.to_datetime(ts_col, unit='s')
        else:
            # Try ISO parsing with utc=True for timezone-aware strings
            df['timestamp'] = pd.to_datetime(ts_col, utc=True)
        
        # Convert to timezone-naive for consistent comparison
        if df['timestamp'].dt.tz is not None:
            df['timestamp'] = df['timestamp'].dt.tz_localize(None)
        
        return df
    
    def _aggregate_to_1h(self, df_15m: pd.DataFrame) -> pd.DataFrame:
        """Aggregate 15m data to 1h."""
        df_1h = df_15m.resample('1H').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        logger.info(f"[DATA] Aggregated to {len(df_1h)} 1h bars")
        return df_1h
    
    def get_multi_timeframe_slice(
        self,
        symbol: str,
        current_idx: int,
        df_15m: pd.DataFrame,
        df_1h: pd.DataFrame = None,
        lookback_15m: int = 200,
        lookback_1h: int = 100
    ) -> Dict[str, pd.DataFrame]:
        """
        Get OHLCV slices for multiple timeframes at a given bar index.
        
        Returns:
            Dict with 'main' (15m) and 'trend' (1h) DataFrames
        """
        result = {}
        
        # 15m slice (main)
        start_idx = max(0, current_idx - lookback_15m)
        result['main'] = df_15m.iloc[start_idx:current_idx + 1].copy()
        
        # 1h slice (trend)
        if df_1h is not None and not df_1h.empty:
            current_time = df_15m.index[current_idx]
            # Get 1h bars up to current time
            trend_df = df_1h[df_1h.index <= current_time].tail(lookback_1h)
            result['trend'] = trend_df.copy()
        
        return result
    
    def get_bar_at_index(self, df: pd.DataFrame, idx: int) -> pd.Series:
        """Get a single bar at index."""
        return df.iloc[idx]
    
    def list_available_files(self) -> list:
        """List available OHLCV files."""
        files = list(self.data_dir.glob("*.csv"))
        return [f.name for f in files]
    
    def get_date_range(self, df: pd.DataFrame) -> Tuple[datetime, datetime]:
        """Get date range of a DataFrame."""
        return df.index.min(), df.index.max()


# Helper function for easy import
def load_backtest_data(
    symbol: str,
    timeframe: str = "15m",
    start_date: str = None,
    end_date: str = None,
    data_dir: str = "data/backtest_ohlcv"
) -> pd.DataFrame:
    """
    Convenience function to load backtest data.
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)
        data_dir: Data directory
        
    Returns:
        DataFrame with OHLCV data
    """
    loader = BacktestDataLoader(data_dir)
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    return loader.load_ohlcv(symbol, timeframe, start_dt, end_dt)
