# AiBotBS Metrik Rehberi

> **Prometheus metrikleri ve PromQL sorguları için kapsamlı rehber**

## 📊 Metrik Kategorileri

### 1. **Trading Metrikleri**
- Pozisyon açma/kapama sayıları
- Win/loss oranları
- PnL takibi
- Trade süreleri

### 2. **Scoring Metrikleri**
- Composite skorlar
- Bileşen skorları (TA, ML, News, Risk)
- ML confidence seviyeleri
- Sinyal kalitesi

### 3. **Risk Metrikleri**
- Drawdown takibi
- Pozisyon maruziyeti
- Korelasyon riski
- Volatilite riski

### 4. **Sistem Metrikleri**
- Job execution süreleri
- Hata sayıları
- API çağrıları
- Circuit breaker durumu

### 5. **LLM Metrikleri**
- LLM istek sayıları
- Token kullanımı
- Maliyet takibi
- Rate limit durumu

## 🎯 Önemli Metrikler

### Trading Metrikleri

#### `aibot_open_transitions_total`
**Açıklama**: OPEN durumuna geçiş sayısı
**Etiketler**: `symbol`, `direction`
**Kullanım**: Pozisyon açma aktivitesini takip eder

```promql
# Toplam pozisyon açma sayısı
sum(aibot_open_transitions_total)

# Sembol bazında pozisyon açma
sum(aibot_open_transitions_total) by (symbol)

# Yön bazında pozisyon açma
sum(aibot_open_transitions_total) by (direction)
```

#### `aibot_flip_events_total`
**Açıklama**: Pozisyon çevirme sayısı
**Etiketler**: `symbol`, `from_direction`, `to_direction`
**Kullanım**: Reversal aktivitesini takip eder

```promql
# Toplam flip sayısı
sum(aibot_flip_events_total)

# LONG'dan SHORT'a çevirme
sum(aibot_flip_events_total{from_direction="LONG", to_direction="SHORT"})

# SHORT'dan LONG'a çevirme
sum(aibot_flip_events_total{from_direction="SHORT", to_direction="LONG"})
```

#### `aibot_entry_skips_total`
**Açıklama**: Giriş atlama sayısı
**Etiketler**: `reason`
**Kullanım**: Neden giriş yapılmadığını analiz eder

```promql
# Tüm skip nedenleri
sum(aibot_entry_skips_total) by (reason)

# En yaygın skip nedenleri
topk(5, sum(aibot_entry_skips_total) by (reason))

# once_per_bar skip'leri
sum(aibot_entry_skips_total{reason="once_per_bar"})

# cooldown skip'leri
sum(aibot_entry_skips_total{reason="cooldown"})

# same_direction_block skip'leri
sum(aibot_entry_skips_total{reason="same_direction_block"})
```

#### `aibot_position_tpsl_applied_total`
**Açıklama**: Position-level TP/SL uygulama sayısı
**Etiketler**: `symbol`, `mode`
**Kullanım**: TP/SL aktivitesini takip eder

```promql
# Toplam TP/SL uygulama
sum(aibot_position_tpsl_applied_total)

# Mod bazında TP/SL
sum(aibot_position_tpsl_applied_total) by (mode)

# Sembol bazında TP/SL
sum(aibot_position_tpsl_applied_total) by (symbol)
```

#### `aibot_trailing_modify_total`
**Açıklama**: Trailing stop güncelleme sayısı
**Etiketler**: `symbol`, `mode`
**Kullanım**: Trailing stop aktivitesini takip eder

```promql
# Toplam trailing modify
sum(aibot_trailing_modify_total)

# Sembol bazında trailing
sum(aibot_trailing_modify_total) by (symbol)
```

### Scoring Metrikleri

#### `aibot_composite_score`
**Açıklama**: Son composite skor (0-100)
**Etiketler**: `symbol`
**Kullanım**: Sinyal kalitesini takip eder

```promql
# Mevcut composite skorlar
aibot_composite_score

# BTC composite skoru
aibot_composite_score{symbol="BTC-USDT-SWAP"}

# Yüksek skorlu semboller (>70)
aibot_composite_score > 70
```

#### `aibot_ta_score`, `aibot_ml_score`, `aibot_news_score`, `aibot_risk_score`
**Açıklama**: Bileşen skorları (0-100)
**Etiketler**: `symbol`
**Kullanım**: Skor bileşenlerini analiz eder

