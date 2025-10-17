"""
OHLCV Data Loader for Backtesting.
Loads historical price data from CSV files.
"""

import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class OHLCVDataLoader:
    """
    Loads OHLCV (Open, High, Low, Close, Volume) data from CSV files.
    
    Expected CSV format:
    timestamp,open,high,low,close,volume
    2024-01-01 00:00:00,42000.0,42100.0,41900.0,42050.0,1000.5
    """
    
    def __init__(self, data_dir: str = "backtests/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"OHLCVDataLoader initialized: {self.data_dir}")
    
    def load_csv(self, file_path: str, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        Load OHLCV data from a CSV file.
        
        Args:
            file_path: Path to CSV file (relative to data_dir or absolute)
            symbol: Symbol name (optional, extracted from filename if not provided)
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If CSV format is invalid
        """
        # Resolve file path
        path = Path(file_path)
        if not path.is_absolute():
            path = self.data_dir / file_path
        
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        
        logger.info(f"Loading data from {path}")
        
        try:
            # Load CSV
            df = pd.read_csv(path)
            
            # Validate columns
            required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Parse timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # Extract symbol from filename if not provided
            if symbol is None:
                symbol = path.stem.split('_')[0]  # e.g., "BTC-USDT_15m.csv" -> "BTC-USDT"
            
            df['symbol'] = symbol
            
            # Data quality checks
            self._validate_data(df)
            
            logger.info(f"Loaded {len(df)} bars for {symbol} ({df['timestamp'].min()} to {df['timestamp'].max()})")
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load data from {path}: {e}")
            raise
    
    def _validate_data(self, df: pd.DataFrame):
        """Validate data quality."""
        # Check for missing values
        if df[['open', 'high', 'low', 'close', 'volume']].isnull().any().any():
            logger.warning("Data contains missing values")
        
        # Check for negative prices
        if (df[['open', 'high', 'low', 'close']] < 0).any().any():
            raise ValueError("Data contains negative prices")
        
        # Check for zero volume
        if (df['volume'] == 0).sum() > len(df) * 0.1:  # More than 10% zero volume
            logger.warning("Data contains many zero-volume bars")
        
        # Check high >= low
        if (df['high'] < df['low']).any():
            raise ValueError("Data contains bars where high < low")
        
        # Check OHLC consistency
        invalid_ohlc = (
            (df['open'] > df['high']) | 
            (df['open'] < df['low']) | 
            (df['close'] > df['high']) | 
            (df['close'] < df['low'])
        )
        if invalid_ohlc.any():
            logger.warning(f"Data contains {invalid_ohlc.sum()} bars with invalid OHLC relationships")
    
    def load_multiple(self, file_patterns: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Load multiple CSV files.
        
        Args:
            file_patterns: List of file paths or glob patterns
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        data = {}
        
        for pattern in file_patterns:
            # Handle glob patterns
            if '*' in pattern:
                files = list(self.data_dir.glob(pattern))
            else:
                files = [Path(pattern) if Path(pattern).is_absolute() else self.data_dir / pattern]
            
            for file_path in files:
                if file_path.exists():
                    try:
                        symbol = file_path.stem.split('_')[0]
                        df = self.load_csv(str(file_path), symbol=symbol)
                        data[symbol] = df
                    except Exception as e:
                        logger.error(f"Failed to load {file_path}: {e}")
        
        logger.info(f"Loaded data for {len(data)} symbols")
        return data
    
    def create_sample_data(
        self, 
        symbol: str = "BTC-USDT", 
        start_price: float = 40000.0,
        num_bars: int = 1000,
        timeframe: str = "15m"
    ) -> pd.DataFrame:
        """
        Create sample OHLCV data for testing.
        
        Args:
            symbol: Symbol name
            start_price: Starting price
            num_bars: Number of bars to generate
            timeframe: Timeframe (e.g., "15m", "1h")
            
        Returns:
            DataFrame with sample data
        """
        import numpy as np
        
        logger.info(f"Generating {num_bars} bars of sample data for {symbol}")
        
        # Generate timestamps
        freq_map = {'15m': '15min', '1h': '1H', '4h': '4H', '1d': '1D'}
        freq = freq_map.get(timeframe, '15min')
        timestamps = pd.date_range(
            start='2024-01-01',
            periods=num_bars,
            freq=freq,
            tz='UTC'
        )
        
        # Generate price data (random walk with trend and volatility)
        np.random.seed(42)
        returns = np.random.normal(0.0001, 0.02, num_bars)  # Small upward drift, 2% volatility
        prices = start_price * np.exp(np.cumsum(returns))
        
        # Generate OHLCV
        data = []
        for i, (ts, close) in enumerate(zip(timestamps, prices)):
            volatility = close * 0.005  # 0.5% intrabar volatility
            
            open_price = prices[i-1] if i > 0 else close
            high = close + np.random.uniform(0, volatility)
            low = close - np.random.uniform(0, volatility)
            
            # Ensure OHLC consistency
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            volume = np.random.uniform(100, 1000)
            
            data.append({
                'timestamp': ts,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'symbol': symbol
            })
        
        df = pd.DataFrame(data)
        
        # Save to file
        output_file = self.data_dir / f"{symbol}_{timeframe}_sample.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"Sample data saved to {output_file}")
        
        return df


# Example usage
if __name__ == "__main__":
    loader = OHLCVDataLoader()
    
    # Create sample data
    df = loader.create_sample_data(
        symbol="BTC-USDT",
        start_price=40000.0,
        num_bars=1000,
        timeframe="15m"
    )
    
    print(f"\nSample data generated:")
    print(f"  Bars: {len(df)}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Price range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")
    print(f"\nFirst 5 rows:")
    print(df.head())

