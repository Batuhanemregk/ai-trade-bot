# Telegram Bot Views / Cards

This document describes all available Telegram bot views (cards) with exact message body formats.

## Overview

The Telegram bot provides 8 main views (plus optional DEBUG view):
1. MAIN - Dashboard overview
2. SIGNALS - Top trading signals
3. RISK - Risk management overview
4. ORDERS - Recent orders (paginated)
5. TP/SL - Take profit / Stop loss brackets
6. TRAILING - Trailing stop management
7. PnL - Profit & Loss breakdown
8. POSITIONS - Open positions overview
9. SETTINGS - User settings

## Global Style Rules

- **Footer**: All views include footer: `Last update: <hh:mm:ss> • TF: <tf> • Mode: <dry/paper>`
- **Buttons**: Max 8 rows, 3-5 buttons per row
- **Message Size**: ≤3500 characters (truncated with "(+more...)" if needed)
- **Emoji Legend** (optional, enabled in Settings):
  - 📈 Long position
  - 📉 Short position
  - ⚠️ Risk warning
  - ⏱️ Age/Time indicator
  - 🎯 Score indicator

## View Specifications

**Note**: All views now use **real data** from services. Sample bodies below show actual format with real data.

### 1. MAIN View

**Header**: `AiBotBS Dashboard • <mode> • <symbols_count> sym`

**Blocks**:
```
Status : <health> • Last job <hh:mm:ss> • Queue <count>
Portfolio: Bal $<balance> • PnL 1D <pnl1d$> / 7D <pnl7d$>
Risk : Exposure <exp%>/<max%> • Open <n>/<max> • CB <ON/OFF>
Signals : <symbol> <score> (<grade>) <direction> • ...
```

**Footer Buttons**:
- [Signals] [Risk] [Positions] [Orders] [PnL] [TP/SL] [Trailing] [Settings]

**Sample**:
```
AiBotBS Dashboard • paper • 12 sym

Status : healthy • Last job 02:30:15 • Queue 0
Portfolio: Bal $1,245.80 • PnL 1D +$12.4 / 7D +$37.2
Risk : Exposure 18% / 60% • Open 3 / 20 • CB OFF
Signals : BTC 65.8 (B) LONG • ETH 44.1 (D) FLAT • SOL 58.2 (C) LONG

Last update: 02:30:15 • TF: 15m • Mode: paper
```

### 2. SIGNALS View

**Header**: `Signals • TF <timeframe> • Last <hh:mm:ss>`

**Body**: Top 6 signals (sorted by confidence/score)
```
<symbol> Final <score> (<grade>) Dir <direction>
TA <ta_score> ML <ml_score> News <news_score> Risk <risk_score>
Persist <n>/<max> Age <n>/<max> Confirm <n>/<max>
```

**Footer Buttons**:
- [Main] [Risk] [Positions] [Orders]

**Sample**:
```
Signals • TF 15m • Last 02:30:15

BTC Final 65.8 (B) Dir LONG
TA 75 ML 68 News 55 Risk 42
Persist 3/5 Age 2/6 Confirm 1/2

ETH Final 44.1 (D) Dir FLAT
TA 40 ML 52 News 60 Risk 35

Last update: 02:30:15 • TF: 15m • Mode: paper
```

### 3. RISK View

**Header**: `Risk Overview • Exposure <exp%>/<max%> • Open <n>/<max> • CB <ON/OFF>`

**Body**:
```
Tier Alloc: T1 <x%> • T2 <y%> • T3 <z%>
Limits: MaxPos <max%> • StopLoss <sl%> • Leverage <lev>x
Guards: persist=<n> age=<n> confirm=<n> hyster=<±n>
Alerts (last 1h): <summary or "None">
```

**Footer Buttons**:
- [Main] [Settings] [Positions] [Orders]

**Sample**:
```
Risk Overview • Exposure 18% / 60% • Open 3 / 20 • CB OFF

Tier Alloc: T1 40% • T2 35% • T3 25%
Limits: MaxPos 10% • StopLoss 1.5% • Leverage 3x
Guards: persist=3 age=6 confirm=2 hyster=±5

Alerts (last 1h): None

Last update: 02:30:15 • TF: 15m • Mode: paper
```

### 4. ORDERS View

**Header**: `Orders • Last <hh:mm:ss>`

**Body**: Recent 5-8 orders (paginated)
```
<hh:mm> <symbol> <type> <side> qty <qty> @<price> <status>
```

**Buttons**:
- [Prev] [Next] [Main]

**Sample**:
```
Orders • Last 02:30:15

01:54 BTC MKT OPEN qty 10.79 @111,155.2 ok
01:55 BTC TP SELL qty 10.79 @111,094.5 queued
01:55 BTC SL SELL qty 10.79 @108,130.3 queued

Last update: 02:30:15 • TF: 15m • Mode: paper
```

