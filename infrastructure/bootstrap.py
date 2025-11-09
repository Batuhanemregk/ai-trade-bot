"""
Bootstrap utilities for the trading system.
Handles environment setup, configuration loading, and logging initialization.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import find_dotenv, load_dotenv
from loguru import logger
import yaml

from infrastructure.logger import initialize_logging


def _resolve_env_vars(obj: Any) -> Any:
    """Recursively resolve environment variables in policy configuration."""
    if isinstance(obj, dict):
        return {key: _resolve_env_vars(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_resolve_env_vars(item) for item in obj]
    elif isinstance(obj, str):
        # Replace ${VAR} with environment variable values
        def replace_env_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Return original if not found
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, obj)
    else:
        return obj


def load_env(env_file: Optional[str] = None) -> None:
    """
    Load environment variables from .env file.
    
    Args:
        env_file: Path to .env file, defaults to auto-discovery
    """
    try:
        if env_file:
            env_path = Path(env_file)
            if env_path.exists():
                load_dotenv(env_path, override=False)
                logger.info(f"Loaded environment from {env_path}")
            else:
                logger.warning(f"Environment file not found: {env_path}")
        else:
            # Auto-discover .env file
            env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=False)
                logger.info(f"Loaded environment from {env_path}")
            else:
                logger.info("No .env file found, using system environment")

        # Ensure default feature flag values exist without overriding explicit envs
        os.environ.setdefault('DEDUP_ENABLED', 'true')
        os.environ.setdefault('DEDUP_CACHE_SECONDS', '3600')
        os.environ.setdefault('DEDUP_CACHE_MAX_ITEMS', '128')
        os.environ.setdefault('NEWS_DEDUP', 'true')
        os.environ.setdefault('RISK_CACHE_TTL_SECONDS', '75')
        os.environ.setdefault('TELEGRAM_MOCK', 'false')
        # Load comprehensive configuration banner
        try:
            from infrastructure.config_manager import config_manager
            banner = config_manager.get_mode_banner()
            logger.info(banner)
            
            # Save banner to file for reports
            out_dir = Path('reports/strategy')
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / 'CONFIG_BANNER.txt').write_text(banner, encoding='utf-8')
        except Exception as e:
            logger.warning(f"Failed to load config banner: {e}")
            # Fallback to simple mode banner
            mode = os.getenv('TRADING_MODE', 'paper')
            testnet = os.getenv('OKX_TESTNET', 'false')
            sandbox = os.getenv('OKX_SANDBOX', 'false')
            dry = os.getenv('DRY_RUN', 'false')
            logger.info(f"[MODE] TRADING_MODE={mode} TESTNET={testnet} SANDBOX={sandbox} DRY_RUN={dry}")
                
    except Exception as e:
        logger.error(f"Failed to load environment: {e}")
        raise


def load_policy(policy_path: str = "configs/policy.yaml") -> Dict[str, Any]:
    """
    Load trading policy configuration from YAML file.
    
    Args:
        policy_path: Path to policy.yaml file
        
    Returns:
        Dictionary containing policy configuration
        
    Raises:
        FileNotFoundError: If policy file doesn't exist
        yaml.YAMLError: If policy file is invalid YAML
    """
    try:
        policy_file = Path(policy_path)
        if not policy_file.exists():
            logger.warning(f"Policy file not found: {policy_path}, using defaults")
            return _get_default_policy()
        
        with open(policy_file, 'r', encoding='utf-8') as f:
            policy = yaml.safe_load(f)
        
        # Resolve environment variables in policy
        policy = _resolve_env_vars(policy)
        
        logger.info(f"Loaded policy from {policy_path}")
        return policy
        
    except FileNotFoundError:
        logger.error(f"Policy file not found: {policy_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in policy file {policy_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to load policy from {policy_path}: {e}")
        raise


def init_logging(config_path: Optional[str] = None) -> None:
    """
    Initialize logging system.
    
    Args:
        config_path: Path to logging configuration file
    """
    try:
        if config_path:
            logging_config = Path(config_path)
            if logging_config.exists():
                initialize_logging(str(logging_config))
                logger.info(f"Logging initialized from {config_path}")
            else:
                logger.warning(f"Logging config not found: {config_path}, using defaults")
                initialize_logging()
        else:
            # Use default logging configuration
            initialize_logging()
            logger.info("Logging initialized with default configuration")
            
    except Exception as e:
        logger.error(f"Failed to initialize logging: {e}")
        # Fallback to basic logging
        logger.add(
            "logs/fallback.log",
            rotation="1 day",
            retention="7 days",
            level="INFO"
        )
        logger.warning("Using fallback logging configuration")


def _get_default_policy() -> Dict[str, Any]:
    """Get default trading policy configuration."""
    return {
        "risk": {
            "max_daily_loss": 0.05,
            "max_position_size": 0.1,
            "stop_loss_atr_multiplier": 2.0,
            "max_active_positions": 5
        },
        "scoring": {
            "min_score": 0.5,
            "news_weight": 0.3,
            "ta_weight": 0.4,
            "ml_weight": 0.3
        },
        "trading": {
            "default_timeframe": "1h",
            "analysis_interval": 300,
            "position_update_interval": 60,
            "dry_run": True,
            "paper_trading": True
        },
        "symbols": ["BTC-USDT", "ETH-USDT"],
        "notifications": {
            "telegram_enabled": True,
            "risk_alerts": True,
            "trade_notifications": True
        }
    }


def validate_policy(policy: Dict[str, Any]) -> bool:
    """
    Validate policy configuration.
    
    Args:
        policy: Policy configuration dictionary
        
    Returns:
        True if policy is valid, False otherwise
    """
    try:
        # Check if trading section exists
        if "trading" not in policy:
            logger.error("Missing required policy section: trading")
            return False
        
        # Check if trading.risk section exists
        trading = policy.get("trading", {})
        if "risk" not in trading:
            logger.error("Missing required policy section: trading.risk")
            return False
        
        # Validate trading.risk section
        risk = trading.get("risk", {})
        if not isinstance(risk.get("max_position_size_pct"), (int, float)):
            logger.error("max_position_size_pct must be a number")
            return False
        
        # Check if symbols exist (either at root, trading, or exchange.symbols.trading_pairs)
        symbols = (policy.get("symbols", []) or 
                  trading.get("symbols", []) or 
                  policy.get("exchange", {}).get("symbols", {}).get("trading_pairs", []))
        if not isinstance(symbols, list) or len(symbols) == 0:
            logger.error("symbols must be a non-empty list")
            return False
        
        logger.info("Policy validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Policy validation failed: {e}")
        return False


def get_config_summary(policy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get a summary of the loaded configuration.
    
    Args:
        policy: Policy configuration dictionary
        
    Returns:
        Configuration summary dictionary
    """
    try:
        trading = policy.get('trading', {})
        symbols = (policy.get('symbols', []) or 
                  trading.get('symbols', []) or 
                  policy.get('exchange', {}).get('symbols', {}).get('trading_pairs', []))
        
        return {
            "risk_limits": {
                "max_position_size": f"{trading.get('risk', {}).get('max_position_size', 0.1) * 100:.1f}%",
                "max_leverage": trading.get('risk', {}).get('max_leverage', 3.0),
                "stop_loss_pct": f"{trading.get('risk', {}).get('stop_loss_pct', 0.02) * 100:.1f}%"
            },
            "trading_mode": {
                "dry_run": trading.get('mode') == 'dry-run',
                "paper_trading": trading.get('mode') == 'paper',
                "timeframe": trading.get('execution', {}).get('default_timeout', '1h')
            },
            "symbols": {
                "count": len(symbols),
                "list": symbols[:5] + ['...'] if len(symbols) > 5 else symbols
            },
            "notifications": {
                "telegram": policy.get('notifications', {}).get('telegram_enabled', True),
                "risk_alerts": True
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to generate config summary: {e}")
        return {}
