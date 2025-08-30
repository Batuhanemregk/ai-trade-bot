# 💻 CLI Usage Examples

> **Command Line Interface examples and usage patterns**

## 🚀 Quick Start

### Environment Setup
```bash
# Set Python path
export PYTHONPATH=$PWD

# Verify setup
python -m compileall .
```

### Basic Commands
```bash
# Show help
python -m infrastructure.cli --help

# Show specific command help
python -m infrastructure.cli agents --help
python -m infrastructure.cli scheduler --help
```

## 🤖 Agent Commands

### Agents Run (Dry Run)
**Command**: `python -m infrastructure.cli agents run --graph default --dry-run`

**Example Output**:
```bash
🚀 AGENTS DRY-RUN STARTED
⏰ Time: 2024-01-15 14:30:00 UTC
🔒 Mode: DRY RUN (no live orders)
📊 Graph: default

📋 AGENT INITIALIZATION
├── Orchestrator Agent: ✅ STARTED
├── Scoring Agent: ✅ STARTED
├── Risk Agent: ✅ STARTED
├── Execution Agent: ✅ STARTED
├── Portfolio Agent: ✅ STARTED
└── Scheduler Agent: ✅ STARTED

🔄 EXECUTION CYCLE STARTED
⏰ Cycle: 1/10 (max cycles: 10)

📊 MARKET DATA COLLECTION
├── BTC-USDT: $42,800 (+1.2%)
├── ETH-USDT: $2,520 (+0.8%)
├── SOL-USDT: $101.20 (+2.1%)
└── AVAX-USDT: $32.10 (+1.5%)

🎯 SIGNAL GENERATION (Scoring Agent)
├── BTC-USDT: Score 0.73 (73%) - STRONG BUY
├── ETH-USDT: Score 0.68 (68%) - BUY
├── SOL-USDT: Score 0.71 (71%) - BUY
└── AVAX-USDT: Score 0.65 (65%) - NEUTRAL

⚠️ RISK ASSESSMENT (Risk Agent)
├── Portfolio Risk: MEDIUM (0.45)
├── Total Exposure: $12,450 (24.9%)
├── Daily P&L: +$234 (+1.9%)
└── Risk Decision: ALLOW

🚀 ORDER EXECUTION (Execution Agent)
├── BTC-USDT: LONG 0.1 BTC @ $42,800
│   ├── Entry Order: ✅ SIMULATED
│   ├── Take Profit: $43,680 (+2.0%)
│   └── Stop Loss: $41,920 (-2.0%)
│
├── ETH-USDT: LONG 1.5 ETH @ $2,520
│   ├── Entry Order: ✅ SIMULATED
│   ├── Take Profit: $2,570 (+2.0%)
│   └── Stop Loss: $2,470 (-2.0%)
│
└── SOL-USDT: LONG 28.7 SOL @ $101.20
    ├── Entry Order: ✅ SIMULATED
    ├── Take Profit: $103.22 (+2.0%)
    └── Stop Loss: $99.18 (-2.0%)

📊 PORTFOLIO UPDATE (Portfolio Agent)
├── New Positions: 3
├── Total Value: $62,450
├── Total P&L: +$1,234 (+2.0%)
└── Risk Level: MEDIUM

🔄 EXECUTION CYCLE COMPLETED
⏰ Duration: 2.3 seconds
📊 Status: SUCCESS

✅ AGENTS DRY-RUN COMPLETED
⏰ Total Time: 8.5 seconds
📊 Cycles Executed: 1
🔒 Mode: DRY RUN (no real orders)
💾 State Saved: ✅
```

### Agents Run (Live Mode)
**Command**: `python -m infrastructure.cli agents run --graph default`

