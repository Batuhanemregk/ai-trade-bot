"""
Configuration Manager - Single Source of Truth
Manages configuration with priority: ENV > policy.yaml > defaults
"""

import os
import yaml
from typing import Dict, Any, Optional, Tuple
from loguru import logger


class ConfigManager:
    """
    Configuration manager with ENV override capability.
    Priority: ENV > policy.yaml > defaults
    """
    
    def __init__(self, policy_path: str = "configs/policy.yaml"):
        self.policy_path = policy_path
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from policy.yaml"""
        try:
            with open(self.policy_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            logger.info(f"✅ Loaded configuration from {self.policy_path}")
        except Exception as e:
            logger.error(f"❌ Failed to load policy.yaml: {e}")
            self._config = {}
    
    def get(self, key_path: str, default: Any = None) -> Tuple[Any, str]:
        """
        Get configuration value with source tracking.
        
        Args:
            key_path: Dot-separated path (e.g., 'trading.mode')
            default: Default value if not found
            
        Returns:
            Tuple of (value, source) where source is 'ENV', 'policy.yaml', or 'default'
        """
        # Check ENV first
        env_key = key_path.upper().replace('.', '_')
        if env_key in os.environ:
            value = os.environ[env_key]
            # Convert to appropriate type based on default
            if isinstance(default, bool):
                value = value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(default, int):
                try:
                    value = int(value)
                except ValueError:
                    value = default
            elif isinstance(default, float):
                try:
                    value = float(value)
                except ValueError:
                    value = default
            return value, 'ENV'
        
        # Check policy.yaml
        try:
            keys = key_path.split('.')
            value = self._config
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default, 'default'
            return value, 'policy.yaml'
        except Exception:
            return default, 'default'
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration with source tracking"""
        config = {}
        sources = {}
        
        # Mode configuration
        config['mode'], sources['mode'] = self.get('trading.mode', 'PAPER')
        config['use_position_tpsl'], sources['use_position_tpsl'] = self.get('trading.use_position_tpsl', True)
        config['reduce_only'], sources['reduce_only'] = self.get('trading.reduce_only', True)
        config['entry_cooldown_bars'], sources['entry_cooldown_bars'] = self.get('trading.entry_cooldown_bars', 2)
        
        # Strategy configuration
        config['strategy_type'], sources['strategy_type'] = self.get('trading.strategy.type', 'single_flip')
        config['once_per_bar'], sources['once_per_bar'] = self.get('trading.strategy.once_per_bar', True)
        config['same_direction_block'], sources['same_direction_block'] = self.get('trading.strategy.same_direction_block', True)
        config['reversal_enabled'], sources['reversal_enabled'] = self.get('trading.strategy.reversal_enabled', True)
        
        # Scale-in configuration
        config['scale_in_enabled'], sources['scale_in_enabled'] = self.get('trading.strategy.scale_in.enabled', False)
        config['max_ladders'], sources['max_ladders'] = self.get('trading.strategy.scale_in.max_ladders', 2)
        config['ladder_size_usdt'], sources['ladder_size_usdt'] = self.get('trading.strategy.scale_in.ladder_size_usdt', 5)
        config['min_dist_pct'], sources['min_dist_pct'] = self.get('trading.strategy.scale_in.min_dist_pct', 0.5)
        config['add_on_profit_only'], sources['add_on_profit_only'] = self.get('trading.strategy.scale_in.add_on_profit_only', True)
        
        # Risk configuration
        config['max_position_size_pct'], sources['max_position_size_pct'] = self.get('trading.risk.max_position_size_pct', 0.01)
        config['max_total_risk_pct'], sources['max_total_risk_pct'] = self.get('trading.risk.max_total_risk_pct', 0.60)
        config['max_leverage'], sources['max_leverage'] = self.get('trading.risk.max_leverage', 3.0)
        
        # Exchange configuration
        config['supported_pairs'], sources['supported_pairs'] = self.get('exchange.symbols.supported_pairs', ['BTC', 'ETH', 'SOL'])
        config['trading_pairs'], sources['trading_pairs'] = self.get('exchange.symbols.trading_pairs', ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP'])
        
        return config, sources
    
    def get_symbols(self) -> Tuple[list, str]:
        """Get trading symbols with source tracking"""
        # Check ENV override first
        if 'SYMBOLS' in os.environ:
            symbols = [s.strip() for s in os.environ['SYMBOLS'].split(',')]
            return symbols, 'ENV'
        
        # Check policy.yaml
        pairs, source = self.get('exchange.symbols.trading_pairs', ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP'])
        return pairs, source
    
    def get_timeframe(self) -> Tuple[str, str]:
        """Get timeframe with source tracking"""
        timeframe, source = self.get('TIMEFRAME', '15m')
        return timeframe, source
    
    def get_mode_banner(self) -> str:
        """Generate mode banner with source information"""
        config, sources = self.get_trading_config()
        symbols, symbol_source = self.get_symbols()
        timeframe, tf_source = self.get_timeframe()
        
        banner_lines = [
            "=" * 80,
            "🚀 AIBOTBS CONFIGURATION BANNER",
            "=" * 80,
            f"MODE: {config['mode']} (source={sources['mode']})",
            f"STRATEGY: {config['strategy_type']} (source={sources['strategy_type']})",
            f"USE_POSITION_TPSL: {config['use_position_tpsl']} (source={sources['use_position_tpsl']})",
            f"REDUCE_ONLY: {config['reduce_only']} (source={sources['reduce_only']})",
            f"ENTRY_COOLDOWN_BARS: {config['entry_cooldown_bars']} (source={sources['entry_cooldown_bars']})",
            f"ONCE_PER_BAR: {config['once_per_bar']} (source={sources['once_per_bar']})",
            f"SAME_DIRECTION_BLOCK: {config['same_direction_block']} (source={sources['same_direction_block']})",
            f"REVERSAL_ENABLED: {config['reversal_enabled']} (source={sources['reversal_enabled']})",
            "",
            "RISK LIMITS:",
            f"  max_position_size_pct: {config['max_position_size_pct']} (source={sources['max_position_size_pct']})",
            f"  max_total_risk_pct: {config['max_total_risk_pct']} (source={sources['max_total_risk_pct']})",
            f"  max_leverage: {config['max_leverage']} (source={sources['max_leverage']})",
            "",
            "SYMBOLS:",
            f"  supported_pairs: {symbols} (source={symbol_source})",
            f"  timeframe: {timeframe} (source={tf_source})",
            "",
            "SCALE-IN CONFIG (if enabled):",
            f"  enabled: {config['scale_in_enabled']} (source={sources['scale_in_enabled']})",
            f"  max_ladders: {config['max_ladders']} (source={sources['max_ladders']})",
            f"  ladder_size_usdt: {config['ladder_size_usdt']} (source={sources['ladder_size_usdt']})",
            f"  min_dist_pct: {config['min_dist_pct']} (source={sources['min_dist_pct']})",
            f"  add_on_profit_only: {config['add_on_profit_only']} (source={sources['add_on_profit_only']})",
            "=" * 80
        ]
        
        return "\n".join(banner_lines)


# Global config manager instance
config_manager = ConfigManager()
