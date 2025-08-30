# ⚙️ Configuration Guide

> **System Configuration and Policy Management**

## 🎯 Overview

AiBotBS uses a comprehensive configuration system based on YAML files and environment variables. The main configuration file is `policy.yaml`, which controls trading behavior, risk management, and system parameters.

## 📁 Configuration Files

### 1. `policy.yaml` - Main Configuration
Primary configuration file for trading policies and system behavior.

### 2. `logging.yaml` - Logging Configuration
Controls logging levels, handlers, and output formats.

### 3. `.env` - Environment Variables
Sensitive configuration like API keys and environment-specific settings.

## 🔧 Policy Configuration

### Core Structure
```yaml
# policy.yaml
risk:
  max_daily_loss: 0.05
  max_position_size: 0.1
  stop_loss_atr_multiplier: 2.0

scoring:
  min_score: 0.5
  news_weight: 0.3
  ta_weight: 0.4
  ml_weight: 0.3

timeframes:
  entry_confirmation: "15m"
  main: "1h"
  trend_filter: "4h"

execution:
  default_mode: "entry_then_attach"
  auto_attach_bracket: true
  reduce_only: true
```

### Risk Management Section

#### `risk.max_daily_loss`
**Type**: Float (0.0 - 1.0)  
**Default**: 0.05 (5%)  
**Description**: Maximum daily loss before trading is paused

```yaml
risk:
  max_daily_loss: 0.05  # 5% daily loss limit
```

#### `risk.max_position_size`
**Type**: Float (0.0 - 1.0)  
**Default**: 0.1 (10%)  
**Description**: Maximum size of any single position

```yaml
risk:
  max_position_size: 0.1  # 10% max per position
```

#### `risk.stop_loss_atr_multiplier`
**Type**: Float  
**Default**: 2.0  
**Description**: ATR multiplier for automatic stop loss calculation

```yaml
risk:
  stop_loss_atr_multiplier: 2.0  # 2x ATR for stop loss
```

#### `risk.correlation_limit`
**Type**: Float (0.0 - 1.0)  
**Default**: 0.7  
**Description**: Maximum correlation between positions

```yaml
risk:
  correlation_limit: 0.7  # 70% correlation limit
```

#### `risk.max_portfolio_exposure`
**Type**: Float (0.0 - 1.0)  
**Default**: 0.45 (45%)  
**Description**: Maximum total portfolio exposure

```yaml
risk:
  max_portfolio_exposure: 0.45  # 45% max exposure
```

### Scoring Configuration Section

#### `scoring.min_score`
**Type**: Float (0.0 - 1.0)  
**Default**: 0.5  
**Description**: Minimum score required for trade execution

```yaml
scoring:
  min_score: 0.5  # 50% minimum score
```

#### `scoring.ta_weight`
**Type**: Float (0.0 - 1.0)  
**Default**: 0.4  
**Description**: Weight for technical analysis scoring

```yaml
scoring:
  ta_weight: 0.4  # 40% weight for TA
```

#### `scoring.ml_weight`
**Type**: Float (0.0 - 1.0)  
**Default**: 0.3  
**Description**: Weight for machine learning scoring

```yaml
scoring:
  ml_weight: 0.3  # 30% weight for ML
```

#### `scoring.news_weight`
**Type**: Float (0.0 - 1.0)  
**Default**: 0.3  
**Description**: Weight for news sentiment scoring

```yaml
scoring:
  news_weight: 0.3  # 30% weight for news
```

**Note**: Weights should sum to 1.0 (100%)

### Timeframe Configuration Section

#### `timeframes.entry_confirmation`
**Type**: String  
**Default**: "15m"  
**Description**: Timeframe for entry confirmation signals

```yaml
timeframes:
  entry_confirmation: "15m"  # 15-minute confirmation
```

#### `timeframes.main`
**Type**: String  
**Default**: "1h"  
**Description**: Main analysis timeframe

```yaml
timeframes:
  main: "1h"  # 1-hour main analysis
```

#### `timeframes.trend_filter`
**Type**: String  
**Default**: "4h"  
**Description**: Timeframe for trend filtering