**Example Output**:
```bash
🚀 AGENTS LIVE MODE STARTED
⏰ Time: 2024-01-15 14:30:00 UTC
🔴 Mode: LIVE TRADING (real orders)
📊 Graph: default

⚠️  WARNING: Live trading mode enabled
💰 Account Balance: $50,000
🔒 Risk Limits: ACTIVE

📋 AGENT INITIALIZATION
├── Orchestrator Agent: ✅ STARTED
├── Scoring Agent: ✅ STARTED
├── Risk Agent: ✅ STARTED
├── Execution Agent: ✅ STARTED
├── Portfolio Agent: ✅ STARTED
└── Scheduler Agent: ✅ STARTED

🔄 EXECUTION CYCLE STARTED
⏰ Cycle: 1/∞ (continuous mode)

📊 MARKET DATA COLLECTION
├── BTC-USDT: $42,800 (+1.2%)
├── ETH-USDT: $2,520 (+0.8%)
├── SOL-USDT: $101.20 (+2.1%)
└── AVAX-USDT: $32.10 (+1.5%)

🎯 SIGNAL GENERATION (Scoring Agent)
├── BTC-USDT: Score 0.73 (73%) - STRONG BUY
├── ETH-USDT: Score 0.68 (68%) - BUY
├── SOL-USDT: Score 0.71 (71%) - BUY
└── AVAX-USDT: Score 0.65 (65%) - NEUTRAL

⚠️ RISK ASSESSMENT (Risk Agent)
├── Portfolio Risk: MEDIUM (0.45)
├── Total Exposure: $12,450 (24.9%)
├── Daily P&L: +$234 (+1.9%)
└── Risk Decision: ALLOW

🚀 ORDER EXECUTION (Execution Agent)
├── BTC-USDT: LONG 0.1 BTC @ $42,800
│   ├── Entry Order: 🚀 SUBMITTED
│   ├── Order ID: 12345
│   ├── Status: PENDING
│   ├── Take Profit: $43,680 (+2.0%)
│   └── Stop Loss: $41,920 (-2.0%)
│
├── ETH-USDT: LONG 1.5 ETH @ $2,520
│   ├── Entry Order: 🚀 SUBMITTED
│   ├── Order ID: 12346
│   ├── Status: PENDING
│   ├── Take Profit: $2,570 (+2.0%)
│   └── Stop Loss: $2,470 (-2.0%)
│
└── SOL-USDT: LONG 28.7 SOL @ $101.20
    ├── Entry Order: 🚀 SUBMITTED
    ├── Order ID: 12347
    ├── Status: PENDING
    ├── Take Profit: $103.22 (+2.0%)
    └── Stop Loss: $99.18 (-2.0%)

📊 PORTFOLIO UPDATE (Portfolio Agent)
├── New Positions: 3
├── Total Value: $62,450
├── Total P&L: +$1,234 (+2.0%)
└── Risk Level: MEDIUM

🔄 EXECUTION CYCLE COMPLETED
⏰ Duration: 3.1 seconds
📊 Status: SUCCESS

⏰ Waiting for next cycle (15 minutes)...
```

### Agents Status
**Command**: `python -m infrastructure.cli agents status`

**Example Output**:
```bash
🤖 AGENT SYSTEM STATUS

✅ Overall Status: HEALTHY
📊 Active Agents: 6/6
⏰ Last Update: 2 minutes ago

🔵 Agent Details
├── Orchestrator Agent
│   ├── Status: ✅ RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 30 seconds ago
│   ├── Performance: EXCELLENT
│   └── Memory Usage: 45 MB
│
├── Scoring Agent
│   ├── Status: ✅ RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 2 minutes ago
│   ├── Performance: EXCELLENT
│   └── Memory Usage: 67 MB
│
├── Risk Agent
│   ├── Status: ✅ RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 1 minute ago
│   ├── Performance: EXCELLENT
│   └── Memory Usage: 38 MB
│
├── Execution Agent
│   ├── Status: ✅ RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 45 seconds ago
│   ├── Performance: EXCELLENT
│   └── Memory Usage: 89 MB
│
├── Portfolio Agent
│   ├── Status: ✅ RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 1 minute ago
│   ├── Performance: EXCELLENT
│   └── Memory Usage: 52 MB
│
└── Scheduler Agent
    ├── Status: ✅ RUNNING
    ├── Uptime: 2 days, 5 hours
    ├── Last Activity: 30 seconds ago
    ├── Performance: EXCELLENT
    └── Memory Usage: 41 MB

📊 System Metrics
├── CPU Usage: 23%
├── Memory Usage: 45%
├── Network: 1.2 MB/s
├── Active Connections: 12
├── Error Rate: 0.1%
└── Uptime: 2 days, 5 hours, 23 minutes
```

### Agents Stop
**Command**: `python -m infrastructure.cli agents stop`

