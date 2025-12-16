"""
Coin Registry Service

Central registry for coin metadata, tier assignments, and ML routing.
- Loads configuration from configs/coin_registry.yaml
- Auto-classifies new coins by 24h volume
- Provides tier info to risk_service and ml_scorer
- Persists tier assignments for consistency across restarts
"""

import os
import yaml
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, List
from pathlib import Path
from loguru import logger


class CoinRegistry:
    """
    Central registry for coin metadata and tier assignments.
    
    Responsibilities:
    1. Load tier assignments from coin_registry.yaml on startup
    2. Auto-classify new coins by fetching 24h volume from exchange
    3. Provide tier info to RiskService for threshold lookups
    4. Provide ML routing info (has real model vs TA-only)
    5. Persist tier assignments for restart consistency
    """
    
    _instance: Optional['CoinRegistry'] = None
    
    def __init__(self):
        self._config_path = Path(os.getcwd()) / 'configs' / 'coin_registry.yaml'
        self._config: Dict = {}
        self._coin_tiers: Dict[str, str] = {}
        self._tier_settings: Dict[str, Dict] = {}
        self._ml_enabled_symbols: List[str] = []
        self._classification_rules: Dict[str, float] = {}
        self._exchange_adapter = None  # Lazy load to avoid circular imports
        
        self._load_config()
    
    def _load_config(self):
        """Load configuration from coin_registry.yaml."""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            else:
                logger.warning(f"[COIN_REGISTRY] Config not found, using defaults: {self._config_path}")
                self._config = self._get_default_config()
                self._save_config()
            
            # Extract sections
            self._coin_tiers = self._config.get('coin_tiers', {})
            self._tier_settings = self._config.get('tier_settings', {})
            self._ml_enabled_symbols = self._config.get('ml_enabled_symbols', ['BTC', 'ETH', 'SOL'])
            self._classification_rules = self._config.get('classification_rules', {
                'tier_1_volume_min': 500_000_000,
                'tier_2_volume_min': 50_000_000,
                'tier_3_volume_min': 5_000_000,
                'tier_4_volume_min': 0
            })
            
            logger.info(f"[COIN_REGISTRY] Loaded {len(self._coin_tiers)} coin tier assignments")
            logger.info(f"[COIN_REGISTRY] ML-enabled symbols: {self._ml_enabled_symbols}")
            
        except Exception as e:
            logger.error(f"[COIN_REGISTRY] Failed to load config: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration."""
        return {
            'classification_rules': {
                'tier_1_volume_min': 500_000_000,
                'tier_2_volume_min': 50_000_000,
                'tier_3_volume_min': 5_000_000,
                'tier_4_volume_min': 0
            },
            'tier_settings': {
                'tier_1': {'correlation_risk': 25.0, 'leverage_max': 10},
                'tier_2': {'correlation_risk': 35.0, 'leverage_max': 10},
                'tier_3': {'correlation_risk': 50.0, 'leverage_max': 7},
                'tier_4': {'correlation_risk': 70.0, 'leverage_max': 5}
            },
            'ml_enabled_symbols': ['BTC', 'ETH', 'SOL'],
            'coin_tiers': {'BTC': 'tier_1', 'ETH': 'tier_1', 'SOL': 'tier_2'},
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    def _save_config(self):
        """Persist configuration to coin_registry.yaml."""
        try:
            self._config['coin_tiers'] = self._coin_tiers
            self._config['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.debug(f"[COIN_REGISTRY] Config saved to {self._config_path}")
        except Exception as e:
            logger.error(f"[COIN_REGISTRY] Failed to save config: {e}")
    
    def _get_base_symbol(self, symbol: str) -> str:
        """Extract base symbol from full symbol (e.g., 'BTC-USDT-SWAP' → 'BTC')."""
        if '-' in symbol:
            return symbol.split('-')[0]
        elif 'USDT' in symbol:
            return symbol.replace('USDT', '').replace('_USDT', '')
        return symbol
    
    async def _fetch_24h_volume(self, symbol: str) -> Optional[float]:
        """Fetch 24h volume from exchange for tier classification."""
        try:
            # Lazy import to avoid circular dependency
            if self._exchange_adapter is None:
                from adapters.exchange_okx_ccxt import OKXCCXTAdapter
                self._exchange_adapter = OKXCCXTAdapter()
            
            # Fetch ticker for 24h volume
            full_symbol = symbol if '-USDT-SWAP' in symbol else f"{symbol}-USDT-SWAP"
            ticker = await self._exchange_adapter.fetch_ticker(full_symbol)
            
            if ticker and 'quoteVolume' in ticker:
                volume = float(ticker['quoteVolume'])
                logger.debug(f"[COIN_REGISTRY] {symbol} 24h volume: ${volume:,.0f}")
                return volume
            
            return None
        except Exception as e:
            logger.warning(f"[COIN_REGISTRY] Failed to fetch volume for {symbol}: {e}")
            return None
    
    def _classify_tier_by_volume(self, volume: Optional[float]) -> str:
        """Classify tier based on 24h volume (5-tier system)."""
        if volume is None:
            # Conservative fallback for unknown volume
            logger.warning("[COIN_REGISTRY] No volume data, defaulting to tier_5")
            return 'tier_5'
        
        if volume >= self._classification_rules.get('tier_1_volume_min', 500_000_000):
            return 'tier_1'
        elif volume >= self._classification_rules.get('tier_2_volume_min', 50_000_000):
            return 'tier_2'
        elif volume >= self._classification_rules.get('tier_3_volume_min', 10_000_000):
            return 'tier_3'
        elif volume >= self._classification_rules.get('tier_4_volume_min', 1_000_000):
            return 'tier_4'
        else:
            return 'tier_5'
    
    async def register_coin(self, symbol: str, source: str = 'unknown') -> str:
        """
        Register a new coin and assign tier based on 24h volume.
        
        Args:
            symbol: Trading symbol (e.g., 'GRT' or 'GRT-USDT-SWAP')
            source: Registration source for logging ('telegram', 'startup', etc.)
        
        Returns:
            Assigned tier (e.g., 'tier_3')
        """
        base_symbol = self._get_base_symbol(symbol)
        
        # Check if already registered
        if base_symbol in self._coin_tiers:
            tier = self._coin_tiers[base_symbol]
            logger.debug(f"[COIN_REGISTRY] {base_symbol} already registered as {tier}")
            return tier
        
        # Fetch volume and classify
        volume = await self._fetch_24h_volume(base_symbol)
        tier = self._classify_tier_by_volume(volume)
        
        # Register and persist
        self._coin_tiers[base_symbol] = tier
        self._save_config()
        
        volume_str = f"${volume:,.0f}" if volume else "unknown"
        logger.info(f"[COIN_ONBOARDING] {base_symbol} → {tier}, vol={volume_str}, source={source}")
        
        return tier
    
    def get_tier(self, symbol: str) -> str:
        """
        Get tier for a symbol. Returns cached tier or 'tier_4' if not registered.
        
        Note: For new coins, use register_coin() first to properly classify.
        This method does NOT auto-register to avoid blocking on async calls.
        """
        base_symbol = self._get_base_symbol(symbol)
        
        if base_symbol in self._coin_tiers:
            return self._coin_tiers[base_symbol]
        
        # Not registered - return conservative default
        logger.debug(f"[COIN_REGISTRY] {base_symbol} not registered, using tier_4")
        return 'tier_4'
    
    def get_tier_settings(self, tier: str) -> Dict:
        """Get settings for a specific tier."""
        return self._tier_settings.get(tier, self._tier_settings.get('tier_4', {}))
    
    def get_correlation_risk(self, symbol: str) -> float:
        """Get correlation risk score for a symbol based on its tier."""
        tier = self.get_tier(symbol)
        settings = self.get_tier_settings(tier)
        return settings.get('correlation_risk', 60.0)
    
    def get_volatility_thresholds(self, symbol: str) -> Dict:
        """Get volatility thresholds for a symbol based on its tier."""
        tier = self.get_tier(symbol)
        settings = self.get_tier_settings(tier)
        return settings.get('volatility_thresholds', {'low': 0.30, 'medium': 0.50, 'high': 0.70})
    
    def get_volume_thresholds(self, symbol: str) -> Dict:
        """Get volume thresholds for a symbol based on its tier."""
        tier = self.get_tier(symbol)
        settings = self.get_tier_settings(tier)
        return settings.get('volume_thresholds', {'high': 1000000, 'medium': 200000, 'low': 20000})
    
    def get_max_leverage(self, symbol: str) -> int:
        """Get maximum allowed leverage for a symbol based on its tier."""
        tier = self.get_tier(symbol)
        settings = self.get_tier_settings(tier)
        return settings.get('leverage_max', 5)
    
    def has_ml_model(self, symbol: str) -> bool:
        """Check if a symbol has a real ML model available."""
        base_symbol = self._get_base_symbol(symbol)
        return base_symbol in self._ml_enabled_symbols
    
    def get_ml_enabled_symbols(self) -> List[str]:
        """Get list of symbols with real ML models."""
        return self._ml_enabled_symbols.copy()
    
    def is_registered(self, symbol: str) -> bool:
        """Check if a symbol is registered in the registry."""
        base_symbol = self._get_base_symbol(symbol)
        return base_symbol in self._coin_tiers
    
    def get_all_registered_coins(self) -> Dict[str, str]:
        """Get all registered coins and their tiers."""
        return self._coin_tiers.copy()


# Singleton instance
_coin_registry: Optional[CoinRegistry] = None


def get_coin_registry() -> CoinRegistry:
    """Get singleton CoinRegistry instance."""
    global _coin_registry
    if _coin_registry is None:
        _coin_registry = CoinRegistry()
    return _coin_registry


def reset_coin_registry():
    """Reset singleton (for testing)."""
    global _coin_registry
    _coin_registry = None
