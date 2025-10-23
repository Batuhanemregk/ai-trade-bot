# AiBotBS Kapsamlı Test Planı

**Tarih:** 2025-10-16  
**Versiyon:** 1.0  
**Durum:** Test Hazırlığı ✅

## 🎯 Test Hedefleri

Bu kapsamlı test planı, AiBotBS trading sisteminin tüm bileşenlerini, entegrasyonlarını ve edge case'lerini kapsamlı şekilde test etmeyi amaçlar:

1. **Sistem Bileşenleri** - Tüm servislerin doğru çalışması
2. **Entegrasyonlar** - External API'ler ve veri kaynakları
3. **Edge Cases** - Anormal durumlar ve hata senaryoları
4. **Performance** - Yük altında sistem davranışı
5. **Data Integrity** - Veri tutarlılığı ve senkronizasyon
6. **Security** - Güvenlik açıkları ve API key yönetimi

## 🏗️ Sistem Bileşenleri Analizi

### **Core Services**
- ✅ **TradingAnalysisJob** - Ana analiz job'ı (15m)
- ✅ **RiskMonitorJob** - Risk izleme (1m)
- ✅ **Trailing5mJob** - Stop-loss yönetimi (5m)
- ✅ **NewsIncremental5mJob** - Haber güncellemeleri (5m)
- ✅ **TelegramSummary15mJob** - Telegram özetleri (15m)
- ✅ **Regime1hJob** - Market rejim analizi (1h)
- ✅ **MarketOverviewJob** - Piyasa genel bakış

### **Scoring Services**
- ✅ **TAScorer** - Teknik analiz skorlama
- ✅ **MLScorer** - Makine öğrenmesi skorlama
- ✅ **NewsScorer** - Haber sentiment skorlama
- ✅ **RiskService** - Risk değerlendirme

### **External Integrations**
- ✅ **OKX Exchange** - CCXT + REST API
- ✅ **CryptoCompare News** - Haber API'si
- ✅ **OpenAI GPT** - LLM analizi
- ✅ **Telegram Bot** - Bildirimler
- ✅ **Prometheus** - Metrik toplama
- ✅ **Grafana** - Dashboard

### **Data Sources**
- ✅ **OHLCV Data** - 1m, 5m, 15m, 1h timeframes
- ✅ **News Data** - CryptoCompare API
- ✅ **Market Data** - OKX ticker, orderbook
- ✅ **ML Models** - Random Forest (rf_v1.pkl)

## 🧪 Test Kategorileri

### **1. Unit Tests (Bileşen Testleri)**

#### **1.1 Scoring Services**
```bash
# TA Scorer Tests
python -m pytest tests/test_ta_scorer.py -v
- RSI hesaplama doğruluğu
- MACD sinyal üretimi
- Bollinger Bands breakout tespiti
- ATR volatilite hesaplama
- Edge case: Yetersiz veri
- Edge case: NaN değerler

# ML Scorer Tests  
python -m pytest tests/test_ml_scorer.py -v
- Model yükleme ve çalıştırma
- Feature engineering doğruluğu
- Prediction confidence hesaplama
- Edge case: Model dosyası yok
- Edge case: Corrupt model file

# News Scorer Tests
python -m pytest tests/test_news_scorer.py -v
- Sentiment analizi doğruluğu
- Keyword matching
- Confidence scoring
- Edge case: Boş haber listesi
- Edge case: API timeout

# Risk Service Tests
python -m pytest tests/test_risk_service.py -v
- Volatility risk hesaplama
- Liquidity risk assessment
- Correlation risk analysis
- Position sizing logic
- Edge case: Market crash simulation
```

#### **1.2 Data Services**
```bash
# Market Data Service Tests
python -m pytest tests/test_market_data_service.py -v
- OHLCV data fetching
- Cache functionality
- Data validation
- Edge case: Network timeout
- Edge case: Invalid symbol

# News Service Tests
python -m pytest tests/test_news_service.py -v
- News fetching from CryptoCompare
- LLM analysis integration
- Symbol alias mapping
- Edge case: API rate limiting
- Edge case: Empty response

# Log Services Tests
python -m pytest tests/test_log_services.py -v
- LogDedupService functionality
- LogFormatter line/block modes
- AnalysisSummaryLogger integration
- Edge case: High frequency logging
```

### **2. Integration Tests (Entegrasyon Testleri)**

#### **2.1 Exchange Integration**
```bash
# OKX CCXT Adapter Tests
python -m pytest tests/test_okx_ccxt_integration.py -v
- Connection establishment
- OHLCV data fetching
- Order placement (testnet)
- Balance retrieval
- Edge case: API key invalid
- Edge case: Network disconnection
- Edge case: Rate limiting

# OKX REST Adapter Tests
python -m pytest tests/test_okx_rest_integration.py -v
- REST API authentication
- Advanced order types
- Position management
- Edge case: Authentication failure
- Edge case: Insufficient balance
```

