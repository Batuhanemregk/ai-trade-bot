"""
Main entry point for the AiBotBS trading system.

This file has been refactored to follow SOLID principles:
- Single Responsibility: Only handles entry point and delegation
- Open/Closed: Extensible through new modules
- Liskov Substitution: Uses interfaces and abstractions
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depends on abstractions, not concretions

Code has been moved to:
- infrastructure/bootstrap.py: Environment and config loading
- infrastructure/runtime.py: Runtime execution logic
- domain/trading_orchestrator.py: Main trading coordination
- domain/analysis_engine.py: Technical analysis
- domain/position_monitor.py: Position monitoring
- infrastructure/cli.py: Command line interface

Usage:
    python main.py [command] [options]
    
Commands:
    agents     - Run agent system
    scheduler  - Run scheduler
    trading    - Run complete trading system
    health     - Run health check
    portfolio  - Show portfolio status
    config     - Validate configuration
"""

import sys
from loguru import logger

# Import the new runtime system
from infrastructure.runtime import main as runtime_main


def main():
    """
    Main entry point that delegates to the runtime system.
    
    This function serves as a thin wrapper that:
    1. Sets up basic logging
    2. Delegates execution to infrastructure.runtime
    3. Handles any top-level exceptions
    """
    try:
        # Set up basic logging for the entry point
        logger.add(
            "logs/main.log",
            rotation="1 day",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
        )
        
        logger.info("AiBotBS Trading System starting...")
        logger.info("Main entry point delegating to infrastructure.runtime")
        
        # Delegate to the runtime system
        # This handles all the actual business logic
        exit_code = runtime_main()
        
        logger.info(f"AiBotBS Trading System completed with exit code: {exit_code}")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down gracefully")
        return 0
        
    except Exception as e:
        logger.error(f"Fatal error in main entry point: {e}")
        logger.exception("Stack trace:")
        return 1


if __name__ == "__main__":
    # Exit with the appropriate code
    sys.exit(main())


# ============================================================================
# DEPRECATION SHIMS - For backward compatibility
# These functions forward to the new modules and emit deprecation warnings
# ============================================================================

import warnings
from typing import Any, Dict, Optional


def _deprecation_warning(old_name: str, new_location: str):
    """Helper to emit deprecation warnings."""
    warnings.warn(
        f"{old_name} is deprecated and will be removed. "
        f"Use {new_location} instead.",
        DeprecationWarning,
        stacklevel=3
    )


def load_policy(policy_path: str = "policy.yaml") -> Dict[str, Any]:
    """
    DEPRECATED: Load trading policy configuration.
    
    Use infrastructure.bootstrap.load_policy() instead.
    """
    _deprecation_warning("load_policy", "infrastructure.bootstrap.load_policy")
    
    from infrastructure.bootstrap import load_policy as new_load_policy
    return new_load_policy(policy_path)


def is_dry_run() -> bool:
    """
    DEPRECATED: Check if system is running in dry-run mode.
    
    Use policy configuration directly instead.
    """
    _deprecation_warning("is_dry_run", "policy configuration")
    
    try:
        policy = load_policy()
        return policy.get('trading', {}).get('dry_run', True)
    except Exception:
        return True


def is_paper_trading() -> bool:
    """
    DEPRECATED: Check if system is running in paper trading mode.
    
    Use policy configuration directly instead.
    """
    _deprecation_warning("is_paper_trading", "policy configuration")
    
    try:
        policy = load_policy()
        return policy.get('trading', {}).get('paper_trading', True)
    except Exception:
        return True


def get_symbols() -> list:
    """
    DEPRECATED: Get list of trading symbols.
    
    Use policy configuration directly instead.
    """
    _deprecation_warning("get_symbols", "policy configuration")
    
    try:
        policy = load_policy()
        return policy.get('symbols', ['BTC-USDT', 'ETH-USDT'])
    except Exception:
        return ['BTC-USDT', 'ETH-USDT']


def get_timeframe() -> str:
    """
    DEPRECATED: Get default trading timeframe.
    
    Use policy configuration directly instead.
    """
    _deprecation_warning("get_timeframe", "policy configuration")
    
    try:
        policy = load_policy()
        return policy.get('trading', {}).get('default_timeframe', '1h')
    except Exception:
        return '1h'


# ============================================================================
# LEGACY COMPATIBILITY - For any remaining old imports
# ============================================================================

class LegacyTradingBot:
    """
    DEPRECATED: Legacy trading bot class for backward compatibility.
    
    This class is maintained only for backward compatibility.
    New code should use application.trading_orchestrator.TradingOrchestrator
    """
    
    def __init__(self):
        _deprecation_warning("LegacyTradingBot", "application.trading_orchestrator.TradingOrchestrator")
        
        # Import the new orchestrator
        from application.trading_orchestrator import TradingOrchestrator
        from infrastructure.bootstrap import load_policy
        
        policy = load_policy()
        self.orchestrator = TradingOrchestrator(policy)
        
        # Set up legacy attributes for compatibility
        self.policy = policy
        self.symbols = policy.get('symbols', ['BTC-USDT', 'ETH-USDT'])
        self.timeframe = policy.get('trading', {}).get('default_timeframe', '1h')
        self.running = False
    
    async def start(self):
        """Start the trading system."""
        return await self.orchestrator.start()
    
    async def stop(self):
        """Stop the trading system."""
        await self.orchestrator.stop()
    
    def get_status(self):
        """Get system status."""
        return self.orchestrator.get_status()


# Export legacy names for backward compatibility
TradingBot = LegacyTradingBot
