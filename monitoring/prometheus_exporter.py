"""
Prometheus Exporter
-------------------
Exports trading bot metrics in Prometheus format.

Metrics Categories:
- Trades: Total trades, win/loss counts, PnL
- Scoring: Composite scores, component scores
- Risk: Drawdown, exposure, position sizes
- System: Job execution times, errors
"""
import time
from typing import Dict, Any, Optional
from loguru import logger
from prometheus_client import (
    Counter, Gauge, Histogram, Info,
    CollectorRegistry, generate_latest,
    start_http_server, CONTENT_TYPE_LATEST
)


class PrometheusExporter:
    """
    Prometheus metrics exporter for trading bot.
    
    Usage:
        exporter = PrometheusExporter(port=8000)
        exporter.start()
        
        # Record metrics
        exporter.record_trade('BTC-USDT', 'LONG', 'win', 42.50)
        exporter.update_score('BTC-USDT', 75.3)
    """
    
    def __init__(self, port: int = 8000, registry: Optional[CollectorRegistry] = None):
        """
        Initialize Prometheus exporter.
        
        Args:
            port: HTTP port for metrics endpoint
            registry: Custom registry (optional, uses default if None)
        """
        self.port = port
        self.registry = registry or CollectorRegistry()
        self.server = None
        
        # Initialize all metrics
        self._init_metrics()
        
        logger.info(f"Prometheus exporter initialized (port={port})")
    
    def _init_metrics(self):
        """Initialize all Prometheus metrics."""
        
        # ============================================================
        # TRADE METRICS
        # ============================================================
        
        # Total trades counter
        self.trades_total = Counter(
            'aibot_trades_total',
            'Total number of trades executed',
            ['symbol', 'direction', 'result'],  # result: win, loss, breakeven
            registry=self.registry
        )
        
        # Realized PnL gauge (per symbol)
        self.pnl_realized = Gauge(
            'aibot_pnl_realized_usd',
            'Realized PnL in USD',
            ['symbol'],
            registry=self.registry
        )
        
        # Total portfolio PnL
        self.portfolio_pnl = Gauge(
            'aibot_portfolio_pnl_usd',
            'Total portfolio PnL in USD',
            registry=self.registry
        )
        
        # Win rate gauge
        self.win_rate = Gauge(
            'aibot_win_rate',
            'Win rate percentage',
            ['symbol'],
            registry=self.registry
        )
        
        # Average trade PnL
        self.avg_trade_pnl = Gauge(
            'aibot_avg_trade_pnl_usd',
            'Average PnL per trade in USD',
            ['symbol'],
            registry=self.registry
        )
        
        # Trade duration histogram
        self.trade_duration = Histogram(
            'aibot_trade_duration_minutes',
            'Trade duration in minutes',
            ['symbol'],
            registry=self.registry
        )
        
        # ============================================================
        # SCORING METRICS
        # ============================================================
        
        # Composite score
        self.composite_score = Gauge(
            'aibot_composite_score',
            'Latest composite score (0-100)',
            ['symbol'],
            registry=self.registry
        )
        
        # Component scores
        self.ta_score = Gauge(
            'aibot_ta_score',
            'Technical analysis score (0-100)',
            ['symbol'],
            registry=self.registry
        )
        
        self.ml_score = Gauge(
            'aibot_ml_score',
            'Machine learning score (0-100)',
            ['symbol'],
            registry=self.registry
        )
        
        self.news_score = Gauge(
            'aibot_news_score',
            'News sentiment score (0-100)',
            ['symbol'],
            registry=self.registry
        )
        
        self.risk_score = Gauge(
            'aibot_risk_score',
            'Risk assessment score (0-100)',
            ['symbol'],
            registry=self.registry
        )
        
        # ML confidence
        self.ml_confidence = Gauge(
            'aibot_ml_confidence',
            'ML model confidence (0=low, 1=medium, 2=high)',
            ['symbol'],
            registry=self.registry
        )
        
        # Last signal (NEW - for enhanced logging)
        self.last_signal = Gauge(
            'aibot_last_signal',
            'Last trading signal score with direction',
            ['symbol', 'direction'],  # direction: LONG, SHORT, HOLD
            registry=self.registry
        )
        
        # Analysis execution counter (NEW)
        self.analysis_total = Counter(
            'aibot_analysis_total',
            'Total analyses performed',
            ['symbol', 'direction'],
            registry=self.registry
        )
        
        # Analysis duration (NEW)
        self.analysis_duration = Histogram(
            'aibot_analysis_duration_seconds',
            'Analysis execution duration in seconds',
            ['symbol'],
            registry=self.registry
        )
        
        # ============================================================
        # RISK METRICS
        # ============================================================
        
        # Current drawdown
        self.drawdown_current = Gauge(
            'aibot_drawdown_current',
            'Current drawdown percentage',
            registry=self.registry
        )
        
        # Maximum drawdown
        self.drawdown_max = Gauge(
            'aibot_drawdown_max',
            'Maximum drawdown percentage',
            registry=self.registry
        )
        
        # Portfolio exposure
        self.exposure_pct = Gauge(
            'aibot_exposure_percentage',
            'Portfolio exposure percentage',
            registry=self.registry
        )
        
        # Total exposure in USD
        self.exposure_usd = Gauge(
            'aibot_exposure_usd',
            'Total exposure in USD',
            registry=self.registry
        )
        
        # Position count
        self.positions_open = Gauge(
            'aibot_positions_open',
            'Number of open positions',
            registry=self.registry
        )
        
        # Position size per symbol
        self.position_size = Gauge(
            'aibot_position_size_usd',
            'Position size in USD',
            ['symbol'],
            registry=self.registry
        )
        
        # Leverage used
        self.leverage_used = Gauge(
            'aibot_leverage_used',
            'Leverage multiplier used',
            ['symbol'],
            registry=self.registry
        )
        
        # ============================================================
        # SYSTEM METRICS
        # ============================================================
        
        # Job execution time
        self.job_duration = Histogram(
            'aibot_job_duration_seconds',
            'Job execution duration in seconds',
            ['job_name'],
            registry=self.registry
        )
        
        # Job success/failure
        self.job_executions = Counter(
            'aibot_job_executions_total',
            'Total job executions',
            ['job_name', 'status'],  # status: success, failure
            registry=self.registry
        )
        
        # Error counter
        self.errors_total = Counter(
            'aibot_errors_total',
            'Total errors encountered',
            ['error_type', 'component'],
            registry=self.registry
        )
        
        # API calls
        self.api_calls = Counter(
            'aibot_api_calls_total',
            'Total API calls made',
            ['exchange', 'endpoint'],
            registry=self.registry
        )
        
        # API latency
        self.api_latency = Histogram(
            'aibot_api_latency_seconds',
            'API call latency in seconds',
            ['exchange', 'endpoint'],
            registry=self.registry
        )
        
        # Circuit breaker status
        self.circuit_breaker_state = Gauge(
            'aibot_circuit_breaker_state',
            'Circuit breaker state (0=normal, 1=warning, 2=emergency, 3=paused)',
            registry=self.registry
        )
        
        # Bot info
        self.bot_info = Info(
            'aibot_info',
            'Bot version and configuration info',
            registry=self.registry
        )
        
        # System uptime
        self.uptime_seconds = Gauge(
            'aibot_uptime_seconds',
            'Bot uptime in seconds',
            registry=self.registry
        )
        
        # ============================================================
        # LLM METRICS
        # ============================================================
        
        # LLM requests counter
        self.llm_requests_total = Counter(
            'aibot_llm_requests_total',
            'Total LLM requests made',
            ['status'],  # status: 2xx, 4xx, 5xx
            registry=self.registry
        )
        
        # LLM rate limits counter
        self.llm_rate_limits_total = Counter(
            'aibot_llm_rate_limits_total',
            'Total LLM rate limit hits',
            ['source'],  # source: openai
            registry=self.registry
        )
        
        # LLM internal errors counter
        self.llm_internal_errors_total = Counter(
            'aibot_llm_internal_errors_total',
            'Total LLM internal/network errors',
            registry=self.registry
        )
        
        # LLM request tokens
        self.llm_request_tokens_sum = Counter(
            'aibot_llm_request_tokens_sum',
            'Total LLM request tokens used',
            ['model'],
            registry=self.registry
        )
        
        # LLM response tokens
        self.llm_response_tokens_sum = Counter(
            'aibot_llm_response_tokens_sum',
            'Total LLM response tokens used',
            ['model'],
            registry=self.registry
        )
        
        # LLM cost tracking
        self.llm_cost_usd_total = Counter(
            'aibot_llm_cost_usd_total',
            'Total LLM cost in USD',
            registry=self.registry
        )
        
        # LLM budget trips
        self.llm_budget_trips_total = Counter(
            'aibot_llm_budget_trips_total',
            'Total budget limit trips',
            ['type'],  # type: tokens, usd
            registry=self.registry
        )
        
        # News items tracking
        self.news_items_total = Counter(
            'aibot_news_items_total',
            'Total news items processed',
            ['sent_to_llm'],  # sent_to_llm: true, false
            registry=self.registry
        )
        
        # News digest hits
        self.news_digest_hits_total = Counter(
            'aibot_news_digest_hits_total',
            'Total news digest cache hits',
            registry=self.registry
        )
        
        # Strategy Mode Metrics
        self.strategy_mode = Gauge(
            'aibot_strategy_mode',
            'Current strategy mode',
            ['mode'],  # 'single_flip' or 'scale_in'
            registry=self.registry
        )
        
        self.open_transitions_total = Counter(
            'aibot_open_transitions_total',
            'Total state transitions to OPEN',
            ['symbol', 'direction'],
            registry=self.registry
        )
        
        self.flip_events_total = Counter(
            'aibot_flip_events_total',
            'Total flip events',
            ['symbol', 'from_direction', 'to_direction'],
            registry=self.registry
        )
        
        self.entry_skips_total = Counter(
            'aibot_entry_skips_total',
            'Total entry skips',
            ['reason'],  # 'once_per_bar', 'same_dir_block', 'below_min', etc.
            registry=self.registry
        )
        
        self.position_tpsl_applied_total = Counter(
            'aibot_position_tpsl_applied_total',
            'Total position-level TP/SL applied',
            ['symbol', 'mode'],  # 'LIVE', 'PAPER', 'DRY-RUN'
            registry=self.registry
        )
        
        self.trailing_modify_total = Counter(
            'aibot_trailing_modify_total',
            'Total trailing stop modifications',
            ['symbol', 'mode'],
            registry=self.registry
        )
        
        self.orders_blocked_total = Counter(
            'aibot_orders_blocked_total',
            'Total orders blocked by mode',
            ['mode'],  # 'DRY_RUN', 'PAPER'
            registry=self.registry
        )
        
        self.start_time = time.time()
        
        logger.info("Initialized Prometheus metrics")
    
    def start(self):
        """Start HTTP server for metrics endpoint."""
        try:
            start_http_server(self.port, registry=self.registry)
            self.server = True
            logger.info(f"📊 Prometheus metrics server started: http://localhost:{self.port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")
            raise
    
    def get_metrics(self) -> bytes:
        """Get metrics in Prometheus format."""
        return generate_latest(self.registry)
    
    # ============================================================
    # RECORDING METHODS
    # ============================================================
    
    def record_trade(self, symbol: str, direction: str, result: str, pnl: float, duration_minutes: Optional[float] = None):
        """
        Record a completed trade.
        
        Args:
            symbol: Trading symbol
            direction: LONG or SHORT
            result: win, loss, or breakeven
            pnl: Realized PnL in USD
            duration_minutes: Trade duration in minutes
        """
        self.trades_total.labels(symbol=symbol, direction=direction, result=result).inc()
        self.pnl_realized.labels(symbol=symbol).set(pnl)
        
        if duration_minutes:
            self.trade_duration.labels(symbol=symbol).observe(duration_minutes)
        
        logger.debug(f"Recorded trade: {symbol} {direction} {result} PnL=${pnl:.2f}")
    
    def update_scores(self, symbol: str, scores: Dict[str, float]):
        """
        Update scoring metrics.
        
        Args:
            symbol: Trading symbol
            scores: Dictionary with keys: composite, ta, ml, news, risk
        """
        if 'composite' in scores:
            self.composite_score.labels(symbol=symbol).set(scores['composite'])
        
        if 'ta' in scores:
            self.ta_score.labels(symbol=symbol).set(scores['ta'])
        
        if 'ml' in scores:
            self.ml_score.labels(symbol=symbol).set(scores['ml'])
        
        if 'news' in scores:
            self.news_score.labels(symbol=symbol).set(scores['news'])
        
        if 'risk' in scores:
            self.risk_score.labels(symbol=symbol).set(scores['risk'])
        
        logger.debug(f"Updated scores for {symbol}: composite={scores.get('composite', 0):.1f}")
    
    def update_ml_confidence(self, symbol: str, confidence: str):
        """
        Update ML confidence level.
        
        Args:
            symbol: Trading symbol
            confidence: 'low', 'medium', or 'high'
        """
        confidence_map = {'low': 0, 'medium': 1, 'high': 2}
        value = confidence_map.get(confidence.lower(), 0)
        self.ml_confidence.labels(symbol=symbol).set(value)
    
    def update_portfolio_metrics(self, metrics: Dict[str, Any]):
        """
        Update portfolio-level metrics.
        
        Args:
            metrics: Dictionary with keys: pnl, drawdown, max_drawdown, exposure_pct, exposure_usd, positions_open
        """
        if 'pnl' in metrics:
            self.portfolio_pnl.set(metrics['pnl'])
        
        if 'drawdown' in metrics:
            self.drawdown_current.set(metrics['drawdown'] * 100)  # Convert to percentage
        
        if 'max_drawdown' in metrics:
            self.drawdown_max.set(metrics['max_drawdown'] * 100)
        
        if 'exposure_pct' in metrics:
            self.exposure_pct.set(metrics['exposure_pct'] * 100)
        
        if 'exposure_usd' in metrics:
            self.exposure_usd.set(metrics['exposure_usd'])
        
        if 'positions_open' in metrics:
            self.positions_open.set(metrics['positions_open'])
        
        logger.debug(f"Updated portfolio metrics: PnL=${metrics.get('pnl', 0):.2f}")
    
    def update_position(self, symbol: str, size_usd: float, leverage: float):
        """Update position metrics."""
        self.position_size.labels(symbol=symbol).set(size_usd)
        self.leverage_used.labels(symbol=symbol).set(leverage)
    
    def record_job_execution(self, job_name: str, duration_seconds: float, success: bool):
        """Record job execution metrics."""
        self.job_duration.labels(job_name=job_name).observe(duration_seconds)
        status = 'success' if success else 'failure'
        self.job_executions.labels(job_name=job_name, status=status).inc()
    
    def record_error(self, error_type: str, component: str):
        """Record an error occurrence."""
        self.errors_total.labels(error_type=error_type, component=component).inc()
    
    def record_api_call(self, exchange: str, endpoint: str, latency_seconds: float):
        """Record API call metrics."""
        self.api_calls.labels(exchange=exchange, endpoint=endpoint).inc()
        self.api_latency.labels(exchange=exchange, endpoint=endpoint).observe(latency_seconds)
    
    def update_circuit_breaker(self, state: str):
        """
        Update circuit breaker state.
        
        Args:
            state: 'normal', 'warning', 'emergency', or 'paused'
        """
        state_map = {'normal': 0, 'warning': 1, 'emergency': 2, 'paused': 3}
        value = state_map.get(state.lower(), 0)
        self.circuit_breaker_state.set(value)
    
    def set_bot_info(self, version: str, mode: str, symbols: str):
        """Set bot information."""
        self.bot_info.info({
            'version': version,
            'mode': mode,
            'symbols': symbols
        })
    
    def update_uptime(self):
        """Update uptime metric."""
        uptime = time.time() - self.start_time
        self.uptime_seconds.set(uptime)
    
    def update_win_rate(self, symbol: str, win_rate: float):
        """Update win rate for a symbol."""
        self.win_rate.labels(symbol=symbol).set(win_rate * 100)  # Convert to percentage
    
    def update_avg_trade_pnl(self, symbol: str, avg_pnl: float):
        """Update average trade PnL."""
        self.avg_trade_pnl.labels(symbol=symbol).set(avg_pnl)
    
    def set_last_signal(self, symbol: str, direction: str, score: float):
        """
        Set last signal metric (NEW - for enhanced logging).
        
        Args:
            symbol: Trading symbol
            direction: LONG, SHORT, or HOLD
            score: Final composite score (0-100)
        """
        self.last_signal.labels(symbol=symbol, direction=direction).set(score)
        logger.debug(f"Updated last_signal metric: {symbol} {direction} score={score:.1f}")
    
    def inc_analysis_total(self, symbol: str, direction: str):
        """
        Increment analysis counter (NEW).
        
        Args:
            symbol: Trading symbol
            direction: Signal direction
        """
        self.analysis_total.labels(symbol=symbol, direction=direction).inc()
    
    def record_analysis_duration(self, symbol: str, duration_seconds: float):
        """
        Record analysis duration (NEW).
        
        Args:
            symbol: Trading symbol
            duration_seconds: Duration in seconds
        """
        self.analysis_duration.labels(symbol=symbol).observe(duration_seconds)
    
    # ============================================================
    # LLM METRICS METHODS
    # ============================================================
    
    def record_llm_request(self, status: str, model: str = "unknown"):
        """
        Record LLM request.
        
        Args:
            status: HTTP status category (2xx, 4xx, 5xx)
            model: LLM model used
        """
        self.llm_requests_total.labels(status=status).inc()
        logger.debug(f"Recorded LLM request: status={status}, model={model}")
    
    def record_llm_rate_limit(self, source: str = "openai"):
        """
        Record LLM rate limit hit.
        
        Args:
            source: Rate limit source (openai)
        """
        self.llm_rate_limits_total.labels(source=source).inc()
        logger.debug(f"Recorded LLM rate limit: source={source}")
    
    def record_llm_internal_error(self):
        """Record LLM internal/network error."""
        self.llm_internal_errors_total.inc()
        logger.debug("Recorded LLM internal error")
    
    def record_llm_tokens(self, model: str, request_tokens: int, response_tokens: int):
        """
        Record LLM token usage.
        
        Args:
            model: LLM model used
            request_tokens: Number of request tokens
            response_tokens: Number of response tokens
        """
        self.llm_request_tokens_sum.labels(model=model).inc(request_tokens)
        self.llm_response_tokens_sum.labels(model=model).inc(response_tokens)
        logger.debug(f"Recorded LLM tokens: model={model}, req={request_tokens}, resp={response_tokens}")
    
    def record_llm_cost(self, cost_usd: float):
        """
        Record LLM cost in USD.
        
        Args:
            cost_usd: Cost in USD
        """
        self.llm_cost_usd_total.inc(cost_usd)
        logger.debug(f"Recorded LLM cost: ${cost_usd:.6f}")
    
    def record_budget_trip(self, trip_type: str):
        """
        Record budget limit trip.
        
        Args:
            trip_type: Type of trip (tokens, usd)
        """
        self.llm_budget_trips_total.labels(type=trip_type).inc()
        logger.debug(f"Recorded budget trip: {trip_type}")
    
    def record_news_items(self, count: int, sent_to_llm: bool, reason: str = "success"):
        """
        Record news items processed.
        
        Args:
            count: Number of news items
            sent_to_llm: Whether items were sent to LLM
            reason: Reason if not sent (budget_exceeded, error, digest_hit)
        """
        self.news_items_total.labels(sent_to_llm=str(sent_to_llm).lower()).inc(count)
        logger.debug(f"Recorded news items: count={count}, sent_to_llm={sent_to_llm}, reason={reason}")
    
    def record_digest_hit(self):
        """Record news digest cache hit."""
        self.news_digest_hits_total.inc()
    
    def record_strategy_mode(self, mode: str):
        """Record current strategy mode."""
        # Set all modes to 0, then set current to 1
        self.strategy_mode.labels(mode='single_flip').set(0)
        self.strategy_mode.labels(mode='scale_in').set(0)
        self.strategy_mode.labels(mode=mode).set(1)
    
    def record_open_transition(self, symbol: str, direction: str):
        """Record state transition to OPEN."""
        self.open_transitions_total.labels(symbol=symbol, direction=direction).inc()
    
    def record_flip_event(self, symbol: str, from_direction: str, to_direction: str):
        """Record flip event."""
        self.flip_events_total.labels(
            symbol=symbol, 
            from_direction=from_direction, 
            to_direction=to_direction
        ).inc()
    
    def record_entry_skip(self, reason: str):
        """Record entry skip."""
        self.entry_skips_total.labels(reason=reason).inc()
    
    def record_position_tpsl(self, symbol: str, mode: str):
        """Record position-level TP/SL applied."""
        self.position_tpsl_applied_total.labels(symbol=symbol, mode=mode).inc()
    
    def record_trailing_modify(self, symbol: str, mode: str):
        """Record trailing stop modification."""
        self.trailing_modify_total.labels(symbol=symbol, mode=mode).inc()
    
    def record_order_blocked(self, mode: str):
        """Record order blocked by mode."""
        self.orders_blocked_total.labels(mode=mode).inc()
        logger.debug("Recorded digest cache hit")


# Global registry instance
_global_registry = None
_global_exporter = None


def get_metrics_registry() -> CollectorRegistry:
    """Get the global metrics registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = CollectorRegistry()
    return _global_registry


def get_prometheus_exporter(port: int = 8000) -> PrometheusExporter:
    """
    Get or create the global Prometheus exporter.
    
    Args:
        port: HTTP port for metrics endpoint
    
    Returns:
        PrometheusExporter instance
    """
    global _global_exporter
    
    if _global_exporter is None:
        registry = get_metrics_registry()
        _global_exporter = PrometheusExporter(port=port, registry=registry)
    
    return _global_exporter



