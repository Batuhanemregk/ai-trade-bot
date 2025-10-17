# 🤖 AiBotBS Runtime Agent System

> **Production-grade AI Trading Bot with Scheduler Architecture & SOLID Principles**

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-org/aibotbs)
[![Test Coverage](https://img.shields.io/badge/coverage-65%25-orange)](https://github.com/your-org/aibotbs)
[![Code Quality](https://img.shields.io/badge/ruff-passing-brightgreen)](https://github.com/your-org/aibotbs)
[![Type Check](https://img.shields.io/badge/mypy-passing-brightgreen)](https://github.com/your-org/aibotbs)

## 🚀 Quick Start

```bash
# Clone and setup
git clone <your-repo>
cd ai-trade-bot
pip install -r requirements.txt

# Create .env (OKX, Telegram, OpenAI keys)
cp .env.example .env  # then edit values

# Test scheduler
python scripts/test_scheduler.py

# Configure OKX IP whitelist (IMPORTANT!)
# https://www.okx.com → API Management → Add your IP

# Start production scheduler
python -m infrastructure.scheduler_runner
```

**📖 Quick Guide:** See [docs/QUICKSTART.md](docs/QUICKSTART.md) for 5-minute setup  
**📚 Scheduler Guide:** See [docs/SCHEDULER_CALISTIRMA_KILAVUZU.md](docs/SCHEDULER_CALISTIRMA_KILAVUZU.md) (Turkish)  
**🔧 Development:** See [docs/DEVELOPMENT_TESTING.md](docs/DEVELOPMENT_TESTING.md) for dev workflow  
**🚀 Start & Monitoring:** See [docs/START_AND_MONITORING.md](docs/START_AND_MONITORING.md) for scripts & monitoring setup  
**📊 Enhanced Logging:** See [docs/ENHANCED_LOGGING.md](docs/ENHANCED_LOGGING.md) for professional logging system (v2.0)

## ✨ Features

- **🧠 Multi-Source Scoring**: Technical Analysis, ML Models, LLM-backed News Sentiment, Risk Assessment
- **⚡ Real-time Execution**: OKX Exchange integration via CCXT + REST APIs
- **🤖 Agent Runtime**: Configurable agent graphs with dry-run safety
- **📱 Telegram Notifications + Bot**: Trade/alert cards and command interface with inline keyboards
- **⏰ Job Scheduler**: APScheduler-based cron jobs (15m trading, 5m trailing, 5m news, 1h regime, 1m risk)
- **🔒 Risk Management**: Position sizing, stop-loss, take-profit automation
- **📊 Portfolio Tracking**: Real-time PnL, exposure, correlation analysis
- **🧪 Offline Testing**: Deterministic mocks for development

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   Agent Runtime │    │   Scheduler     │
│   Commands      │    │   Graph Engine  │    │   Job Manager   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │    │     Domain      │    │   Execution     │
│   Services      │    │   Entities      │    │   Adapters      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Scoring     │    │   Risk Engine   │    │   OKX CCXT     │
│   TA/ML/News    │    │   Validation    │    │   + REST       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📚 Documentation

### **Getting Started:**
- **[⚡ Quick Start](docs/QUICKSTART.md)** - 5-minute setup guide
- **[🇹🇷 Türkçe Başlangıç](docs/BASLATMA_ONEMLI.md)** - Hızlı başlatma (Turkish)
- **[📊 Scheduler Guide](docs/SCHEDULER_CALISTIRMA_KILAVUZU.md)** - Complete scheduler guide (Turkish)

### **Architecture & Design:**
- **[🏗️ Architecture](docs/ARCHITECTURE_FINAL.md)** - Clean Architecture layers, SOLID principles
- **[🤖 Agents](docs/AGENTS.md)** - Multi-agent system, workflows, message protocol
- **[⏰ Scheduler](docs/SCHEDULER.md)** - Job architecture, scheduling patterns

### **Development:**
- **[🔧 Development & Testing](docs/DEVELOPMENT_TESTING.md)** - Dev workflow, when to use which mode
- **[🧪 Testing Strategy](docs/TESTING.md)** - Test types, markers, best practices
- **[🤝 Contributing](docs/CONTRIBUTING.md)** - PR process, code standards

### **Operations:**
- **[⚡ Execution](docs/EXECUTION.md)** - Order execution, bracket orders, quantization
- **[📱 Telegram](docs/TELEGRAM.md)** - Bot commands, notifications, cards
- **[⚙️ Configuration](docs/CONFIG.md)** - Policy.yaml reference, risk settings

### **Production:**
- **[✅ Production Readiness](docs/SCHEDULER_PRODUCTION_READY.md)** - Deployment checklist, monitoring
- **[📖 Scheduler Operations](docs/START_SCHEDULER.md)** - Operations guide, troubleshooting

## 🛠️ Development

```bash
# Install development dependencies
pip install -r requirements_testing.txt

# Run tests with markers
pytest -m "core"      # Core functionality tests
pytest -m "glue"      # Integration tests
pytest --cov          # Coverage report

# Code quality
ruff check .          # Linting
mypy .                # Type checking
black .               # Code formatting
```

## 🔧 Configuration

The system uses `configs/policy.yaml` for all configuration:

```yaml
exchange:
  mode: "dry-run"  # or "live"
  
trading:
  risk:
    max_position_size: 0.1
    max_total_risk: 0.6
    stop_loss_pct: 0.02
  
  scoring:
    ta_weight: 0.4
    ml_weight: 0.25
    news_weight: 0.2
    risk_weight: 0.15
```

See [docs/CONFIG.md](docs/CONFIG.md) for complete configuration reference.

## 🚨 Safety Features

- **Dry-Run Mode**: Test strategies without live trading
- **Circuit Breaker**: Auto emergency stop on 25% daily loss, 3 consecutive losses
- **Risk Limits**: Configurable position sizing and loss limits
- **Config Validation**: JSON Schema + Pydantic validation
- **Log Redaction**: Automatic API key/secret masking
- **Decision Logging**: Full trade replay capability
- **Prevalidation**: Order validation before execution
- **Telegram Controls**: /stop, /pause, /resume commands

## 📈 Status

- **Current Version**: 1.0.0
- **Architecture**: Clean Architecture + SOLID Principles
- **Scheduler**: Production Ready ✅
- **Security**: Log Redaction, Circuit Breaker ✅
- **Config Validation**: JSON Schema + Pydantic ✅
- **Decision Logging**: Structured JSONL ✅
- **Testing**: 26+ tests (Core + Integration)
- **Coverage**: 65%+ (target: 80%)
- **Quality**: Ruff + MyPy compliant
- **Jobs**: 7 automated jobs (trading, trailing, news, regime, risk, overview, telegram)

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines, code standards, and PR process.

## 📄 License

[Your License] - see LICENSE file for details.

---

**⚠️ Warning**: This is a production trading system. Always test in dry-run mode first and ensure proper risk management configuration.
