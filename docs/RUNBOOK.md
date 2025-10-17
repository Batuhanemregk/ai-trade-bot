# 📖 **AiBotBS Runbook - Operations Guide**

> **Emergency procedures, troubleshooting, and operations manual**

---

## 🚨 **EMERGENCY PROCEDURES**

### **Emergency Stop (Immediate)**

**When to use:**
- Daily loss >25%
- System malfunction
- Exchange issues
- Manual intervention needed

**How to trigger:**

```bash
# Via Telegram
/stop

# Via Python
python -c "from application.circuit_breaker import get_circuit_breaker; import asyncio; asyncio.run(get_circuit_breaker().manual_stop('Emergency'))"
```

**What happens:**
1. Circuit breaker → EMERGENCY state
2. Trading halted immediately
3. Telegram alert sent
4. State persisted to disk
5. Manual resume required

**Recovery:**
```bash
# After investigation
/resume  # Via Telegram

# Or reset emergency state
python -c "from application.circuit_breaker import get_circuit_breaker; import asyncio; asyncio.run(get_circuit_breaker().reset_emergency())"
```

---

### **Pause Trading (Temporary)**

**When to use:**
- Monitoring suspicious activity
- Market volatility
- Scheduled maintenance
- Testing changes

**How to trigger:**

```bash
# Pause for 24 hours (default)
/pause

# Pause for specific duration
/pause 12  # 12 hours
/pause 48  # 48 hours
```

**What happens:**
1. Circuit breaker → PAUSED state
2. No new trades
3. Existing positions monitored
4. Auto-resume after duration

**Manual resume:**
```bash
/resume
```

---

### **Circuit Breaker Status**

**Check current state:**

```bash
# Via Telegram
/breaker

# Via Python
python -c "from application.circuit_breaker import get_circuit_breaker; import json; print(json.dumps(get_circuit_breaker().get_status(), indent=2))"
```

**States:**
- 🟢 **NORMAL** - All systems operational
- 🟡 **WARNING** - High drawdown detected
- ⏸️ **PAUSED** - Trading temporarily suspended
- 🚨 **EMERGENCY** - Emergency stop triggered

---

## 🔄 **ROUTINE OPERATIONS**

### **Starting the System**

```bash
# 1. Check configuration
python scripts/validate_config.py

# 2. Health check
python scripts/check_scheduler_health.py

# 3. Start scheduler
python -m infrastructure.scheduler_runner

# Monitor logs
tail -f logs/main.log
```

### **Stopping the System**

```bash
# Graceful shutdown
Ctrl+C

# Or via command
kill -TERM <pid>
```

**What happens:**
- New jobs won't start
- Running jobs complete (max 30s)
- State saved
- Telegram shutdown message

---

### **Health Monitoring**

**Regular checks (every 5-10 minutes):**

```bash
# Quick health check
python scripts/check_scheduler_health.py

# Scheduler status
ps aux | grep scheduler_runner  # Linux
tasklist | findstr python       # Windows

# Log errors
grep "ERROR" logs/main.log | tail -20

# Job history
tail -20 data/run_history.jsonl
```

---

## 🔧 **TROUBLESHOOTING**

### **Problem: Scheduler Not Running**

**Symptoms:**
- No recent job history
- Telegram notifications stopped
- Stale logs

**Diagnosis:**
```bash
# Check process
ps aux | grep scheduler_runner

# Check last job
tail -1 data/run_history.jsonl

# Check logs
tail -50 logs/main.log | grep "ERROR"
```

**Solution:**
```bash
# Restart scheduler
python -m infrastructure.scheduler_runner
```

---

### **Problem: IP Whitelist Error**

**Symptoms:**
```
okx {"msg":"Your IP is not included in whitelist","code":"50110"}
```

**Solution:**
1. Get current IP: `curl ifconfig.me`
2. OKX dashboard → API Management
3. Add IP to whitelist
4. Wait 5 minutes
5. Test: `python scripts/okx_auth_check.py`

---

### **Problem: High Memory Usage**

**Symptoms:**
- Memory >500MB
- Slow performance

**Diagnosis:**
```bash
# Check memory
python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"

# Check process
top | grep python  # Linux
tasklist /FI "IMAGENAME eq python.exe" /FO TABLE  # Windows
```

**Solution:**
```bash
# Clean up old state
python -c "from infrastructure.scheduler_runner import SchedulerRunner; import asyncio; r = SchedulerRunner(); asyncio.run(r.initialize()); asyncio.run(r.jobs['trading_analysis'].cleanup_old_state())"

# Restart scheduler
Ctrl+C
python -m infrastructure.scheduler_runner
```

---

### **Problem: Jobs Not Executing**

**Symptoms:**
- No job execution in history
- Missed runs

