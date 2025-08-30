"""
Logging infrastructure for AiBotBS.
Provides structured logging with YAML configuration, multiple handlers, and colored output.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None


def initialize_logging(config_path: Optional[str] = None):
    """Initialize the logging system."""
    # Basic setup for now
    logger.remove()
    logger.add(sys.stdout, level="INFO", colorize=True)
    logger.add("logs/aibotbs.log", level="DEBUG", rotation="10 MB")
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    logger.info("✅ Basic logging initialized")


def get_logger(name: str) -> logging.Logger:
    """Get a standard library logger."""
    return logging.getLogger(name)


def set_log_level(logger_name: str, level: str):
    """Set log level for a specific logger."""
    try:
        std_logger = logging.getLogger(logger_name)
        std_logger.setLevel(getattr(logging, level.upper()))
        logger.info(f"Set log level for '{logger_name}' to {level}")
    except Exception as e:
        logger.error(f"Failed to set log level for '{logger_name}': {e}")


def set_all_log_levels(level: str):
    """Set log level for all loggers."""
    try:
        # Set loguru level
        logger.level(level.upper())
        
        # Set standard library logger levels
        for logger_name in ['agents', 'execution', 'infrastructure', 'application']:
            std_logger = logging.getLogger(logger_name)
            std_logger.setLevel(getattr(logging, level.upper()))
        
        logger.info(f"Set all log levels to {level}")
    except Exception as e:
        logger.error(f"Failed to set all log levels: {e}")


def get_log_levels() -> Dict[str, str]:
    """Get current log levels for all loggers."""
    levels = {}
    
    # Get loguru levels
    for logger_name in ['agents', 'execution', 'infrastructure', 'application']:
        try:
            level = logger.level().name
            levels[logger_name] = level
        except:
            levels[logger_name] = 'INFO'
    
    # Get standard library logger levels
    for logger_name in ['agents', 'execution', 'infrastructure', 'application']:
        std_logger = logging.getLogger(logger_name)
        levels[f"{logger_name}_std"] = logging.getLevelName(std_logger.level)
    
    return levels


def add_log_handler(logger_name: str, handler: logging.Handler):
    """Add a handler to a specific logger."""
    try:
        logger_instance = logging.getLogger(logger_name)
        logger_instance.addHandler(handler)
        logger.info(f"Added handler to logger '{logger_name}'")
    except Exception as e:
        logger.error(f"Failed to add handler to logger '{logger_name}': {e}")


def remove_log_handler(logger_name: str, handler: logging.Handler):
    """Remove a handler from a specific logger."""
    try:
        logger_instance = logging.getLogger(logger_name)
        logger_instance.removeHandler(handler)
        logger.info(f"Removed handler from logger '{logger_name}'")
    except Exception as e:
        logger.error(f"Failed to remove handler from logger '{logger_name}': {e}")


def get_agent_logger(name: str) -> logging.Logger:
    """Get agent logger with duplicate handler prevention."""
    logger_name = f"agent.{name}"
    std_logger = logging.getLogger(logger_name)
    
    # Prevent duplicate handlers
    if not std_logger.handlers:
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Use JSON formatter if available, else simple formatter
        if jsonlogger:
            formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(formatter)
        std_logger.addHandler(console_handler)
        
        # Add file handler
        file_handler = logging.FileHandler(f"logs/agent_{name}.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        std_logger.addHandler(file_handler)
        
        std_logger.setLevel(logging.DEBUG)
    
    return std_logger


def get_service_logger(name: str) -> logging.Logger:
    """Create/get logger for service.{name} with project formatters/handlers."""
    logger_name = f"service.{name}"
    service_logger = logging.getLogger(logger_name)

    # Avoid duplicate handlers
    if service_logger.handlers:
        return service_logger

    # Set level
    service_logger.setLevel(logging.INFO)

    # Create formatter
    if jsonlogger:
        # Use JSON formatter if available
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        # Fallback to simple formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    service_logger.addHandler(console_handler)

    # Create file handler
    try:
        file_handler = logging.FileHandler(f"logs/service_{name}.log")
        file_handler.setFormatter(formatter)
        service_logger.addHandler(file_handler)
    except Exception:
        pass  # File handler is optional

    return service_logger


def get_system_logger(name: str) -> logging.Logger:
    """Create/get logger for system.{name} with project formatters/handlers."""
    logger_name = f"system.{name}"
    system_logger = logging.getLogger(logger_name)

    # Avoid duplicate handlers
    if system_logger.handlers:
        return system_logger

    # Set level
    system_logger.setLevel(logging.INFO)

    # Create formatter
    if jsonlogger:
        # Use JSON formatter if available
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        # Fallback to simple formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    system_logger.addHandler(console_handler)

    # Create file handler
    try:
        file_handler = logging.FileHandler(f"logs/system_{name}.log")
        file_handler.setFormatter(formatter)
        system_logger.addHandler(file_handler)
    except Exception:
        pass  # File handler is optional

    return system_logger


def add_file_handler(logger_name: str, file_path: str, level: str = "DEBUG", 
                    formatter: Optional[logging.Formatter] = None):
    """Add a file handler to a specific logger."""
    try:
        # Create file handler
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(getattr(logging, level.upper()))
        
        # Set formatter
        if formatter:
            file_handler.setFormatter(formatter)
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
        
        # Add to logger
        logger_instance = logging.getLogger(logger_name)
        logger_instance.addHandler(file_handler)
        
        logger.info(f"Added file handler to logger '{logger_name}' (file: {file_path})")
        
    except Exception as e:
        logger.error(f"Failed to add file handler to logger '{logger_name}': {e}")


def remove_handler(logger_name: str, handler: logging.Handler):
    """Remove a handler from a specific logger."""
    try:
        logger_instance = logging.getLogger(logger_name)
        logger_instance.removeHandler(handler)
        logger.info(f"Removed handler from logger '{logger_name}'")
    except Exception as e:
        logger.error(f"Failed to remove handler from logger '{logger_name}': {e}")


def get_logger_info(logger_name: str) -> Dict[str, Any]:
    """Get information about a specific logger."""
    try:
        logger_instance = logging.getLogger(logger_name)
        return {
            'name': logger_name,
            'level': logging.getLevelName(logger_instance.level),
            'handlers': [type(h).__name__ for h in logger_instance.handlers],
            'propagate': logger_instance.propagate
        }
    except Exception as e:
        logger.error(f"Failed to get logger info for '{logger_name}': {e}")
        return {}


def list_loggers() -> List[str]:
    """List all configured loggers."""
    return ['agents', 'execution', 'infrastructure', 'application']


def rotate_logs():
    """Rotate log files."""
    logger.info("Log rotation requested")


def cleanup_old_logs(max_age_days: int = 30):
    """Clean up old log files."""
    logger.info(f"Cleanup old logs requested (max age: {max_age_days} days)")


def log_function_call(func_name: str, args: tuple = None, kwargs: dict = None):
    """Log function call for debugging."""
    try:
        args_str = str(args) if args else "()"
        kwargs_str = str(kwargs) if kwargs else "{}"
        logger.debug(f"Function call: {func_name}{args_str} {kwargs_str}")
    except Exception as e:
        logger.error(f"Failed to log function call: {e}")


def log_execution_time(func_name: str, execution_time: float):
    """Log function execution time."""
    try:
        logger.debug(f"Function {func_name} executed in {execution_time:.4f} seconds")
    except Exception as e:
        logger.error(f"Failed to log execution time: {e}")


def setup_basic_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Set up basic logging without YAML configuration."""
    # Remove existing handlers
    logger.remove()
    
    # Add console handler
    logger.add(sys.stdout, level=level, colorize=True)
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(log_file, level=level, rotation="10 MB")
    
    logger.info(f"Basic logging initialized at level {level}")


__all__ = [
    "initialize_logging",
    "get_logger",
    "set_log_level",
    "set_all_log_levels",
    "get_log_levels",
    "add_log_handler",
    "remove_log_handler",
    "get_agent_logger",
    "get_service_logger",
    "get_system_logger",
    "add_file_handler",
    "remove_handler",
    "get_logger_info",
    "list_loggers",
    "rotate_logs",
    "cleanup_old_logs",
    "log_function_call",
    "log_execution_time",
    "setup_basic_logging",
]
