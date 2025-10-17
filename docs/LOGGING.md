# 📝 **AiBotBS Logging Standards**

> **Comprehensive logging guide for debugging and monitoring**

---

## 🎯 **Log Types**

### **1. Decision Logs (Structured JSONL)**

**Location:** `logs/decisions/decisions_YYYY-MM-DD.jsonl`

**Format:**
```json
{
  "t": "2025-10-09T12:00:07.123456+00:00",
  "ts_unix": 1696851607,
  "sym": "BTC-USDT-SWAP",
  "comp": 68.2,
  "dir": "LONG",
  "grade": "B",
  "conf": 68.2,
  "ta": 65.4,
  "ml": 61.2,
  "news": 70.8,
  "risk": 74.0,
  "ta_trend": "up",
  "ta_meanrev": "off",
  "ta_breakout": "off",
  "gate": "pers=true,bias=true,rev=true",
  "action": "OPEN",
  "size": 0.001044,
  "tp": 70400.0,
  "sl": 65300.0,
  "reason": "New long entry signal",
  "timeframe": "15m",
  "meta": {...}
}
```

**Compact Format (Console):**
```
[DECISION] t=12:00:07 sym=BTC-USDT-SWAP  comp=68.2  dir=LONG  ta=65   ml=61   news=71   risk=74   gate=pers=t,bias=t  action=OPEN    size=0.001044 tp=70400.00 sl=65300.00
```

**Usage:**
```python
from infrastructure.decision_logger import get_decision_logger

logger = get_decision_logger()
logger.log_decision(
    symbol="BTC-USDT-SWAP",
    composite_signal=signal,
    action="OPEN",
    position_size=0.001,
    tp_price=70400,
    sl_price=65300,
    reason="Entry signal confirmed"
)
```

---

### **2. Application Logs**

**Location:** `logs/main.log`, `logs/aibotbs.log`

**Format:**
```
2025-10-09 12:00:07.123 | INFO | module:function:line | Message
```

**Levels:**
- `DEBUG` - Detailed information (development)
- `INFO` - General information (production)
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical failures

**Security:**
- ✅ Automatic redaction (API keys, tokens, secrets)
- ✅ 7-day retention
- ✅ 10 MB rotation

---

### **3. Job History**

**Location:** `data/run_history.jsonl`

**Format:**
```json
{
  "name": "trading_analysis",
  "started_at": "2025-10-09T12:00:07+00:00",
  "finished_at": "2025-10-09T12:00:30+00:00",
  "status": "SUCCESS",
  "duration_ms": 23456,
  "error": null
}
```

**Usage:**
```bash
# Last 10 jobs
tail -10 data/run_history.jsonl

# Success rate
cat data/run_history.jsonl | jq 'select(.status=="SUCCESS")' | wc -l

# Failed jobs
cat data/run_history.jsonl | jq 'select(.status=="FAILED")'
```

---

## 📊 **Log Standards**

### **Decision Logging:**

```python
# Every trading decision must be logged
logger.log_decision(
    symbol=symbol,
    composite_signal=signal,
    action=action,  # OPEN, CLOSE, SKIP, REJECTED
    position_size=size,
    tp_price=tp,
    sl_price=sl,
    reason=reason,
    gate_results=gate_results
)
```

**Fields:**
- **t** - Timestamp (ISO 8601)
- **sym** - Symbol
- **comp** - Composite score (0-100)
- **dir** - Direction (LONG/SHORT/FLAT)
- **ta/ml/news/risk** - Component scores
- **gate** - Gate check results
- **action** - What happened
- **size/tp/sl** - Execution details
- **reason** - Why

---

### **Job Logging:**

```python
# Start
logger.info("[JOB] trading_analysis starting")

# Progress
logger.info(f"[JOB] processing symbol {i}/{total}")

# Complete
logger.info(f"[JOB-SUMMARY] trading_analysis symbols={24} entries={3} exits={1}")
```

**Format:**
- `[JOB]` - Job execution
- `[JOB-SUMMARY]` - Job summary
- Structured key=value pairs

---

### **Trade Logging:**

```python
# Order placement
logger.info(f"[ORDER] sym={symbol} clientId={client_id} side={side} amount={amount}")

# Order result
logger.info(f"[ORDER] sym={symbol} clientId={client_id} status=SUCCESS ordId={ord_id}")

# Entry log
logger.info(f"[ENTRY] sym={symbol} dir={direction} size={size} px={price} reason={reason}")

# Exit log
logger.info(f"[EXIT] sym={symbol} reason={reason} pnl={pnl}")
```

---

## 🔒 **Security Standards**

### **Sensitive Data Redaction:**

