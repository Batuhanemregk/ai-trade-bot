# Telegram Bot Callbacks

This document describes the callback data schema, compression algorithm, and registry usage.

## Schema Format

### General Format
```
ai:<view>|k1=v1|k2=v2
```

### Components
- **Prefix**: `ai:` (identifies as bot callback)
- **View ID**: `<view>` (e.g., `main`, `sig`, `risk`, `ord`, `tpsl`, `trl`, `pnl`, `pos`, `set`)
- **Parameters**: `|k1=v1|k2=v2` (optional, pipe-separated key=value pairs)

## Examples

### Simple Views
```
ai:main          → Main view
ai:risk          → Risk view
ai:pnl           → PnL view
ai:set           → Settings view
```

### Views with Parameters
```
ai:sig|s=BTC           → Signals view, filtered by BTC
ai:ord|s=BTC|p=next    → Orders view, BTC symbol, next page
ai:tpsl|s=ETH|a=edit   → TP/SL view, ETH symbol, edit action
ai:trl|s=BTC|a=be      → Trailing view, BTC symbol, breakeven action
```

## Key Shortcuts (Compression)

To stay within 64-byte limit, common keys are shortened:

| Full Key | Short Key | Example |
|----------|-----------|---------|
| `sym` | `s` | `ai:sig\|s=BTC` |
| `symbol` | `s` | `ai:ord\|s=BTC` |
| `action` | `a` | `ai:tpsl\|a=edit` |
| `act` | `a` | `ai:trl\|a=be` |
| `page` | `p` | `ai:ord\|p=next` |
| `view` | `v` | (internal only) |

### Compression Rules
- **Automatic**: Registry automatically compresses keys on `register()`
- **Transparent**: Keys are expanded on `resolve()` (backwards compatible)
- **Priority**: Short keys take precedence if both exist

## Callback Registry

### Usage
```python
from adapters.telegram.callback_registry import get_callback_registry

registry = get_callback_registry()

# Register callback (compresses if needed)
short_id = registry.register("ai:sig|sym=BTCUSDT|page=next")
# Returns: "ai:sig|s=BTCUSDT|p=next" (if ≤64B) or "cb0" (if >64B)

# Resolve callback (expands keys)
full_callback = registry.resolve(short_id)
# Returns: "ai:sig|sym=BTCUSDT|page=next" (with expanded keys)
```

### Compression Algorithm

1. **Check length**: If ≤64 bytes, return as-is
2. **Compress keys**: Replace `|sym=` with `|s=`, etc.
3. **Check again**: If still >64 bytes, generate short ID (`cb0`, `cb1`, ...)
4. **Register**: Store mapping `short_id → full_callback` in registry
5. **Return**: Return short ID for button

### Short ID Format
- **Pattern**: `cb` + base62 number (e.g., `cb0`, `cb1`, `cbA`, `cbZ`)
- **Encoding**: Base62 (0-9, a-z, A-Z) for compact representation
- **Max**: Unlimited (but registry grows with unique callbacks)

## Callback Routing

### Handler Routing
```python
# In handlers.py
def _parse_callback(self, callback_data: str) -> Dict[str, Any]:
    """Parse callback data: ai:<view>|k1=v1|k2=v2"""
    if not callback_data.startswith('ai:'):
        return {'view_id': 'main', 'params': {}}
    
    parts = callback_data[3:].split('|')
    view_id = parts[0]
    params = {}
    
    for part in parts[1:]:
        if '=' in part:
            k, v = part.split('=', 1)
            params[k] = v
    
    return {'view_id': view_id, 'params': params}
```

### View Routing
```python
view_id_map = {
    'main': ('main', resolve_main_context, build_main_view),
    'sig': ('signals', resolve_signals_context, build_signals_view),
    'risk': ('risk', resolve_risk_context, build_risk_view),
    # ... etc
}
```

## 64-Byte Limit

### Why 64 Bytes?
Telegram Bot API enforces a **64-byte limit** on `callback_data` for inline keyboard buttons.

### Enforcement
- **Automatic**: Registry compresses callbacks to fit within limit
- **Test**: `test_callbacks_len.py` asserts all callbacks ≤64B
- **Validation**: Throws error if callback cannot be compressed to ≤64B

### Edge Cases
- **Long symbols**: `BTCUSDT` (7B) is fine, but `VERYLONGSYMBOL` (14B) might push over limit
- **Multiple params**: `ai:ord|s=BTC|p=next|f=btc|t=1h` (38B) is fine
- **Compression**: Registry automatically uses short IDs if needed

## Common Callbacks

### Navigation
- `ai:main` - Main view
- `ai:sig` - Signals view
- `ai:risk` - Risk view
- `ai:pos` - Positions view
- `ai:ord` - Orders view
- `ai:pnl` - PnL view
- `ai:tpsl` - TP/SL view
- `ai:trl` - Trailing view
- `ai:set` - Settings view

### Actions
- `ai:sig|s=BTC|a=open` - Open position for BTC (signals view)
- `ai:tpsl|s=ETH|a=edit` - Edit TP/SL for ETH
- `ai:trl|s=BTC|a=be` - Move trailing to breakeven for BTC
- `ai:ord|p=next` - Next page of orders
- `ai:ord|p=prev` - Previous page of orders
- `ai:pnl|a=csv` - Export PnL as CSV

### Pagination
- `ai:ord|p=0` - Orders page 0 (first page)
- `ai:ord|p=1` - Orders page 1 (second page)
- `ai:ord|p=next` - Next page (relative)
- `ai:ord|p=prev` - Previous page (relative)

## Testing

Run callback length tests:
```bash
pytest tests/telegram/test_callbacks_len.py -v
```

Tests verify:
- All callbacks ≤64 bytes
- Compression works correctly
- Keys expand correctly on resolve
- Schema parsing works for all formats