```promql
# Tüm skor bileşenleri
aibot_ta_score{symbol="BTC-USDT-SWAP"}
aibot_ml_score{symbol="BTC-USDT-SWAP"}
aibot_news_score{symbol="BTC-USDT-SWAP"}
aibot_risk_score{symbol="BTC-USDT-SWAP"}

# Skor karşılaştırması
aibot_ta_score{symbol="BTC-USDT-SWAP"} > aibot_ml_score{symbol="BTC-USDT-SWAP"}
```

### Risk Metrikleri

#### `aibot_drawdown_current`
**Açıklama**: Mevcut drawdown yüzdesi
**Kullanım**: Risk durumunu takip eder

```promql
# Mevcut drawdown
aibot_drawdown_current

# Drawdown eşiği (>10%)
aibot_drawdown_current > 10
```

#### `aibot_exposure_percentage`
**Açıklama**: Portfolio maruziyet yüzdesi
**Kullanım**: Risk maruziyetini takip eder

```promql
# Mevcut maruziyet
aibot_exposure_percentage

# Maruziyet eşiği (>50%)
aibot_exposure_percentage > 50
```

#### `aibot_positions_open`
**Açıklama**: Açık pozisyon sayısı
**Kullanım**: Pozisyon yoğunluğunu takip eder

```promql
# Açık pozisyon sayısı
aibot_positions_open

# Maksimum pozisyon eşiği (>5)
aibot_positions_open > 5
```

### Sistem Metrikleri

#### `aibot_job_executions_total`
**Açıklama**: Job execution sayısı
**Etiketler**: `job_name`, `status`
**Kullanım**: Job performansını takip eder

```promql
# Job execution oranı
rate(aibot_job_executions_total[5m])

# Başarılı job'lar
sum(aibot_job_executions_total{status="success"})

# Başarısız job'lar
sum(aibot_job_executions_total{status="failure"})

# Job başarı oranı
sum(aibot_job_executions_total{status="success"}) / sum(aibot_job_executions_total)
```

#### `aibot_errors_total`
**Açıklama**: Hata sayısı
**Etiketler**: `error_type`, `component`
**Kullanım**: Hata durumunu takip eder

```promql
# Hata oranı
rate(aibot_errors_total[5m])

# Hata türüne göre
sum(aibot_errors_total) by (error_type)

# Bileşen bazında hatalar
sum(aibot_errors_total) by (component)
```

#### `aibot_scheduler_shutdowns_total`
**Açıklama**: Scheduler kapanma sayısı
**Kullanım**: Sistem kararlılığını takip eder

```promql
# Scheduler kapanma sayısı
aibot_scheduler_shutdowns_total

# Kapanma oranı
rate(aibot_scheduler_shutdowns_total[1h])
```

### LLM Metrikleri

#### `aibot_llm_requests_total`
**Açıklama**: LLM istek sayısı
**Etiketler**: `status`
**Kullanım**: LLM kullanımını takip eder

```promql
# LLM istek oranı
rate(aibot_llm_requests_total[5m])

# Başarılı istekler
sum(aibot_llm_requests_total{status="2xx"})

# Hata oranı
sum(aibot_llm_requests_total{status="4xx"}) / sum(aibot_llm_requests_total)
```

#### `aibot_llm_cost_usd_total`
**Açıklama**: LLM maliyeti (USD)
**Kullanım**: Maliyet takibi

```promql
# Toplam LLM maliyeti
aibot_llm_cost_usd_total

# Günlük maliyet artışı
increase(aibot_llm_cost_usd_total[1d])
```

## 📈 PromQL Örnekleri

### 1. **Rate Hesaplamaları**
```promql
# 5 dakikalık pozisyon açma oranı
rate(aibot_open_transitions_total[5m])

# 1 saatlik hata oranı
rate(aibot_errors_total[1h])

# 15 dakikalık job execution oranı
rate(aibot_job_executions_total[15m])
```

### 2. **Increase Hesaplamaları**
```promql
# Son 1 saatteki pozisyon açma sayısı
increase(aibot_open_transitions_total[1h])

# Son 24 saatteki toplam işlem
increase(aibot_trades_total[1d])

# Son 1 haftadaki LLM maliyeti
increase(aibot_llm_cost_usd_total[1w])
```

### 3. **TopK Sorguları**
```promql
# En aktif 5 sembol
topk(5, sum(aibot_open_transitions_total) by (symbol))

# En yaygın 5 hata türü
topk(5, sum(aibot_errors_total) by (error_type))

# En yüksek 3 composite skor
topk(3, aibot_composite_score)
```