**Example Output**:
```bash
🛑 AGENT SYSTEM SHUTDOWN

⚠️  WARNING: This will stop all agents
🚫 All trading will be stopped
💾 State will be saved

📋 Shutdown Process
├── Step 1: Stopping Orchestrator Agent... ✅
├── Step 2: Stopping Scoring Agent... ✅
├── Step 3: Stopping Risk Agent... ✅
├── Step 4: Stopping Execution Agent... ✅
├── Step 5: Stopping Portfolio Agent... ✅
├── Step 6: Stopping Scheduler Agent... ✅
├── Step 7: Saving system state... ✅
├── Step 8: Closing connections... ✅
└── Step 9: Final cleanup... ✅

✅ Agent System Shutdown Complete
⏰ Shutdown time: 8 seconds
💾 State saved successfully
📊 All agents stopped: 6/6

🚫 System is now offline
💡 To restart, use: python -m infrastructure.cli agents run
📱 Notifications: DISABLED
```

## 🕐 Scheduler Commands

### Scheduler Status
**Command**: `python -m infrastructure.cli scheduler status`

**Example Output**:
```bash
🕐 SCHEDULER STATUS

✅ Status: RUNNING
📊 Active Jobs: 3
⏰ Last Update: 2 minutes ago

📋 ACTIVE JOBS
├── market_overview_15m
│   ├── Status: ✅ ACTIVE
│   ├── Schedule: Every 15 minutes
│   ├── Last Run: 12 minutes ago
│   ├── Next Run: 3 minutes
│   ├── Success Rate: 98%
│   ├── Total Runs: 1,247
│   └── Average Duration: 2.3s
│
├── health_check_5m
│   ├── Status: ✅ ACTIVE
│   ├── Schedule: Every 5 minutes
│   ├── Last Run: 2 minutes ago
│   ├── Next Run: 3 minutes
│   ├── Success Rate: 100%
│   ├── Total Runs: 3,456
│   └── Average Duration: 0.8s
│
└── data_cleanup_1h
    ├── Status: ✅ ACTIVE
    ├── Schedule: Every hour
    ├── Last Run: 45 minutes ago
    ├── Next Run: 15 minutes
    ├── Success Rate: 95%
    ├── Total Runs: 89
    └── Average Duration: 12.4s

📊 Performance Metrics
├── Total Jobs Executed: 4,792
├── Overall Success Rate: 97.2%
├── Average Execution Time: 3.2s
├── Failed Jobs: 135
├── Retry Rate: 2.8%
└── System Load: LOW

⏰ Next Scheduled Jobs
├── health_check_5m: 3 minutes
├── market_overview_15m: 3 minutes
└── data_cleanup_1h: 15 minutes
```

### Scheduler Jobs List
**Command**: `python -m infrastructure.cli scheduler jobs list`

**Example Output**:
```bash
📋 SCHEDULER JOBS LIST

📊 Total Jobs: 3
✅ Active: 3
❌ Inactive: 0

🔵 JOB DETAILS

1. market_overview_15m
   ├── Status: ✅ ACTIVE
   ├── Type: INTERVAL
   ├── Schedule: Every 15 minutes
   ├── Function: generate_market_overview
   ├── Last Run: 12 minutes ago
   ├── Next Run: 3 minutes
   ├── Success Rate: 98%
   ├── Total Runs: 1,247
   ├── Average Duration: 2.3s
   ├── Last Error: None
   └── Retry Count: 0

2. health_check_5m
   ├── Status: ✅ ACTIVE
   ├── Type: INTERVAL
   ├── Schedule: Every 5 minutes
   ├── Function: perform_health_check
   ├── Last Run: 2 minutes ago
   ├── Next Run: 3 minutes
   ├── Success Rate: 100%
   ├── Total Runs: 3,456
   ├── Average Duration: 0.8s
   ├── Last Error: None
   └── Retry Count: 0

3. data_cleanup_1h
   ├── Status: ✅ ACTIVE
   ├── Type: INTERVAL
   ├── Schedule: Every hour
   ├── Function: cleanup_old_data
   ├── Last Run: 45 minutes ago
   ├── Next Run: 15 minutes
   ├── Success Rate: 95%
   ├── Total Runs: 89
   ├── Average Duration: 12.4s
   ├── Last Error: Database timeout (2 days ago)
   └── Retry Count: 3

📊 Job Statistics
├── Total Executions: 4,792
├── Successful: 4,657 (97.2%)
├── Failed: 135 (2.8%)
├── Average Success Rate: 97.2%
└── System Health: EXCELLENT
```

