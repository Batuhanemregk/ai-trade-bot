# Grafana Dashboard Validation Notes

Bu dosya Grafana dashboard'larının E2E test sırasında doğru çalıştığını doğrular.

## Dashboard Listesi

### 1. Trading Overview Dashboard
**URL**: `/d/trading-overview/trading-overview`

**Paneller**:
- [ ] Portfolio PnL (Real-time)
- [ ] Position Count
- [ ] Trade Volume
- [ ] Win Rate
- [ ] Drawdown Chart
- [ ] Exposure Percentage

**Doğrulama**:
- [ ] PnL değerleri güncelleniyor
- [ ] Position sayısı doğru
- [ ] Trade hacmi hesaplanıyor
- [ ] Win rate yüzdesi doğru
- [ ] Drawdown eğrisi çiziliyor
- [ ] Exposure yüzdesi güncel

### 2. Signal Analysis Dashboard
**URL**: `/d/signal-analysis/signal-analysis`

**Paneller**:
- [ ] Composite Score (per symbol)
- [ ] TA Score
- [ ] ML Score
- [ ] News Score
- [ ] Risk Score
- [ ] Signal Direction
- [ ] Signal Strength

**Doğrulama**:
- [ ] Skorlar 0-100 aralığında
- [ ] Sembol bazında ayrılmış
- [ ] Gerçek zamanlı güncelleniyor
- [ ] Yön bilgisi doğru (LONG/SHORT/HOLD)
- [ ] Güç değerleri mantıklı

### 3. Risk Management Dashboard
**URL**: `/d/risk-management/risk-management`

**Paneller**:
- [ ] Portfolio Exposure
- [ ] Position Sizes
- [ ] Risk Scores
- [ ] Circuit Breaker Status
- [ ] Drawdown Alerts
- [ ] Correlation Matrix

**Doğrulama**:
- [ ] Exposure limitleri aşılmıyor
- [ ] Position boyutları uygun
- [ ] Risk skorları yüksek değil
- [ ] Circuit breaker normal durumda
- [ ] Drawdown uyarıları çalışıyor
- [ ] Korelasyon matrisi güncel

### 4. Order Management Dashboard
**URL**: `/d/order-management/order-management`

**Paneller**:
- [ ] Active Orders
- [ ] Order Status
- [ ] Fill Rates
- [ ] Slippage
- [ ] Order Duration
- [ ] Bracket Orders

**Doğrulama**:
- [ ] Aktif emirler listeleniyor
- [ ] Emir durumları doğru
- [ ] Dolum oranları hesaplanıyor
- [ ] Slippage değerleri makul
- [ ] Emir süreleri takip ediliyor
- [ ] Bracket emirler görünüyor

### 5. System Health Dashboard
**URL**: `/d/system-health/system-health`

**Paneller**:
- [ ] API Latency
- [ ] Error Rates
- [ ] Job Execution Times
- [ ] Memory Usage
- [ ] CPU Usage
- [ ] Disk Usage

**Doğrulama**:
- [ ] API gecikmeleri düşük
- [ ] Hata oranları düşük
- [ ] Job süreleri makul
- [ ] Bellek kullanımı normal
- [ ] CPU kullanımı normal
- [ ] Disk kullanımı normal

## Test Senaryoları

### Senaryo 1: Normal Trading
**Durum**: Bot normal çalışıyor
**Beklenen**:
- [ ] Tüm paneller veri gösteriyor
- [ ] Metrikler güncelleniyor
- [ ] Uyarılar yok
- [ ] Performans iyi

### Senaryo 2: High Volatility
**Durum**: Yüksek volatilite
**Beklenen**:
- [ ] Risk skorları yüksek
- [ ] Drawdown uyarıları
- [ ] Position boyutları küçük
- [ ] Circuit breaker aktif olabilir

### Senaryo 3: API Issues
**Durum**: API sorunları
**Beklenen**:
- [ ] API gecikmeleri yüksek
- [ ] Hata oranları artıyor
- [ ] Emirler gecikiyor
- [ ] Sistem uyarıları

### Senaryo 4: High Exposure
**Durum**: Yüksek exposure
**Beklenen**:
- [ ] Exposure uyarıları
- [ ] Yeni emirler engelleniyor
- [ ] Risk skorları yüksek
- [ ] Position sayısı limit

## Metrik Doğrulama

### Gerekli Metrikler
- [ ] `aibot_trades_total`
- [ ] `aibot_composite_score`
- [ ] `aibot_portfolio_pnl_usd`
- [ ] `aibot_positions_open`
- [ ] `aibot_exposure_percentage`
- [ ] `aibot_drawdown_current`
- [ ] `aibot_circuit_breaker_state`
- [ ] `aibot_job_executions_total`
- [ ] `aibot_api_latency_seconds`
- [ ] `aibot_errors_total`

### Metrik Değer Aralıkları
- **PnL**: -∞ to +∞ (USD)
- **Scores**: 0 to 100
- **Exposure**: 0 to 100 (%)
- **Drawdown**: 0 to 100 (%)
- **Circuit Breaker**: 0-3 (0=normal, 1=warning, 2=emergency, 3=paused)
- **Latency**: 0 to 10 (seconds)
- **Error Rate**: 0 to 100 (%)

## Alert Kuralları

### Kritik Uyarılar
- [ ] Circuit breaker emergency
- [ ] Drawdown > 15%
- [ ] Exposure > 70%
- [ ] API errors > 10%
- [ ] Job failures > 5%

### Uyarı Seviyeleri
- [ ] High exposure > 60%
- [ ] High drawdown > 10%
- [ ] High latency > 5s
- [ ] High error rate > 5%

## Dashboard Performansı

### Yükleme Süreleri
- [ ] Trading Overview < 2s
- [ ] Signal Analysis < 3s
- [ ] Risk Management < 2s
- [ ] Order Management < 2s
- [ ] System Health < 1s

### Veri Güncelleme
- [ ] Real-time updates (1s)
- [ ] Historical data (1m)
- [ ] Aggregated data (5m)
- [ ] Long-term data (1h)

## Sorun Giderme

### Yaygın Sorunlar
1. **Dashboard yüklenmiyor**
   - Grafana servisini kontrol edin
   - Prometheus bağlantısını kontrol edin
   - Panel sorgularını kontrol edin

2. **Veri güncellenmiyor**
   - Prometheus scraping'i kontrol edin
   - Bot metriklerini kontrol edin
   - Time range'i kontrol edin

3. **Yanlış veri**
   - Metrik etiketlerini kontrol edin
   - Sorgu syntax'ını kontrol edin
   - Bot konfigürasyonunu kontrol edin

### Debug Adımları
1. Grafana logs'larını kontrol edin
2. Prometheus targets'ı kontrol edin
3. Bot metrics endpoint'ini kontrol edin
4. Panel sorgularını test edin
5. Veri kaynağını doğrulayın

## Test Sonuçları

### Başarı Kriterleri
- [ ] Tüm dashboard'lar yükleniyor
- [ ] Veriler güncelleniyor
- [ ] Uyarılar çalışıyor
- [ ] Performans iyi
- [ ] Metrikler doğru

### Test Tarihi
- **Test Tarihi**: ___________
- **Test Süresi**: ___________
- **Test Modu**: ___________
- **Test Sonucu**: ___________

### Notlar
- ___________
- ___________
- ___________

## Güncelleme Geçmişi

- **v1.0.0** - İlk sürüm
- Dashboard listesi
- Test senaryoları
- Metrik doğrulama
- Sorun giderme


