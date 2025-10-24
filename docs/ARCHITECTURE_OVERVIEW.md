# AiBotBS Mimari Genel Bakış

> **Clean Architecture prensiplerine uygun, katmanlı sistem mimarisi**

## 🏗️ Clean Architecture Diyagramı

```
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │   Bootstrap │ │   Logging   │ │ Monitoring  │ │  Docker  │ │
│  │   Config    │ │   Logger    │ │ Prometheus  │ │ Compose  │ │
│  │   Runtime   │ │   Formatter │ │   Grafana   │ │   etc.   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                     APPLICATION LAYER                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │   Services  │ │     Jobs    │ │Orchestrator │ │  Utils   │ │
│  │   Risk      │ │  Trading    │ │   Trading   │ │  Helpers │ │
│  │  Portfolio  │ │   News      │ │   Signal    │ │   etc.   │ │
│  │    Trade    │ │  Trailing   │ │    Gate     │ │          │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      DOMAIN LAYER                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │   Models    │ │ Strategies  │ │   Events    │ │  Errors  │ │
│  │  Position   │ │   Single    │ │   Trade     │ │  Custom  │ │
│  │   Order     │ │   Scale     │ │  Position   │ │  Excep.  │ │
│  │   Signal    │ │   Flip      │ │   Risk      │ │          │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                      ADAPTERS LAYER                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │   Exchange  │ │    News     │ │  Telegram   │ │   LLM    │ │
│  │     OKX     │ │   APIs      │ │    Bot      │ │  OpenAI  │ │
│  │    CCXT     │ │  Scrapers   │ │  Notifier   │ │  Models  │ │
│  │    REST     │ │  Sentiment  │ │   Alerts    │ │  Cache   │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Veri Akışı (15 Dakika Döngüsü)

### 1. **Market Data Collection**
```
OKX Exchange → OHLCV Data → Multi-timeframe (1m, 15m, 1h) → Market Data Cache
```

### 2. **Analysis Pipeline**
```
Market Data → Technical Analysis → ML Prediction → News Analysis → Risk Assessment
```

### 3. **Decision Making**
```
Analysis Results → Composite Score → Signal Gate → Position State Manager → Trading Decision
```

### 4. **Execution Pipeline**
```
Trading Decision → Order Executor → Position Manager → TP/SL Attachment → Telegram Notification
```

## 📊 Job/Scheduler Akışı

### Zamanlanmış Görevler

| Job | Sıklık | Açıklama |
|-----|--------|----------|
| **risk_monitor** | 1 dakika | Risk kontrolü ve pozisyon izleme |
| **news_analysis** | 5 dakika | Haber toplama ve sentiment analizi |
| **trailing_stops** | 5 dakika | Trailing stop güncellemeleri |
| **trading_analysis** | 15 dakika | Ana trading analizi ve karar verme |
| **regime_analysis** | 1 saat | Piyasa rejimi analizi |
| **market_overview** | 15 dakika | Piyasa genel durumu |
| **telegram_summary** | 15 dakika | Telegram özet raporları |

### Job Execution Flow
```
Scheduler → Job Queue → Semaphore (Max 2) → Job Execution → Result Logging → Metrics Update
```

## 🎯 Execution Zinciri

### 1. **Order Execution**
```
Signal → Order Prevalidator → Exchange Adapter → Order Placement → Fill Confirmation
```

### 2. **Position Management**
```
Order Fill → Position State Update → TP/SL Calculation → Bracket Order Creation → Position Monitoring
```

### 3. **Trailing Stop Management**
```
Position Update → R-Multiple Calculation → Trailing Stop Update → Order Modification → State Persistence
```

## 🏛️ Katman Detayları

### Infrastructure Layer
**Amaç**: Sistem altyapısı ve dış bağımlılıklar

**Bileşenler**:
- **Bootstrap**: Konfigürasyon yükleme, environment setup
- **Logging**: Merkezi log yönetimi, formatter'lar
- **Monitoring**: Prometheus metrics, Grafana dashboards
- **Docker**: Container orchestration, service discovery

**Sorumluluklar**:
- Sistem başlatma ve kapatma
- Konfigürasyon yönetimi
- Log toplama ve formatlama
- Metrik toplama ve görselleştirme

### Application Layer
**Amaç**: İş mantığı ve use case'ler

**Bileşenler**:
- **Services**: Risk, Portfolio, Trade servisleri
- **Jobs**: Zamanlanmış görevler
- **Orchestrator**: Ana koordinatör
- **Utils**: Yardımcı fonksiyonlar

**Sorumluluklar**:
- İş mantığı implementasyonu
- Use case koordinasyonu
- Job scheduling ve execution
- Service orchestration

### Domain Layer
**Amaç**: Core business logic ve entities

**Bileşenler**:
- **Models**: Position, Order, Signal modelleri
- **Strategies**: Trading stratejileri
- **Events**: Domain event'leri
- **Errors**: Custom exception'lar

**Sorumluluklar**:
- Business rule'ları
- Domain logic
- Entity relationships
- Event definitions

### Adapters Layer
**Amaç**: Dış sistemlerle entegrasyon

**Bileşenler**:
- **Exchange**: OKX API entegrasyonu
- **News**: Haber API'leri ve sentiment
- **Telegram**: Bot ve notification
- **LLM**: OpenAI entegrasyonu

**Sorumluluklar**:
- External API communication
- Data transformation
- Protocol adaptation
- Error handling

## 🔄 Event System

### Event Types
- **TRADE_SIGNAL**: Trading sinyali oluştu
- **POSITION_UPDATE**: Pozisyon durumu değişti
- **RISK_ALERT**: Risk uyarısı
- **PORTFOLIO_UPDATE**: Portfolio güncellendi
- **SYSTEM_STATUS**: Sistem durumu değişti

### Event Flow
```
Event Source → Event Bus → Event Handlers → Action Execution → Result Logging
```

### Event Priorities
- **CRITICAL**: Sistem hataları
- **HIGH**: Risk uyarıları
- **MEDIUM**: Trading sinyalleri
- **LOW**: Pozisyon güncellemeleri
- **INFO**: Durum bilgileri

## 🎯 Strategy Pattern

### Strategy Types
1. **Technical Analysis**: RSI, MACD, Bollinger Bands
2. **Machine Learning**: Random Forest predictions
3. **News Sentiment**: Crypto news analysis
4. **Composite**: Multiple strategies combined

### Strategy Implementation
```python
# Strategy interface
class TradingStrategy:
    def analyze(self, data: MarketData) -> Signal
    def get_confidence(self) -> float
    def get_metadata(self) -> dict

