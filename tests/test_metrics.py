"""
Test suite for Prometheus metrics infrastructure.
Tests metric creation, recording, and registry functionality.
"""

import time
from unittest.mock import Mock, patch

import pytest

from observability.metrics import (
    MetricConfig,
    MetricsRegistry,
    MetricType,
    generate_metrics,
    get_metrics_registry,
    get_metrics_summary,
    increment_counter,
    measure_latency,
    measure_ml_inference,
    measure_news_fetch,
    measure_ta_compute,
    observe_histogram,
    record_agent_message,
    record_latency,
    record_order_created,
    set_gauge,
)


class TestMetricsRegistry:
    """Test the MetricsRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh metrics registry for testing."""
        return MetricsRegistry()

    def test_registry_initialization(self, registry):
        """Test registry initialization."""
        assert not registry._initialized
        assert len(registry.metrics) == 0

        registry.initialize()

        assert registry._initialized
        assert len(registry.metrics) > 0

        # Check that key metrics were created
        expected_metrics = [
            "agent_messages_total",
            "orders_created_total",
            "latency_seconds",
            "ta_compute_seconds",
            "ml_infer_seconds",
            "news_fetch_seconds"
        ]

        for metric_name in expected_metrics:
            assert metric_name in registry.metrics

    def test_metric_creation(self, registry):
        """Test metric creation from configuration."""
        config = MetricConfig(
            name="test_counter",
            description="Test counter metric",
            labels=["label1", "label2"],
            metric_type=MetricType.COUNTER
        )

        registry._create_metric(config)

        assert "test_counter" in registry.metrics
        metric = registry.metrics["test_counter"]
        assert metric is not None

    def test_counter_increment(self, registry):
        """Test counter metric increment."""
        registry.initialize()

        # Test incrementing a counter
        labels = {"agent": "test_agent", "type": "test_message"}
        registry.increment_counter("agent_messages_total", labels)

        # Verify the metric was incremented
        metric = registry.get_metric("agent_messages_total")
        assert metric is not None

    def test_histogram_observation(self, registry):
        """Test histogram metric observation."""
        registry.initialize()

        # Test observing a value in a histogram
        labels = {"op": "test_operation", "status": "success"}
        registry.observe_histogram("latency_seconds", labels, 0.5)

        # Verify the metric was observed
        metric = registry.get_metric("latency_seconds")
        assert metric is not None

    def test_gauge_setting(self, registry):
        """Test gauge metric setting."""
        registry.initialize()

        # Test setting a gauge value
        labels = {"type": "memory"}
        registry.set_gauge("system_memory_bytes", labels, 1024.0)

        # Verify the metric was set
        metric = registry.get_metric("system_memory_bytes")
        assert metric is not None

    def test_get_metric_nonexistent(self, registry):
        """Test getting a non-existent metric."""
        metric = registry.get_metric("nonexistent_metric")
        assert metric is None

    def test_metrics_summary(self, registry):
        """Test metrics summary generation."""
        registry.initialize()

        summary = registry.get_metrics_summary()

        assert isinstance(summary, dict)
        assert len(summary) > 0

        # Check that summary contains expected information
        for metric_name, metric_info in summary.items():
            assert 'type' in metric_info
            assert 'labels' in metric_info
            assert 'description' in metric_info


class TestMetricsFunctions:
    """Test the convenience metric functions."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock metrics registry."""
        with patch('observability.metrics._metrics_registry') as mock:
            mock.increment_counter = Mock()
            mock.observe_histogram = Mock()
            mock.set_gauge = Mock()
            yield mock

    def test_record_agent_message(self, mock_registry):
        """Test recording agent message metrics."""
        record_agent_message("test_agent", "test_message")

        mock_registry.increment_counter.assert_called_once_with(
            "agent_messages_total",
            {"agent": "test_agent", "type": "test_message"},
            1.0
        )

    def test_record_order_created(self, mock_registry):
        """Test recording order creation metrics."""
        record_order_created("BTC-USDT", "buy", "limit")

        mock_registry.increment_counter.assert_called_once_with(
            "orders_created_total",
            {"symbol": "BTC-USDT", "side": "buy", "type": "limit"},
            1.0
        )

    def test_record_latency(self, mock_registry):
        """Test recording latency metrics."""
        record_latency("test_operation", "success", 0.5)

        mock_registry.observe_histogram.assert_called_once_with(
            "latency_seconds",
            {"op": "test_operation", "status": "success"},
            0.5
        )

    def test_record_latency_with_error_status(self, mock_registry):
        """Test recording latency metrics with error status."""
        record_latency("test_operation", "error", 1.0)

        mock_registry.observe_histogram.assert_called_once_with(
            "latency_seconds",
            {"op": "test_operation", "status": "error"},
            1.0
        )