**Patterns Automatically Redacted:**
```python
# API Keys
"api_key=abc123456789" → "api_key=abc1***"

# Secrets
"secret='my-secret-key'" → "secret='my-s***'"

# Tokens
"token: 123456:ABC-DEF" → "token: 1234***"

# Passwords
"password=MyPassword123" → "password=****"

# Emails
"user@example.com" → "us***@example.com"
```

**Implementation:**
```python
from infrastructure.log_redaction import create_redaction_filter

logger.add(
    "logs/main.log",
    filter=create_redaction_filter(show_prefix=4)
)
```

---

### **Manual Masking:**

```python
from infrastructure.log_redaction import mask_secret

api_key = "abc123def456"
logger.info(f"API Key: {mask_secret(api_key)}")
# Output: "API Key: abc1..."
```

---

## 📁 **Log File Organization**

```
logs/
├── main.log                    # Main application log
├── aibotbs.log                 # Alternative application log
│
├── decisions/                  # Trading decisions (JSONL)
│   ├── decisions_2025-10-09.jsonl
│   ├── decisions_2025-10-08.jsonl
│   └── ...
│
├── agent_*.log                 # Agent-specific logs
│   ├── agent_telegram_bot.log
│   └── agent_telegram_commands.log
│
└── service_*.log               # Service logs (optional)
```

---

## 🔍 **Log Analysis**

### **Decision Replay:**

```bash
# Replay today's decisions
python scripts/replay_decisions.py

# Replay specific date
python scripts/replay_decisions.py --date 2025-10-09

# Filter by symbol
python scripts/replay_decisions.py --symbol BTC-USDT-SWAP

# Last 10 decisions
python scripts/replay_decisions.py --last 10

# Summary only
python scripts/replay_decisions.py --summary
```

**Output:**
```
============================================================
DECISION REPLAY: BTC-USDT-SWAP
============================================================

⏰ Time: 2025-10-09T12:00:07+00:00

📊 Composite Signal:
  Score: 68.2/100 (Grade: B)
  Decision: LONG
  Confidence: 68.2%

🎯 Component Scores:
  TA:   65.4/100 - Trend: up
  ML:   61.2/100
  News: 70.8/100
  Risk: 74.0/100

...
```

---

### **Log Searching:**

```bash
# Errors
grep "ERROR" logs/main.log

# Specific symbol
grep "BTC-USDT" logs/main.log

# Decisions
grep "\[DECISION\]" logs/main.log

# Job summaries
grep "\[JOB-SUMMARY\]" logs/main.log

# Circuit breaker
grep "circuit.breaker\|EMERGENCY\|PAUSED" logs/main.log -i
```

---

### **Performance Analysis:**

```bash
# Job duration
cat data/run_history.jsonl | jq '.duration_ms' | awk '{s+=$1; c++} END {print "Avg:", s/c, "ms"}'

# Success rate
total=$(cat data/run_history.jsonl | wc -l)
success=$(cat data/run_history.jsonl | jq 'select(.status=="SUCCESS")' | wc -l)
echo "Success rate: $(echo "scale=2; $success/$total*100" | bc)%"

# Decision distribution
cat logs/decisions/*.jsonl | jq -r '.dir' | sort | uniq -c
```

---

## ⚙️ **Configuration**

### **Log Level:**

```bash
# .env
LOG_LEVEL=INFO   # DEBUG, INFO, WARNING, ERROR

# Or runtime
python -c "from infrastructure.logger import set_all_log_levels; set_all_log_levels('DEBUG')"
```

### **Redaction:**

```python
# config.yaml or policy.yaml (future)
logging:
  redaction:
    enabled: true
    show_prefix: 4  # Show first 4 chars
    patterns:
      - api_key
      - secret
      - token
      - password
```

---

## 🎓 **Best Practices**

### **DO:**
- ✅ Log all trading decisions
- ✅ Use structured formats (JSONL)
- ✅ Include context (symbol, score, reason)
- ✅ Use consistent prefixes ([JOB], [ORDER], [DECISION])
- ✅ Redact sensitive data
- ✅ Rotate logs regularly

### **DON'T:**
- ❌ Log full API credentials
- ❌ Log passwords/secrets
- ❌ Log PII without redaction
- ❌ Use inconsistent formats
- ❌ Skip critical decisions
- ❌ Ignore log errors

---

## 📖 **Log Reading Guide**

### **Quick Scan:**
```bash
# Latest activity
tail -50 logs/main.log

# Real-time monitoring
tail -f logs/main.log | grep "DECISION\|ERROR\|EMERGENCY"
```

### **Deep Dive:**
```bash
# Specific trade investigation
python scripts/replay_decisions.py --symbol BTC-USDT-SWAP --date 2025-10-09

# Full day analysis
python scripts/replay_decisions.py --date 2025-10-09 --summary
```

---

**Last Updated:** 2025-10-10  
**Version:** 1.0.0