#### **2.2 External API Integration**
```bash
# News API Integration Tests
python -m pytest tests/test_news_api_integration.py -v
- CryptoCompare API connectivity
- News data parsing
- Rate limiting handling
- Edge case: API downtime
- Edge case: Malformed responses

# OpenAI Integration Tests
python -m pytest tests/test_openai_integration.py -v
- GPT API connectivity
- Sentiment analysis accuracy
- Token usage tracking
- Edge case: API quota exceeded
- Edge case: Invalid API key

# Telegram Integration Tests
python -m pytest tests/test_telegram_integration.py -v
- Bot message sending
- Queue management
- Retry mechanism
- Edge case: Network issues
- Edge case: Invalid chat ID
```

### **3. Job Execution Tests (Job Çalıştırma Testleri)**

#### **3.1 Scheduler Tests**
```bash
# Scheduler Functionality Tests
python -m pytest tests/test_scheduler.py -v
- Job scheduling accuracy
- Cron expression parsing
- Job execution timing
- Edge case: System clock changes
- Edge case: Job execution timeout

# Watchdog Tests
python -m pytest tests/test_watchdog.py -v
- Missed run detection
- Catch-up execution
- Job history tracking
- Edge case: Multiple missed runs
- Edge case: Job failure cascade
```

#### **3.2 Job-Specific Tests**
```bash
# Trading Analysis Job Tests
python -m pytest tests/test_trading_analysis_job.py -v
- Multi-symbol processing
- Bar idempotency
- Signal generation
- Edge case: Symbol delisting
- Edge case: Data corruption

# Risk Monitor Job Tests
python -m pytest tests/test_risk_monitor_job.py -v
- Risk threshold monitoring
- Alert generation
- Position monitoring
- Edge case: Extreme market volatility
- Edge case: Risk calculation errors

# News Incremental Job Tests
python -m pytest tests/test_news_incremental_job.py -v
- Incremental news updates
- Symbol-specific filtering
- LLM analysis triggering
- Edge case: News API failures
- Edge case: LLM analysis timeout
```

### **4. End-to-End Tests (Bütünsel Testler)**

#### **4.1 Complete Trading Cycle**
```bash
# Full Trading Cycle Test
python -m pytest tests/test_complete_trading_cycle.py -v
- Data fetching → Analysis → Signal → Risk → Execution
- Multi-timeframe data consistency
- Signal persistence and gating
- Edge case: Market gap
- Edge case: Exchange maintenance

# Multi-Symbol Processing Test
python -m pytest tests/test_multi_symbol_processing.py -v
- Parallel symbol processing
- Resource management
- Error isolation
- Edge case: One symbol fails
- Edge case: Memory exhaustion
```

#### **4.2 System Resilience Tests**
```bash
# System Resilience Test
python -m pytest tests/test_system_resilience.py -v
- Network interruption recovery
- API failure handling
- Memory leak detection
- Edge case: Long-running execution
- Edge case: Resource exhaustion
```

### **5. Performance Tests (Performans Testleri)**

#### **5.1 Load Tests**
```bash
# High-Frequency Processing Test
python -m pytest tests/test_high_frequency_processing.py -v
- 50+ symbols simultaneous processing
- Memory usage monitoring
- CPU utilization tracking
- Edge case: System overload
- Edge case: Memory leak detection

# API Rate Limiting Test
python -m pytest tests/test_api_rate_limiting.py -v
- OKX API rate limit compliance
- News API rate limit handling
- Backoff strategy effectiveness
- Edge case: Rate limit exceeded
- Edge case: Concurrent requests
```

#### **5.2 Memory and Resource Tests**
```bash
# Memory Management Test
python -m pytest tests/test_memory_management.py -v
- Memory usage over time
- Cache size management
- Garbage collection effectiveness
- Edge case: Memory exhaustion
- Edge case: Cache overflow
```

### **6. Security Tests (Güvenlik Testleri)**

#### **6.1 API Key Security**
```bash
# API Key Security Test
python -m pytest tests/test_api_key_security.py -v
- API key masking in logs
- Environment variable handling
- Key rotation capability
- Edge case: Exposed keys
- Edge case: Invalid key format
```

#### **6.2 Data Validation**
```bash
# Data Validation Test
python -m pytest tests/test_data_validation.py -v
- Input sanitization
- SQL injection prevention
- XSS prevention
- Edge case: Malicious input
- Edge case: Data corruption
```

### **7. Configuration Tests (Konfigürasyon Testleri)**

#### **7.1 Policy Validation**
```bash
# Policy Configuration Test
python -m pytest tests/test_policy_validation.py -v
- Policy schema validation
- Required field checking
- Value range validation
- Edge case: Invalid configuration
- Edge case: Missing required fields
```

#### **7.2 Environment Tests**
```bash
# Environment Configuration Test
python -m pytest tests/test_environment_config.py -v
- Environment variable loading
- Default value handling
- Configuration override
- Edge case: Missing environment variables
- Edge case: Invalid environment values
```

## 🚨 Edge Cases ve Anormal Durumlar

