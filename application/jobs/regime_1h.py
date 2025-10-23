"""
Regime Update Job (1h)
Handles 1H ADX/trend filter updates every hour
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from loguru import logger

from .base_job import BaseJob


class Regime1hJob(BaseJob):
    """1-hour regime update job for trend filtering."""
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.exchange_adapter = None
        self.regime_cache = {}
        
    async def initialize(self):
        """Initialize regime update components."""
        try:
            # Initialize exchange adapter
            from adapters.exchange_okx_ccxt import OKXCCXTAdapter
            self.exchange_adapter = OKXCCXTAdapter()
            
            logger.info("✅ Regime1hJob initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Regime1hJob: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup regime update resources"""
        try:
            if hasattr(self, 'exchange_adapter') and self.exchange_adapter:
                await self.exchange_adapter.close()
                logger.debug("✅ Closed exchange adapter for Regime1hJob")
        except Exception as e:
            logger.error(f"❌ Regime1hJob cleanup failed: {e}")
    
    async def execute(self):
        """Execute 1-hour regime update."""
        try:
            logger.info("[JOB] regime_1h starting execution")
            
            symbols = self.get_all_symbols()
            logger.info(f"[REGIME] Processing {len(symbols)} symbols for regime update")
            
            processed_count = 0
            for symbol in symbols:
                try:
                    # Check bar idempotency
                    if self.is_bar_already_processed(symbol, '1h'):
                        logger.debug(f"[BAR] {symbol} 1h bar already processed, skipping")
                        continue
                    
                    # Process regime update for this symbol
                    await self._process_regime_update(symbol)
                    
                    # Mark bar as processed
                    self.mark_bar_processed(symbol, '1h')
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process regime update for {symbol}: {e}")
                    continue
            
            logger.info(f"[JOB] regime_1h completed {processed_count}/{len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"❌ Regime1hJob execution failed: {e}")
            raise
    
    async def _process_regime_update(self, symbol: str):
        """Process regime update for a specific symbol."""
        try:
            logger.info(f"[REGIME] Processing regime update for {symbol}")
            
            # Fetch 1H OHLCV data
            ohlcv_data = await self.exchange_adapter.fetch_ohlcv(symbol, '1h', limit=50)
            
            if not ohlcv_data or len(ohlcv_data) < 14:
                logger.warning(f"[REGIME] Insufficient 1H data for {symbol}")
                return
            
            # Calculate ADX
            adx_value = self._calculate_adx(ohlcv_data)
            
            # Determine regime
            regime_info = self._determine_regime(adx_value)
            
            # Cache regime info
            self.regime_cache[symbol] = {
                'adx': adx_value,
                'regime': regime_info['regime'],
                'confidence_multiplier': regime_info['confidence_multiplier'],
                'trend_throttle': regime_info['trend_throttle'],
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Log regime information
            if regime_info['trend_throttle']:
                logger.info(f"[REGIME] {symbol} ADX(1H)={adx_value:.1f} → {regime_info['regime']} mode, confidence_mult={regime_info['confidence_multiplier']}")
            else:
                logger.info(f"[REGIME] {symbol} ADX(1H)={adx_value:.1f} → {regime_info['regime']} mode")
            
        except Exception as e:
            logger.error(f"❌ Failed to process regime update for {symbol}: {e}")
            raise
    
    def _calculate_adx(self, ohlcv_data: List[List]) -> float:
        """Calculate ADX from 1H OHLCV data."""
        try:
            import pandas as pd
            import numpy as np
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calculate True Range
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['close'].shift(1))
            df['tr3'] = abs(df['low'] - df['close'].shift(1))
            df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # Calculate Directional Movement
            df['dm_plus'] = np.where(
                (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                np.maximum(df['high'] - df['high'].shift(1), 0),
                0
            )
            df['dm_minus'] = np.where(
                (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                np.maximum(df['low'].shift(1) - df['low'], 0),
                0
            )
            
            # Calculate smoothed values (14-period)
            period = 14
            df['atr'] = df['tr'].rolling(window=period).mean()
            df['di_plus'] = 100 * (df['dm_plus'].rolling(window=period).mean() / df['atr'])
            df['di_minus'] = 100 * (df['dm_minus'].rolling(window=period).mean() / df['atr'])
            
            # Calculate DX and ADX
            df['dx'] = 100 * abs(df['di_plus'] - df['di_minus']) / (df['di_plus'] + df['di_minus'])
            df['adx'] = df['dx'].rolling(window=period).mean()
            
            # Return latest ADX value
            return float(df['adx'].iloc[-1]) if not pd.isna(df['adx'].iloc[-1]) else 0.0
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate ADX: {e}")
            return 0.0
    
    def _determine_regime(self, adx_value: float) -> Dict[str, Any]:
        """Determine market regime based on ADX value."""
        try:
            adx_min = self.get_regime_config('adx_1h_min')
            low_adx_threshold = self.get_regime_config('low_adx_threshold')
            regime_multiplier = self.policy['trading']['scoring']['position_sizing']['regime_multiplier']
            
            if adx_value >= adx_min:
                return {
                    'regime': 'trend',
                    'confidence_multiplier': 1.0,
                    'trend_throttle': False
                }
            elif adx_value >= low_adx_threshold:
                return {
                    'regime': 'sideways',
                    'confidence_multiplier': 0.8,
                    'trend_throttle': False
                }
            else:
                return {
                    'regime': 'mean_reversion',
                    'confidence_multiplier': regime_multiplier,
                    'trend_throttle': True
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to determine regime: {e}")
            return {
                'regime': 'unknown',
                'confidence_multiplier': 1.0,
                'trend_throttle': False
            }
    
    def get_regime_info(self, symbol: str) -> Dict[str, Any]:
        """Get cached regime information for a symbol."""
        return self.regime_cache.get(symbol, {
            'adx': 0.0,
            'regime': 'unknown',
            'confidence_multiplier': 1.0,
            'trend_throttle': False,
            'timestamp': None
        })