# Composite strategy
composite = CompositeStrategy()
composite.add_strategy(ta_strategy, weight=0.4)
composite.add_strategy(ml_strategy, weight=0.25)
composite.add_strategy(news_strategy, weight=0.2)
composite.add_strategy(risk_strategy, weight=0.15)
```

## 🔧 SOLID Principles

### ✅ Single Responsibility Principle (SRP)
- Her sınıf tek bir sorumluluğa sahip
- `RiskMonitor` sadece risk yönetimi
- `PortfolioManager` sadece portfolio yönetimi
- `EventBus` sadece event processing

### ✅ Open/Closed Principle (OCP)
- Yeni event types eklenebilir
- Yeni strategies eklenebilir
- Yeni handlers eklenebilir
- Mevcut kod değiştirilmeden

### ✅ Liskov Substitution Principle (LSP)
- Interface'ler üzerinden çalışır
- Concrete implementations değiştirilebilir
- Polymorphic behavior

### ✅ Interface Segregation Principle (ISP)
- Küçük, odaklanmış interface'ler
- Client'lar sadece ihtiyaç duydukları method'ları implement eder

### ✅ Dependency Inversion Principle (DIP)
- High-level modüller low-level modüllere bağımlı değil
- Her ikisi de abstraction'lara bağımlı
- Dependency injection kullanılır

## 🚀 System Lifecycle

### 1. **Initialization Phase**
```python
# Bootstrap
load_env()
init_logging()
load_policy()

# Domain Layer
setup_strategies()
initialize_components()

# Infrastructure Layer
start_event_bus()
start_scheduler()
```

### 2. **Runtime Phase**
```python
# Main Loop
while running:
    await analyze_markets()
    await process_signals()
    await update_positions()
    await monitor_risk()
    await publish_events()
```

### 3. **Shutdown Phase**
```python
# Graceful Shutdown
stop_event_bus()
stop_scheduler()
close_positions()
cleanup_resources()
```

## 📊 Performance Considerations

### 1. **Caching Strategy**
- Market data cache (5 dakika TTL)
- News digest cache (120 dakika TTL)
- ML model cache (1 saat TTL)

### 2. **Concurrency**
- Semaphore limit: 2 concurrent jobs
- Async/await pattern
- Non-blocking I/O

### 3. **Memory Management**
- Lazy loading
- Garbage collection optimization
- Resource cleanup

### 4. **Database**
- SQLite for state persistence
- JSON files for configuration
- In-memory caching

## 🔍 Monitoring ve Observability

### 1. **Metrics**
- Prometheus metrics collection
- Custom business metrics
- System performance metrics

### 2. **Logging**
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Log rotation and retention

### 3. **Tracing**
- Request tracing
- Performance profiling
- Error tracking

### 4. **Alerting**
- Risk threshold alerts
- System health alerts
- Performance degradation alerts

## 📚 Sonraki Adımlar

1. [OPERATIONS_PLAYBOOK.md](OPERATIONS_PLAYBOOK.md) - Operasyon pratikleri
2. [METRICS_CHEATSHEET.md](METRICS_CHEATSHEET.md) - Metrik rehberi
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Sorun giderme
4. [POLICY_REFERENCE.md](POLICY_REFERENCE.md) - Konfigürasyon referansı

