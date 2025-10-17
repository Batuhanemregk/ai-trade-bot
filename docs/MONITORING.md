# 📊 MONITORING GUIDE
## AiBotBS Trading Bot Monitoring & Observability

> **Real-time metrics, alerting, and performance tracking with Prometheus + Grafana**

---

## 🎯 **Overview**

AiBotBS provides comprehensive monitoring through:
- **Prometheus** - Metrics collection and storage
- **Grafana** - Visual dashboards and alerting
- **Log aggregation** - Structured logging with Loguru

---

## 🚀 **Quick Start**

### **1. Enable Monitoring**

Edit `configs/policy.yaml`:

```yaml
monitoring:
  prometheus:
    enabled: true
    port: 8000
  
  alerts:
    drawdown_threshold: 0.10   # 10% drawdown alert
    exposure_threshold: 0.70   # 70% exposure alert
    loss_streak_threshold: 3   # 3 consecutive losses alert
```

### **2. Install Dependencies**

```bash
pip install prometheus-client
```

### **3. Start the Bot**

```bash
python -m infrastructure.scheduler_runner
```

Prometheus metrics will be available at: **`http://localhost:8000/metrics`**

---

## 📈 **Metrics Categories**

### **1. Trade Metrics**

| Metric | Type | Description |
|--------|------|-------------|
| `aibot_trades_total` | Counter | Total trades executed (labels: symbol, direction, result) |
| `aibot_pnl_realized_usd` | Gauge | Realized PnL in USD per symbol |
| `aibot_portfolio_pnl_usd` | Gauge | Total portfolio PnL |
| `aibot_win_rate` | Gauge | Win rate percentage per symbol |
| `aibot_avg_trade_pnl_usd` | Gauge | Average PnL per trade |
| `aibot_trade_duration_minutes` | Histogram | Trade duration distribution |

**Example Queries:**

```promql
# Total trades in last hour
increase(aibot_trades_total[1h])

# Win rate by symbol
aibot_win_rate{symbol="BTC-USDT"}

# Portfolio PnL over time
aibot_portfolio_pnl_usd
```

### **2. Scoring Metrics**

| Metric | Type | Description |
|--------|------|-------------|
| `aibot_composite_score` | Gauge | Latest composite score (0-100) |
| `aibot_ta_score` | Gauge | Technical analysis score |
| `aibot_ml_score` | Gauge | Machine learning score |
| `aibot_news_score` | Gauge | News sentiment score |
| `aibot_risk_score` | Gauge | Risk assessment score |
| `aibot_ml_confidence` | Gauge | ML confidence level (0=low, 1=med, 2=high) |

**Example Queries:**

```promql
# Composite score trend
aibot_composite_score{symbol="BTC-USDT"}

# Score component breakdown
aibot_ta_score{symbol="BTC-USDT"}
aibot_ml_score{symbol="BTC-USDT"}
aibot_news_score{symbol="BTC-USDT"}
aibot_risk_score{symbol="BTC-USDT"}
```

### **3. Risk Metrics**

| Metric | Type | Description |
|--------|------|-------------|
| `aibot_drawdown_current` | Gauge | Current drawdown percentage |
| `aibot_drawdown_max` | Gauge | Maximum drawdown percentage |
| `aibot_exposure_percentage` | Gauge | Portfolio exposure percentage |
| `aibot_exposure_usd` | Gauge | Total exposure in USD |
| `aibot_positions_open` | Gauge | Number of open positions |
| `aibot_position_size_usd` | Gauge | Position size per symbol |
| `aibot_leverage_used` | Gauge | Leverage multiplier per symbol |

**Example Queries:**

```promql
# Current drawdown alert
aibot_drawdown_current > 10

# High exposure warning
aibot_exposure_percentage > 70

# Position count
aibot_positions_open
```

### **4. System Metrics**

