# 🔒 **AiBotBS Security Guide**

> **Security best practices and safety features**

---

## 🛡️ **SECURITY FEATURES**

### **1. API Key Protection**

#### **Environment Variables:**
```bash
# .env file (NEVER commit to git!)
OKX_API_KEY=your_key_here
OKX_API_SECRET=your_secret_here
OKX_API_PASSPHRASE=your_passphrase_here
TELEGRAM_BOT_TOKEN=your_token_here
OPENAI_API_KEY=your_openai_key_here
```

#### **Gitignore:**
```
# .gitignore
.env
*.env
.env.*
!.env.example
```

#### **Log Redaction:**
```python
# Automatic redaction in logs
logger.info(f"API Key: {api_key}")
# Output: "API Key: abc1***"

# All sensitive patterns masked:
✅ api_key → abc1***
✅ secret → xyz9***
✅ token → 1234***
✅ passphrase → pass***
✅ password → ****
```

---

### **2. IP Whitelist (OKX)**

**Setup:**
1. OKX Dashboard → API Management
2. Select your API key
3. Add IP addresses
4. Save

**Best Practices:**
- ✅ Use specific IP (not 0.0.0.0/0)
- ✅ Update when IP changes
- ✅ Monitor failed auth attempts
- ❌ Never use wildcard in production

---

### **3. Trading Safety**

#### **Dry-Run Mode:**
```yaml
# policy.yaml
exchange:
  mode: "dry-run"  # No real orders
```

**Features:**
- Orders simulated, not sent
- Full scoring and logic runs
- Safe for testing
- No capital risk

#### **Risk Limits:**
```yaml
trading:
  risk:
    max_position_size: 0.1   # 10% max per position
    max_total_risk: 0.6      # 60% total exposure
    max_drawdown: 0.15       # 15% drawdown limit
```

---

### **4. Circuit Breaker**

**Automatic Protection:**

```
🔴 Daily Loss >25%
   → Emergency stop
   → Close all positions (recommended)
   → Telegram alert
   → Manual resume required

🟡 Drawdown >15%
   → Warning state
   → Continue with caution
   → Increased monitoring

⏸️ Consecutive Losses ≥3
   → 24-hour pause
   → Auto-resume after cooldown
   → Manual resume available
```

**Manual Controls:**
- `/stop` - Emergency stop
- `/pause [hours]` - Temporary pause
- `/resume` - Resume trading
- `/breaker` - Check status

---

### **5. Data Protection**

#### **State Files:**
```
data/
├── runtime_state.json           # Encrypted recommended
├── circuit_breaker_state.json   # Secure permissions
└── run_history.jsonl            # Log rotation
```

**Permissions:**
```bash
# Linux
chmod 600 data/*.json
chmod 700 data/

# Backup
tar -czf backup.tar.gz data/ --exclude="*.log"
```

---

## 🔐 **ACCESS CONTROL**

### **API Permissions (OKX):**

**Required:**
- ✅ Read Account
- ✅ Trade
- ✅ Withdraw (optional, for profits)

**Recommended Settings:**
- ✅ IP Whitelist enabled
- ✅ Withdraw whitelist addresses
- ✅ 2FA enabled on OKX account
- ❌ No universal API key

---

### **Telegram Bot Security:**

**Bot Token:**
```bash
# Keep secure
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...

# Never log full token
# Redaction: 1234***
```

**Chat ID:**
```bash
# Restrict to your chat only
TELEGRAM_CHAT_ID=your_chat_id

# Bot only responds to this chat
```

**Commands:**
- Admin commands require chat ID match
- No public access
- Rate limiting applied

---

## 🔍 **AUDIT & LOGGING**

### **What Gets Logged:**

#### **✅ Safe to Log:**
- Trading decisions (scores, directions)
- Performance metrics
- System events
- Error messages (sanitized)

#### **🔒 Redacted Automatically:**
- API keys (abc1***)
- Secrets (xyz9***)
- Tokens (1234***)
- Passwords (*****)
- Email addresses (us***@domain.com)

#### **❌ Never Logged:**
- Full API credentials
- Private keys
- User passwords

---

### **Log Files:**

