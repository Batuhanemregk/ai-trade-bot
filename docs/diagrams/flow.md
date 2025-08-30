# 🔄 System Flow Diagrams

> **ASCII diagrams for system data and decision flows**

## 📊 Scoring Flow (TA/ML/News → Score)

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Technical     │    │   Machine       │    │     News        │
│   Analysis      │    │   Learning      │    │   Sentiment     │
│                 │    │                 │    │                 │
│ • RSI, MACD     │    │ • Price         │    │ • Headlines     │
│ • Bollinger     │    │   patterns      │    │ • Sentiment     │
│ • ATR, Volume   │    │ • Volatility    │    │ • Impact        │
│ • Support/      │    │ • Correlation   │    │ • Volume        │
│   Resistance    │    │ • Momentum      │    │ • Timeliness    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   TA Score      │    │   ML Score      │    │   News Score    │
│   (0.0 - 1.0)   │    │   (0.0 - 1.0)   │    │   (0.0 - 1.0)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   Composite Signal      │
                    │                         │
                    │ • Weighted average     │
                    │ • Confidence scoring   │
                    │ • Signal strength      │
                    │ • Direction (LONG/     │
                    │   SHORT/NEUTRAL)       │
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Final Score           │
                    │   (0.0 - 1.0)          │
                    └─────────────────────────┘
```

## ⚠️ Risk Assessment Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Position      │    │   Portfolio     │    │   Market        │
│   Risk          │    │   Exposure      │    │   Conditions    │
│                 │    │                 │    │                 │
│ • Size limits   │    │ • Total         │    │ • Volatility    │
│ • Stop loss     │    │   exposure      │    │ • Liquidity     │
│ • Leverage      │    │ • Correlation   │    │ • Spreads       │
│ • Margin        │    │ • Diversification│   │ • News impact   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Position      │    │   Portfolio     │    │   Market        │
│   Risk Score    │    │   Risk Score    │    │   Risk Score    │
│   (0.0 - 1.0)   │    │   (0.0 - 1.0)   │    │   (0.0 - 1.0)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   Composite Risk        │
                    │   Assessment            │
                    │                         │
                    │ • Risk score            │
                    │ • Risk level            │
                    │ • Risk factors          │
                    │ • Recommendations       │
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Risk Decision         │
                    │                         │
                    │ • ALLOW: Execute        │
                    │ • REDUCE: Smaller size  │
                    │ • BLOCK: No trade      │
                    │ • DELAY: Wait for      │
                    │   better conditions     │
                    └─────────────────────────┘
```

## 🚀 Execution Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Signal        │    │   Risk          │    │   Order         │
│   Generation    │    │   Validation    │    │   Preparation   │
│                 │    │                 │    │                 │
│ • Score >       │    │ • Position      │    │ • Symbol       │
│   threshold     │    │   limits        │    │   validation    │
│ • Direction     │    │ • Portfolio     │    │ • Size          │
│   confirmed     │    │   exposure      │    │   calculation   │
│ • Timing        │    │ • Market        │    │ • Price         │
│   optimal       │    │   conditions    │    │   calculation   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Signal        │    │   Risk          │    │   Order         │
│   Validated     │    │   Approved      │    │   Ready         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   Order Execution       │
                    │                         │
                    │ • Entry order           │
                    │ • Price quantization    │
                    │ • Size validation       │
                    │ • Exchange submission   │
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Order Monitoring      │
                    │                         │
                    │ • Fill confirmation     │
                    │ • Partial fills         │
                    │ • Timeout handling      │
                    │ • Error recovery        │
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Bracket Orders        │
                    │                         │
                    │ • Take Profit           │
                    │ • Stop Loss             │
                    │ • Trailing Stop         │
                    │ • OCO emulation         │
                    └─────────────────────────┘