| Metric | Type | Description |
|--------|------|-------------|
| `aibot_job_duration_seconds` | Histogram | Job execution duration |
| `aibot_job_executions_total` | Counter | Total job executions (labels: job_name, status) |
| `aibot_errors_total` | Counter | Total errors (labels: error_type, component) |
| `aibot_api_calls_total` | Counter | Total API calls (labels: exchange, endpoint) |
| `aibot_api_latency_seconds` | Histogram | API call latency |
| `aibot_circuit_breaker_state` | Gauge | Circuit breaker state (0-3) |
| `aibot_uptime_seconds` | Gauge | Bot uptime in seconds |

**Example Queries:**

```promql
# Job success rate
rate(aibot_job_executions_total{status="success"}[5m]) /
rate(aibot_job_executions_total[5m])

# Error rate
rate(aibot_errors_total[5m])

# API latency p95
histogram_quantile(0.95, rate(aibot_api_latency_seconds_bucket[5m]))
```

---

## 📊 **Grafana Dashboard**

### **Setup**

1. **Start Prometheus:**

```bash
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'aibot'
    static_configs:
      - targets: ['localhost:8000']
```

```bash
prometheus --config.file=prometheus.yml
```

2. **Start Grafana:**

```bash
docker run -d -p 3000:3000 grafana/grafana
```

3. **Import Dashboard:**

- Open Grafana: http://localhost:3000
- Go to **Dashboards** → **Import**
- Upload: `monitoring/grafana/dashboard.json`
- Select Prometheus data source
- Click **Import**

### **Dashboard Panels**

The default dashboard includes:

1. **Portfolio Overview**
   - Total PnL (USD)
   - Open positions count
   - Current drawdown
   - Exposure percentage

2. **Trading Performance**
   - Win rate by symbol
   - Trade distribution (win/loss/breakeven)
   - Average trade PnL

3. **Scoring Analysis**
   - Composite scores over time
   - Score component breakdown (TA, ML, News, Risk)
   - ML confidence levels

4. **Risk Monitoring**
   - Drawdown trend
   - Exposure levels
   - Position sizes by symbol
   - Leverage usage

5. **System Health**
   - Bot uptime
   - Job execution rate
   - Error rate
   - API latency (p95, p99)
   - Circuit breaker state

---

## 🚨 **Alerting**

### **Prometheus Alerts**

Create `alerts.yml`:

```yaml
groups:
  - name: trading_alerts
    interval: 30s
    rules:
      # High Drawdown Alert
      - alert: HighDrawdown
        expr: aibot_drawdown_current > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High drawdown detected"
          description: "Current drawdown is {{ $value }}%"
      
      # High Exposure Alert
      - alert: HighExposure
        expr: aibot_exposure_percentage > 70
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High portfolio exposure"
          description: "Exposure is {{ $value }}%"
      
      # Trading Halted Alert
      - alert: TradingHalted
        expr: aibot_circuit_breaker_state > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Trading halted by circuit breaker"
          description: "Circuit breaker state: {{ $value }}"
      
      # Job Failure Alert
      - alert: JobFailureRate
        expr: |
          rate(aibot_job_executions_total{status="failure"}[5m]) /
          rate(aibot_job_executions_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High job failure rate"
          description: "{{ $labels.job_name }} failing at {{ $value | humanizePercentage }}"
      
      # API Latency Alert
      - alert: HighAPILatency
        expr: |
          histogram_quantile(0.95,
            rate(aibot_api_latency_seconds_bucket[5m])
          ) > 5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High API latency detected"
          description: "{{ $labels.exchange }}/{{ $labels.endpoint }} p95 latency: {{ $value }}s"
      
      # Bot Down Alert
      - alert: BotDown
        expr: up{job="aibot"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Trading bot is down"
          description: "Bot has been unreachable for 1 minute"
```

### **Grafana Alerts**

Configure alerts in Grafana:

