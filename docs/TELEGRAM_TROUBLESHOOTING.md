# Telegram Bot Troubleshooting

Common errors, debug logging, metrics usage, and callback debugging.

## Common Errors

### 1. "Telegram bot token not provided"
**Error**: `ValueError: Telegram bot token not provided and TELEGRAM_BOT_TOKEN not set`

**Solution**:
- Set `TELEGRAM_BOT_TOKEN` environment variable
- Or pass token to `init_telegram_app(token="...")`
- Get token from [@BotFather](https://t.me/botfather) on Telegram

### 2. "Couldn't load <block>"
**Error**: View shows "Couldn't load <block>. Tap to retry."

**Causes**:
- Data source timeout (exchange API, portfolio service)
- Network issues
- Service unavailability

**Solution**:
- Check exchange adapter connection
- Verify portfolio service is running
- Check network connectivity
- Review logs for specific error

**Debugging**:
```bash
# Check logs
grep "context_resolver" logs/app.log | grep ERROR

# Check metrics
curl http://localhost:9090/metrics | grep aibot_tg_errors_total
```

### 3. "Rate limit exceeded"
**Error**: Message shows "Rate limit exceeded. Please wait."

**Cause**: User exceeded 10 requests per 60 seconds

**Solution**:
- Wait 60 seconds
- Reduce interaction frequency
- Rate limit resets automatically

**Metrics**:
```bash
# Check rate limit hits
curl http://localhost:9090/metrics | grep aibot_tg_rate_limited_total
```

### 4. "Unknown callback"
**Error**: Callback query fails with unknown view ID

**Causes**:
- Corrupted callback data
- Unsupported view ID
- Registry resolution failure

**Solution**:
- Check callback data format: `ai:<view>|k1=v1|k2=v2`
- Verify view ID exists in `view_id_map`
- Check registry for short ID resolution

**Debugging**:
```python
# In handlers.py, add logging:
logger.debug(f"Callback data: {callback_data}")
logger.debug(f"Parsed: {parsed}")
```

### 5. Message editing fails
**Error**: `MessageNotModified` or `MessageNotFound`

**Causes**:
- Message deleted by user
- Message already has same content
- Message ID invalid

**Solution**:
- `MessageNotModified`: Swallowed gracefully (no action needed)
- `MessageNotFound`: Re-send MAIN view
- Check message ID in logs

**Logs**:
```bash
grep "MessageNotModified\|MessageNotFound" logs/app.log
```

## Debug Logging

### Enable Debug Logging

Set log level to DEBUG:
```python
import logging
logging.getLogger('adapters.telegram').setLevel(logging.DEBUG)
```

Or in `configs/logging.yaml`:
```yaml
loggers:
  adapters.telegram:
    level: DEBUG
```

### Log Format

One-line logs for performance:
```
TG view=signals sym=BTC t=38ms size=1240B
TG callback=ai:sig|s=BTC t=12ms
TG error=resolver type=timeout
```

### Component Tags

- `telegram_client` - Client connection, message sending
- `telegram_handlers` - Command/callback handling
- `context_resolver` - Data fetching, context resolution
- `callback_registry` - Callback compression/resolution
- `telegram_middleware` - Rate limiting, error handling

### Correlation IDs

All errors include correlation ID for tracing:
```
Error: Couldn't load portfolio (timeout) [corr_id: abc123]
```

Use correlation ID to find related logs:
```bash
grep "abc123" logs/app.log
```

## Metrics Usage

### View Metrics

Check view render counts:
```bash
curl http://localhost:9090/metrics | grep aibot_tg_views_render_total
```

Output:
```
# HELP aibot_tg_views_render_total Total Telegram views rendered
# TYPE aibot_tg_views_render_total counter
aibot_tg_views_render_total{view="main"} 150
aibot_tg_views_render_total{view="signals"} 45
aibot_tg_views_render_total{view="risk"} 23
```

### Latency Metrics

Check render latency:
```bash
curl http://localhost:9090/metrics | grep aibot_tg_latency_ms
```

Output:
```
# HELP aibot_tg_latency_ms_bucket Telegram view render latency in milliseconds
# TYPE aibot_tg_latency_ms_bucket histogram
aibot_tg_latency_ms_bucket{view="main",le="10"} 50
aibot_tg_latency_ms_bucket{view="main",le="25"} 120
aibot_tg_latency_ms_bucket{view="main",le="50"} 145
```

### Error Metrics

Check error counts by type:
```bash
curl http://localhost:9090/metrics | grep aibot_tg_errors_total
```

Output:
```
# HELP aibot_tg_errors_total Total Telegram errors
# TYPE aibot_tg_errors_total counter
aibot_tg_errors_total{type="resolver"} 5
aibot_tg_errors_total{type="handler"} 2
aibot_tg_errors_total{type="timeout"} 3
```

### Rate Limit Metrics

Check rate limit hits:
```bash
curl http://localhost:9090/metrics | grep aibot_tg_rate_limited_total
```

Output:
```
# HELP aibot_tg_rate_limited_total Total Telegram rate limit hits
# TYPE aibot_tg_rate_limited_total counter
aibot_tg_rate_limited_total 12
```

## Callback Debugging

### Check Callback Length

All callbacks must be ≤64 bytes. Check in tests:
```bash
pytest tests/telegram/test_callbacks_len.py -v
```

### Inspect Registry

Print registry contents:
```python
from adapters.telegram.callback_registry import get_callback_registry

registry = get_callback_registry()
print(f"Registry size: {len(registry.registry)}")
for short_id, full_callback in registry.registry.items():
    print(f"{short_id} → {full_callback}")
```

### Parse Callback Manually

```python
from adapters.telegram.handlers import TelegramHandlers

handlers = TelegramHandlers()
parsed = handlers._parse_callback("ai:sig|s=BTC|a=open")
print(parsed)  # {'view_id': 'sig', 'params': {'s': 'BTC', 'a': 'open'}}
```

## Testing

### Run All Telegram Tests
```bash
pytest tests/telegram/ -v
```

### Run Specific Test
```bash
pytest tests/telegram/test_callbacks_len.py -v
pytest tests/telegram/test_routing_smoke.py -v
pytest tests/telegram/test_metrics.py -v
```

### Test Callback Length
```bash
pytest tests/telegram/test_callbacks_len.py::test_all_callbacks_under_64_bytes -v
```

### Test Navigation
```bash
pytest tests/telegram/test_routing_smoke.py::test_callback_navigation_roundtrip -v
```

## Performance

### Slow Renders

If views take >500ms to render:
1. Check context resolver cache (should be 5-10s)
2. Check exchange adapter latency
3. Review data fetching logic (should be minimal per view)
4. Check metrics: `aibot_tg_latency_ms_bucket`

### High Error Rate

If error rate >1%:
1. Check data source availability
2. Review timeout settings
3. Check network connectivity
4. Review logs for specific errors

## Support

For issues:
1. Check logs: `logs/app.log`
2. Check metrics: `http://localhost:9090/metrics`
3. Review this document
4. Check GitHub issues
5. Contact maintainers