### Scheduler Job Run
**Command**: `python -m infrastructure.cli scheduler jobs run market_overview_15m`

**Example Output**:
```bash
🕐 SCHEDULER JOB EXECUTION

✅ Job Started: market_overview_15m
⏰ Start Time: 2024-01-15 14:30:00 UTC
🔧 Function: generate_market_overview

📊 Execution Progress
├── Step 1: Market data collection... ✅
│   ├── BTC-USDT: $42,800 (+1.2%)
│   ├── ETH-USDT: $2,520 (+0.8%)
│   ├── SOL-USDT: $101.20 (+2.1%)
│   └── AVAX-USDT: $32.10 (+1.5%)
│
├── Step 2: Technical analysis... ✅
│   ├── RSI calculations: ✅
│   ├── MACD analysis: ✅
│   ├── Bollinger Bands: ✅
│   └── Support/Resistance: ✅
│
├── Step 3: ML scoring... ✅
│   ├── Price pattern analysis: ✅
│   ├── Volatility calculation: ✅
│   ├── Momentum indicators: ✅
│   └── Correlation analysis: ✅
│
├── Step 4: News sentiment... ✅
│   ├── Headline analysis: ✅
│   ├── Sentiment scoring: ✅
│   ├── Impact assessment: ✅
│   └── Volume analysis: ✅
│
├── Step 5: Composite scoring... ✅
│   ├── Weight calculation: ✅
│   ├── Score aggregation: ✅
│   ├── Signal generation: ✅
│   └── Confidence scoring: ✅
│
└── Step 6: Report generation... ✅
    ├── Data compilation: ✅
    ├── Formatting: ✅
    ├── Database storage: ✅
    └── Notification: ✅

✅ Job Completed Successfully
⏰ Duration: 1.8 seconds
📊 Result: Market overview generated
💾 Data saved to database

📋 Summary
├── Top Performers: BTC, ETH, SOL
├── Risk Level: MEDIUM
├── Opportunities: 3
├── Warnings: 1
└── Overall Sentiment: POSITIVE

📊 Performance Metrics
├── Execution Time: 1.8s (target: <5s)
├── Memory Usage: 45 MB
├── Database Operations: 12
└── External API Calls: 8
```

### Scheduler Job Enable/Disable
**Command**: `python -m infrastructure.cli scheduler jobs enable market_overview_15m`

**Example Output**:
```bash
✅ JOB ENABLED SUCCESSFULLY

📋 Job: market_overview_15m
🔄 Status: ENABLED
⏰ Next Run: 3 minutes
📊 Schedule: Every 15 minutes

💡 Job will now run automatically
📱 Notifications: ENABLED
🔧 Monitoring: ACTIVE
```

**Command**: `python -m infrastructure.cli scheduler jobs disable market_overview_15m`

**Example Output**:
```bash
❌ JOB DISABLED SUCCESSFULLY

📋 Job: market_overview_15m
🔄 Status: DISABLED
⏰ Next Run: N/A
📊 Schedule: Every 15 minutes

⚠️  Job will not run automatically
📱 Notifications: DISABLED
🔧 Monitoring: INACTIVE

💡 To re-enable: scheduler jobs enable market_overview_15m
```

## 🔧 Configuration Commands

### Config Get
**Command**: `python -m infrastructure.cli config get`

**Example Output**:
```bash
⚙️ CURRENT CONFIGURATION

🎯 Risk Management
├── max_daily_loss: 0.05 (5%)
├── max_position_size: 0.1 (10%)
├── max_portfolio_exposure: 0.45 (45%)
├── stop_loss_atr_multiplier: 2.0
├── take_profit_percent: 2.0
└── trailing_percent: 0.8

📊 Scoring Weights
├── ta_weight: 0.4 (40%)
├── ml_weight: 0.3 (30%)
└── news_weight: 0.3 (30%)

⏰ Timeframes
├── entry_confirmation: 15m
├── main: 1h
└── trend_filter: 4h

🔧 Execution Settings
├── default_mode: entry_then_attach
├── auto_attach_bracket: true
├── reduce_only: true
├── order_timeout: 30
└── max_retries: 3

📱 Notifications
├── telegram_enabled: true
├── email_enabled: false
├── webhook_enabled: false
└── alert_level: medium

🌍 Environment
├── exchange: okx
├── market: futures
├── testnet: false
├── dry_run: true
└── log_level: INFO
```

