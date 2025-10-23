# Single Flip Strategy - System Status Report

## Test Started: 2025-10-23 16:44:44

### ✅ System Configuration

**Mode**: PAPER (source=policy.yaml)  
**Strategy**: single_flip (source=policy.yaml)  
**Symbols**: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP (source=ENV)  
**Timeframe**: 15m (source=ENV)

### ✅ Protection Guards

- **USE_POSITION_TPSL**: True ✅
- **REDUCE_ONLY**: True ✅
- **ENTRY_COOLDOWN_BARS**: 2 ✅
- **ONCE_PER_BAR**: True ✅
- **SAME_DIRECTION_BLOCK**: True ✅
- **REVERSAL_ENABLED**: True ✅

### ✅ Risk Limits

- **max_position_size_pct**: 0.01 (1%)
- **max_total_risk_pct**: 0.60 (60%)
- **max_leverage**: 3.0

### ✅ Scale-In Config (Disabled)

- **enabled**: False
- **max_ladders**: 2
- **ladder_size_usdt**: 5
- **min_dist_pct**: 0.5
- **add_on_profit_only**: True

### 📊 System Status

- **Policy Validation**: ✅ PASSED
- **Scheduler Started**: ✅ YES (16:44:44)
- **Python Processes**: 2 active
- **Log Files**: fallback.log, main.log

### ⏰ Scheduled Jobs

Jobs will run at these intervals:
- **trading_analysis**: Every 15 minutes
- **trailing_5m**: Every 5 minutes  
- **regime_1h**: Every hour
- **risk_1m**: Every minute
- **market_overview**: Every 15 minutes
- **telegram_summary_15m**: Every 15 minutes

### 🔍 Next Steps

1. **Wait for first job execution** (next 15m job at :00, :15, :30, :45)
2. **Monitor logs** for decision traces
3. **Check metrics** at http://localhost:8000/metrics
4. **Validate protection guards** in action
5. **Generate 1-hour test report**

### 📝 Test Duration

**Target**: 1 hour (60 minutes)
**Start Time**: 16:44:44
**Expected End**: 17:44:44
**First Job Expected**: Around 16:45:00 or 17:00:00