```yaml
timeframes:
  trend_filter: "4h"  # 4-hour trend filter
```

### Execution Configuration Section

#### `execution.default_mode`
**Type**: String  
**Default**: "entry_then_attach"  
**Description**: Default order execution mode

```yaml
execution:
  default_mode: "entry_then_attach"  # Entry first, then TP/SL
```

#### `execution.auto_attach_bracket`
**Type**: Boolean  
**Default**: true  
**Description**: Automatically attach TP/SL orders

```yaml
execution:
  auto_attach_bracket: true  # Auto-attach bracket orders
```

#### `execution.reduce_only`
**Type**: Boolean  
**Default**: true  
**Description**: Use reduce-only for TP/SL orders

```yaml
execution:
  reduce_only: true  # Reduce-only TP/SL orders
```

## 🔐 Environment Variables

### Required Variables
```bash
# OKX API Configuration
OKX_API_KEY=your_api_key_here
OKX_API_SECRET=your_api_secret_here
OKX_API_PASSPHRASE=your_passphrase_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Optional Variables
```bash
# Core Behavior
EXCHANGE=okx
MARKET=futures
DRY_RUN=true
LOG_LEVEL=INFO

# OpenAI Configuration (optional)
OPENAI_API_KEY=your_openai_key_here

# Risk Management
TRAILING_PERCENT=0.8
TAKE_PROFIT_PERCENT=2.0
STOP_LOSS_ATR_MULT=1.2
MAX_MARGIN_RATIO=70
DAILY_LOSS_CAP_PERCENT=1.5
MAX_POSITION_RISK_USD=10

# System Configuration
AIBOTBS_STATE_DIR=state
AIBOTBS_LOG_DIR=logs
AIBOTBS_CONFIG_DIR=configs
```

## 📊 Configuration Examples

### Conservative Trading Policy
```yaml
# Conservative policy for capital preservation
risk:
  max_daily_loss: 0.02          # 2% daily loss limit
  max_position_size: 0.05       # 5% max per position
  stop_loss_atr_multiplier: 1.5 # Tighter stop losses
  correlation_limit: 0.5         # Lower correlation limit
  max_portfolio_exposure: 0.3   # 30% max exposure

scoring:
  min_score: 0.7                # Higher score requirement
  ta_weight: 0.5                # 50% technical analysis
  ml_weight: 0.3                # 30% machine learning
  news_weight: 0.2              # 20% news sentiment

timeframes:
  entry_confirmation: "30m"     # Longer confirmation
  main: "4h"                    # Longer main analysis
  trend_filter: "1d"            # Daily trend filter

execution:
  default_mode: "entry_then_attach"
  auto_attach_bracket: true
  reduce_only: true
```

### Aggressive Trading Policy
```yaml
# Aggressive policy for higher returns
risk:
  max_daily_loss: 0.08          # 8% daily loss limit
  max_position_size: 0.15       # 15% max per position
  stop_loss_atr_multiplier: 2.5 # Wider stop losses
  correlation_limit: 0.8         # Higher correlation limit
  max_portfolio_exposure: 0.6   # 60% max exposure

scoring:
  min_score: 0.4                # Lower score requirement
  ta_weight: 0.4                # 40% technical analysis
  ml_weight: 0.4                # 40% machine learning
  news_weight: 0.2              # 20% news sentiment

timeframes:
  entry_confirmation: "5m"      # Shorter confirmation
  main: "30m"                   # Shorter main analysis
  trend_filter: "2h"            # Shorter trend filter

execution:
  default_mode: "entry_then_attach"
  auto_attach_bracket: true
  reduce_only: true
```

### Balanced Trading Policy
```yaml
# Balanced policy for moderate risk/reward
risk:
  max_daily_loss: 0.05          # 5% daily loss limit
  max_position_size: 0.1         # 10% max per position
  stop_loss_atr_multiplier: 2.0 # Standard stop losses
  correlation_limit: 0.7         # Standard correlation limit
  max_portfolio_exposure: 0.45  # 45% max exposure

scoring:
  min_score: 0.5                # Standard score requirement
  ta_weight: 0.4                # 40% technical analysis
  ml_weight: 0.3                # 30% machine learning
  news_weight: 0.3              # 30% news sentiment