### Config Set
**Command**: `python -m infrastructure.cli config set risk.max_daily_loss 0.03`

**Example Output**:
```bash
⚙️ CONFIGURATION UPDATED

✅ Successfully updated: risk.max_daily_loss
📊 Old Value: 0.05 (5%)
📊 New Value: 0.03 (3%)

💡 Impact: Daily loss limit reduced from 5% to 3%
⚠️  Note: More conservative risk management
📱 Change will take effect immediately

🔍 Current risk settings:
├── max_position_size: 0.1 (10%)
├── max_daily_loss: 0.03 (3%) ← UPDATED
├── max_portfolio_exposure: 0.45 (45%)
└── stop_loss_atr_multiplier: 2.0

💾 Configuration saved to: configs/policy.yaml
🔄 System will reload configuration
```

### Config Validate
**Command**: `python -m infrastructure.cli config validate`

**Example Output**:
```bash
✅ CONFIGURATION VALIDATION

🔍 Validating configuration files...
├── policy.yaml: ✅ VALID
├── logging.yaml: ✅ VALID
└── .env: ✅ VALID

🔍 Validating configuration values...
├── Risk settings: ✅ VALID
├── Scoring weights: ✅ VALID
├── Timeframes: ✅ VALID
├── Execution settings: ✅ VALID
└── Notification settings: ✅ VALID

🔍 Validating environment variables...
├── OKX API: ✅ CONFIGURED
├── Telegram Bot: ✅ CONFIGURED
├── OpenAI API: ⚠️  OPTIONAL
└── System paths: ✅ VALID

🔍 Validating external connections...
├── OKX Exchange: ✅ CONNECTED
├── Telegram Bot: ✅ CONNECTED
└── Database: ✅ CONNECTED

✅ Configuration is valid and ready
📊 All checks passed: 15/15
💡 System can start safely
```

## 📊 Portfolio Commands

### Portfolio Status
**Command**: `python -m infrastructure.cli portfolio status`

**Example Output**:
```bash
📊 PORTFOLIO STATUS

💰 Portfolio Value: $50,000
📈 Total P&L: +$1,234 (+2.5%)
📊 Daily P&L: +$234 (+0.5%)
⏰ Last Update: 2 minutes ago

📈 CURRENT POSITIONS
├── BTC-USDT: LONG $4,200 (8.4%)
│   ├── Entry Price: $42,150
│   ├── Current Price: $42,800
│   ├── P&L: +$65 (+1.5%)
│   ├── Duration: 2 days
│   └── Risk: LOW
│
├── ETH-USDT: LONG $3,800 (7.6%)
│   ├── Entry Price: $2,450
│   ├── Current Price: $2,520
│   ├── P&L: +$70 (+1.8%)
│   ├── Duration: 1 day
│   └── Risk: MEDIUM
│
├── SOL-USDT: LONG $2,900 (5.8%)
│   ├── Entry Price: $98.50
│   ├── Current Price: $101.20
│   ├── P&L: +$78 (+2.7%)
│   ├── Duration: 3 days
│   └── Risk: LOW
│
└── AVAX-USDT: LONG $1,550 (3.1%)
    ├── Entry Price: $31.20
    ├── Current Price: $32.10
    ├── P&L: +$45 (+2.9%)
    ├── Duration: 1 day
    └── Risk: LOW

📋 OPEN ORDERS
├── BTC-USDT BUY LIMIT: 0.1 BTC @ $41,500
├── ETH-USDT SELL STOP: 1.5 ETH @ $2,400
└── SOL-USDT TAKE PROFIT: 28.7 SOL @ $105.00

📊 SUMMARY
├── Total Positions: 4
├── Total Orders: 3
├── Average P&L: +2.2%
├── Best Performer: SOL-USDT (+2.7%)
├── Risk Level: MEDIUM
└── Diversification: GOOD
```

### Portfolio Positions
**Command**: `python -m infrastructure.cli portfolio positions`

