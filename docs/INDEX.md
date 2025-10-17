# 📚 **AiBotBS Documentation Index**

## 🚀 **Getting Started** (Başlangıç)

### **Hızlı Başlangıç:**
1. **[⚡ QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide (English)
2. **[🇹🇷 BASLATMA_ONEMLI.md](BASLATMA_ONEMLI.md)** - Kritik başlatma notları (Turkish)
3. **[📊 SCHEDULER_CALISTIRMA_KILAVUZU.md](SCHEDULER_CALISTIRMA_KILAVUZU.md)** - Kapsamlı scheduler rehberi (Turkish)

### **Quick Reference:**
- **[📖 SCHEDULER_OZET.md](SCHEDULER_OZET.md)** - Scheduler özet bilgiler (Turkish)
- **[📋 START_SCHEDULER.md](START_SCHEDULER.md)** - Scheduler başlatma detayları
- **[✅ SCHEDULER_PRODUCTION_READY.md](SCHEDULER_PRODUCTION_READY.md)** - Production readiness report

---

## 🏗️ **Architecture & Design** (Mimari)

### **System Architecture:**
1. **[🏛️ ARCHITECTURE_FINAL.md](ARCHITECTURE_FINAL.md)** - Clean Architecture implementation
2. **[📐 ARCHITECTURE.md](ARCHITECTURE.md)** - System overview
3. **[🤖 AGENTS.md](AGENTS.md)** - Multi-agent system design
4. **[⏰ SCHEDULER.md](SCHEDULER.md)** - Job scheduling architecture

### **Design Decisions:**
- **[📋 ADR/0001-clean-architecture.md](ADR/0001-clean-architecture.md)** - Architecture Decision Record

---

## 🔧 **Development** (Geliştirme)

### **Development Workflow:**
1. **[🔧 DEVELOPMENT_TESTING.md](DEVELOPMENT_TESTING.md)** - **ÖNEMLİ!** Development & testing workflow
   - Direct mode vs Scheduler mode
   - When to use which
   - Test strategies
   - Debug techniques

2. **[🧪 TESTING.md](TESTING.md)** - Testing strategy
   - Unit tests, integration tests
   - Smoke tests, markers
   - Test coverage

3. **[🤝 CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
   - PR process
   - Code standards
   - Review checklist

---

## ⚙️ **Configuration** (Konfigürasyon)

1. **[⚙️ CONFIG.md](CONFIG.md)** - Policy.yaml reference
   - Risk settings
   - Scoring weights
   - Schedule configuration
   - Agent settings

---

## 🚀 **Operations** (Operasyon)

### **Execution:**
1. **[⚡ EXECUTION.md](EXECUTION.md)** - Order execution details
   - Bracket orders
   - Quantization
   - Pre-validation
   - Adapters

### **Communication:**
2. **[📱 TELEGRAM.md](TELEGRAM.md)** - Telegram bot guide
   - Commands
   - Notifications
   - Analysis cards
   - Inline keyboards

---

## 📝 **Reference** (Referans)

### **Changelog:**
- **[📋 CHANGELOG.md](CHANGELOG.md)** - Version history and updates

### **Examples:**
- **[💻 snippets/cli_examples.md](snippets/cli_examples.md)** - CLI usage examples
- **[📱 snippets/telegram_examples.md](snippets/telegram_examples.md)** - Telegram examples

### **Diagrams:**
- **[📊 diagrams/flow.md](diagrams/flow.md)** - System flow diagrams

---

## 🎓 **Recommended Reading Order**

### **For New Users:**
```
1. README.md (root) - Project overview
2. QUICKSTART.md - Get started in 5 minutes
3. BASLATMA_ONEMLI.md - Critical startup notes (Turkish)
4. SCHEDULER_CALISTIRMA_KILAVUZU.md - Full guide (Turkish)
```

### **For Developers:**
```
1. ARCHITECTURE_FINAL.md - Understand system design
2. DEVELOPMENT_TESTING.md - Learn development workflow ★
3. CONTRIBUTING.md - Contribution guidelines
4. TESTING.md - Testing strategies
```

### **For Operators:**
```
1. START_SCHEDULER.md - Operations guide
2. SCHEDULER_PRODUCTION_READY.md - Production checklist
3. CONFIG.md - Configuration reference
4. TELEGRAM.md - Monitoring setup
```

---

## 🔑 **Key Documents Summary**

### **🌟 MUST READ:**

1. **[DEVELOPMENT_TESTING.md](DEVELOPMENT_TESTING.md)** ⭐⭐⭐
   - **EN ÖNEMLİ!**
   - Direct mode vs Scheduler mode
   - When to use which
   - Development workflow

2. **[QUICKSTART.md](QUICKSTART.md)** ⭐⭐
   - 5-minute setup
   - Quick start commands

3. **[SCHEDULER_CALISTIRMA_KILAVUZU.md](SCHEDULER_CALISTIRMA_KILAVUZU.md)** ⭐⭐
   - Complete Turkish guide
   - Step-by-step instructions

### **Important:**

4. **[ARCHITECTURE_FINAL.md](ARCHITECTURE_FINAL.md)** ⭐
   - System design
   - Clean Architecture

5. **[CONFIG.md](CONFIG.md)** ⭐
   - Configuration reference

6. **[SCHEDULER_PRODUCTION_READY.md](SCHEDULER_PRODUCTION_READY.md)** ⭐
   - Production deployment

---

## 📂 **Document Categories**

```
docs/
├── Getting Started (Başlangıç)
│   ├── QUICKSTART.md
│   ├── BASLATMA_ONEMLI.md
│   ├── SCHEDULER_CALISTIRMA_KILAVUZU.md
│   ├── SCHEDULER_OZET.md
│   └── START_SCHEDULER.md
│
├── Architecture (Mimari)
│   ├── ARCHITECTURE_FINAL.md
│   ├── ARCHITECTURE.md
│   ├── AGENTS.md
│   ├── SCHEDULER.md
│   └── ADR/
│
├── Development (Geliştirme)
│   ├── DEVELOPMENT_TESTING.md ★
│   ├── TESTING.md
│   └── CONTRIBUTING.md
│
├── Operations (Operasyon)
│   ├── SCHEDULER_PRODUCTION_READY.md
│   ├── EXECUTION.md
│   ├── TELEGRAM.md
│   └── CONFIG.md
│
└── Reference (Referans)
    ├── CHANGELOG.md
    ├── README.md
    └── snippets/
```

---

## 🎯 **Quick Links by Use Case**

### **"Sistemi ilk defa başlatıyorum"**
→ [QUICKSTART.md](QUICKSTART.md) veya [BASLATMA_ONEMLI.md](BASLATMA_ONEMLI.md)

### **"Yeni feature geliştiriyorum"**
→ [DEVELOPMENT_TESTING.md](DEVELOPMENT_TESTING.md) ⭐

### **"Test nasıl yapılır?"**
→ [DEVELOPMENT_TESTING.md](DEVELOPMENT_TESTING.md) → Testing section

### **"Production'a nasıl deploy edilir?"**
→ [SCHEDULER_PRODUCTION_READY.md](SCHEDULER_PRODUCTION_READY.md)

### **"Scheduler nasıl çalışır?"**
→ [SCHEDULER_CALISTIRMA_KILAVUZU.md](SCHEDULER_CALISTIRMA_KILAVUZU.md)

### **"Config nasıl değiştirilir?"**
→ [CONFIG.md](CONFIG.md)

### **"Telegram bot nasıl kullanılır?"**
→ [TELEGRAM.md](TELEGRAM.md)

### **"Mimari nasıl organize edilmiş?"**
→ [ARCHITECTURE_FINAL.md](ARCHITECTURE_FINAL.md)

---

## 📖 **Documentation Standards**

All documentation follows:
- ✅ Clear structure with headers
- ✅ Code examples with syntax highlighting
- ✅ Step-by-step instructions
- ✅ Troubleshooting sections
- ✅ Cross-references to related docs
- ✅ Both English and Turkish (where applicable)

---

**Last Updated:** 2025-10-09  
**Version:** 1.0.0

