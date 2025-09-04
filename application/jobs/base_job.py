"""
Base Job Class for Professional Scheduler Architecture
Provides common functionality for all jobs including bar idempotency
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from loguru import logger


class BaseJob(ABC):
    """Base class for all scheduler jobs with common functionality."""
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        self.policy = policy
        self.semaphore = semaphore
        self.runtime_state = runtime_state
        self.job_name = self.__class__.__name__.replace('Job', '').lower()
        
        # Bar idempotency tracking
        self.last_processed_bars = self.runtime_state.setdefault('last_processed_bars', {})
        
    @abstractmethod
    async def initialize(self):
        """Initialize job-specific resources."""
        pass
    
    @abstractmethod
    async def execute(self):
        """Execute the main job logic."""
        pass
    
    def get_current_bar_id(self, timeframe: str) -> str:
        """Get current closed bar ID for given timeframe."""
        now = datetime.now(timezone.utc)
        
        if timeframe == '1m':
            # Round down to minute boundary
            bar_time = now.replace(second=0, microsecond=0)
        elif timeframe == '5m':
            # Round down to 5-minute boundary
            minute = (now.minute // 5) * 5
            bar_time = now.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == '15m':
            # Round down to 15-minute boundary
            minute = (now.minute // 15) * 15
            bar_time = now.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == '1h':
            # Round down to hour boundary
            bar_time = now.replace(minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        return bar_time.isoformat()
    
    def is_bar_already_processed(self, symbol: str, timeframe: str) -> bool:
        """Check if current bar has already been processed for this symbol/timeframe."""
        bar_id = self.get_current_bar_id(timeframe)
        key = f"{symbol}_{timeframe}"
        
        last_processed = self.last_processed_bars.get(key)
        if last_processed and last_processed >= bar_id:
            return True
        
        return False
    
    def mark_bar_processed(self, symbol: str, timeframe: str):
        """Mark current bar as processed for this symbol/timeframe."""
        bar_id = self.get_current_bar_id(timeframe)
        key = f"{symbol}_{timeframe}"
        
        self.last_processed_bars[key] = bar_id
        logger.debug(f"[BAR] tf={timeframe} symbol={symbol} bar={bar_id} processed")
    
    def get_symbols_batch(self, all_symbols: List[str], batch_index: int = 0) -> List[str]:
        """Get a batch of symbols for processing."""
        batch_size = self.policy['trading']['scoring']['risk_management']['batch_size']
        start_idx = batch_index * batch_size
        end_idx = start_idx + batch_size
        
        return all_symbols[start_idx:end_idx]
    
    def get_all_symbols(self) -> List[str]:
        """Get all trading symbols from policy."""
        symbols = (self.policy.get('symbols', []) or 
                  self.policy.get('exchange', {}).get('symbols', {}).get('trading_pairs', []) or
                  ['BTC-USDT-SWAP'])
        
        # Convert to futures format
        futures_symbols = []
        for symbol in symbols:
            if symbol.endswith('-USDT-SWAP'):
                futures_symbols.append(symbol)
            elif symbol.endswith('-USDT'):
                futures_symbols.append(symbol.replace('-USDT', '-USDT-SWAP'))
            else:
                futures_symbols.append(f"{symbol}-USDT-SWAP")
        
        return futures_symbols
    
    def calculate_edge_cost_ratio(self, expected_move: float, fees_bps: int, slippage_bps: int) -> float:
        """Calculate edge vs cost ratio for reversal decisions."""
        total_cost_bps = fees_bps + slippage_bps
        cost_ratio = total_cost_bps / 10000.0  # Convert bps to decimal
        
        if cost_ratio == 0:
            return float('inf')
        
        return expected_move / cost_ratio
    
    def get_threshold(self, threshold_name: str) -> float:
        """Get threshold value from policy (single source of truth)."""
        thresholds = self.policy['trading']['scoring']['thresholds']
        return thresholds.get(threshold_name, 50.0)  # Default fallback
    
    def get_signal_config(self, config_name: str) -> Any:
        """Get signal configuration from policy."""
        signal_config = self.policy['trading']['scoring']
        return signal_config.get(config_name)
    
    def get_regime_config(self, config_name: str) -> Any:
        """Get regime configuration from policy."""
        regime_config = self.policy['trading']['scoring']['regime']
        return regime_config.get(config_name)
    
    def get_risk_config(self, config_name: str) -> Any:
        """Get risk configuration from policy."""
        risk_config = self.policy['trading']['scoring']['risk_management']
        return risk_config.get(config_name)
    
    async def cleanup_old_state(self):
        """Clean up old state data to prevent memory bloat."""
        try:
            cleanup_interval = self.policy['idempotency']['cleanup_interval_hours']
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=cleanup_interval)
            
            # Clean up old bar processing records
            keys_to_remove = []
            for key, bar_id in self.last_processed_bars.items():
                try:
                    bar_time = datetime.fromisoformat(bar_id.replace('Z', '+00:00'))
                    if bar_time < cutoff_time:
                        keys_to_remove.append(key)
                except:
                    keys_to_remove.append(key)  # Remove invalid entries
            
            for key in keys_to_remove:
                del self.last_processed_bars[key]
            
            if keys_to_remove:
                logger.info(f"[CLEANUP] Removed {len(keys_to_remove)} old bar records")
                
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old state: {e}")