**Example Output**:
```bash
📈 CURRENT POSITIONS

📊 Total Positions: 4
💰 Total Value: $12,450
📈 Total P&L: +$258 (+2.1%)

🔵 LONG POSITIONS

1. BTC-USDT
   ├── Size: $4,200 (8.4% of portfolio)
   ├── Entry Price: $42,150
   ├── Current Price: $42,800
   ├── P&L: +$65 (+1.5%)
   ├── Duration: 2 days
   ├── Risk: LOW
   ├── Take Profit: $43,680 (+2.0%)
   └── Stop Loss: $41,920 (-2.0%)

2. ETH-USDT
   ├── Size: $3,800 (7.6% of portfolio)
   ├── Entry Price: $2,450
   ├── Current Price: $2,520
   ├── P&L: +$70 (+1.8%)
   ├── Duration: 1 day
   ├── Risk: MEDIUM
   ├── Take Profit: $2,570 (+2.0%)
   └── Stop Loss: $2,470 (-2.0%)

3. SOL-USDT
   ├── Size: $2,900 (5.8% of portfolio)
   ├── Entry Price: $98.50
   ├── Current Price: $101.20
   ├── P&L: +$78 (+2.7%)
   ├── Duration: 3 days
   ├── Risk: LOW
   ├── Take Profit: $103.22 (+2.0%)
   └── Stop Loss: $99.18 (-2.0%)

4. AVAX-USDT
   ├── Size: $1,550 (3.1% of portfolio)
   ├── Entry Price: $31.20
   ├── Current Price: $32.10
   ├── P&L: +$45 (+2.9%)
   ├── Duration: 1 day
   ├── Risk: LOW
   ├── Take Profit: $32.76 (+2.0%)
   └── Stop Loss: $30.58 (-2.0%)

📊 PERFORMANCE SUMMARY
├── Best Performer: SOL-USDT (+2.7%)
├── Worst Performer: BTC-USDT (+1.5%)
├── Average P&L: +2.2%
├── Total Duration: 1.75 days
├── Risk Distribution: 2 LOW, 1 MEDIUM, 0 HIGH
└── Correlation: 0.45 (LOW)
```

## 🔍 Debug Commands

### Debug Scoring
**Command**: `python -m infrastructure.cli debug scoring BTC-USDT`

**Example Output**:
```bash
🔍 DEBUG SCORING: BTC-USDT

📊 MARKET DATA
├── Current Price: $42,800
├── 24h Change: +1.2%
├── 24h Volume: $2.1B
├── Market Cap: $840B
└── Last Update: 2 minutes ago

📈 TECHNICAL ANALYSIS (40% weight)
├── RSI (14): 65.4
│   ├── Value: 65.4
│   ├── Signal: NEUTRAL
│   ├── Score: 0.65 (65%)
│   └── Interpretation: Not overbought/oversold
│
├── MACD (12,26,9)
│   ├── MACD Line: +125.6
│   ├── Signal Line: +98.3
│   ├── Histogram: +27.3
│   ├── Signal: BULLISH
│   ├── Score: 0.78 (78%)
│   └── Interpretation: Bullish momentum
│
├── Bollinger Bands (20,2)
│   ├── Upper Band: $44,200
│   ├── Middle Band: $42,800
│   ├── Lower Band: $41,400
│   ├── Position: NEAR UPPER
│   ├── Signal: BULLISH
│   ├── Score: 0.72 (72%)
│   └── Interpretation: Price near upper band
│
├── ATR (14): 850
│   ├── Value: $850
│   ├── Volatility: MEDIUM
│   ├── Score: 0.68 (68%)
│   └── Interpretation: Normal volatility
│
└── Support/Resistance
    ├── Support: $41,500 (strong)
    ├── Resistance: $43,000 (moderate)
    ├── Distance to Support: -3.0%
    ├── Distance to Resistance: +0.5%
    ├── Signal: BULLISH
    ├── Score: 0.75 (75%)
    └── Interpretation: Strong support below

🤖 MACHINE LEARNING (30% weight)
├── Price Pattern Recognition
│   ├── Pattern: BULLISH FLAG
│   ├── Confidence: 0.71 (71%)
│   ├── Score: 0.71 (71%)
│   └── Interpretation: Bullish continuation pattern
│
├── Volatility Analysis
│   ├── Current Volatility: 0.45
│   ├── Historical Average: 0.52
│   ├── Signal: NORMAL
│   ├── Score: 0.65 (65%)
│   └── Interpretation: Below average volatility
│
├── Momentum Indicators
│   ├── Momentum: 0.79 (79%)
│   ├── Signal: STRONG
│   ├── Score: 0.79 (79%)
│   └── Interpretation: Strong upward momentum
│
└── Correlation Analysis
    ├── BTC-ETH Correlation: 0.62
    ├── BTC-SOL Correlation: 0.58
    ├── Signal: LOW
    ├── Score: 0.62 (62%)
    └── Interpretation: Low correlation with other assets

📰 NEWS SENTIMENT (30% weight)
├── Headline Analysis
│   ├── Positive Headlines: 8
│   ├── Negative Headlines: 2
│   ├── Neutral Headlines: 3
│   ├── Signal: POSITIVE
│   ├── Score: 0.85 (85%)
│   └── Interpretation: Very positive news coverage
│
├── Sentiment Scoring
│   ├── Overall Sentiment: 0.82 (82%)
│   ├── Signal: BULLISH
│   ├── Score: 0.82 (82%)
│   └── Interpretation: Bullish sentiment
│
├── Impact Assessment
│   ├── High Impact News: 3
│   ├── Medium Impact News: 5
│   ├── Low Impact News: 5
│   ├── Signal: HIGH
│   ├── Score: 0.78 (78%)
│   └── Interpretation: High impact news
│
└── Volume Analysis
    ├── News Volume: HIGH
    ├── Social Media Activity: HIGH
    ├── Signal: POSITIVE
    ├── Score: 0.81 (81%)
    └── Interpretation: High news volume

🔢 COMPOSITE SCORING
├── Technical Analysis: 0.72 × 0.4 = 0.288
├── Machine Learning: 0.69 × 0.3 = 0.207
├── News Sentiment: 0.82 × 0.3 = 0.246
├── Total Score: 0.741 (74.1%)
└── Final Score: 0.73 (73%)

📊 FINAL RESULT
├── Score: 0.73 (73%)
├── Signal: STRONG BUY
├── Direction: LONG
├── Confidence: HIGH
├── Valid Until: 2024-01-15 15:30:00 UTC
└── Recommendation: Consider LONG position
```

