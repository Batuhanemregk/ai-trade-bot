"""
Base Job Class for Professional Scheduler Architecture
Provides common functionality for all jobs including bar idempotency
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from uuid import uuid4

from loguru import logger

from infrastructure.feature_flags import (
    DEDUP_CACHE_MAX_ITEMS,
    DEDUP_CACHE_SECONDS,
    DEDUP_ENABLED,
)


class BaseJob(ABC):
    """Base class for all scheduler jobs with common functionality."""
    
    _SUPPORTED_TIMEFRAMES = {'1m', '5m', '15m', '1h', '4h', '1d'}
    _job_dedup_cache: "OrderedDict[str, float]" = OrderedDict()
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        self.policy = policy
        self.semaphore = semaphore
        self.runtime_state = runtime_state
        self.job_name = self.__class__.__name__.replace('Job', '').lower()
        # Scheduler assigns canonical ID after instantiation
        self.job_id: str = self.job_name
        self.run_id: Optional[str] = None
        self.current_bar_id: Optional[str] = None
        
        # Bar idempotency tracking
        self.last_processed_bars = self.runtime_state.setdefault('last_processed_bars', {})
        self.runtime_state.setdefault('job_runs', {})
        self.runtime_state.setdefault('job_dedup_history', {})
        self._invalid_timeframes_logged: set[str] = set()
        
    @abstractmethod
    async def initialize(self):
        """Initialize job-specific resources."""
        pass
    
    @abstractmethod
    async def execute(self):
        """Execute the main job logic."""
        pass
    
    async def cleanup(self):
        """Cleanup job resources (optional override)."""
        pass
    
    def _normalize_timeframe(self, timeframe: Any) -> str:
        """Ensure timeframe is a known cadence string."""
        if isinstance(timeframe, datetime):
            logger.warning(f"⚠️ get_current_bar_id received datetime instead of timeframe string: {timeframe}")
            return '15m'
        
        timeframe_str = str(timeframe).lower().strip()
        if timeframe_str in self._SUPPORTED_TIMEFRAMES:
            return timeframe_str
        
        # Detect ISO bar identifiers mistakenly passed in as timeframe
        looks_like_bar_id = 't' in timeframe_str and ':' in timeframe_str
        if looks_like_bar_id:
            if timeframe_str not in self._invalid_timeframes_logged:
                self._invalid_timeframes_logged.add(timeframe_str)
                logger.opt(stack=True).warning(
                    f"[BAR] Detected bar id '{timeframe}' passed as timeframe in {self.job_name}. "
                    "Defaulting to 15m and recording stack for diagnostics."
                )
            return '15m'
        
        # Unknown timeframe — allow downstream handler to log once
        return timeframe_str
    
    def get_current_bar_id(self, timeframe: str) -> str:
        """Get current closed bar ID for given timeframe."""
        now = datetime.now(timezone.utc)
        timeframe_str = self._normalize_timeframe(timeframe)
        bar_start = self.get_bar_id(now, timeframe_str)
        return bar_start
    
    @staticmethod
    def get_bar_id(moment: datetime, timeframe: str) -> str:
        """Return ISO timestamp (UTC) representing bar start."""
        dt = moment.astimezone(timezone.utc)
        
        def _round_minutes(minutes: int) -> datetime:
            minute = (dt.minute // minutes) * minutes
            return dt.replace(minute=minute, second=0, microsecond=0)
        
        def _round_hours(hours: int) -> datetime:
            hour = dt.hour - (dt.hour % hours)
            return dt.replace(hour=hour, minute=0, second=0, microsecond=0)
        
        if timeframe == '1m':
            bar_time = dt.replace(second=0, microsecond=0)
        elif timeframe == '5m':
            bar_time = _round_minutes(5)
        elif timeframe == '15m':
            bar_time = _round_minutes(15)
        elif timeframe == '1h':
            bar_time = dt.replace(minute=0, second=0, microsecond=0)
        elif timeframe == '4h':
            bar_time = _round_hours(4)
        elif timeframe == '1d':
            bar_time = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # Generic parsing: support Xm / Xh if possible
            try:
                if timeframe.endswith('m'):
                    minutes = int(timeframe[:-1])
                    minutes = max(minutes, 1)
                    bar_time = _round_minutes(minutes)
                elif timeframe.endswith('h'):
                    hours = int(timeframe[:-1])
                    hours = max(hours, 1)
                    bar_time = _round_hours(hours)
                else:
                    logger.warning(f"⚠️ Unhandled timeframe '{timeframe}', defaulting to 15m rounding")
                    bar_time = _round_minutes(15)
            except ValueError:
                logger.warning(f"⚠️ Invalid timeframe '{timeframe}', defaulting to 15m rounding")
                bar_time = _round_minutes(15)
        
        return bar_time.isoformat().replace('+00:00', 'Z')
    
    def get_effective_bar_id(self, timeframe: str) -> str:
        """Compute current bar id for given timeframe."""
        return self.get_current_bar_id(timeframe)
    
    @staticmethod
    def build_job_key(job_name: str, bar_id: str) -> str:
        return f"{job_name}:{bar_id}"
    
    @classmethod
    def _prune_dedup_cache(cls) -> None:
        if not cls._job_dedup_cache:
            return
        
        now = time.time()
        # Remove expired entries
        while cls._job_dedup_cache:
            oldest_key, timestamp = next(iter(cls._job_dedup_cache.items()))
            if (now - timestamp) > DEDUP_CACHE_SECONDS or len(cls._job_dedup_cache) > DEDUP_CACHE_MAX_ITEMS:
                cls._job_dedup_cache.popitem(last=False)
            else:
                break
    
    @classmethod
    def should_skip_job(cls, job_key: str) -> bool:
        """Return True if job already executed for the bar and dedup active."""
        if not DEDUP_ENABLED:
            return False
        
        cls._prune_dedup_cache()
        return job_key in cls._job_dedup_cache
    
    @classmethod
    def record_job_run(cls, job_key: str, dedup_hit: bool) -> None:
        """Record job execution in dedup cache."""
        if not DEDUP_ENABLED:
            return
        
        cls._job_dedup_cache[job_key] = time.time()
        cls._prune_dedup_cache()
    
    def start_run(self, timeframe: str) -> bool:
        """
        Initialise run context with run_id/bar_id and apply dedup guard.
        
        Returns:
            bool: True if execution should continue, False if dedup skip.
        """
        self.run_id = uuid4().hex
        self.current_bar_id = self.get_effective_bar_id(timeframe)
        job_key = self.build_job_key(self.job_id, self.current_bar_id)
        
        if self.should_skip_job(job_key):
            self.record_job_run(job_key, dedup_hit=True)
            logger.info(
                f"[RUN] job={self.job_id} run_id={self.run_id} bar_id={self.current_bar_id} "
                "status=skipped reason=dedup"
            )
            self.runtime_state['job_runs'][self.job_id] = {
                "run_id": self.run_id,
                "bar_id": self.current_bar_id,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "status": "dedup_hit",
            }
            self.runtime_state['job_dedup_history'][job_key] = {
                "run_id": self.run_id,
                "bar_id": self.current_bar_id,
                "status": "dedup_hit",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            return False
        
        self.record_job_run(job_key, dedup_hit=False)
        self.runtime_state['job_runs'][self.job_id] = {
            "run_id": self.run_id,
            "bar_id": self.current_bar_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            f"[RUN] job={self.job_id} run_id={self.run_id} bar_id={self.current_bar_id} status=starting"
        )
        return True
    
    def finish_run(self, status: str = "SUCCESS", error: Optional[str] = None) -> None:
        """Update runtime metadata after job execution."""
        if not self.current_bar_id or not self.run_id:
            return
        
        self.runtime_state['job_runs'][self.job_id] = {
            "run_id": self.run_id,
            "bar_id": self.current_bar_id,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "error": error,
        }
        job_key = self.build_job_key(self.job_id, self.current_bar_id)
        self.runtime_state['job_dedup_history'][job_key] = {
            "run_id": self.run_id,
            "bar_id": self.current_bar_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }
        log_line = (
            f"[RUN] job={self.job_id} run_id={self.run_id} bar_id={self.current_bar_id} status={status}"
        )
        if error:
            log_line += f" error={error}"
        logger.info(log_line)
        # Reset context
        self.run_id = None
        self.current_bar_id = None
    
    def is_bar_already_processed(self, symbol: str, timeframe: str) -> bool:
        """Check if current bar has already been processed for this symbol/timeframe."""
        normalized_timeframe = self._normalize_timeframe(timeframe)
        bar_id = self.get_current_bar_id(normalized_timeframe)
        key = f"{symbol}_{normalized_timeframe}"
        
        last_processed = self.last_processed_bars.get(key)
        if last_processed and last_processed >= bar_id:
            logger.debug(f"[BAR] tf={normalized_timeframe} symbol={symbol} bar={bar_id} already processed")
            return True
        
        return False
    
    def mark_bar_processed(self, symbol: str, timeframe: str):
        """Mark current bar as processed for this symbol/timeframe."""
        normalized_timeframe = self._normalize_timeframe(timeframe)
        bar_id = self.get_current_bar_id(normalized_timeframe)
        key = f"{symbol}_{normalized_timeframe}"
        
        self.last_processed_bars[key] = bar_id
        logger.debug(f"[BAR] tf={normalized_timeframe} symbol={symbol} bar={bar_id} processed")
    
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
