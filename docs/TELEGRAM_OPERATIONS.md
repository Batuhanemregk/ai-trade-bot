# Telegram Bot Operations

This document describes Telegram bot commands, navigation flows, data source contracts, and rate limiting.

## Commands

All commands start with `/` and are registered with the bot:

- `/start` - Initialize bot and show MAIN view
- `/help` - Show help message with command list
- `/portfolio` - Show MAIN view (alias for /start)
- `/positions` - Show POSITIONS view
- `/risk` - Show RISK view
- `/health` - Show bot health status

## Navigation Flow

The bot uses **inline message editing** for navigation (not sending new messages):

1. User sends `/start` → Bot sends MAIN view message (with inline keyboard)
2. User taps button → Bot **edits** the same message to show new view
3. User taps [Main] → Bot edits message back to MAIN view
4. Same `message_id` is reused throughout navigation

### Navigation Map

```
/start → MAIN
  ├─ [Signals] → SIGNALS → [Main] → MAIN
  ├─ [Risk] → RISK → [Main] → MAIN
  ├─ [Positions] → POSITIONS → [Main] → MAIN
  ├─ [Orders] → ORDERS → [Main] → MAIN
  ├─ [PnL] → PNL → [Main] → MAIN
  ├─ [TP/SL] → TP/SL → [Main] → MAIN
  ├─ [Trailing] → TRAILING → [Main] → MAIN
  └─ [Settings] → SETTINGS → [Save] → SETTINGS (updated)
```

## Data Source Contracts

All data is fetched **read-only** from existing services with **real data integration**:

### ✅ Real Data Sources
- **Signals**: `ScoringService.get_top_symbols()` + component scores from `get_score_summary()`
- **Positions**: Exchange adapter `fetch_positions()` with qty/entry/mark/UPNL
- **Portfolio**: `PortfolioService.get_portfolio_value()` for balance
- **Risk**: Real exposure calculation from positions, circuit breaker state
- **Exchange Adapter**: Created with real config from env (OKX_API_KEY, OKX_API_SECRET, OKX_API_PASSPHRASE)

### Signals / Scoring ✅ REAL DATA
- **Source**: `ScoringService` / `CompositeSignal`
- **Method**: `get_top_symbols(limit)` → Returns top symbols with scores
- **Component Scores**: `get_score_summary(symbol)` → Returns TA/ML/News component scores
- **Cache**: 10 seconds (context resolver handles caching)
- **Fallback**: If ScoringService unavailable, returns empty list with issues

### Risk
- **Source**: `RiskService`
- **Methods**:
  - Exposure calculation: `get_portfolio_risk(positions)` → Returns risk metrics
  - Circuit breaker: `get_circuit_breaker().get_status()` → Returns CB state
- **Cache**: 5 seconds

### Positions & Orders ✅ REAL DATA
- **Source**: `OKXExchangeAdapter` (created with real config from env)
- **Methods**:
  - Positions: `exchange_adapter.fetch_positions()` → Returns open positions with qty/entry/mark/UPNL
  - Orders: `exchange_adapter.fetch_open_orders()` → Returns open orders
- **Cache**: 5 seconds for positions, 5 seconds for orders
- **Data Format**: Real positions with `contracts`, `avgPrice`, `markPrice`, `unrealizedPnl`
- **Fallback**: If exchange adapter unavailable, returns empty list with issues

### PnL / Balance
- **Source**: `PortfolioService`
- **Methods**:
  - Balance: `portfolio_service.get_portfolio_value()` → Returns total value
  - PnL: Calculated from positions (`unrealizedPnl`)
- **Cache**: 5 seconds

### Trailing
- **Source**: `PositionMonitor` / `PositionStateManager`
- **Methods**: Get trailing stop state from position monitor
- **Cache**: 5 seconds

### Config
- **Source**: `policy.yaml` (via `load_policy()`)
- **Cache**: 30 seconds (reloads on access if stale)

## Rate Limiting

- **User-based**: 10 requests per 60 seconds per user ID
- **Global**: 100 requests per 60 seconds (across all users)
- **Violation**: Returns friendly message: "Rate limit exceeded. Please wait."
- **Metrics**: `aibot_tg_rate_limited_total` counter increments

## Error Handling

### Context Resolver Errors
- **Fallback**: Returns empty/default data structure
- **Logging**: Error logged with correlation ID
- **Metrics**: `aibot_tg_errors_total{type="resolver"}` increments
- **User Message**: "Couldn't load <block>. Tap to retry." with [Retry] button

### Handler Errors
- **Catch-all**: All handler errors caught and logged
- **Metrics**: `aibot_tg_errors_total{type="handler"}` increments
- **User Message**: Friendly error message sent to user

### Message Editing Errors
- **MessageNotModified**: Swallowed gracefully (no-op)
- **MessageNotFound**: Re-send MAIN view and continue
- **Other errors**: Logged and metrics recorded

## Bootstrap

### Integrated with start_bot.py ✅

The Telegram bot is now **fully integrated** into `start_bot.py`:

```bash
python start_bot.py
```

This will:
- ✅ Start trading bot (paper mode by default)
- ✅ Initialize Telegram bot (if `TELEGRAM_ENABLED=true`)
- ✅ Register all command handlers (/start, /help, /portfolio, /positions, /risk, /health)
- ✅ Register callback handler for ai:* schema
- ✅ Use real data from services (ScoringService, PortfolioService, exchange adapter)

### Manual Initialization (Alternative)

If you need to start Telegram bot separately:

```python
from adapters.telegram.client import init_telegram_app
import asyncio

async def main():
    # Initialize and start bot
    client = await init_telegram_app()  # Token from TELEGRAM_BOT_TOKEN env var
    # Bot is now running and handling messages
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

## Environment Variables

- `TELEGRAM_BOT_TOKEN` - Required. Telegram bot token from BotFather
- `TELEGRAM_ENABLED` - Optional. Default `true`. Set to `false` to disable

## Metrics

All metrics exposed via Prometheus (see `/metrics` endpoint):

- `aibot_tg_views_render_total{view}` - Total views rendered
- `aibot_tg_callbacks_total{view,act}` - Total callbacks processed
- `aibot_tg_errors_total{type}` - Total errors by type
- `aibot_tg_rate_limited_total` - Total rate limit hits
- `aibot_tg_latency_ms_bucket{view}` - Render latency histogram
- `aibot_tg_message_size_bytes` - Current message size (gauge)

## Logging

- **Component**: `telegram_handlers`, `telegram_client`, `context_resolver`
- **Format**: One-line logs: `TG view=signals sym=BTC t=38ms size=1240B`
- **Error Logging**: Full stack trace with correlation ID
- **Secrets**: Never logged (bot token, API keys, etc.)

