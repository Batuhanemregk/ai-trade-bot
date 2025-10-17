# ⚡ **Quick Reference Card**

## 🚀 **Başlatma Komutları**

### **Production (24/7):**
```bash
python -m infrastructure.scheduler_runner
```

### **Development (Quick Test):**
```bash
python main.py trading --timeout 300
```

### **Test Suite:**
```bash
python scripts/test_scheduler.py
```

### **Health Check:**
```bash
python scripts/check_scheduler_health.py
```

---

## 📊 **Mode Comparison**

| Mode | Command | Use For | Scheduler? |
|------|---------|---------|------------|
| **Scheduler** | `scheduler_runner` | Production, 24/7 | ✅ APScheduler |
| **Direct** | `main.py trading` | Development, quick test | ❌ While loops |

---

## 🔧 **Configuration**

### **Mode Selection (policy.yaml):**
```yaml
exchange:
  mode: "dry-run"  # Safe (no real orders)
  # mode: "live"   # Real trading (CAUTION!)
```

### **Risk Settings:**
```yaml
trading:
  risk:
    max_position_size: 0.1   # 10% max per position
    max_total_risk: 0.6      # 60% total exposure
    stop_loss_pct: 0.02      # 2% SL
    take_profit_pct: 0.04    # 4% TP
```

---

## 📋 **Jobs Schedule**

| Job | Frequency | What It Does |
|-----|-----------|--------------|
| trading_analysis | 15m | Main trading logic |
| trailing_5m | 5m | Update trailing stops |
| news_5m | 5m | Fetch & analyze news |
| regime_1h | 1h | Market regime detection |
| risk_monitor | 1m | Risk metrics check |

---

## 🛑 **Stop Commands**

```bash
# Graceful
Ctrl+C

# Force (emergency only)
kill -9 <pid>
```

---

## 📝 **Log Files**

```bash
logs/main.log              # Main log
data/runtime_state.json    # Current state
data/run_history.jsonl     # Job history
```

---

## 🚨 **Common Issues**

### **IP Whitelist Error:**
```
okx {"code":"50110"}
```
**Fix:** Add IP to OKX dashboard

### **Telegram Not Working:**
**Fix:** Send /start to bot

### **Job Not Running:**
**Fix:** Check logs, restart scheduler

---

## 📚 **Documentation**

| Topic | File |
|-------|------|
| Quick Start | `docs/QUICKSTART.md` |
| Development | `docs/DEVELOPMENT_TESTING.md` ⭐ |
| Production | `docs/SCHEDULER_PRODUCTION_READY.md` |
| Full Guide | `docs/SCHEDULER_CALISTIRMA_KILAVUZU.md` |

---

**📖 Full index:** [docs/INDEX.md](INDEX.md)