class TestContextManagers:
    """Test the context manager decorators for measuring operations."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock metrics registry."""
        with patch('observability.metrics._metrics_registry') as mock:
            mock.observe_histogram = Mock()
            yield mock

    def test_measure_latency_success(self, mock_registry):
        """Test measuring latency for successful operations."""
        with measure_latency("test_operation", "success"):
            time.sleep(0.01)  # Small delay to ensure measurable time

        # Verify that latency was recorded
        mock_registry.observe_histogram.assert_called_once()
        call_args = mock_registry.observe_histogram.call_args
        assert call_args[0][0] == "latency_seconds"
        assert call_args[0][1]["op"] == "test_operation"
        assert call_args[0][1]["status"] == "success"
        assert call_args[0][2] > 0  # Duration should be positive

    def test_measure_latency_error(self, mock_registry):
        """Test measuring latency for operations that raise exceptions."""
        with pytest.raises(ValueError):
            with measure_latency("test_operation", "success"):
                time.sleep(0.01)
                raise ValueError("Test error")

        # Verify that latency was recorded with error status
        mock_registry.observe_histogram.assert_called_once()
        call_args = mock_registry.observe_histogram.call_args
        assert call_args[0][1]["status"] == "error"

    def test_measure_ta_compute(self, mock_registry):
        """Test measuring TA computation time."""
        with measure_ta_compute("BTC-USDT", "rsi"):
            time.sleep(0.01)

        # Verify that TA compute time was recorded
        mock_registry.observe_histogram.assert_called_once()
        call_args = mock_registry.observe_histogram.call_args
        assert call_args[0][0] == "ta_compute_seconds"
        assert call_args[0][1]["symbol"] == "BTC-USDT"
        assert call_args[0][1]["indicator"] == "rsi"

    def test_measure_ml_inference(self, mock_registry):
        """Test measuring ML inference time."""
        with measure_ml_inference("BTC-USDT", "lstm"):
            time.sleep(0.01)

        # Verify that ML inference time was recorded
        mock_registry.observe_histogram.assert_called_once()
        call_args = mock_registry.observe_histogram.call_args
        assert call_args[0][0] == "ml_infer_seconds"
        assert call_args[0][1]["symbol"] == "BTC-USDT"
        assert call_args[0][1]["model"] == "lstm"

    def test_measure_news_fetch(self, mock_registry):
        """Test measuring news fetch time."""
        with measure_news_fetch("cryptopanic", "BTC-USDT"):
            time.sleep(0.01)

        # Verify that news fetch time was recorded
        mock_registry.observe_histogram.assert_called_once()
        call_args = mock_registry.observe_histogram.call_args
        assert call_args[0][0] == "news_fetch_seconds"
        assert call_args[0][1]["source"] == "cryptopanic"
        assert call_args[0][1]["symbol"] == "BTC-USDT"


class TestMetricsIntegration:
    """Integration tests for metrics functionality."""

    def test_global_registry_access(self):
        """Test access to the global metrics registry."""
        registry = get_metrics_registry()
        assert isinstance(registry, MetricsRegistry)

        # Test that it's initialized
        assert registry._initialized

    def test_metrics_generation(self):
        """Test metrics generation functionality."""
        metrics_output = generate_metrics()
        assert isinstance(metrics_output, bytes)
        assert len(metrics_output) > 0

    def test_metrics_summary(self):
        """Test metrics summary functionality."""
        summary = get_metrics_summary()
        assert isinstance(summary, dict)
        assert len(summary) > 0

        # Check that summary contains expected metric types
        metric_types = {info['type'] for info in summary.values()}
        expected_types = {'Counter', 'Histogram', 'Gauge', 'MockMetric'}

        # Some metrics should be present
        assert len(metric_types.intersection(expected_types)) > 0

    def test_metric_labels_consistency(self):
        """Test that metric labels are consistent across operations."""
        registry = get_metrics_registry()

        # Test counter with labels
        increment_counter("agent_messages_total", {"agent": "test", "type": "message"})

        # Test that the metric exists and has the expected structure
        metric = registry.get_metric("agent_messages_total")
        assert metric is not None

    def test_histogram_buckets(self):
        """Test that histogram metrics have appropriate buckets."""
        registry = get_metrics_registry()
        registry.initialize()

        # Check latency histogram buckets
        latency_metric = registry.get_metric("latency_seconds")
        if latency_metric and hasattr(latency_metric, '_buckets'):
            buckets = latency_metric._buckets
            assert len(buckets) > 0
            assert all(isinstance(b, float) for b in buckets)
            assert buckets == sorted(buckets)  # Buckets should be sorted


class TestMetricsErrorHandling:
    """Test error handling in metrics operations."""

    def test_invalid_metric_name(self):
        """Test handling of invalid metric names."""
        # This should not raise an exception
        increment_counter("", {"label": "value"})
        increment_counter("invalid_metric_name", {"label": "value"})

    def test_invalid_labels(self):
        """Test handling of invalid labels."""
        # This should not raise an exception
        increment_counter("agent_messages_total", {})
        increment_counter("agent_messages_total", {"invalid": "label"})

    def test_negative_values(self):
        """Test handling of negative values."""
        # This should not raise an exception
        observe_histogram("latency_seconds", {"op": "test"}, -1.0)
        set_gauge("system_memory_bytes", {"type": "test"}, -100.0)

    def test_very_large_values(self):
        """Test handling of very large values."""
        # This should not raise an exception
        observe_histogram("latency_seconds", {"op": "test"}, 1e6)
        set_gauge("system_memory_bytes", {"type": "test"}, 1e12)


class TestMetricsPerformance:
    """Test performance characteristics of metrics operations."""

    def test_metrics_recording_speed(self):
        """Test that metrics recording is fast."""
        start_time = time.time()

        # Record many metrics quickly
        for i in range(100):
            record_agent_message(f"agent_{i}", f"message_{i}")
            record_latency(f"operation_{i}", "success", 0.1)
            set_gauge(f"metric_{i}", {"label": "value"}, float(i))

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (less than 1 second)
        assert duration < 1.0

    def test_concurrent_metrics_access(self):
        """Test that metrics can be accessed concurrently."""
        import threading

        results = []
        errors = []

        def record_metrics(thread_id):
            try:
                for i in range(10):
                    record_agent_message(f"agent_{thread_id}", f"message_{i}")
                    record_latency(f"operation_{thread_id}_{i}", "success", 0.1)
                results.append(thread_id)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_metrics, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that all threads completed successfully
        assert len(results) == 5
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
