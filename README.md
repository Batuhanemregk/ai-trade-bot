# 🤖 AiBotBS Runtime Agent System

> **Production-grade Runtime Agent System with Clean Architecture & SOLID Principles**

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-org/aibotbs)
[![Test Coverage](https://img.shields.io/badge/coverage-65%25-orange)](https://github.com/your-org/aibotbs)
[![Code Quality](https://img.shields.io/badge/ruff-passing-brightgreen)](https://github.com/your-org/aibotbs)
[![Type Check](https://img.shields.io/badge/mypy-passing-brightgreen)](https://github.com/your-org/aibotbs)

## 🚀 Quick Start

```bash
# Clone and setup
git clone <your-repo>
cd AiBotBS
pip install -r requirements.txt

# Create .env (OKX, Telegram, OpenAI keys)
cp .env.example .env  # then edit values

# Install dependencies
pip install -r requirements.txt

# Start professional scheduler (live/dry mode via policy.yaml)
python -m infrastructure.scheduler_runner
```

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

- **[🏗️ Architecture](docs/ARCHITECTURE.md)** - Clean Architecture layers, module map, data flow
- **[🤖 Agents](docs/AGENTS.md)** - Agent roles, graphs, dry-run lifecycle, troubleshooting
- **[⚡ Execution](docs/EXECUTION.md)** - Quantization, prevalidation, bracket orders, adapters
- **[📱 Telegram](docs/TELEGRAM.md)** - Bot setup, commands, examples, offline mocks
- **[⏰ Scheduler](docs/SCHEDULER.md)** - Job API, cron/interval jobs, management
- **[⚙️ Configuration](docs/CONFIG.md)** - Policy fields, weights, limits, examples
- **[🧪 Testing](docs/TESTING.md)** - Core/glue tests, smoke, markers, offline rules
- **[🤝 Contributing](docs/CONTRIBUTING.md)** - Development setup, standards, PR process

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

The system uses `policy.yaml` for configuration:

```yaml
risk:
  max_daily_loss: 0.05
  max_position_size: 0.1
  stop_loss_atr_multiplier: 2.0

scoring:
  min_score: 0.5
  news_weight: 0.3
  ta_weight: 0.4
```

See [CONFIG.md](docs/CONFIG.md) for complete configuration options.

## 🚨 Safety Features

- **Dry-Run Mode**: Test strategies without live trading
- **Risk Limits**: Configurable position sizing and loss limits
- **Prevalidation**: Order validation before execution
- **Offline Mocks**: Deterministic testing environment
- **Environment Isolation**: Safe configuration management

## 📈 Status

- **Current Version**: 1.0.0
- **Architecture**: Clean Architecture + SOLID Principles
- **Testing**: 26 tests (Core + Glue)
- **Coverage**: 65%+ (target)
- **Quality**: Ruff + MyPy compliant

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines, code standards, and PR process.

## 📄 License

[Your License] - see LICENSE file for details.

---

**⚠️ Warning**: This is a production trading system. Always test in dry-run mode first and ensure proper risk management configuration.
