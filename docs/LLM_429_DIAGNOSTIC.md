# LLM 429 Diagnostic System
**Created:** 2025-10-20  
**Purpose:** Detailed diagnostic logging for LLM API calls to distinguish between real OpenAI rate limits and internal/network errors.

## Overview

This diagnostic system provides comprehensive logging and metrics for LLM API calls, specifically designed to identify and classify different types of errors, particularly distinguishing between:

- **Real OpenAI rate limits** (HTTP 429 with rate-limit headers)
- **Internal/network errors** (other HTTP errors or network issues)

## Added Fields and Logging

### Console Logging (Summary)
```
📊 [LLM] sym=BTC req_id=req_123 tokens=150+75
❌ [LLM] sym=BTC req_id=req_456 status=429 rate_limit retry_after=60
❌ [LLM] sym=BTC req_id=req_789 status=500 internal_error
```

### File Logging (Detailed)
```
LLM_SUCCESS | symbol=BTC | request_id=req_123 | model=gpt-3.5-turbo | prompt_tokens=150 | completion_tokens=75 | status=200

LLM_ERROR | symbol=BTC | request_id=req_456 | model=gpt-3.5-turbo | http_status=429 | error_source=openai_rate_limit | error_type=insufficient_quota | error_code=insufficient_quota | retry_after=60 | message=You exceeded your current quota...

LLM_ERROR | symbol=BTC | request_id=req_789 | model=gpt-3.5-turbo | http_status=500 | error_source=internal_or_network | error_type=server_error | error_code=internal_error | retry_after=None | message=Internal server error
```

## Prometheus Metrics

### New Metrics Added

1. **`aibot_llm_requests_total`**
   - Labels: `status` (2xx, 4xx, 5xx)
   - Description: Total LLM requests made

2. **`aibot_llm_rate_limits_total`**
   - Labels: `source` (openai)
   - Description: Total LLM rate limit hits

3. **`aibot_llm_internal_errors_total`**
   - Description: Total LLM internal/network errors

4. **`aibot_llm_request_tokens_sum`**
   - Labels: `model`
   - Description: Total LLM request tokens used

5. **`aibot_llm_response_tokens_sum`**
   - Labels: `model`
   - Description: Total LLM response tokens used

### Example Metrics Output
```
# HELP aibot_llm_requests_total Total LLM requests made
# TYPE aibot_llm_requests_total counter
aibot_llm_requests_total{status="2xx"} 45
aibot_llm_requests_total{status="4xx"} 12
aibot_llm_requests_total{status="5xx"} 3

# HELP aibot_llm_rate_limits_total Total LLM rate limit hits
# TYPE aibot_llm_rate_limits_total counter
aibot_llm_rate_limits_total{source="openai"} 8

# HELP aibot_llm_internal_errors_total Total LLM internal/network errors
# TYPE aibot_llm_internal_errors_total counter
aibot_llm_internal_errors_total 4

# HELP aibot_llm_request_tokens_sum Total LLM request tokens used
# TYPE aibot_llm_request_tokens_sum counter
aibot_llm_request_tokens_sum{model="gpt-3.5-turbo"} 6750

# HELP aibot_llm_response_tokens_sum Total LLM response tokens used
# TYPE aibot_llm_response_tokens_sum counter
aibot_llm_response_tokens_sum{model="gpt-3.5-turbo"} 2250
```

## How to Identify Real 429 Rate Limits

### Real OpenAI Rate Limit (HTTP 429)
**Indicators:**
- HTTP status code: 429
- Response headers contain rate-limit information:
  - `x-ratelimit-limit-requests`
  - `x-ratelimit-remaining-requests`
  - `x-ratelimit-reset-requests`
  - `x-ratelimit-limit-tokens`
  - `x-ratelimit-remaining-tokens`
  - `x-ratelimit-reset-tokens`
  - `retry-after`
- Error body contains OpenAI-specific error information
- `error_source=openai_rate_limit` in logs

**Example:**
```
HTTP 429
Headers: x-ratelimit-limit-requests: 60, x-ratelimit-remaining-requests: 0, retry-after: 60
Body: {"error": {"type": "insufficient_quota", "code": "insufficient_quota", "message": "You exceeded your current quota..."}}
```

### Internal/Network Error
**Indicators:**
- HTTP status code: 4xx (except 429) or 5xx
- No rate-limit headers present
- Generic error messages
- `error_source=internal_or_network` in logs

**Examples:**
```
HTTP 500 - Internal server error
HTTP 401 - Unauthorized (invalid API key)
HTTP 403 - Forbidden
Network timeout
Connection refused
```

## Error Classification Logic

```python
if http_status == 429 and 'x-ratelimit-limit-requests' in headers:
    error_source = "openai_rate_limit"
    # Record as rate limit
elif http_status and str(http_status).startswith('4'):
    error_source = "internal_or_network"
    # Record as 4xx error
elif http_status and str(http_status).startswith('5'):
    error_source = "internal_or_network"
    # Record as 5xx error
else:
    error_source = "internal_or_network"
    # Record as internal error
```

## Usage

### In Code
```python
from application.news_llm_analyzer import NewsLLMAnalyzer

analyzer = NewsLLMAnalyzer(api_key="your-key")
result = await analyzer.analyze_news_batch(articles, "BTC", aliases)
```

### Monitoring
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics | grep aibot_llm_

# Check logs
tail -f logs/bot.log | grep "LLM_"
```

## Benefits

1. **Clear Error Classification**: Distinguish between real rate limits and other errors
2. **Detailed Diagnostics**: Full HTTP headers and error details in logs
3. **Prometheus Metrics**: Track LLM usage patterns and error rates
4. **Token Tracking**: Monitor token consumption per model
5. **Request Tracing**: Track individual requests with request IDs

## Troubleshooting

### High Rate Limit Errors
- Check OpenAI API usage limits
- Implement request throttling
- Consider upgrading API plan

### High Internal Errors
- Check network connectivity
- Verify API key validity
- Check OpenAI service status

### Token Usage Issues
- Monitor token consumption patterns
- Optimize prompts to reduce token usage
- Consider model alternatives

## Notes

- **No Behavior Changes**: This system only adds diagnostic logging, no throttling or retry logic
- **API Key Security**: API keys are never logged
- **Console vs File**: Console shows summary, file shows full details
- **Performance**: Minimal overhead, async logging

