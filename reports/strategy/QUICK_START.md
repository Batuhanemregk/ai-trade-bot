# Strategy Modes Quick Start Guide

## How to Start

### Single Flip Strategy (Default)
```bash
# Set environment variables
export MODE=PAPER
export STRATEGY_MODE=single_flip
export SYMBOLS=BTC-USDT-SWAP
export TIMEFRAME=15m

# Run the bot
python main.py scheduler run
```

### Scale-In Strategy (Optional)
```bash
# Set environment variables
export MODE=PAPER
export STRATEGY_MODE=scale_in
export SYMBOLS=BTC-USDT-SWAP
export TIMEFRAME=15m
export MAX_LADDERS=3
export LADDER_SIZE_USDT=5
export MIN_DIST_PCT=0.5
export ADD_ON_PROFIT_ONLY=true

# Run the bot
python main.py scheduler run
```

### ENV Override Examples
```bash
# Quick test overrides
export STRATEGY_MODE=scale_in
export ENTRY_COOLDOWN_BARS=1
export USE_POSITION_TPSL=true
export REDUCE_ONLY=true

# Run the bot
python main.py scheduler run
```

## Configuration Sources

1. **ENV variables** (temporary override)
2. **policy.yaml** (permanent configuration)
3. **Defaults** (fallback)

## Safety Modes

- **LIVE**: Real orders to exchange
- **PAPER**: Virtual orders/positions (recommended for testing)
- **DRY-RUN**: Analysis-only (no state changes)

## Protection Guards

All protection guards are enabled by default:
- Once-per-bar protection
- Same-direction block
- Entry cooldown (2 bars)
- Reversal enabled
- Position-level TP/SL
- Reduce-only orders

## Monitoring

Metrics available at: `http://localhost:8000/metrics`

Key metrics:
- `aibot_strategy_mode` - Current strategy
- `aibot_open_transitions_total` - State transitions
- `aibot_flip_events_total` - Flip events
- `aibot_entry_skips_total` - Entry skips by reason

## Test Commands

```bash
# Run strategy mode tests
python -m scripts.test_strategy_modes

# Check configuration banner
python -c "from infrastructure.config_manager import config_manager; print(config_manager.get_mode_banner())"
```
