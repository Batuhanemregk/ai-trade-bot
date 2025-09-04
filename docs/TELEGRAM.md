# AiBotBS Telegram Bot Commands

> **Complete reference for all Telegram bot commands and features**

## 🤖 Bot Overview

The AiBotBS Telegram bot provides real-time access to your trading system through a rich, interactive interface. All commands return formatted HTML responses with color-coded status indicators and pagination for large datasets.

## 📱 Getting Started

### Bot Setup
1. **Create Bot**: Message [@BotFather](https://t.me/botfather) on Telegram
2. **Get Token**: Receive your bot token
3. **Configure**: Add `TELEGRAM_BOT_TOKEN=your_token` to your `.env` file
4. **Start Bot**: Send `/start` to your bot

### Basic Usage
```
/start          - Initialize the bot
/help           - Show command help
/status         - Check system status
```

## 🔔 Notifications Delivery

- Notifications are sent via `infrastructure/notification_service.NotificationManager`.
- Preferred path uses the running Telegram bot application for rich messaging.
- Fallback: If the bot app isn't started, the system uses direct Bot API to send messages using `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from `.env`.
- Ensure both variables are set to receive trade and system alerts even without the bot process.

## 📊 Trading Commands

### 1. **System Status** - `/status`
**Purpose**: Check overall system health and status

**Usage**: `/status`

**Response Example**:
```html
🟢 System Status: ONLINE
⏰ Last Update: 2024-01-15 14:30:25 UTC

📈 Trading Status:
• Mode: Paper Trading
• Risk Level: Medium
• Circuit Breaker: Disabled

🤖 Agent Status:
• Orchestrator: 🟢 Online
• Technical Analyzer: 🟢 Online
• ML Agent: 🟢 Online
• News Agent: 🟢 Online
• Execution Agent: 🟢 Online
• Risk Agent: 🟢 Online

💾 System Resources:
• Memory: 256MB / 512MB
• CPU: 15%
• Uptime: 2d 14h 32m
```

### 2. **Trading Signals** - `/signals`
**Purpose**: View recent trading signals and analysis

**Usage**: `/signals [symbol] [limit]`

**Examples**:
```
/signals                    - Show all recent signals
/signals BTC-USDT          - Show signals for BTC-USDT
/signals ETH-USDT 10       - Show last 10 ETH signals
```

**Response Example**:
```html
📊 Trading Signals - Last 24 Hours

🔴 BTC-USDT (Strong Sell)
• Score: 0.85 (A+)
• Entry: $42,150
• TP: $44,250 (+5.0%)
• SL: $40,075 (-4.9%)
• TA: 0.82 | ML: 0.88 | News: 0.85
• Status: Executed
• Time: 14:25:10 UTC

🟡 ETH-USDT (Hold)
• Score: 0.62 (B)
• Entry: $2,580
• TP: $2,700 (+4.7%)
• SL: $2,460 (-4.7%)
• TA: 0.58 | ML: 0.65 | News: 0.63
• Status: Skipped (Score < 0.7)
• Time: 14:20:15 UTC

📄 Page 1 of 3 | Use /signals 2 for next page
```

### 3. **Open Positions** - `/positions`
**Purpose**: Monitor current open positions and their status

**Usage**: `/positions [symbol] [page]`

**Examples**:
```
/positions                  - Show all open positions
/positions BTC-USDT        - Show BTC position details
/positions 2               - Show page 2 of positions
```

**Response Example**:
```html
📈 Open Positions (5 total)

🟢 BTC-USDT LONG
• Size: 0.5 BTC ($21,075)
• Entry: $42,150
• Current: $43,200
• PnL: +$525 (+2.5%)
• Duration: 2h 15m
• TP: $44,250 | SL: $40,075
• Risk Level: Low

🔴 SOL-USDT SHORT
• Size: 50 SOL ($4,250)
• Entry: $85.00
• Current: $87.50
• PnL: -$125 (-2.9%)
• Duration: 45m
• TP: $82.00 | SL: $88.50
• Risk Level: Medium

📄 Page 1 of 2 | Use /positions 2 for next page
```

### 4. **Order Management** - `/orders`
**Purpose**: View and manage open orders

**Usage**: `/orders [status] [page]`

**Examples**:
```
/orders                    - Show all orders
/orders open              - Show only open orders
/orders filled            - Show filled orders
/orders 2                 - Show page 2
```

**Response Example**:
```html
📋 Order Management

⏳ Open Orders (3)
• BTC-USDT BUY 0.5 @ $42,150
  Status: Pending | Time: 14:25:10
  Client ID: E_20240115_142510_001

• ETH-USDT SELL 2.0 @ $2,580
  Status: Pending | Time: 14:20:15
  Client ID: E_20240115_142015_002

✅ Filled Orders (12)
• SOL-USDT BUY 50 @ $85.00
  Filled: 14:15:30 | Fee: $2.13

📄 Page 1 of 3 | Use /orders 2 for next page
```

### 5. **Profit & Loss** - `/pnl`
**Purpose**: View profit/loss summary and performance metrics

**Usage**: `/pnl [period] [page]`

**Examples**:
```
/pnl                      - Show today's PnL
/pnl week                - Show weekly PnL
/pnl month               - Show monthly PnL
/pnl year                - Show yearly PnL
```

**Response Example**:
```html
💰 Profit & Loss Summary

📅 Today (2024-01-15)
• Realized PnL: +$1,250 (+2.1%)
• Unrealized PnL: +$425 (+0.7%)
• Total PnL: +$1,675 (+2.8%)
• Trades: 8 (6 wins, 2 losses)
• Win Rate: 75%

📊 This Week
• Realized PnL: +$3,450 (+5.8%)
• Unrealized PnL: +$1,125 (+1.9%)
• Total PnL: +$4,575 (+7.7%)
• Trades: 32 (24 wins, 8 losses)
• Win Rate: 75%

🏆 Top Performers
• BTC-USDT: +$2,100 (+4.2%)
• ETH-USDT: +$1,350 (+2.7%)
• SOL-USDT: +$800 (+1.6%)
```

## 🔍 Analysis Commands

### 6. **News & Sentiment** - `/news`
**Purpose**: View latest news and sentiment analysis

**Usage**: `/news [symbol] [limit]`

**Examples**:
```
/news                     - Show all recent news
/news BTC                 - Show BTC-related news
/news ETH 5               - Show last 5 ETH news items
```

**Response Example**:
```html
📰 News & Sentiment Analysis

🟢 BTC-USDT (Bullish: 0.78)
• "Bitcoin ETF Approval Expected This Week"
  Source: CoinDesk | Time: 14:30:00
  Sentiment: Very Bullish (+0.85)
  Impact: High | AI Commentary: "Strong positive sentiment with institutional adoption narrative"

🟡 ETH-USDT (Neutral: 0.52)
• "Ethereum Network Upgrade Delayed"
  Source: Cointelegraph | Time: 14:25:00
  Sentiment: Slightly Bearish (-0.15)
  Impact: Medium | AI Commentary: "Technical delay, minimal market impact expected"

🔴 SOL-USDT (Bearish: 0.32)
• "Solana Network Outage Concerns"
  Source: Decrypt | Time: 14:20:00
  Sentiment: Bearish (-0.45)
  Impact: High | AI Commentary: "Network reliability concerns affecting investor confidence"

📄 Page 1 of 2 | Use /news 2 for next page
```

### 7. **Scoring Analysis** - `/scoring`
**Purpose**: View detailed scoring breakdown for symbols

**Usage**: `/scoring [symbol] [timeframe]`

**Examples**:
```
/scoring                  - Show scoring for all symbols
/scoring BTC-USDT        - Show BTC scoring details
/scoring ETH-USDT 1h     - Show ETH 1-hour scoring
```

**Response Example**:
```html
📊 Scoring Analysis

🟢 BTC-USDT - Composite Score: 0.85 (A+)
⏰ Timeframe: 1h | Last Update: 14:30:00

📈 Technical Analysis: 0.82 (A)
• RSI: 65 (Neutral)
• MACD: Bullish crossover
• Bollinger Bands: Price near upper band
• ATR: Low volatility
• Volume: Above average

🤖 Machine Learning: 0.88 (A+)
• Price Prediction: $44,200 (+4.9%)
• Confidence: 87%
• Pattern Recognition: Bull flag detected
• Support: $41,800
• Resistance: $44,500

📰 News Sentiment: 0.85 (A+)
• Overall Sentiment: Bullish (+0.78)
• News Count: 15
• Positive: 12 | Neutral: 2 | Negative: 1
• Key Events: ETF approval, institutional buying

🎯 Final Recommendation: STRONG BUY
• Risk Level: Low
• Position Size: 5% of portfolio
• Entry Zone: $42,000 - $42,500
• Stop Loss: $40,500 (-3.6%)
• Take Profit: $44,500 (+4.8%)
```

### 8. **Risk Assessment** - `/risk`
**Purpose**: View risk analysis and portfolio exposure

**Usage**: `/risk [symbol] [detail]`

**Examples**:
```
/risk                     - Show overall risk summary
/risk BTC-USDT           - Show BTC risk details
/risk portfolio          - Show portfolio risk analysis
```

**Response Example**:
```html
⚠️ Risk Assessment

📊 Portfolio Risk Summary
• Total Exposure: 45% of portfolio
• Risk Level: Medium
• Daily VaR: 2.3%
• Max Drawdown: 8.5%

🔴 High Risk Positions
• SOL-USDT: 12% exposure, -2.9% PnL
  Risk Factors: High volatility, negative momentum
  Recommendation: Consider reducing position

🟡 Medium Risk Positions
• ETH-USDT: 8% exposure, +2.7% PnL
  Risk Factors: Network upgrade delays
  Recommendation: Monitor closely

🟢 Low Risk Positions
• BTC-USDT: 15% exposure, +4.2% PnL
  Risk Factors: None significant
  Recommendation: Hold

📈 Correlation Analysis
• BTC-ETH: 0.78 (High correlation)
• BTC-SOL: 0.65 (Medium correlation)
• ETH-SOL: 0.72 (Medium correlation)

⚠️ Risk Alerts
• Portfolio correlation: 0.71 (Above threshold)
• Daily loss approaching limit: 85% used
• Consider reducing correlated positions
```

## ⚙️ Configuration Commands

### 9. **Get Configuration** - `/config_get`
**Purpose**: View current system configuration

**Usage**: `/config_get [section] [key]`

**Examples**:
```
/config_get               - Show all configuration
/config_get trading      - Show trading configuration
/config_get risk         - Show risk configuration
/config_get trading.mode - Show trading mode setting
```

**Response Example**:
```html
⚙️ Configuration Settings

🔧 Trading Configuration
• Mode: Paper Trading
• Enabled: Yes
• Min Score Threshold: 0.7
• Max Position Size: 10%
• Max Daily Loss: 5%

🛡️ Risk Configuration
• Max Correlation: 0.7
• Max Drawdown: 15%
• Circuit Breaker: Enabled
• Emergency Stop: 25%

📊 Scoring Weights
• Technical Analysis: 40%
• Machine Learning: 40%
• News Sentiment: 20%

⏰ Execution Settings
• Max Slippage: 0.2%
• Retry Attempts: 3
• Order Timeout: 30s
• Cooldown Period: 30m
```

### 10. **Set Configuration** - `/config_set`
**Purpose**: Update system configuration

**Usage**: `/config_set <key> <value>`

**Examples**:
```
/config_set trading.mode paper
/config_set risk.max_drawdown 0.12
/config_set scoring.ta_weight 0.45
```

**Response Example**:
```html
✅ Configuration Updated

🔧 Setting Changed:
• Key: trading.mode
• Old Value: live
• New Value: paper
• Status: Applied

⚠️ Important Notes:
• Changes take effect immediately
• Some changes require system restart
• Risk parameters affect active positions

📋 Current Trading Mode: Paper Trading
• No real orders will be placed
• All trades are simulated
• Perfect for testing strategies
```

## 🕐 System Management Commands

### 11. **Scheduler Status** - `/scheduler`
**Purpose**: View and manage scheduled jobs

**Usage**: `/scheduler [action] [job_name]`

**Examples**:
```
/scheduler                - Show scheduler status
/scheduler list          - List all jobs
/scheduler run market_overview
/scheduler stop heartbeat
```

**Response Example**:
```html
⏰ Scheduler Status

🟢 Active Jobs (4)
• market_overview: Running (Every 5 minutes)
  Last Run: 14:30:00 | Next Run: 14:35:00
  Status: Success | Duration: 45s

• state_backup: Running (Every 6 hours)
  Last Run: 12:00:00 | Next Run: 18:00:00
  Status: Success | Duration: 2m 15s

• heartbeat: Running (Every 1 minute)
  Last Run: 14:30:00 | Next Run: 14:31:00
  Status: Success | Duration: 0.5s

• cleanup: Running (Every 24 hours)
  Last Run: 00:00:00 | Next Run: 24:00:00
  Status: Success | Duration: 1m 30s

📊 Job Statistics
• Total Jobs: 4
• Running: 4
• Failed: 0
• Success Rate: 100%
• Average Duration: 1m 7s
```

### 12. **Agent Management** - `/agents`
**Purpose**: Monitor and manage agent status

**Usage**: `/agents [action] [agent_name]`

**Examples**:
```
/agents                   - Show all agents
/agents restart orchestrator
/agents status ml_agent
```

**Response Example**:
```html
🤖 Agent Management

🟢 Orchestrator Agent
• Status: Online
• State: Ready
• Messages: 1,247
• Response Time: 45ms
• Memory: 45MB
• Uptime: 2d 14h 32m

🟢 Technical Analyzer
• Status: Online
• State: Ready
• Messages: 892
• Response Time: 23ms
• Memory: 32MB
• Uptime: 2d 14h 32m

🟢 ML Agent
• Status: Online
• State: Ready
• Messages: 156
• Response Time: 156ms
• Memory: 128MB
• Uptime: 2d 14h 32m

🟢 News Agent
• Status: Online
• State: Ready
• Messages: 234
• Response Time: 89ms
• Memory: 28MB
• Uptime: 2d 14h 32m

🟢 Execution Agent
• Status: Online
• State: Ready
• Messages: 445
• Response Time: 67ms
• Memory: 56MB
• Uptime: 2d 14h 32m

🟢 Risk Agent
• Status: Online
• State: Ready
• Messages: 334
• Response Time: 34ms
• Memory: 41MB
• Uptime: 2d 14h 32m

📊 System Overview
• Total Agents: 6
• Online: 6
• Offline: 0
• Average Response Time: 69ms
• Total Memory Usage: 330MB
```

### 13. **System Restart** - `/restart`
**Purpose**: Restart the trading system

**Usage**: `/restart [component]`

**Examples**:
```
/restart                  - Restart entire system
/restart agents          - Restart all agents
/restart orchestrator    - Restart specific agent
```

**Response Example**:
```html
🔄 System Restart

⚠️ Warning: This will interrupt current operations

📋 Restart Plan:
• Component: Entire System
• Estimated Downtime: 2-3 minutes
• Active Trades: Will be preserved
• Orders: Will be maintained

⏰ Restart Process:
1. Stopping all agents...
2. Saving current state...
3. Restarting core services...
4. Reinitializing agents...
5. Restoring connections...

✅ Restart Initiated
• Time: 14:35:00 UTC
• Status: In Progress
• ETA: 14:37:00 UTC

📱 You will receive a notification when the system is back online.
```

### 14. **System Shutdown** - `/shutdown`
**Purpose**: Safely shut down the trading system

**Usage**: `/shutdown [reason]`

**Examples**:
```
/shutdown                 - Shutdown system
/shutdown maintenance     - Shutdown for maintenance
/shutdown emergency       - Emergency shutdown
```

**Response Example**:
```html
🛑 System Shutdown

⚠️ Critical Action: This will stop all trading activities

📋 Shutdown Plan:
• Reason: User Requested
• Type: Graceful Shutdown
• Active Positions: Will be maintained
• Open Orders: Will be cancelled
• State: Will be saved

⏰ Shutdown Process:
1. Cancelling open orders...
2. Saving current state...
3. Stopping all agents...
4. Closing connections...
5. System shutdown...

✅ Shutdown Initiated
• Time: 14:40:00 UTC
• Status: In Progress
• ETA: 14:41:00 UTC

⚠️ Important:
• No new trades will be executed
• Existing positions remain active
• System can be restarted with /start
```

## 🔧 Advanced Features

### Pagination
Most commands support pagination for large datasets:
```
/positions 2              - Show page 2
/signals BTC-USDT 3       - Show page 3 of BTC signals
/orders filled 2          - Show page 2 of filled orders
```

### Filtering
Many commands support filtering:
```
/signals BTC-USDT         - Filter by symbol
/orders open              - Filter by status
/news ETH                 - Filter news by symbol
```

### Time Ranges
Some commands support time-based filtering:
```
/pnl week                 - Weekly PnL
/pnl month                - Monthly PnL
/pnl year                 - Yearly PnL
```

## 📱 Response Formatting

### Color Coding
- 🟢 **Green**: Positive, success, good status
- 🟡 **Yellow**: Neutral, warning, moderate status
- 🔴 **Red**: Negative, error, critical status
- 🔵 **Blue**: Information, neutral status

### Status Indicators
- ✅ **Checkmark**: Success, completed
- ⚠️ **Warning**: Warning, attention needed
- ❌ **Cross**: Error, failed
- ⏳ **Clock**: Pending, in progress
- 🔄 **Arrows**: Processing, updating

### Data Tables
Responses use HTML formatting for better readability:
- **Bold text** for important information
- *Italic text* for secondary information
- Bullet points for lists
- Tables for structured data

## 🚨 Error Handling

### Common Errors
```
❌ Error: Invalid symbol format
   Use: BTC-USDT, ETH-USDT, SOL-USDT

❌ Error: Page number out of range
   Available pages: 1-3

❌ Error: Command not found
   Use /help for available commands

❌ Error: System offline
   Use /status to check system health
```

### Error Recovery
- **Invalid Input**: Bot will suggest correct format
- **System Errors**: Automatic retry with exponential backoff
- **Network Issues**: Graceful degradation with cached data
- **Permission Errors**: Clear explanation of required permissions

## 📊 Performance Metrics

### Response Times
- **Simple Commands**: < 100ms
- **Data Queries**: < 500ms
- **Complex Analysis**: < 2s
- **System Operations**: < 5s

### Rate Limits
- **Standard Commands**: 10 per minute
- **System Commands**: 5 per minute
- **Analysis Commands**: 3 per minute
- **Configuration**: 2 per minute

## 🔐 Security Features

### Authentication
- **Bot Token**: Secure bot authentication
- **User Verification**: Telegram user ID validation
- **Command Logging**: Audit trail of all commands
- **Access Control**: Role-based command access

### Data Protection
- **No Sensitive Data**: API keys never exposed
- **Encrypted Storage**: Secure configuration storage
- **Session Management**: Secure session handling
- **Input Validation**: All inputs sanitized

## 🆘 Support & Troubleshooting

### Getting Help
```
/help                     - Show command help
/start                    - Reinitialize bot
/status                   - Check system health
```

### Common Issues
1. **Bot Not Responding**: Check system status with `/status`
2. **Slow Responses**: System may be under load
3. **Command Errors**: Verify command syntax with `/help`
4. **Data Not Updating**: Check last update time in responses

### Contact Support
- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check docs/ directory
- **Community**: Join discussion forums
- **Email**: Support email for urgent issues

---

The Telegram bot provides a comprehensive interface to your AiBotBS trading system, allowing you to monitor, control, and analyze your trading activities from anywhere in the world.