### 5. TP/SL View

**Header**: `TP/SL Brackets • <n> pos`

**Body**:
```
<symbol> entry <entry> SL <sl> (<sl_atr>) TP <tp> (<tp_atr>) R:R <rr>
```

**Footer Buttons**:
- [Main] [Trailing] [Positions]

**Sample**:
```
TP/SL Brackets • 1 pos

BTC entry 109,032.6 SL 108,130.3 (-2ATR) TP 111,094.5 (+4ATR) R:R 1:2

Last update: 02:30:15 • TF: 15m • Mode: paper
```

### 6. TRAILING View

**Header**: `Trailing Stops • job <interval> • Last <hh:mm:ss>`

**Body**:
```
<symbol> trail <ON/OFF> base SL <base_sl> trail <trail_price> gain +<gain_r>R
```

**Footer Buttons**:
- [Main] [TP/SL] [Positions]

**Sample**:
```
Trailing Stops • job 5m • Last 02:30:15

BTC trail ON base SL 108,130.3 trail 108,980.0 gain +0.35R

Last update: 02:30:15 • TF: 15m • Mode: paper
```

### 7. PnL View

**Header**: `PnL • Bal $<balance> • UPNL $<upnl> • RPNL $<rpnl>`

**Body**:
```
<symbol> qty <qty> entry <entry> mark <mark> UPNL $<upnl> (<upnl_pct>%)
```

**Footer Buttons**:
- [Export CSV] [Main]

**Sample**:
```
PnL • Bal $1,245.80 • UPNL -$2.58 • RPNL +$47.12

BTC qty 76.2 entry 109,032.6 mark 108,853.3 UPNL -0.12 (-1.31%)
SOL qty 207.7 entry 189.06 mark 187.16 UPNL -2.11 (-3.01%)

Last update: 02:30:15 • TF: 15m • Mode: paper
```

### 8. POSITIONS View ✅ REAL DATA

**Header**: `Positions • <n> open • Last <hh:mm:ss>`

**Body**:
```
<symbol> <side> size <size> entry <entry> mark <mark> UPNL $<upnl> (<upnl_pct>%)
```

**Footer Buttons**:
- [Main] [PnL] [TP/SL] [Orders]

**Real Data Sample** (from exchange adapter):
```
Positions • 2 open • Last 02:30:15

⚠️ Exchange adapter unavailable (if error)

BTC LONG size 76.2 entry 109,032.6 mark 108,853.3 UPNL -$0.12 (-1.31%)
SOL SHORT size 207.7 entry 189.06 mark 187.16 UPNL -$2.11 (-3.01%)

Last update: 02:30:15 • TF: 15m • Mode: paper
```

**Data Source**: Real positions from `exchange_adapter.fetch_positions()` with:
- `contracts` → size
- `avgPrice` → entry_price
- `markPrice` → current_price
- `unrealizedPnl` → unrealized_pnl
- Calculated `upnl_pct` from entry and size

### 9. SETTINGS View

**Header**: `Settings`

**Body**:
```
Compact mode: <ON/OFF>
Emojis : <ON/OFF>
Confirmations: <ON/OFF>
Timeframe : <tf> (<locked/unlocked>)
```

**Footer Buttons**:
- [Save] [Main]

**Sample**:
```
Settings

Compact mode: ON
Emojis : OFF
Confirmations: ON
Timeframe : 15m (locked by policy)

Last update: 02:30:15 • TF: 15m • Mode: paper
```

## Button Layout Rules

- **Max Rows**: 8 rows maximum
- **Buttons per Row**: 3-5 buttons per row (optimal: 4)
- **Navigation**: Always include [Main] button in sub-views (leftmost or first row)
- **Callback Format**: `ai:<view>|k1=v1|k2=v2` (see TELEGRAM_CALLBACKS.md)

## Error Handling ✅ IMPLEMENTED

If a data block fails to load:
- Show issues in view: `⚠️ <issue1>, <issue2>, ...` (first 3 issues)
- View still renders with partial data (other blocks unaffected)
- Log error with correlation ID
- Increment `aibot_tg_errors_total{type="resolver"}` metric
- Cache is skipped on errors (only successful fetches cached)

## Message Size Limits ✅ IMPLEMENTED

- **Maximum**: 3500 characters
- **Truncation**: If content exceeds limit, truncate at character boundary and append `(+more...)`
- **Footer**: Always included (counts toward size limit)
- **Validation**: All handlers validate and truncate before sending
- **Logging**: One-line log: `tg view=<id> ms=<t> size=<bytes> err=<0/1>`