### 4. **Karşılaştırma Sorguları**
```promql
# Composite skor > 70 olan semboller
aibot_composite_score > 70

# Drawdown > 10% olan durumlar
aibot_drawdown_current > 10

# Maruziyet > 50% olan durumlar
aibot_exposure_percentage > 50
```

### 5. **Zaman Serisi Analizi**
```promql
# Son 1 saatteki composite skor değişimi
aibot_composite_score{symbol="BTC-USDT-SWAP"}[1h]

# Son 24 saatteki pozisyon açma trendi
rate(aibot_open_transitions_total[1h])[24h:1h]
```

## 🎨 Grafana Panel Önerileri

### 1. **Trading Dashboard**
- **Pozisyon Açma Oranı**: `rate(aibot_open_transitions_total[5m])`
- **Win Rate**: `sum(aibot_trades_total{result="win"}) / sum(aibot_trades_total)`
- **Aktif Pozisyonlar**: `aibot_positions_open`
- **PnL Trendi**: `aibot_portfolio_pnl_usd`

### 2. **Risk Dashboard**
- **Drawdown**: `aibot_drawdown_current`
- **Maruziyet**: `aibot_exposure_percentage`
- **Risk Skorları**: `aibot_risk_score`
- **Pozisyon Dağılımı**: `aibot_position_size_usd`

### 3. **Sistem Dashboard**
- **Job Başarı Oranı**: `sum(aibot_job_executions_total{status="success"}) / sum(aibot_job_executions_total)`
- **Hata Oranı**: `rate(aibot_errors_total[5m])`
- **API Latency**: `aibot_api_latency_seconds`
- **Uptime**: `aibot_uptime_seconds`

### 4. **Scoring Dashboard**
- **Composite Skorlar**: `aibot_composite_score`
- **Skor Bileşenleri**: `aibot_ta_score`, `aibot_ml_score`, `aibot_news_score`
- **ML Confidence**: `aibot_ml_confidence`
- **Sinyal Kalitesi**: `aibot_last_signal`

## 🔧 Metrik Endpoint'leri

### 1. **Prometheus Metrics**
```bash
# Tüm metrikleri görüntüle
curl http://localhost:8000/metrics

# Belirli metrikleri filtrele
curl http://localhost:8000/metrics | grep aibot_trading

# JSON formatında
curl -H "Accept: application/json" http://localhost:8000/metrics
```

### 2. **Grafana Dashboard**
- **URL**: http://localhost:3000
- **Kullanıcı**: admin
- **Şifre**: admin
- **Dashboard**: AiBotBS Trading Dashboard

### 3. **Prometheus Query**
- **URL**: http://localhost:9090
- **Query**: PromQL sorgularını test et
- **Graph**: Zaman serisi görselleştirme

## 🚨 Alert Kuralları

### 1. **Risk Alertları**
```yaml
# Yüksek drawdown
- alert: HighDrawdown
  expr: aibot_drawdown_current > 15
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High drawdown detected"

# Yüksek maruziyet
- alert: HighExposure
  expr: aibot_exposure_percentage > 70
  for: 2m
  labels:
    severity: critical
  annotations:
    summary: "Portfolio exposure too high"
```

### 2. **Sistem Alertları**
```yaml
# Yüksek hata oranı
- alert: HighErrorRate
  expr: rate(aibot_errors_total[5m]) > 0.1
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High error rate detected"

# Scheduler kapanma
- alert: SchedulerShutdown
  expr: increase(aibot_scheduler_shutdowns_total[1m]) > 0
  for: 0m
  labels:
    severity: critical
  annotations:
    summary: "Scheduler has shut down"
```

### 3. **Trading Alertları**
```yaml
# Çok fazla skip
- alert: TooManySkips
  expr: rate(aibot_entry_skips_total[15m]) > 0.5
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Too many entry skips"

# Pozisyon takılması
- alert: StuckPositions
  expr: aibot_positions_open > 10
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Too many open positions"
```

## 📚 Sonraki Adımlar

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Sorun giderme rehberi
2. [POLICY_REFERENCE.md](POLICY_REFERENCE.md) - Konfigürasyon referansı
3. [OPERATIONS_PLAYBOOK.md](OPERATIONS_PLAYBOOK.md) - Operasyon pratikleri

