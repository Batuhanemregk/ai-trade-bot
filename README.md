# 🤖 AI Trading Bot

> **Production-Grade Multi-Agent AI Cryptocurrency Trading System**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![OKX Exchange](https://img.shields.io/badge/exchange-OKX-green.svg)](https://www.okx.com/)
[![Telegram Bot](https://img.shields.io/badge/telegram-bot-blue.svg)](https://core.telegram.org/bots)

## 🎯 Overview

A sophisticated algorithmic trading bot that combines **Technical Analysis**, **Machine Learning predictions**, **News Sentiment Analysis**, and **Risk Management** into a unified scoring system for cryptocurrency futures trading on OKX.

### Key Highlights

- 🧠 **Multi-Agent Scoring**: TA (40%) + ML (25%) + News (20%) + Risk (15%)
- ⚡ **Real-Time Execution**: Sub-second order placement with OCO brackets
- 📱 **Full Telegram Control**: Interactive dashboard with live positions, PnL tracking
- 🛡️ **Enterprise Risk Management**: Circuit breaker, trailing stops, dynamic TP/SL
- 🔄 **24/7 Automated Trading**: APScheduler-based job system

## ✨ Features

### Trading Engine

- **Smart Order Execution**: Market/Limit orders with automatic TP/SL brackets
- **ATR-Based TP/SL**: Dynamic stop-loss and take-profit based on volatility
- **Trailing Stop**: R-multiple based trailing with configurable presets
- **Partial Take Profit**: Automatic position scaling at profit targets
- **Position Management**: Maximum age limits, exposure controls

### Signal Generation

- **Technical Analysis**: RSI, MACD, Bollinger Bands, ATR, SMA
- **ML Predictions**: XGBoost/LightGBM models for 25+ coin pairs
- **News Sentiment**: Real-time sentiment from CryptoCompare, CryptoPanic
- **Signal Gating**: Persistence filters, hysteresis, regime detection

### Risk Management

- **Circuit Breaker**: Auto-stop on consecutive losses or daily drawdown
- **Exposure Limits**: Per-position and portfolio-wide limits
- **Correlation Risk**: Tiered exposure based on market cap
- **Loss Streak Protection**: Progressive position reduction

### Telegram Interface

- 📊 **Live Dashboard**: Balance, positions, exposure, signals
- 💰 **PnL Tracking**: Daily, weekly, monthly breakdowns by coin
- ⚙️ **Settings Control**: Leverage, thresholds, exit strategies
- 🚨 **Emergency Controls**: Close all, circuit breaker activation

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OKX Account with API access
- Telegram Bot Token

### Installation

```bash
# Clone repository
git clone https://github.com/Batuhanemregk/ai-trade-bot.git
cd ai-trade-bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Create `.env` file:

```env
OKX_API_KEY=your_api_key
OKX_SECRET_KEY=your_secret_key
OKX_PASSPHRASE=your_passphrase
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### Running

```powershell
# Windows - Interactive Menu
.\run_live.ps1 -menu

# Direct start
python main.py
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Telegram Interface                        │
│         Dashboard • Settings • Positions • PnL • Alerts          │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                      Application Services                        │
│   Signal Gate • Position Manager • Risk Service • Notifier       │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌───────────────┬───────────────┬───────────────┬─────────────────┐
│   TA Agent    │   ML Agent    │  News Agent   │   Risk Agent    │
│  Indicators   │   XGBoost     │  Sentiment    │  Exposure       │
│  Pattern Det. │   LightGBM    │  Headlines    │  Correlation    │
└───────────────┴───────────────┴───────────────┴─────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                        Execution Layer                           │
│      OKX CCXT Adapter • Order Quantization • Prevalidation       │
└─────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────┐
│                         Infrastructure                           │
│    APScheduler • State Persistence • Logging • Monitoring        │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
ai-trade-bot/
├── adapters/               # External integrations
│   ├── exchange_okx_ccxt.py    # OKX trading adapter
│   └── telegram/               # Telegram bot & views
├── application/            # Business logic
│   ├── signal_gate.py          # Signal filtering
│   ├── position_state_manager.py
│   └── risk_service.py
├── domain/                 # Core entities
│   ├── agents/                 # TA, ML, News, Risk agents
│   └── scoring/                # Score calculation
├── execution/              # Order execution
│   ├── quantize.py             # Size/price quantization
│   └── prevalidation.py        # Order validation
├── infrastructure/         # Framework & utilities
│   ├── runtime.py              # Trade execution engine
│   └── scheduler.py            # Job scheduling
├── configs/
│   └── policy.yaml             # Trading configuration
└── main.py                 # Application entry point
```

## ⚙️ Configuration

Key settings in `configs/policy.yaml`:

```yaml
trading:
  risk:
    leverage:
      default: 7
    exposure:
      max_single: 15 # Max 15% per position
      max_total: 60 # Max 60% total exposure

  scoring:
    weights:
      ta: 0.40 # Technical Analysis
      ml: 0.25 # Machine Learning
      news: 0.20 # News Sentiment
      risk: 0.15 # Risk Assessment

    thresholds:
      enter_long: 60 # Long entry threshold
      exit_long: 50 # Long exit threshold
      enter_short: 40 # Short entry threshold
      exit_short: 50 # Short exit threshold

  exit_strategies:
    trailing:
      enabled: true
      activation_r: 0.5 # Activate at 0.5R profit
    partial_tp:
      enabled: true
    dynamic_tpsl:
      sl_atr_multiplier: 1.0
      tp_atr_multiplier: 4.0
```

## 🛡️ Safety Features

- **Dry-Run Mode**: Test without live trading
- **Circuit Breaker**: Auto-stop on 25% daily loss or 3 consecutive losses
- **Prevalidation**: All orders validated before submission
- **API Key Redaction**: Sensitive data masked in logs
- **Position Limits**: Maximum positions and exposure limits
- **Telegram Kill Switch**: Emergency stop commands

## 📊 Supported Coins

Currently configured for 17 trading pairs including:

- **Large Cap**: BTC, ETH, SOL
- **DeFi**: UNI, AVAX, ATOM
- **Layer 2**: OP, ARB
- **Others**: DOGE, XRP, NEAR, RENDER, SEI, and more

ML predictions available for 26+ coins.

## 📝 License

This project is for educational and personal use. Use at your own risk.

## ⚠️ Disclaimer

**Trading cryptocurrency involves significant risk.** This bot is provided as-is with no guarantees. Always:

- Test thoroughly in dry-run mode
- Start with small positions
- Never risk more than you can afford to lose
- Monitor positions actively

---

**Built with** ❤️ **using Python, CCXT, APScheduler, and Telegram**
