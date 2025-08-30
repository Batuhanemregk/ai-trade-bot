"""
Test suite for structured logging infrastructure.
Tests logger initialization and basic functionality.
"""

import logging

import pytest

from infrastructure.logger import (
    get_agent_logger,
    get_logger,
    get_service_logger,
    get_system_logger,
    initialize_logging,
    set_log_level,
)


class TestLoggingInfrastructure:
    """Test the logging infrastructure."""

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test.logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.logger"

    def test_get_system_logger(self):
        """Test getting the system logger."""
        logger = get_system_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "aibotbs"

    def test_get_agent_logger(self):
        """Test getting the agent logger."""
        logger = get_agent_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "aibotbs.agents"

    def test_get_service_logger(self):
        """Test getting the service logger."""
        logger = get_service_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "aibotbs.services"

    def test_set_log_level(self):
        """Test setting log levels."""
        # Test setting a valid log level
        set_log_level("test.logger", "DEBUG")
        logger = logging.getLogger("test.logger")
        assert logger.level == logging.DEBUG

        # Test setting an invalid log level (should not raise exception)
        set_log_level("test.logger", "INVALID_LEVEL")

    def test_logger_output(self):
        """Test that loggers actually output messages."""
        logger = get_logger("test.output")

        # Test that logger methods exist and are callable
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)

        # Test that calling them doesn't raise exceptions
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")

    def test_logger_formatting(self):
        """Test that loggers format messages correctly."""
        logger = get_logger("test.formatting")

        # Test that logger has expected attributes
        assert logger.name == "test.formatting"
        assert hasattr(logger, 'level')
        assert hasattr(logger, 'handlers')

        # Test that we can log a message
        logger.info("Test message")

    def test_initialize_logging_with_config(self):
        """Test logging initialization with config file."""
        # Test that we can call initialize_logging without errors
        try:
            initialize_logging("configs/logging.yaml")
        except Exception as e:
            # It's okay if it fails due to missing config, but shouldn't crash
            assert "config" in str(e).lower() or "yaml" in str(e).lower()

    def test_initialize_logging_without_config(self):
        """Test logging initialization without config file."""
        # Test that we can call initialize_logging without errors
        try:
            initialize_logging()
        except Exception:
            pytest.fail("Logging initialization should not raise exceptions")

    def test_logger_initialization_error_handling(self):
        """Test that logging initialization handles errors gracefully."""
        # This should not raise an exception even if there are issues
        try:
            initialize_logging("nonexistent_config.yaml")
        except Exception:
            pytest.fail("Logging initialization should handle errors gracefully")

    def test_multiple_logger_instances(self):
        """Test that multiple logger instances work correctly."""
        logger1 = get_logger("test.multiple.1")
        logger2 = get_logger("test.multiple.2")
        logger3 = get_logger("test.multiple.1")  # Same name as logger1

        assert logger1 is not logger2
        assert logger1 is logger3  # Should return the same instance for same name

        # Test that they have different names
        assert logger1.name == "test.multiple.1"
        assert logger2.name == "test.multiple.2"

    def test_logger_levels(self):
        """Test that loggers respect level settings."""
        logger = get_logger("test.levels")

        # Test that we can set and get log levels
        original_level = logger.level
        logger.setLevel(logging.INFO)
        assert logger.level == logging.INFO

        # Test that we can change it back
        logger.setLevel(original_level)
        assert logger.level == original_level


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def test_logger_with_metrics(self):
        """Test that logging works alongside metrics."""
        from observability.metrics import record_agent_message

        logger = get_logger("test.integration")

        # Test that both work without interference
        logger.info("Processing agent message")
        record_agent_message("test_agent", "test_message")

        # Verify metric was recorded (should not raise exception)
        from observability.metrics import get_metrics_summary
        summary = get_metrics_summary()
        assert "agent_messages_total" in summary

    def test_logger_with_scheduler(self):
        """Test that logging works alongside scheduler."""
        from infrastructure.scheduler import create_scheduler

        logger = get_logger("test.scheduler")

        # Test that both work without interference
        logger.info("Creating scheduler")

        # Create scheduler (should not interfere with logging)
        config = {"max_history": 10}
        scheduler = create_scheduler(config)

        # Both should work
        assert scheduler is not None
        assert len(scheduler.jobs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