## 🚨 Error Handling Examples

### Connection Error
```bash
❌ CONNECTION ERROR

🔴 Failed to connect to OKX exchange
⏰ Time: 2024-01-15 14:30:00 UTC
💻 Error: Network timeout after 30 seconds

🔧 Troubleshooting Steps
├── Check internet connection
├── Verify API credentials
├── Check exchange status
└── Try again in 5 minutes

📱 Support: Contact administrator
🔄 Auto-retry: ENABLED (3 attempts)
```

### Configuration Error
```bash
❌ CONFIGURATION ERROR

🔴 Invalid configuration value
⏰ Time: 2024-01-15 14:30:00 UTC
💻 Error: risk.max_daily_loss must be between 0.01 and 0.10

🔧 Troubleshooting Steps
├── Check policy.yaml file
├── Validate configuration values
├── Use config validate command
└── Fix invalid values

📱 Support: Check CONFIG.md for valid ranges
🔄 Auto-retry: DISABLED
```

### Permission Error
```bash
❌ PERMISSION ERROR

🔴 Insufficient API permissions
⏰ Time: 2024-01-15 14:30:00 UTC
💻 Error: API key does not have trading permissions

🔧 Troubleshooting Steps
├── Check API key permissions
├── Enable trading permissions
├── Verify API key is active
└── Contact exchange support

📱 Support: Check API key settings
🔄 Auto-retry: DISABLED
```

## 💡 Tips and Best Practices

### Command Usage
- Always set `PYTHONPATH=$PWD` before running commands
- Use `--help` flag to see available options
- Start with dry-run mode to test configuration
- Monitor logs for detailed execution information

### Performance
- Dry-run mode is faster than live mode
- Use specific job names for scheduler commands
- Monitor system resources during execution
- Check execution times for optimization

### Troubleshooting
- Use `config validate` to check configuration
- Check agent status with `agents status`
- Monitor scheduler with `scheduler status`
- Use debug commands for detailed analysis

### Security
- Never share API credentials
- Use environment variables for sensitive data
- Enable dry-run mode for testing
- Monitor API usage and limits

---

**Next**: See [docs/snippets/telegram_examples.md](telegram_examples.md) for Telegram bot examples, or return to [README.md](../../README.md) for project overview.