1. **Dashboard Panel** → **Alert** tab
2. Set **Conditions** (e.g., `aibot_drawdown_current > 10`)
3. Set **Notifications** (Email, Slack, Telegram)
4. **Save**

---

## 📝 **Recording Metrics in Code**

### **Trading Job Example**

```python
from monitoring.prometheus_exporter import get_prometheus_exporter

class TradingAnalysisJob(BaseJob):
    def __init__(self, policy, semaphore, runtime_state):
        super().__init__(policy, semaphore, runtime_state)
        self.prometheus = get_prometheus_exporter()
    
    async def _process_symbol(self, symbol: str):
        # ... scoring logic ...
        
        # Record scores
        if self.prometheus:
            self.prometheus.update_scores(symbol, {
                'composite': composite_signal.final_score,
                'ta': composite_signal.technical.score,
                'ml': composite_signal.ml.score,
                'news': composite_signal.news.score,
                'risk': composite_signal.risk.score
            })
            
            # Record ML confidence
            ml_confidence = composite_signal.ml.details.get('confidence', 'low')
            self.prometheus.update_ml_confidence(symbol, ml_confidence)
        
        # ... trade execution ...
        
        if trade_executed:
            # Record trade
            self.prometheus.record_trade(
                symbol=symbol,
                direction=direction,
                result='win' if pnl > 0 else 'loss',
                pnl=pnl,
                duration_minutes=duration
            )
```

### **Risk Monitor Example**

```python
class RiskMonitorJob(BaseJob):
    async def execute(self):
        portfolio = await self.get_portfolio()
        
        if self.prometheus:
            # Update portfolio metrics
            self.prometheus.update_portfolio_metrics({
                'pnl': portfolio.total_pnl,
                'drawdown': portfolio.current_drawdown,
                'max_drawdown': portfolio.max_drawdown,
                'exposure_pct': portfolio.exposure_pct,
                'exposure_usd': portfolio.exposure_usd,
                'positions_open': len(portfolio.positions)
            })
            
            # Update circuit breaker state
            state = self.circuit_breaker.get_state()
            self.prometheus.update_circuit_breaker(state)
```

---

## 🔍 **Useful PromQL Queries**

### **Performance Analysis**

```promql
# Total profit/loss in last 24h
sum(increase(aibot_pnl_realized_usd[24h]))

# Win rate trend (1h windows)
avg_over_time(aibot_win_rate[1h])

# Best performing symbol
topk(1, aibot_pnl_realized_usd)

# Worst performing symbol
bottomk(1, aibot_pnl_realized_usd)
```

### **Risk Analysis**

```promql
# Maximum drawdown in last week
max_over_time(aibot_drawdown_max[7d])

# Average exposure
avg_over_time(aibot_exposure_percentage[1h])

# High leverage positions
aibot_leverage_used > 2.5
```

### **System Health**

```promql
# Job execution success rate
sum(rate(aibot_job_executions_total{status="success"}[5m])) /
sum(rate(aibot_job_executions_total[5m]))

# Error rate by component
sum by (component) (rate(aibot_errors_total[5m]))

# API call rate
sum(rate(aibot_api_calls_total[5m]))
```

---

## 🛠️ **Troubleshooting**

### **Metrics Not Appearing**

1. **Check Prometheus server:**
   ```bash
   curl http://localhost:8000/metrics
   ```

2. **Verify config:**
   ```yaml
   monitoring:
     prometheus:
       enabled: true  # Must be true
   ```

3. **Check logs:**
   ```bash
   grep "Prometheus" logs/aibotbs.log
   ```

### **High Latency**

```promql
# Identify slow endpoints
topk(5, histogram_quantile(0.99, rate(aibot_api_latency_seconds_bucket[5m])))
```

### **Memory/CPU Issues**

Monitor system metrics with `node_exporter`:

```bash
docker run -d -p 9100:9100 prom/node-exporter
```

---

## 📚 **Additional Resources**

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)

---

**Last Updated:** 2025-10-15
**Version:** 1.0