```
logs/
├── main.log                 # Main log (with redaction)
├── aibotbs.log             # Application log (with redaction)
├── decisions/              # Trading decisions (no secrets)
│   └── decisions_*.jsonl
└── agent_*.log             # Agent logs (with redaction)
```

**Retention:**
- Main logs: 7 days
- Decision logs: 30 days
- Job history: 30 days

**Rotation:**
- Automatic (daily or 10 MB)
- Manual: `python scripts/cleanup_logs.py`

---

## ⚠️ **RISK MANAGEMENT**

### **Position Limits:**

```python
# Maximum exposure per symbol
max_position_size = 10% of portfolio

# Total portfolio risk
max_total_risk = 60% of portfolio

# Concurrent positions
max_positions = 20

# Leverage
max_leverage = 3.0x
```

### **Loss Limits:**

```python
# Per trade
stop_loss = 2% (ATR-based)

# Daily
daily_loss_limit = 25% (circuit breaker)

# Overall
max_drawdown = 15%
```

---

## 🚨 **INCIDENT RESPONSE**

### **Severity Levels:**

**🔴 CRITICAL (Immediate Action):**
- Emergency stop triggered
- Exchange API down
- Unauthorized access detected
- Data corruption

**🟡 HIGH (Within 1 hour):**
- High drawdown (>10%)
- Multiple failed trades
- API errors increasing
- Memory issues

**🟢 MEDIUM (Within 24 hours):**
- Single failed trade
- Warning state
- Performance degradation

**⚪ LOW (Routine):**
- Normal operations
- Scheduled maintenance

---

### **Incident Steps:**

1. **Detect**
   - Circuit breaker alert
   - Telegram notification
   - Log monitoring

2. **Assess**
   - Check severity
   - Review logs
   - Check positions

3. **Contain**
   - `/stop` if critical
   - `/pause` if high
   - Continue monitoring if medium

4. **Investigate**
   - Review decision logs
   - Check job history
   - Analyze root cause

5. **Resolve**
   - Fix issue
   - Test thoroughly
   - Document

6. **Resume**
   - `/resume` command
   - Monitor closely
   - Update procedures

---

## 📋 **SECURITY CHECKLIST**

### **Initial Setup:**
```
□ .env file created (not in git)
□ API keys secured
□ IP whitelist configured
□ Telegram bot token secure
□ Log redaction verified
□ Dry-run mode tested first
```

### **Weekly:**
```
□ Review access logs
□ Check for suspicious activity
□ Verify IP whitelist
□ Audit recent trades
□ Check circuit breaker logs
```

### **Monthly:**
```
□ Rotate API keys (optional)
□ Review permissions
□ Update dependencies
□ Security patch check
□ Backup verification
```

---

## 🔑 **CREDENTIALS MANAGEMENT**

### **.env Template:**

```bash
# .env.example
# Copy to .env and fill in values

# OKX Exchange
OKX_API_KEY=your_api_key_here
OKX_API_SECRET=your_api_secret_here
OKX_API_PASSPHRASE=your_passphrase_here

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# OpenAI (Optional)
OPENAI_API_KEY=your_openai_key_here

# Logging
LOG_LEVEL=INFO
```

### **Safe Practices:**
- ✅ Use .env.example for template
- ✅ Never commit .env
- ✅ Use different keys for test/prod
- ✅ Rotate keys periodically
- ❌ Never hardcode credentials
- ❌ Never share keys in chat/email

---

## 🎯 **SECURITY BEST PRACTICES**

### **1. Principle of Least Privilege:**
- Only required API permissions
- Minimal withdrawal limits
- Restricted IP access

### **2. Defense in Depth:**
- Circuit breaker (automatic)
- Manual controls (Telegram)
- Risk limits (config)
- Monitoring (logs)

### **3. Fail Secure:**
- Default: dry-run mode
- Errors → stop trading
- Unknown state → cautious

### **4. Audit Trail:**
- All decisions logged
- State changes tracked
- Actions traceable

---

## 📞 **EMERGENCY CONTACTS**

**Automated:**
- Circuit Breaker → Telegram alerts
- Error threshold → Notifications
- System status → Updates

**Manual:**
- `/stop` → Emergency halt
- `/pause` → Temporary pause
- Support → (your contact)

---

**Last Updated:** 2025-10-10  
**Version:** 1.0.0