**Diagnosis:**
```bash
# Check scheduler status
python -c "from infrastructure.scheduler_runner import SchedulerRunner; import asyncio; r = SchedulerRunner(); asyncio.run(r.initialize()); print([j.name for j in r.scheduler.get_jobs()])"

# Check watchdog
grep "WATCHDOG" logs/main.log
```

**Solution:**
1. Check cron expressions in policy.yaml
2. Check job enabled status
3. Restart scheduler

---

### **Problem: Telegram Not Working**

**Symptoms:**
- No Telegram notifications
- Bot commands not responding

**Diagnosis:**
```bash
# Check token
echo $TELEGRAM_BOT_TOKEN

# Test connection
python test_telegram_direct.py
```

**Solution:**
1. Verify token in .env
2. Send /start to bot
3. Check policy.yaml: telegram.enabled: true
4. Restart scheduler

---

## 📊 **MONITORING DASHBOARD**

### **Key Metrics to Watch:**

```
Every 5 minutes:
- Job execution success rate
- API latency
- Memory usage

Every 15 minutes:
- Trading signals generated
- Positions opened/closed
- PnL movement

Every hour:
- Win rate
- Portfolio exposure
- Risk metrics
```

### **Log Locations:**

```
logs/main.log                  - Main application log
logs/decisions/                - Trading decisions (JSONL)
logs/agent_*.log               - Agent-specific logs
data/run_history.jsonl         - Job execution history
data/runtime_state.json        - Current state
data/circuit_breaker_state.json - Circuit breaker state
```

---

## 🛠️ **MAINTENANCE TASKS**

### **Daily:**
- [ ] Check Telegram notifications
- [ ] Quick health check
- [ ] Review error logs

### **Weekly:**
- [ ] Full health check
- [ ] Performance review
- [ ] Log cleanup (automatic)

### **Monthly:**
- [ ] State file cleanup
- [ ] Performance analysis
- [ ] Strategy optimization
- [ ] Risk parameter review

---

## 🔒 **SECURITY PROCEDURES**

### **API Key Rotation:**

```bash
# 1. Generate new OKX API keys

# 2. Update .env
OKX_API_KEY=new_key
OKX_API_SECRET=new_secret
OKX_API_PASSPHRASE=new_passphrase

# 3. Restart scheduler
Ctrl+C
python -m infrastructure.scheduler_runner
```

### **Log Security:**

**✅ Automatic redaction enabled:**
- API keys masked (abc1***)
- Tokens masked (1234***)
- Secrets masked
- Emails partially hidden

**Check redaction:**
```bash
grep "api_key" logs/main.log
# Should see: api_key=abc1***
```

---

## 📞 **ESCALATION PROCEDURES**

### **Level 1: Automatic (Circuit Breaker)**
- Daily loss >25% → Emergency stop
- 3 consecutive losses → 24h pause
- High drawdown →warning

### **Level 2: Manual (Operator)**
- `/stop` - Emergency stop
- `/pause` - Temporary pause
- Restart scheduler

### **Level 3: Admin (Developer)**
- Code changes
- Config modifications
- Emergency patches

---

## 📋 **CHECKLISTS**

### **Daily Startup Checklist:**
```
□ Check circuit breaker state (/breaker)
□ Review overnight logs
□ Verify Telegram connectivity
□ Check API health
□ Review open positions
□ Start scheduler
```

### **Incident Response Checklist:**
```
□ Identify issue severity
□ Check circuit breaker state
□ Review recent logs
□ Check positions
□ Trigger emergency stop if needed
□ Investigate root cause
□ Implement fix
□ Test thoroughly
□ Resume trading
□ Document incident
```

---

## 🚀 **DEPLOYMENT PROCEDURES**

### **New Version Deployment:**

```bash
# 1. Backup current state
tar -czf backup_$(date +%Y%m%d).tar.gz data/ logs/

# 2. Stop scheduler
Ctrl+C

# 3. Git pull / update code
git pull origin main

# 4. Run tests
python scripts/test_scheduler.py

# 5. Validate config
python scripts/validate_config.py

# 6. Start scheduler
python -m infrastructure.scheduler_runner

# 7. Monitor for 30 minutes
tail -f logs/main.log
```

---

## 🎯 **QUICK REFERENCE**

| Task | Command |
|------|---------|
| **Start** | `python -m infrastructure.scheduler_runner` |
| **Stop** | `Ctrl+C` |
| **Emergency Stop** | `/stop` (Telegram) |
| **Pause** | `/pause 24` (Telegram) |
| **Resume** | `/resume` (Telegram) |
| **Status** | `/breaker` (Telegram) |
| **Health Check** | `python scripts/check_scheduler_health.py` |
| **Validate Config** | `python scripts/validate_config.py` |
| **View Logs** | `tail -f logs/main.log` |

---

**Last Updated:** 2025-10-10  
**Version:** 1.0.0

