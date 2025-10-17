# 📚 AiBotBS Documentation

> **Comprehensive documentation for the AI-powered trading bot system**  
> **See [INDEX.md](INDEX.md) for complete documentation index**

---

## 🚀 **Quick Start Guides**

### **For New Users:**
1. **[⚡ QUICKSTART.md](QUICKSTART.md)** - 5-minute setup (English)
2. **[🇹🇷 BASLATMA_ONEMLI.md](BASLATMA_ONEMLI.md)** - Hızlı başlatma (Turkish)
3. **[📊 SCHEDULER_CALISTIRMA_KILAVUZU.md](SCHEDULER_CALISTIRMA_KILAVUZU.md)** - Complete guide (Turkish)

### **For Developers:**
1. **[🔧 DEVELOPMENT_TESTING.md](DEVELOPMENT_TESTING.md)** - ⭐ **MUST READ!**
   - Direct mode vs Scheduler mode
   - When to use which
   - Development workflow
   - Testing strategies
2. **[🚀 START_AND_MONITORING.md](START_AND_MONITORING.md)** - Dev scripts & monitoring
   - PowerShell & Bash development scripts
   - Prometheus & Grafana setup
   - Health checks and troubleshooting
3. **[📊 ENHANCED_LOGGING.md](ENHANCED_LOGGING.md)** - Enhanced logging system
   - Line vs Block mode formatting
   - Log deduplication
   - Prometheus metrics integration
   - Performance improvements

---

## 📖 **Main Documentation**

### **🏗️ Architecture & Design:**
- **[ARCHITECTURE_FINAL.md](ARCHITECTURE_FINAL.md)** - Clean Architecture, SOLID principles
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System overview
- **[AGENTS.md](AGENTS.md)** - Multi-agent system
- **[SCHEDULER.md](SCHEDULER.md)** - Job scheduling
- **[ADR/0001-clean-architecture.md](ADR/0001-clean-architecture.md)** - Architecture decisions

### **⚡ Operations & Execution:**
- **[START_SCHEDULER.md](START_SCHEDULER.md)** - Scheduler operations guide
- **[SCHEDULER_PRODUCTION_READY.md](SCHEDULER_PRODUCTION_READY.md)** - Production checklist
- **[EXECUTION.md](EXECUTION.md)** - Order execution, bracket orders
- **[TELEGRAM.md](TELEGRAM.md)** - Telegram bot & notifications

### **⚙️ Configuration:**
- **[CONFIG.md](CONFIG.md)** - Policy.yaml reference
- **[SCHEDULER_OZET.md](SCHEDULER_OZET.md)** - Scheduler summary (Turkish)

### **🧪 Development:**
- **[TESTING.md](TESTING.md)** - Testing strategy
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines

### **📋 Reference:**
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

## 🎯 **Documentation by Use Case**

### **"Sistemi ilk defa başlatıyorum"**
```
1. QUICKSTART.md (English)
   veya
   BASLATMA_ONEMLI.md (Turkish)

2. IP Whitelist ayarla (OKX)

3. python -m infrastructure.scheduler_runner
```

### **"Yeni özellik geliştiriyorum"**
```
1. DEVELOPMENT_TESTING.md ← İlk oku!
   → Direct mode: Quick test (5-10 dk)
   → Scheduler mode: Full test (30-60 dk)

2. TESTING.md
   → Unit tests, integration tests

3. CONTRIBUTING.md
   → PR process, code standards
```

### **"Production'a deploy ediyorum"**
```
1. SCHEDULER_PRODUCTION_READY.md
   → Production checklist
   → Monitoring setup

2. START_SCHEDULER.md
   → Operations guide
   → Troubleshooting

3. CONFIG.md
   → Production config tuning
```

### **"Sistem mimarisini anlamak istiyorum"**
```
1. ARCHITECTURE_FINAL.md
   → Clean Architecture layers
   → SOLID principles

2. AGENTS.md
   → Multi-agent system
   → Message protocol

3. SCHEDULER.md
   → Job architecture
```

---

## 📂 **Document Structure**

```
docs/
├── 🚀 Getting Started
│   ├── QUICKSTART.md                      (English quick start)
│   ├── BASLATMA_ONEMLI.md                 (Turkish quick start)
│   ├── SCHEDULER_CALISTIRMA_KILAVUZU.md   (Turkish full guide)
│   ├── SCHEDULER_OZET.md                  (Turkish summary)
│   └── START_SCHEDULER.md                 (Operations guide)
│
├── 🏗️ Architecture
│   ├── ARCHITECTURE_FINAL.md              (Main architecture)
│   ├── ARCHITECTURE.md                    (Overview)
│   ├── AGENTS.md                          (Multi-agent system)
│   ├── SCHEDULER.md                       (Job architecture)
│   └── ADR/                               (Architecture decisions)
│
├── 🔧 Development
│   ├── DEVELOPMENT_TESTING.md ★           (Dev workflow - MUST READ)
│   ├── TESTING.md                         (Testing strategy)
│   └── CONTRIBUTING.md                    (Contribution guide)
│
├── 🚀 Production
│   ├── SCHEDULER_PRODUCTION_READY.md      (Production readiness)
│   ├── EXECUTION.md                       (Execution details)
│   ├── TELEGRAM.md                        (Telegram integration)
│   └── CONFIG.md                          (Configuration reference)
│
└── 📋 Reference
    ├── CHANGELOG.md                       (Version history)
    ├── INDEX.md                           (This index)
    ├── README.md                          (This file)
    ├── snippets/                          (Code examples)
    └── diagrams/                          (Visual diagrams)
```

---

## 🔍 **Document Cross-Reference**

### **Related Documents:**

| Topic | Primary Doc | Related Docs |
|-------|-------------|--------------|
| **Quick Start** | QUICKSTART.md | BASLATMA_ONEMLI.md |
| **Scheduler** | SCHEDULER_CALISTIRMA_KILAVUZU.md | START_SCHEDULER.md, SCHEDULER_OZET.md |
| **Development** | DEVELOPMENT_TESTING.md | TESTING.md, CONTRIBUTING.md |
| **Architecture** | ARCHITECTURE_FINAL.md | AGENTS.md, SCHEDULER.md |
| **Production** | SCHEDULER_PRODUCTION_READY.md | START_SCHEDULER.md, CONFIG.md |

---

## 💡 **Tips for Reading**

1. **Start with your role:**
   - User → QUICKSTART.md
   - Developer → DEVELOPMENT_TESTING.md
   - Operator → START_SCHEDULER.md

2. **Follow the links:**
   - Each document has cross-references
   - Follow them for deeper understanding

3. **Use INDEX.md:**
   - Complete document index
   - Organized by category

---

**📖 For complete index, see [INDEX.md](INDEX.md)**

*Last Updated: 2025-10-09*
