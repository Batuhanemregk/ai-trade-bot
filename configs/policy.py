"""
Policy Configuration Loader for AiBotBS
Loads and validates policy configuration from YAML files.
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from loguru import logger


def load_policy(policy_file: str = "configs/policy.yaml") -> Dict[str, Any]:
    """
    Load policy configuration from YAML file.
    
    Args:
        policy_file: Path to policy YAML file
        
    Returns:
        Dictionary containing policy configuration
        
    Raises:
        FileNotFoundError: If policy file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    try:
        policy_path = Path(policy_file)
        
        if not policy_path.exists():
            logger.warning(f"Policy file not found: {policy_file}")
            return _get_default_policy()
        
        with open(policy_path, 'r', encoding='utf-8') as f:
            policy = yaml.safe_load(f)
            
        if not policy:
            logger.warning("Policy file is empty, using defaults")
            return _get_default_policy()
            
        logger.info(f"✅ Policy loaded successfully from {policy_file}")
        return policy
        
    except FileNotFoundError:
        logger.warning(f"Policy file not found: {policy_file}, using defaults")
        return _get_default_policy()
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse policy YAML: {e}")
        return _get_default_policy()
    except Exception as e:
        logger.error(f"Failed to load policy: {e}")
        return _get_default_policy()


def _get_default_policy() -> Dict[str, Any]:
    """Get default policy configuration."""
    return {
        "trading": {
            "risk": {
                "max_position_size": 0.1,
                "max_leverage": 3.0,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.04,
                "max_drawdown": 0.15
            },
            "execution": {
                "default_timeout": 30,
                "retry_attempts": 3,
                "slippage_tolerance": 0.001,
                "min_order_size": 10,
                "max_order_size": 10000
            },
            "scoring": {
                "ta_weight": 0.4,
                "ml_weight": 0.3,
                "news_weight": 0.2,
                "risk_weight": 0.1,
                "min_composite_score": 0.6
            }
        },
        "risk_limits": {
            "max_position_size": 100000.0,
            "max_leverage": 10.0,
            "max_drawdown": 0.20,
            "max_margin_ratio": 0.80,
            "max_risk_per_trade": 0.02,
            "max_portfolio_risk": 0.10,
            "max_portfolio_exposure": 0.10,
            "stop_loss_threshold": 0.05,
            "take_profit_threshold": 0.10,
            "max_correlation": 0.8,
            "max_concentration": 0.3
        },
        "bias": {
            "enabled": False,
            "trend_filter": {"enabled": True},
            "news_guard": {
                "enabled": True,
                "threshold": 0.7,
                "categories": ["REGULATION", "SECURITY"],
                "action": "block",
                "cooldown_sec": 3600
            },
            "volatility_guard": {
                "enabled": True,
                "atr_limit_pct": 0.05,
                "penalty": 15
            },
            "funding_guard": {
                "enabled": False,
                "min_abs": 0.0001,
                "action": "downgrade",
                "penalty": 10
            },
            "corr_guard": {
                "enabled": True,
                "max_correlation": 0.8,
                "max_exposure": 0.15
            }
        },
        "flags": {
            "use_ml": True,
            "use_news": True,
            "use_telegram": True,
            "advanced_risk_management": True
        }
    }


def save_policy(policy: Dict[str, Any], policy_file: str = "configs/policy.yaml") -> bool:
    """
    Save policy configuration to YAML file.
    
    Args:
        policy: Policy configuration dictionary
        policy_file: Path to policy YAML file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        policy_path = Path(policy_file)
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(policy_path, 'w', encoding='utf-8') as f:
            yaml.dump(policy, f, default_flow_style=False, indent=2, allow_unicode=True)
            
        logger.info(f"✅ Policy saved successfully to {policy_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save policy: {e}")
        return False


def validate_policy(policy: Dict[str, Any]) -> bool:
    """
    Validate policy configuration.
    
    Args:
        policy: Policy configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    try:
        required_sections = ["trading", "risk_limits", "bias"]
        
        for section in required_sections:
            if section not in policy:
                logger.error(f"Missing required policy section: {section}")
                return False
        
        # Validate risk limits
        risk_limits = policy.get("risk_limits", {})
        if not isinstance(risk_limits.get("max_position_size"), (int, float)):
            logger.error("Invalid max_position_size in risk_limits")
            return False
            
        # Validate bias configuration
        bias = policy.get("bias", {})
        if not isinstance(bias.get("enabled"), bool):
            logger.error("Invalid bias.enabled value")
            return False
            
        logger.info("✅ Policy validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Policy validation failed: {e}")
        return False


# Convenience function for common use cases
def get_risk_limits() -> Dict[str, Any]:
    """Get risk limits from policy."""
    policy = load_policy()
    return policy.get("risk_limits", {})


def get_bias_config() -> Dict[str, Any]:
    """Get bias configuration from policy."""
    policy = load_policy()
    return policy.get("bias", {})


def get_trading_config() -> Dict[str, Any]:
    """Get trading configuration from policy."""
    policy = load_policy()
    return policy.get("trading", {})


if __name__ == "__main__":
    # Test policy loading
    policy = load_policy()
    print("Policy loaded successfully!")
    print(f"Bias enabled: {policy.get('bias', {}).get('enabled', False)}")
    print(f"Risk limits: {list(policy.get('risk_limits', {}).keys())}")
