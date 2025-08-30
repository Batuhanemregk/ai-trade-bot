"""
Runtime execution for the trading system.
Delegates to existing CLI and application services without duplicating logic.
"""

import asyncio
import sys
from typing import Optional

from loguru import logger

from infrastructure.cli import main as cli_main
from application.trading_orchestrator import TradingOrchestrator
from infrastructure.bootstrap import load_env, load_policy, init_logging, validate_policy, get_config_summary


def run_agents(graph: str = "default", mode: str = "dry-run", dry_run: bool = True) -> int:
    """
    Run the agent system with specified configuration.
    
    Args:
        graph: Agent graph to use
        mode: Execution mode
        dry_run: Whether to run in dry-run mode
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info(f"Starting agent system: graph={graph}, mode={mode}, dry_run={dry_run}")
        
        # Load configuration
        policy = load_policy()
        if not validate_policy(policy):
            logger.error("Invalid policy configuration")
            return 1
        
        # Show configuration summary
        config_summary = get_config_summary(policy)
        logger.info("Configuration loaded:")
        for section, values in config_summary.items():
            logger.info(f"  {section}: {values}")
        
        # Run through CLI system
        # This delegates to the existing CLI infrastructure
        sys.argv = [
            "main.py", "agents", "run",
            "--graph", graph,
            "--mode", mode,
            "--dry-run" if dry_run else "--live"
        ]
        
        return cli_main()
        
    except Exception as e:
        logger.error(f"Failed to run agents: {e}")
        return 1


def run_scheduler(job: Optional[str] = None, once: bool = False) -> int:
    """
    Run the scheduler system.
    
    Args:
        job: Specific job to run (if None, runs all scheduled jobs)
        once: Whether to run once or continuously
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info(f"Starting scheduler: job={job}, once={once}")
        
        # Load configuration
        policy = load_policy()
        if not validate_policy(policy):
            logger.error("Invalid policy configuration")
            return 1
        
        # Run through CLI system
        sys.argv = ["main.py", "scheduler"]
        if job:
            sys.argv.extend(["jobs", "run", job])
        else:
            sys.argv.extend(["start"])
        
        if once:
            sys.argv.append("--once")
        
        return cli_main()
        
    except Exception as e:
        logger.error(f"Failed to run scheduler: {e}")
        return 1


def run_trading_system(policy_path: Optional[str] = None, dry_run: bool = True) -> int:
    """
    Run the complete trading system.
    
    Args:
        policy_path: Path to policy file
        dry_run: Whether to run in dry-run mode
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info("Starting complete trading system")
        
        # Load environment variables
        load_env()
        
        # Load configuration
        policy = load_policy(policy_path or "configs/policy.yaml")
        if not validate_policy(policy):
            logger.error("Invalid policy configuration")
            return 1
        
        # Show configuration summary
        config_summary = get_config_summary(policy)
        logger.info("Trading system configuration:")
        for section, values in config_summary.items():
            logger.info(f"  {section}: {values}")
        
        # Create and run trading orchestrator
        orchestrator = TradingOrchestrator(policy)
        
        # Run the system
        success = asyncio.run(orchestrator.start())
        
        if success:
            logger.info("Trading system completed successfully")
            return 0
        else:
            logger.error("Trading system failed")
            return 1
            
    except Exception as e:
        logger.error(f"Failed to run trading system: {e}")
        return 1


def run_health_check() -> int:
    """
    Run system health check.
    
    Returns:
        Exit code (0 for healthy, non-zero for unhealthy)
    """
    try:
        logger.info("Running system health check")
        
        # Load configuration
        policy = load_policy()
        if not validate_policy(policy):
            logger.error("Policy validation failed")
            return 1
        
        # Run through CLI system
        sys.argv = ["main.py", "health"]
        return cli_main()
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return 1


def run_portfolio_status() -> int:
    """
    Show portfolio status.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        logger.info("Getting portfolio status")
        
        # Run through CLI system
        sys.argv = ["main.py", "portfolio", "status"]
        return cli_main()
        
    except Exception as e:
        logger.error(f"Failed to get portfolio status: {e}")
        return 1


def run_config_validation(policy_path: str = "configs/policy.yaml") -> int:
    """
    Validate configuration files.
    
    Args:
        policy_path: Path to policy file
        
    Returns:
        Exit code (0 for valid, non-zero for invalid)
    """
    try:
        logger.info(f"Validating configuration: {policy_path}")
        
        # Load and validate policy
        policy = load_policy(policy_path)
        if validate_policy(policy):
            logger.info("Configuration validation passed")
            
            # Show configuration summary
            config_summary = get_config_summary(policy)
            logger.info("Configuration summary:")
            for section, values in config_summary.items():
                logger.info(f"  {section}: {values}")
            
            return 0
        else:
            logger.error("Configuration validation failed")
            return 1
            
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        return 1


def main():
    """
    Main entry point for runtime execution.
    Delegates to appropriate function based on command line arguments.
    """
    try:
        # Initialize logging
        init_logging()
        
        # Load environment
        load_env()
        
        # Parse command line arguments
        if len(sys.argv) < 2:
            logger.error("Usage: python -m infrastructure.runtime <command> [options]")
            logger.info("Available commands: agents, scheduler, trading, health, portfolio, config")
            return 1
        
        command = sys.argv[1].lower()
        
        if command == "agents":
            # Parse agent options
            graph = "default"
            mode = "dry-run"
            dry_run = True
            
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--graph" and i + 1 < len(sys.argv):
                    graph = sys.argv[i + 1]
                elif arg == "--mode" and i + 1 < len(sys.argv):
                    mode = sys.argv[i + 1]
                elif arg == "--live":
                    dry_run = False
            
            return run_agents(graph, mode, dry_run)
            
        elif command == "scheduler":
            # Parse scheduler options
            job = None
            once = False
            
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--job" and i + 1 < len(sys.argv):
                    job = sys.argv[i + 1]
                elif arg == "--once":
                    once = True
            
            return run_scheduler(job, once)
            
        elif command == "trading":
            # Parse trading options
            policy_path = None
            dry_run = True
            
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--policy" and i + 1 < len(sys.argv):
                    policy_path = sys.argv[i + 1]
                elif arg == "--live":
                    dry_run = False
            
            return run_trading_system(policy_path, dry_run)
            
        elif command == "health":
            return run_health_check()
            
        elif command == "portfolio":
            return run_portfolio_status()
            
        elif command == "config":
            policy_path = "policy.yaml"
            for i, arg in enumerate(sys.argv[2:], 2):
                if arg == "--policy" and i + 1 < len(sys.argv):
                    policy_path = sys.argv[i + 1]
            
            return run_config_validation(policy_path)
            
        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Available commands: agents, scheduler, trading, health, portfolio, config")
            return 1
            
    except Exception as e:
        logger.error(f"Runtime execution failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
