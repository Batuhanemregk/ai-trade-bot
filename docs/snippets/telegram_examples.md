# 📱 Telegram Bot Examples

> **Sample outputs and usage examples for Telegram commands**

## 🚀 Quick Start

### Bot Setup
1. Start a chat with [@BotFather](https://t.me/botfather)
2. Create a new bot: `/newbot`
3. Get your bot token
4. Add the token to your `.env` file
5. Start the bot: `/start`

### Basic Commands
```
/start - Initialize the bot
/help - Show available commands
/status - Check system status
```

## 📊 Scoring Commands

### `/scoring` - Get scoring overview
**Command**: `/scoring`

**Example Output**:
```
🎯 SCORING OVERVIEW

📈 Technical Analysis: 0.75 (75%)
🤖 Machine Learning: 0.68 (68%)
📰 News Sentiment: 0.82 (82%)

🔢 Composite Score: 0.75 (75%)
📊 Signal Strength: STRONG
🎯 Direction: LONG
⏰ Last Updated: 2024-01-15 14:30:00 UTC

💡 Recommendation: Consider LONG position
⚠️  Risk Level: MEDIUM
```

### `/scoring BTC-USDT` - Get symbol-specific scoring
**Command**: `/scoring BTC-USDT`

**Example Output**:
```
🎯 SCORING: BTC-USDT

📈 Technical Analysis (40% weight)
├── RSI: 0.65 (65%) - Neutral
├── MACD: 0.78 (78%) - Bullish
├── Bollinger: 0.72 (72%) - Bullish
├── ATR: 0.68 (68%) - Medium volatility
└── Support/Resistance: 0.75 (75%) - Strong support

🤖 Machine Learning (30% weight)
├── Price Pattern: 0.71 (71%) - Bullish pattern
├── Volatility: 0.65 (65%) - Normal
├── Momentum: 0.79 (79%) - Strong momentum
└── Correlation: 0.62 (62%) - Low correlation

📰 News Sentiment (30% weight)
├── Headlines: 0.85 (85%) - Very positive
├── Sentiment: 0.82 (82%) - Bullish
├── Impact: 0.78 (78%) - High impact
└── Volume: 0.81 (81%) - High volume

🔢 Final Score: 0.73 (73%)
📊 Signal: STRONG BUY
🎯 Direction: LONG
⏰ Valid Until: 2024-01-15 15:30:00 UTC
```

## ⚠️ Risk Commands

### `/risk` - Get risk overview
**Command**: `/risk`

**Example Output**:
```
⚠️ RISK OVERVIEW

🎯 Portfolio Risk: MEDIUM (0.45)
💰 Total Exposure: $12,450 (24.9%)
📊 Daily P&L: +$234 (+1.9%)

🔒 Position Limits
├── Max Position Size: 10% ($5,000)
├── Max Daily Loss: 5% ($2,500)
├── Max Portfolio Exposure: 45% ($22,500)
└── Correlation Limit: 70%

📈 Current Positions
├── BTC-USDT: $4,200 (8.4%) - LOW risk
├── ETH-USDT: $3,800 (7.6%) - MEDIUM risk
├── SOL-USDT: $2,900 (5.8%) - LOW risk
└── AVAX-USDT: $1,550 (3.1%) - LOW risk

⚠️ Risk Factors
├── High volatility in ETH
├── BTC approaching resistance
└── Overall market uncertainty

💡 Recommendations
├── Consider reducing ETH position
├── Monitor BTC resistance level
└── Maintain current diversification
```

### `/risk BTC-USDT` - Get symbol-specific risk
**Command**: `/risk BTC-USDT`

**Example Output**:
```
⚠️ RISK ASSESSMENT: BTC-USDT

📊 Position Details
├── Size: $4,200 (8.4% of portfolio)
├── Entry Price: $42,150
├── Current Price: $42,800
├── P&L: +$65 (+1.5%)
└── Duration: 2 days

🔒 Risk Metrics
├── Position Risk: LOW (0.25)
├── Volatility: MEDIUM (0.45)
├── Liquidity: HIGH (0.90)
├── Market Impact: LOW (0.20)
└── Correlation: MEDIUM (0.55)

⚠️ Risk Factors
├── Approaching resistance at $43,000
├── RSI showing overbought conditions
├── High volume on recent moves
└── News sentiment very positive

🎯 Risk Decision: ALLOW
💡 Recommendations
├── Consider taking partial profits
├── Tighten stop loss to $41,500
├── Monitor resistance level
└── No new positions until breakout
```

## 📰 News Commands

### `/news` - Get latest news
**Command**: `/news`

**Example Output**:
```
📰 LATEST NEWS (Last 24h)

🔥 TOP STORY
Bitcoin ETF Approval Expected This Week
📊 Sentiment: VERY POSITIVE (0.89)
📈 Impact: HIGH
⏰ Published: 2 hours ago
💬 Summary: SEC expected to approve multiple Bitcoin ETFs...

📰 MARKET NEWS
├── Ethereum Upgrade Scheduled for March
│   📊 Sentiment: POSITIVE (0.72)
│   📈 Impact: MEDIUM
│   ⏰ Published: 4 hours ago
│
├── Solana Network Performance Improves
│   📊 Sentiment: POSITIVE (0.68)
│   📈 Impact: LOW
│   ⏰ Published: 6 hours ago
│
└── Regulatory Updates in Asia
│   📊 Sentiment: NEUTRAL (0.52)
│   📈 Impact: MEDIUM
│   ⏰ Published: 8 hours ago

📊 Overall Sentiment: POSITIVE (0.75)
📈 Market Impact: MEDIUM
⏰ Last Updated: 2024-01-15 14:30:00 UTC
```

### `/news BTC` - Get Bitcoin-specific news
**Command**: `/news BTC`

**Example Output**:
```
📰 BITCOIN NEWS (Last 24h)

🔥 BREAKING NEWS
Bitcoin ETF Approval Expected This Week
📊 Sentiment: VERY POSITIVE (0.89)
📈 Impact: HIGH
⏰ Published: 2 hours ago
💬 Summary: SEC expected to approve multiple Bitcoin ETFs...

📰 RECENT NEWS
├── Bitcoin Mining Difficulty Reaches New High
│   📊 Sentiment: POSITIVE (0.71)
│   📈 Impact: MEDIUM
│   ⏰ Published: 6 hours ago
│
├── Institutional Bitcoin Adoption Increases
│   📊 Sentiment: POSITIVE (0.76)
│   📈 Impact: HIGH
│   ⏰ Published: 12 hours ago
│
└── Bitcoin Network Hashrate Grows
│   📊 Sentiment: POSITIVE (0.68)
│   📈 Impact: LOW
│   ⏰ Published: 18 hours ago

📊 Bitcoin Sentiment: POSITIVE (0.76)
📈 Market Impact: HIGH
💡 Trading Impact: Consider LONG positions
⏰ Last Updated: 2024-01-15 14:30:00 UTC
```

## 📊 Portfolio Commands

### `/positions` - Get current positions
**Command**: `/positions`

**Example Output**:
```
📊 CURRENT POSITIONS

💰 Portfolio Value: $50,000
📈 Total P&L: +$1,234 (+2.5%)
📊 Daily P&L: +$234 (+0.5%)

🔵 LONG Positions
├── BTC-USDT: $4,200 (8.4%)
│   ├── Entry: $42,150 | Current: $42,800
│   ├── P&L: +$65 (+1.5%)
│   ├── Duration: 2 days
│   └── Risk: LOW
│
├── ETH-USDT: $3,800 (7.6%)
│   ├── Entry: $2,450 | Current: $2,520
│   ├── P&L: +$70 (+1.8%)
│   ├── Duration: 1 day
│   └── Risk: MEDIUM
│
├── SOL-USDT: $2,900 (5.8%)
│   ├── Entry: $98.50 | Current: $101.20
│   ├── P&L: +$78 (+2.7%)
│   ├── Duration: 3 days
│   └── Risk: LOW
│
└── AVAX-USDT: $1,550 (3.1%)
│   ├── Entry: $31.20 | Current: $32.10
│   ├── P&L: +$45 (+2.9%)
│   ├── Duration: 1 day
│   └── Risk: LOW

📊 Summary
├── Total Positions: 4
├── Average P&L: +2.2%
├── Best Performer: SOL-USDT (+2.7%)
├── Risk Level: MEDIUM
└── Diversification: GOOD
```

### `/orders` - Get open orders
**Command**: `/orders`

**Example Output**:
```
📋 OPEN ORDERS

🔵 PENDING ORDERS
├── BTC-USDT BUY LIMIT
│   ├── Size: 0.1 BTC
│   ├── Price: $41,500
│   ├── Type: LIMIT
│   ├── Status: PENDING
│   └── Created: 1 hour ago
│
├── ETH-USDT SELL STOP
│   ├── Size: 1.5 ETH
│   ├── Price: $2,400
│   ├── Type: STOP
│   ├── Status: PENDING
│   └── Created: 30 min ago
│
└── SOL-USDT TAKE PROFIT
│   ├── Size: 28.7 SOL
│   ├── Price: $105.00
│   ├── Type: TAKE PROFIT
│   ├── Status: PENDING
│   └── Created: 2 hours ago

📊 Summary
├── Total Pending: 3 orders
├── Buy Orders: 1
├── Sell Orders: 2
└── Total Value: $8,450
```

## ⚙️ Configuration Commands

### `/config_get` - Get current configuration
**Command**: `/config_get`

**Example Output**:
```
⚙️ CURRENT CONFIGURATION

🎯 Risk Management
├── Max Position Size: 10%
├── Max Daily Loss: 5%
├── Max Portfolio Exposure: 45%
├── Stop Loss ATR Multiplier: 2.0
├── Take Profit Percentage: 2.0%
└── Trailing Stop: 0.8%

📊 Scoring Weights
├── Technical Analysis: 40%
├── Machine Learning: 30%
└── News Sentiment: 30%

⏰ Timeframes
├── Entry Confirmation: 15m
├── Main Analysis: 1h
└── Trend Filter: 4h

🔧 Execution Settings
├── Default Mode: entry_then_attach
├── Auto Attach Bracket: true
├── Reduce Only: true
├── Order Timeout: 30s
└── Max Retries: 3

📱 Notifications
├── Telegram: ENABLED
├── Email: DISABLED
├── Webhook: DISABLED
└── Alert Level: MEDIUM
```

### `/config_set` - Update configuration
**Command**: `/config_set risk.max_daily_loss 0.03`

**Example Output**:
```
⚙️ CONFIGURATION UPDATED

✅ Successfully updated: risk.max_daily_loss
📊 Old Value: 0.05 (5%)
📊 New Value: 0.03 (3%)

💡 Impact: Daily loss limit reduced from 5% to 3%
⚠️  Note: More conservative risk management
📱 Change will take effect immediately

🔍 Current risk settings:
├── Max Position Size: 10%
├── Max Daily Loss: 3% ← UPDATED
├── Max Portfolio Exposure: 45%
└── Stop Loss ATR Multiplier: 2.0
```

## 🕐 Scheduler Commands

### `/scheduler` - Get scheduler status
**Command**: `/scheduler`

**Example Output**:
```
🕐 SCHEDULER STATUS

✅ Status: RUNNING
📊 Active Jobs: 3
⏰ Last Update: 2 minutes ago

📋 ACTIVE JOBS
├── market_overview_15m
│   ├── Status: ACTIVE
│   ├── Schedule: Every 15 minutes
│   ├── Last Run: 12 minutes ago
│   ├── Next Run: 3 minutes
│   └── Success Rate: 98%
│
├── health_check_5m
│   ├── Status: ACTIVE
│   ├── Schedule: Every 5 minutes
│   ├── Last Run: 2 minutes ago
│   ├── Next Run: 3 minutes
│   └── Success Rate: 100%
│
└── data_cleanup_1h
│   ├── Status: ACTIVE
│   ├── Schedule: Every hour
│   ├── Last Run: 45 minutes ago
│   ├── Next Run: 15 minutes
│   └── Success Rate: 95%

📊 Performance
├── Total Jobs Executed: 1,247
├── Success Rate: 97.2%
├── Average Execution Time: 2.3s
└── Failed Jobs: 35
```

### `/scheduler run market_overview_15m` - Run specific job
**Command**: `/scheduler run market_overview_15m`

**Example Output**:
```
🕐 SCHEDULER JOB EXECUTION

✅ Job Started: market_overview_15m
⏰ Start Time: 2024-01-15 14:30:00 UTC

📊 Execution Progress
├── Step 1: Market data collection... ✅
├── Step 2: Technical analysis... ✅
├── Step 3: ML scoring... ✅
├── Step 4: News sentiment... ✅
├── Step 5: Composite scoring... ✅
└── Step 6: Report generation... ✅

✅ Job Completed Successfully
⏰ Duration: 1.8 seconds
📊 Result: Market overview generated
💾 Data saved to database

📋 Summary
├── Top Performers: BTC, ETH, SOL
├── Risk Level: MEDIUM
├── Opportunities: 3
└── Warnings: 1
```

## 🤖 Agent Commands

### `/agents` - Get agent status
**Command**: `/agents`

**Example Output**:
```
🤖 AGENT SYSTEM STATUS

✅ Overall Status: HEALTHY
📊 Active Agents: 6/6
⏰ Last Update: 1 minute ago

🔵 Agent Status
├── Orchestrator Agent: ✅ HEALTHY
│   ├── Status: RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 30 seconds ago
│   └── Performance: EXCELLENT
│
├── Scoring Agent: ✅ HEALTHY
│   ├── Status: RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 2 minutes ago
│   └── Performance: EXCELLENT
│
├── Risk Agent: ✅ HEALTHY
│   ├── Status: RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 1 minute ago
│   └── Performance: EXCELLENT
│
├── Execution Agent: ✅ HEALTHY
│   ├── Status: RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 45 seconds ago
│   └── Performance: EXCELLENT
│
├── Portfolio Agent: ✅ HEALTHY
│   ├── Status: RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 1 minute ago
│   └── Performance: EXCELLENT
│
└── Scheduler Agent: ✅ HEALTHY
│   ├── Status: RUNNING
│   ├── Uptime: 2 days, 5 hours
│   ├── Last Activity: 30 seconds ago
│   └── Performance: EXCELLENT

📊 System Metrics
├── CPU Usage: 23%
├── Memory Usage: 45%
├── Network: 1.2 MB/s
├── Active Connections: 12
└── Error Rate: 0.1%
```

## 🔄 System Commands

### `/restart` - Restart the system
**Command**: `/restart`

**Example Output**:
```
🔄 SYSTEM RESTART

⚠️  WARNING: This will restart the entire system
⏰ Estimated downtime: 30-60 seconds

📋 Restart Process
├── Step 1: Stopping agents... ✅
├── Step 2: Saving state... ✅
├── Step 3: Closing connections... ✅
├── Step 4: Restarting services... ✅
├── Step 5: Initializing agents... ✅
└── Step 6: Health checks... ✅

✅ System Restarted Successfully
⏰ Total downtime: 42 seconds
📊 All services: HEALTHY
🤖 All agents: RUNNING

💡 System is now ready for trading
📱 Notifications: ENABLED
🔒 Dry run mode: ACTIVE
```

### `/shutdown` - Shutdown the system
**Command**: `/shutdown`

**Example Output**:
```
🛑 SYSTEM SHUTDOWN

⚠️  CRITICAL: This will shutdown the entire system
🚫 All trading will be stopped
💾 State will be saved

📋 Shutdown Process
├── Step 1: Stopping all agents... ✅
├── Step 2: Canceling open orders... ✅
├── Step 3: Saving portfolio state... ✅
├── Step 4: Closing connections... ✅
├── Step 5: Final cleanup... ✅
└── Step 6: System shutdown... ✅

✅ System Shutdown Complete
⏰ Shutdown time: 15 seconds
💾 State saved successfully
📊 All orders canceled: 3

🚫 System is now offline
💡 To restart, use /restart command
📱 Notifications: DISABLED
```

## 📱 Inline Keyboards

### Scoring Keyboard
```
🎯 SCORING OVERVIEW

📊 BTC-USDT: 0.73 (73%) - STRONG BUY
📈 ETH-USDT: 0.68 (68%) - BUY
🔵 SOL-USDT: 0.71 (71%) - BUY
🟡 AVAX-USDT: 0.65 (65%) - NEUTRAL

[📊 Get Details] [📈 Portfolio] [⚠️ Risk]
[🔄 Refresh] [📱 Settings] [❌ Close]
```

### Risk Keyboard
```
⚠️ RISK OVERVIEW

🎯 Portfolio Risk: MEDIUM (0.45)
💰 Total Exposure: $12,450 (24.9%)
📊 Daily P&L: +$234 (+1.9%)

[📊 Positions] [⚠️ Risk Details] [📈 P&L]
[🔄 Refresh] [📱 Settings] [❌ Close]
```

### Portfolio Keyboard
```
📊 PORTFOLIO STATUS

💰 Value: $50,000
📈 P&L: +$1,234 (+2.5%)
📊 Positions: 4 active

[📊 Positions] [📋 Orders] [📈 P&L Chart]
[🔄 Refresh] [📱 Settings] [❌ Close]
```

## 🚨 Error Messages

### Connection Error
```
❌ CONNECTION ERROR

🔴 Unable to connect to exchange
⏰ Time: 2024-01-15 14:30:00 UTC
💻 Error: Network timeout

🔧 Troubleshooting
├── Check internet connection
├── Verify API credentials
├── Check exchange status
└── Try again in 5 minutes

📱 Support: Contact administrator
🔄 Auto-retry: ENABLED
```

### API Error
```
❌ API ERROR

🔴 Exchange API error
⏰ Time: 2024-01-15 14:30:00 UTC
💻 Error: Rate limit exceeded

🔧 Troubleshooting
├── Wait 1 minute before retry
├── Reduce request frequency
├── Check API limits
└── Contact exchange support

📱 Support: Contact administrator
🔄 Auto-retry: DISABLED
```

### Validation Error
```
❌ VALIDATION ERROR

🔴 Invalid command parameters
⏰ Time: 2024-01-15 14:30:00 UTC
💻 Error: Symbol not found

🔧 Troubleshooting
├── Check symbol format (e.g., BTC-USDT)
├── Verify symbol exists
├── Use /help for command syntax
└── Try with different symbol

📱 Support: Use /help command
🔄 Auto-retry: N/A
```

## 💡 Tips and Best Practices

### Command Usage
- Use exact symbol format: `BTC-USDT`, not `BTCUSDT`
- Commands are case-insensitive
- Use `/help` to see all available commands
- Long commands can be abbreviated

### Notifications
- Enable notifications for important events
- Set appropriate alert levels
- Monitor system status regularly
- Use `/status` for quick health check

### Troubleshooting
- Check bot status with `/status`
- Use `/help` for command syntax
- Restart bot with `/restart` if issues persist
- Contact administrator for persistent problems

---

**Next**: See [docs/snippets/cli_examples.md](cli_examples.md) for CLI usage examples, or return to [TELEGRAM.md](../TELEGRAM.md) for complete bot documentation.