### **7.1 Market Data Edge Cases**
- **Market Gap**: Piyasa kapalıyken veri eksikliği
- **Data Corruption**: Bozuk OHLCV verisi
- **Symbol Delisting**: Sembolün işlemden kaldırılması
- **Extreme Volatility**: Aşırı volatilite durumları
- **Network Partition**: Ağ bağlantısı kesintisi

### **7.2 API Edge Cases**
- **Rate Limiting**: API hız sınırlaması
- **Authentication Failure**: Kimlik doğrulama hatası
- **API Downtime**: API servisinin çökmesi
- **Malformed Responses**: Bozuk API yanıtları
- **Timeout Scenarios**: Zaman aşımı durumları

### **7.3 System Edge Cases**
- **Memory Exhaustion**: Bellek tükenmesi
- **Disk Space Full**: Disk alanı dolu
- **Process Crash**: Süreç çökmesi
- **Clock Skew**: Sistem saati kayması
- **Resource Contention**: Kaynak çakışması

### **7.4 Trading Edge Cases**
- **Insufficient Balance**: Yetersiz bakiye
- **Order Rejection**: Emir reddi
- **Position Slippage**: Pozisyon kayması
- **Circuit Breaker**: Devre kesici tetiklenmesi
- **Emergency Stop**: Acil durdurma

## 🔧 Test Execution Plan

### **Phase 1: Unit Tests (1-2 gün)**
```bash
# Tüm unit testleri çalıştır
python -m pytest tests/unit/ -v --cov=application --cov=scoring --cov=adapters

# Coverage raporu oluştur
python -m pytest tests/unit/ --cov=application --cov-report=html
```

### **Phase 2: Integration Tests (2-3 gün)**
```bash
# External API testleri (testnet/sandbox)
python -m pytest tests/integration/ -v --env=test

# Mock API testleri
python -m pytest tests/integration/ -v --env=mock
```

### **Phase 3: End-to-End Tests (2-3 gün)**
```bash
# Tam sistem testi
python -m pytest tests/e2e/ -v --env=testnet

# Performance testleri
python -m pytest tests/performance/ -v --env=testnet
```

### **Phase 4: Security & Configuration Tests (1 gün)**
```bash
# Güvenlik testleri
python -m pytest tests/security/ -v

# Konfigürasyon testleri
python -m pytest tests/config/ -v
```

## 📊 Test Metrics ve KPI'lar

### **Coverage Targets**
- **Unit Tests**: %90+ code coverage
- **Integration Tests**: %80+ API coverage
- **End-to-End Tests**: %100 critical path coverage

### **Performance Targets**
- **Response Time**: < 2s per symbol analysis
- **Memory Usage**: < 512MB sustained
- **API Latency**: < 500ms average
- **Error Rate**: < 1% under normal conditions

### **Reliability Targets**
- **Uptime**: 99.9% availability
- **Data Accuracy**: 99.95% correct signals
- **Recovery Time**: < 30s from failure
- **False Positive Rate**: < 5% for signals

## 🚀 Test Automation

### **CI/CD Pipeline Integration**
```yaml
# .github/workflows/comprehensive-test.yml
name: Comprehensive Test Suite
on: [push, pull_request]
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Unit Tests
        run: python -m pytest tests/unit/ -v --cov=application
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Integration Tests
        run: python -m pytest tests/integration/ -v --env=test
  
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run E2E Tests
        run: python -m pytest tests/e2e/ -v --env=testnet
```

### **Test Data Management**
```bash
# Test data setup
python scripts/setup_test_data.py

# Test environment cleanup
python scripts/cleanup_test_env.py

# Mock data generation
python scripts/generate_mock_data.py
```

## 📋 Test Checklist

### **Pre-Test Setup**
- [ ] Test environment configured
- [ ] Test data prepared
- [ ] Mock services running
- [ ] Testnet API keys configured
- [ ] Test database initialized

### **Test Execution**
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] End-to-end tests passing
- [ ] Performance tests within limits
- [ ] Security tests passing

### **Post-Test Validation**
- [ ] All test results documented
- [ ] Coverage reports generated
- [ ] Performance metrics recorded
- [ ] Issues logged and prioritized
- [ ] Test environment cleaned up

## 🎯 Expected Outcomes

### **Success Criteria**
1. **All tests passing** with >90% coverage
2. **No critical bugs** in core functionality
3. **Performance within** specified limits
4. **Security vulnerabilities** identified and fixed
5. **Documentation updated** with findings

### **Risk Mitigation**
1. **Automated testing** for regression prevention
2. **Continuous monitoring** for production issues
3. **Rollback procedures** for failed deployments
4. **Alert systems** for critical failures
5. **Backup strategies** for data recovery

---

**Bu kapsamlı test planı, AiBotBS sisteminin production-ready olmasını sağlayacak tüm test senaryolarını kapsar. Her test kategorisi detaylı senaryolar ve edge case'ler içerir.**

*Test planı oluşturulma zamanı: 2025-10-16 15:00:00*

