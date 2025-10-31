"""
Telemetry Checker
===============

Monitoring ve telemetry kontrolleri:
- Prometheus metrics validation
- Grafana dashboard health
- Metrics endpoint accessibility
- Metric data quality
- Alert conditions
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class MetricData:
    """Metric data point."""
    timestamp: datetime
    metric_name: str
    value: float
    labels: Dict[str, str] = None
    metric_type: str = "gauge"  # gauge, counter, histogram
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}


@dataclass
class TelemetryEvent:
    """Telemetry event for tracking."""
    timestamp: datetime
    event_type: str  # metric_collected, endpoint_check, alert_triggered
    metric_name: str
    value: float
    status: str  # success, warning, error
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class TelemetryChecker:
    """Checks monitoring and telemetry systems."""
    
    def __init__(self):
        self.metrics_data: List[MetricData] = []
        self.telemetry_events: List[TelemetryEvent] = []
        self.endpoint_status: Dict[str, bool] = {}
        
    async def check_metrics_endpoint(self, metrics_url: str) -> Tuple[bool, str]:
        """
        Check metrics endpoint accessibility.
        
        Args:
            metrics_url: Prometheus metrics URL
            
        Returns:
            (success, message)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(metrics_url, timeout=10) as resp:
                    if resp.status == 200:
                        self.endpoint_status[metrics_url] = True
                        
                        # Record telemetry event
                        event = TelemetryEvent(
                            timestamp=datetime.now(),
                            event_type="endpoint_check",
                            metric_name="metrics_endpoint",
                            value=1.0,
                            status="success",
                            details={"url": metrics_url, "status_code": resp.status}
                        )
                        self.telemetry_events.append(event)
                        
                        logger.info(f"✅ Metrics endpoint accessible: {metrics_url}")
                        return True, f"Metrics endpoint accessible: {resp.status}"
                    else:
                        self.endpoint_status[metrics_url] = False
                        
                        event = TelemetryEvent(
                            timestamp=datetime.now(),
                            event_type="endpoint_check",
                            metric_name="metrics_endpoint",
                            value=0.0,
                            status="error",
                            details={"url": metrics_url, "status_code": resp.status}
                        )
                        self.telemetry_events.append(event)
                        
                        return False, f"Metrics endpoint error: {resp.status}"
                        
        except Exception as e:
            self.endpoint_status[metrics_url] = False
            
            event = TelemetryEvent(
                timestamp=datetime.now(),
                event_type="endpoint_check",
                metric_name="metrics_endpoint",
                value=0.0,
                status="error",
                details={"url": metrics_url, "error": str(e)}
            )
            self.telemetry_events.append(event)
            
            logger.error(f"❌ Metrics endpoint check failed: {e}")
            return False, f"Metrics endpoint check failed: {e}"
    
    async def collect_metrics(self, metrics_url: str) -> Tuple[bool, str]:
        """
        Collect metrics from endpoint.
        
        Args:
            metrics_url: Prometheus metrics URL
            
        Returns:
            (success, message)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(metrics_url, timeout=10) as resp:
                    if resp.status != 200:
                        return False, f"Metrics endpoint returned {resp.status}"
                    
                    metrics_text = await resp.text()
                    
                    # Parse metrics (simplified)
                    metrics_count = 0
                    for line in metrics_text.split('\n'):
                        if line and not line.startswith('#'):
                            metrics_count += 1
                            
                            # Parse metric line (simplified)
                            if ' ' in line:
                                parts = line.split(' ')
                                if len(parts) >= 2:
                                    metric_name = parts[0].split('{')[0]  # Remove labels
                                    try:
                                        value = float(parts[1])
                                        
                                        # Store metric data
                                        metric_data = MetricData(
                                            timestamp=datetime.now(),
                                            metric_name=metric_name,
                                            value=value,
                                            metric_type="gauge"  # Simplified
                                        )
                                        self.metrics_data.append(metric_data)
                                        
                                    except ValueError:
                                        continue
                    
                    # Record telemetry event
                    event = TelemetryEvent(
                        timestamp=datetime.now(),
                        event_type="metric_collected",
                        metric_name="metrics_collection",
                        value=metrics_count,
                        status="success",
                        details={"total_metrics": metrics_count}
                    )
                    self.telemetry_events.append(event)
                    
                    logger.info(f"✅ Collected {metrics_count} metrics")
                    return True, f"Collected {metrics_count} metrics"
                    
        except Exception as e:
            event = TelemetryEvent(
                timestamp=datetime.now(),
                event_type="metric_collected",
                metric_name="metrics_collection",
                value=0.0,
                status="error",
                details={"error": str(e)}
            )
            self.telemetry_events.append(event)
            
            logger.error(f"❌ Metrics collection failed: {e}")
            return False, f"Metrics collection failed: {e}"
    
    async def check_prometheus_server(self, prom_ready_url: str) -> Tuple[bool, str]:
        """
        Check Prometheus server health.
        
        Args:
            prom_ready_url: Prometheus ready endpoint URL
            
        Returns:
            (success, message)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(prom_ready_url, timeout=5) as resp:
                    if resp.status == 200:
                        self.endpoint_status[prom_ready_url] = True
                        
                        event = TelemetryEvent(
                            timestamp=datetime.now(),
                            event_type="endpoint_check",
                            metric_name="prometheus_server",
                            value=1.0,
                            status="success",
                            details={"url": prom_ready_url, "status_code": resp.status}
                        )
                        self.telemetry_events.append(event)
                        
                        logger.info(f"✅ Prometheus server ready: {prom_ready_url}")
                        return True, f"Prometheus server ready: {resp.status}"
                    else:
                        self.endpoint_status[prom_ready_url] = False
                        
                        event = TelemetryEvent(
                            timestamp=datetime.now(),
                            event_type="endpoint_check",
                            metric_name="prometheus_server",
                            value=0.0,
                            status="error",
                            details={"url": prom_ready_url, "status_code": resp.status}
                        )
                        self.telemetry_events.append(event)
                        
                        return False, f"Prometheus server error: {resp.status}"
                        
        except Exception as e:
            self.endpoint_status[prom_ready_url] = False
            
            event = TelemetryEvent(
                timestamp=datetime.now(),
                event_type="endpoint_check",
                metric_name="prometheus_server",
                value=0.0,
                status="error",
                details={"url": prom_ready_url, "error": str(e)}
            )
            self.telemetry_events.append(event)
            
            logger.error(f"❌ Prometheus server check failed: {e}")
            return False, f"Prometheus server check failed: {e}"
    
    async def check_grafana_health(self, grafana_health_url: str) -> Tuple[bool, str]:
        """
        Check Grafana server health.
        
        Args:
            grafana_health_url: Grafana health endpoint URL
            
        Returns:
            (success, message)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(grafana_health_url, timeout=5) as resp:
                    if resp.status == 200:
                        self.endpoint_status[grafana_health_url] = True
                        
                        event = TelemetryEvent(
                            timestamp=datetime.now(),
                            event_type="endpoint_check",
                            metric_name="grafana_server",
                            value=1.0,
                            status="success",
                            details={"url": grafana_health_url, "status_code": resp.status}
                        )
                        self.telemetry_events.append(event)
                        
                        logger.info(f"✅ Grafana server healthy: {grafana_health_url}")
                        return True, f"Grafana server healthy: {resp.status}"
                    else:
                        self.endpoint_status[grafana_health_url] = False
                        
                        event = TelemetryEvent(
                            timestamp=datetime.now(),
                            event_type="endpoint_check",
                            metric_name="grafana_server",
                            value=0.0,
                            status="error",
                            details={"url": grafana_health_url, "status_code": resp.status}
                        )
                        self.telemetry_events.append(event)
                        
                        return False, f"Grafana server error: {resp.status}"
                        
        except Exception as e:
            self.endpoint_status[grafana_health_url] = False
            
            event = TelemetryEvent(
                timestamp=datetime.now(),
                event_type="endpoint_check",
                metric_name="grafana_server",
                value=0.0,
                status="error",
                details={"url": grafana_health_url, "error": str(e)}
            )
            self.telemetry_events.append(event)
            
            logger.error(f"❌ Grafana health check failed: {e}")
            return False, f"Grafana health check failed: {e}"
    
    async def check_prometheus_targets(self, prom_targets_url: str) -> Tuple[bool, str]:
        """
        Check Prometheus targets status.
        
        Args:
            prom_targets_url: Prometheus targets endpoint URL
            
        Returns:
            (success, message)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(prom_targets_url, timeout=10) as resp:
                    if resp.status != 200:
                        return False, f"Prometheus targets endpoint returned {resp.status}"
                    
                    # This would parse the actual targets JSON
                    # For now, we'll just check if the endpoint is accessible
                    
                    event = TelemetryEvent(
                        timestamp=datetime.now(),
                        event_type="endpoint_check",
                        metric_name="prometheus_targets",
                        value=1.0,
                        status="success",
                        details={"url": prom_targets_url, "status_code": resp.status}
                    )
                    self.telemetry_events.append(event)
                    
                    logger.info(f"✅ Prometheus targets accessible: {prom_targets_url}")
                    return True, f"Prometheus targets accessible: {resp.status}"
                    
        except Exception as e:
            event = TelemetryEvent(
                timestamp=datetime.now(),
                event_type="endpoint_check",
                metric_name="prometheus_targets",
                value=0.0,
                status="error",
                details={"url": prom_targets_url, "error": str(e)}
            )
            self.telemetry_events.append(event)
            
            logger.error(f"❌ Prometheus targets check failed: {e}")
            return False, f"Prometheus targets check failed: {e}"
    
    async def check_metric_data_quality(self) -> Tuple[bool, str]:
        """
        Check metric data quality.
        
        Returns:
            (success, message)
        """
        try:
            if not self.metrics_data:
                return False, "No metrics data collected"
            
            # Check for required metrics
            required_metrics = [
                'aibot_trades_total',
                'aibot_composite_score',
                'aibot_portfolio_pnl_usd',
                'aibot_positions_open'
            ]
            
            collected_metrics = set(m.metric_name for m in self.metrics_data)
            missing_metrics = [m for m in required_metrics if m not in collected_metrics]
            
            if missing_metrics:
                return False, f"Missing required metrics: {missing_metrics}"
            
            # Check for recent data
            now = datetime.now()
            recent_metrics = [m for m in self.metrics_data if (now - m.timestamp).total_seconds() < 300]  # 5 minutes
            
            if not recent_metrics:
                return False, "No recent metrics data (older than 5 minutes)"
            
            # Check for valid values
            invalid_metrics = [m for m in self.metrics_data if not isinstance(m.value, (int, float)) or m.value is None]
            
            if invalid_metrics:
                return False, f"Invalid metric values found: {len(invalid_metrics)} metrics"
            
            event = TelemetryEvent(
                timestamp=datetime.now(),
                event_type="metric_collected",
                metric_name="data_quality_check",
                value=len(self.metrics_data),
                status="success",
                details={
                    "total_metrics": len(self.metrics_data),
                    "recent_metrics": len(recent_metrics),
                    "required_metrics_present": len(required_metrics) - len(missing_metrics)
                }
            )
            self.telemetry_events.append(event)
            
            logger.info(f"✅ Metric data quality check passed: {len(self.metrics_data)} metrics")
            return True, f"Metric data quality OK: {len(self.metrics_data)} metrics, {len(recent_metrics)} recent"
            
        except Exception as e:
            event = TelemetryEvent(
                timestamp=datetime.now(),
                event_type="metric_collected",
                metric_name="data_quality_check",
                value=0.0,
                status="error",
                details={"error": str(e)}
            )
            self.telemetry_events.append(event)
            
            logger.error(f"❌ Metric data quality check failed: {e}")
            return False, f"Metric data quality check failed: {e}"
    
    async def check_alert_conditions(self) -> Tuple[bool, str]:
        """
        Check alert conditions.
        
        Returns:
            (success, message)
        """
        try:
            alerts_triggered = []
            
            # Check for high drawdown
            drawdown_metrics = [m for m in self.metrics_data if 'drawdown' in m.metric_name.lower()]
            for metric in drawdown_metrics:
                if metric.value > 10.0:  # 10% drawdown threshold
                    alerts_triggered.append(f"High drawdown: {metric.metric_name}={metric.value:.1f}%")
            
            # Check for high exposure
            exposure_metrics = [m for m in self.metrics_data if 'exposure' in m.metric_name.lower()]
            for metric in exposure_metrics:
                if metric.value > 70.0:  # 70% exposure threshold
                    alerts_triggered.append(f"High exposure: {metric.metric_name}={metric.value:.1f}%")
            
            # Check for circuit breaker
            circuit_breaker_metrics = [m for m in self.metrics_data if 'circuit_breaker' in m.metric_name.lower()]
            for metric in circuit_breaker_metrics:
                if metric.value > 1.0:  # Circuit breaker active
                    alerts_triggered.append(f"Circuit breaker active: {metric.metric_name}={metric.value}")
            
            if alerts_triggered:
                for alert in alerts_triggered:
                    event = TelemetryEvent(
                        timestamp=datetime.now(),
                        event_type="alert_triggered",
                        metric_name="alert_condition",
                        value=1.0,
                        status="warning",
                        details={"alert": alert}
                    )
                    self.telemetry_events.append(event)
                
                logger.warning(f"⚠️ Alerts triggered: {alerts_triggered}")
                return False, f"Alerts triggered: {alerts_triggered}"
            else:
                logger.info("✅ No alert conditions triggered")
                return True, "No alert conditions triggered"
                
        except Exception as e:
            event = TelemetryEvent(
                timestamp=datetime.now(),
                event_type="alert_triggered",
                metric_name="alert_condition",
                value=0.0,
                status="error",
                details={"error": str(e)}
            )
            self.telemetry_events.append(event)
            
            logger.error(f"❌ Alert conditions check failed: {e}")
            return False, f"Alert conditions check failed: {e}"
    
    async def check_monitoring_completeness(self) -> Tuple[bool, str]:
        """
        Check monitoring system completeness.
        
        Returns:
            (success, message)
        """
        try:
            checks = []
            
            # Check endpoint accessibility
            accessible_endpoints = sum(1 for status in self.endpoint_status.values() if status)
            total_endpoints = len(self.endpoint_status)
            
            if accessible_endpoints == total_endpoints:
                checks.append("All endpoints accessible")
            else:
                checks.append(f"Only {accessible_endpoints}/{total_endpoints} endpoints accessible")
            
            # Check metrics collection
            if self.metrics_data:
                checks.append(f"{len(self.metrics_data)} metrics collected")
            else:
                checks.append("No metrics collected")
            
            # Check telemetry events
            if self.telemetry_events:
                checks.append(f"{len(self.telemetry_events)} telemetry events")
            else:
                checks.append("No telemetry events")
            
            # Check for errors
            error_events = [e for e in self.telemetry_events if e.status == "error"]
            if error_events:
                checks.append(f"{len(error_events)} error events")
            else:
                checks.append("No error events")
            
            # Check for warnings
            warning_events = [e for e in self.telemetry_events if e.status == "warning"]
            if warning_events:
                checks.append(f"{len(warning_events)} warning events")
            else:
                checks.append("No warning events")
            
            logger.info(f"✅ Monitoring completeness: {', '.join(checks)}")
            return True, f"Monitoring completeness: {', '.join(checks)}"
            
        except Exception as e:
            logger.error(f"❌ Monitoring completeness check failed: {e}")
            return False, f"Monitoring completeness check failed: {e}"
    
    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Get summary of all telemetry data."""
        return {
            'total_metrics': len(self.metrics_data),
            'total_events': len(self.telemetry_events),
            'endpoint_status': self.endpoint_status.copy(),
            'events_by_type': {
                event_type: len([e for e in self.telemetry_events if e.event_type == event_type])
                for event_type in ['metric_collected', 'endpoint_check', 'alert_triggered']
            },
            'events_by_status': {
                status: len([e for e in self.telemetry_events if e.status == status])
                for status in ['success', 'warning', 'error']
            },
            'metrics_by_name': {
                metric_name: len([m for m in self.metrics_data if m.metric_name == metric_name])
                for metric_name in set(m.metric_name for m in self.metrics_data)
            },
            'accessible_endpoints': sum(1 for status in self.endpoint_status.values() if status),
            'total_endpoints': len(self.endpoint_status)
        }
    
    def get_metrics_data(self) -> List[Dict]:
        """Get all metrics data for analysis."""
        return [
            {
                'timestamp': m.timestamp.isoformat(),
                'metric_name': m.metric_name,
                'value': m.value,
                'labels': m.labels,
                'metric_type': m.metric_type
            }
            for m in self.metrics_data
        ]
    
    def get_telemetry_events(self) -> List[Dict]:
        """Get all telemetry events for analysis."""
        return [
            {
                'timestamp': e.timestamp.isoformat(),
                'event_type': e.event_type,
                'metric_name': e.metric_name,
                'value': e.value,
                'status': e.status,
                'details': e.details
            }
            for e in self.telemetry_events
        ]