```

## 🔄 Complete Trading Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Market Data                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Price     │  │   Volume    │  │   News      │            │
│  │   Data      │  │   Data      │  │   Feed      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Scoring Engine                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Technical   │  │ Machine     │  │ News        │            │
│  │ Analysis    │  │ Learning    │  │ Sentiment   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                │                               │
│                                ▼                               │
│                    ┌─────────────────┐                        │
│                    │ Composite       │                        │
│                    │ Signal          │                        │
│                    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Risk Engine                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Position    │  │ Portfolio   │  │ Market      │            │
│  │ Risk        │  │ Risk        │  │ Risk        │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                │                               │
│                                ▼                               │
│                    ┌─────────────────┐                        │
│                    │ Risk Decision   │                        │
│                    │ (ALLOW/REDUCE/  │                        │
│                    │  BLOCK/DELAY)   │                        │
│                    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Execution Engine                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Order       │  │ Order       │  │ Order       │            │
│  │ Preparation │  │ Execution   │  │ Monitoring  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                │                               │
│                                ▼                               │
│                    ┌─────────────────┐                        │
│                    │ Bracket Orders  │                        │
│                    │ (TP/SL)         │                        │
│                    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Portfolio Management                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Position    │  │ PnL         │  │ Risk        │            │
│  │ Tracking    │  │ Calculation │  │ Monitoring  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                │                               │
│                                ▼                               │
│                    ┌─────────────────┐                        │
│                    │ Portfolio       │                        │
│                    │ Status          │                        │
│                    └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Agent Runtime Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Orchestrator                      │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Scoring   │  │    Risk     │  │ Execution   │            │
│  │   Agent     │  │    Agent    │  │   Agent     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │  Portfolio  │  │  Scheduler  │  │ Telegram    │            │
│  │   Agent     │  │    Agent    │  │    Bot      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Execution Cycle                          │
│                                                                 │
│  1. Market Data Collection                                     │
│  2. Signal Generation (Scoring Agent)                          │
│  3. Risk Assessment (Risk Agent)                               │
│  4. Order Execution (Execution Agent)                          │
│  5. Position Management (Portfolio Agent)                      │
│  6. Scheduled Jobs (Scheduler Agent)                           │
│  7. User Notifications (Telegram Bot)                          │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                 Dry Run Mode                            │    │
│  │  • No real orders                                       │    │
│  │  • Full flow simulation                                 │    │
│  │  • Risk validation                                      │    │
│  │  • Performance metrics                                  │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Error Handling Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Error         │    │   Error         │    │   Error         │
│   Detection     │    │   Classification │    │   Recovery      │
│                 │    │                 │    │                 │
│ • Exception     │    │ • Critical      │    │ • Retry logic   │
│   caught        │    │ • Warning       │    │ • Fallback      │
│ • Log error     │    │ • Info          │    │ • Circuit       │
│ • Capture       │    │ • Debug         │    │   breaker       │
│   context       │    │ • Fatal         │    │ • Graceful      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Error         │    │   Error         │    │   Error         │
│   Logged        │    │   Categorized   │    │   Handled       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   Error Response        │
                    │                         │
                    │ • User notification     │
                    │ • System alert          │
                    │ • Metric recording      │
                    │ • Health check update   │
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   System State          │
                    │                         │
                    │ • Continue normal       │
                    │   operation             │
                    │ • Degraded mode         │
                    │ • Emergency shutdown    │
                    └─────────────────────────┘
```

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Sources                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   OKX       │  │   News      │  │   OpenAI    │            │
│  │   Exchange  │  │   APIs      │  │   API       │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Infrastructure Layer                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Exchange  │  │   News      │  │   LLM       │            │
│  │   Adapters  │  │   Clients   │  │   Clients   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Scoring   │  │   Risk      │  │   Trade     │            │
│  │   Service   │  │   Service   │  │   Service   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Domain Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Entities  │  │   Value     │  │   Domain    │            │
│  │             │  │   Objects   │  │   Services  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Interface Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   CLI       │  │   Telegram  │  │   Scheduler │            │
│  │   Commands  │  │     Bot     │  │   Jobs      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

**Next**: See [docs/snippets/telegram_examples.md](telegram_examples.md) for Telegram command examples, or [docs/snippets/cli_examples.md](cli_examples.md) for CLI usage examples.