timeframes:
  entry_confirmation: "15m"     # Standard confirmation
  main: "1h"                    # Standard main analysis
  trend_filter: "4h"            # Standard trend filter

execution:
  default_mode: "entry_then_attach"
  auto_attach_bracket: true
  reduce_only: true
```

## 🔄 Configuration Management

### Dynamic Configuration Updates
```python
from configs.policy import load_policy, save_policy

# Load current policy
policy = load_policy()

# Update specific values
policy["risk"]["max_daily_loss"] = 0.03
policy["scoring"]["min_score"] = 0.6

# Save updated policy
save_policy(policy)
```

### Environment-Specific Configuration
```bash
# Development environment
cp configs/policy.dev.yaml configs/policy.yaml

# Production environment
cp configs/policy.prod.yaml configs/policy.yaml

# Testing environment
cp configs/policy.test.yaml configs/policy.yaml
```

### Configuration Validation
```python
from configs.validator import validate_policy

# Validate policy configuration
validation_result = validate_policy(policy)

if not validation_result["valid"]:
    print("Configuration errors:")
    for error in validation_result["errors"]:
        print(f"  - {error}")
```

## 📈 Configuration Optimization

### Performance Tuning
```yaml
# Optimize for performance
system:
  max_concurrent_jobs: 10
  job_queue_size: 200
  worker_timeout: 600
  
  # Memory management
  max_memory_usage: 0.8
  cleanup_interval: 1800
  
  # Network optimization
  connection_pool_size: 20
  request_timeout: 30
  retry_attempts: 3
```

### Monitoring Configuration
```yaml
# Monitoring and alerting
monitoring:
  enable_metrics: true
  enable_health_checks: true
  health_check_interval: 300
  
  # Alerting thresholds
  alert_on_error_rate: 0.05
  alert_on_response_time: 5000
  alert_on_memory_usage: 0.9
  
  # Notification channels
  telegram_notifications: true
  email_notifications: false
  webhook_notifications: false
```

## 🚨 Configuration Security

### Sensitive Data Protection
```bash
# Never commit sensitive data to version control
# Add to .gitignore
.env
configs/secrets.yaml
*.key
*.pem
```

### Environment Variable Best Practices
```bash
# Use strong, unique API keys
OKX_API_KEY=your_very_long_random_key_here
OKX_API_SECRET=your_very_long_random_secret_here

# Rotate keys regularly
# Use different keys for different environments
# Never share keys in logs or error messages
```

### Configuration Encryption
```yaml
# For production, consider encrypting sensitive config
security:
  encrypt_sensitive_fields: true
  encryption_key: "${ENCRYPTION_KEY}"
  
  # Fields to encrypt
  encrypted_fields:
    - "api_keys"
    - "secrets"
    - "passwords"
```

## 🔍 Configuration Troubleshooting

### Common Issues

#### 1. Configuration File Not Found
**Error**: `FileNotFoundError: policy.yaml not found`
**Solution**: Verify file path and permissions

#### 2. Invalid YAML Syntax
**Error**: `yaml.YAMLError: Invalid YAML syntax`
**Solution**: Use YAML validator to check syntax

#### 3. Configuration Validation Failed
**Error**: `Configuration validation failed`
**Solution**: Check required fields and value ranges

#### 4. Environment Variable Missing
**Error**: `Environment variable not set`
**Solution**: Set required environment variables

### Debug Configuration
```python
import os
from configs.policy import load_policy

# Debug configuration loading
print("Environment variables:")
for key, value in os.environ.items():
    if "AIBOTBS" in key or "OKX" in key:
        print(f"  {key}: {value[:10]}...")

# Debug policy loading
try:
    policy = load_policy()
    print("Policy loaded successfully")
    print(f"Risk settings: {policy.get('risk', {})}")
except Exception as e:
    print(f"Policy loading failed: {e}")
```

---

**Next**: See [EXECUTION.md](EXECUTION.md) for execution configuration, [SCHEDULER.md](SCHEDULER.md) for job configuration, or [TELEGRAM.md](TELEGRAM.md) for bot configuration.
