# AiBotBS Operasyon Playbook

> **Canlı operasyonda pratik rehber ve best practice'ler**

## 🎯 Operasyon Genel Bakış

### Canlı Operasyon Prensipleri
1. **Güvenlik Öncelikli**: Risk yönetimi her şeyden önce
2. **İzlenebilirlik**: Tüm işlemler loglanır ve metriklenir
3. **Hızlı Müdahale**: Sorun durumunda hızlı aksiyon
4. **Sürekli İzleme**: 7/24 sistem durumu takibi

## 🔍 Canlı Operasyonda Davranış Analizi

### 1. **once_per_bar Davranışı**
**Ne Yapar**: Her 15 dakikalık bar'da sadece 1 karar verir

**Nasıl Okunur**:
```
[GATING] once_per_bar=true
[SKIP] BTC-USDT-SWAP: once_per_bar (bar already processed)
```

**Operasyon Notları**:
- Aynı bar içinde tekrar analiz yapılmaz
- Gereksiz işlemleri önler
- Bar sonunda yeni analiz başlar

### 2. **cooldown Davranışı**
**Ne Yapar**: Giriş sonrası 2 bar (30 dakika) bekleme

**Nasıl Okunur**:
```
[GATING] entry_cooldown_bars=2
[SKIP] BTC-USDT-SWAP: cooldown (2 bars remaining)
```

**Operasyon Notları**:
- Ardışık kayıplarda cooldown artar
- Aşırı işlem yapmayı engeller
- Risk yönetimi için kritik

### 3. **flip Davranışı**
**Ne Yapar**: Pozisyon tersine çevirme kontrolü

**Nasıl Okunur**:
```
[REVERSAL] BTC-USDT-SWAP: LONG → SHORT (strength=0.75, edge=1.8)
[FLIP] Position reversed with TP/SL attached
```

**Operasyon Notları**:
- Edge/cost ratio hesaplaması yapılır
- Sadece kârlı reversal'lara izin verilir
- TP/SL otomatik olarak güncellenir

## 🚨 "Neden Girmedi?" Sorusuna Yanıt

### Skip Reason Sözlüğü

#### 1. **Gating Reasons**
| Reason | Açıklama | Çözüm |
|--------|----------|-------|
| `once_per_bar` | Bar zaten işlendi | Bir sonraki bar'ı bekle |
| `cooldown` | Bekleme süresi devam ediyor | Cooldown bitene kadar bekle |
| `same_direction_block` | Aynı yönde pozisyon var | Mevcut pozisyonu kapat veya reversal yap |
| `below_min_score` | Skor minimum eşiğin altında | Daha güçlü sinyal bekle |

#### 2. **Risk Reasons**
| Reason | Açıklama | Çözüm |
|--------|----------|-------|
| `max_risk_exceeded` | Maksimum risk aşıldı | Risk limitlerini kontrol et |
| `correlation_risk` | Korelasyon riski yüksek | Pozisyon çeşitlendirmesi yap |
| `volatility_risk` | Volatilite riski yüksek | Volatilite azalana kadar bekle |
| `liquidity_risk` | Likidite riski yüksek | Daha likit sembol seç |

#### 3. **Technical Reasons**
| Reason | Açıklama | Çözüm |
|--------|----------|-------|
| `insufficient_data` | Yeterli veri yok | Veri yüklenmesini bekle |
| `model_error` | ML modeli hatası | Model durumunu kontrol et |
| `news_error` | Haber analizi hatası | Haber servisini kontrol et |
| `exchange_error` | Exchange bağlantı hatası | Exchange durumunu kontrol et |

### Örnek Skip Logları
```
[SKIP] BTC-USDT-SWAP: once_per_bar (bar already processed)
[SKIP] ETH-USDT-SWAP: cooldown (1 bars remaining)
[SKIP] SOL-USDT-SWAP: same_direction_block (LONG position exists)
[SKIP] BTC-USDT-SWAP: below_min_score (45.2 < 60.0)
[SKIP] ETH-USDT-SWAP: max_risk_exceeded (0.65 > 0.60)
```

## 🛡️ Position-Level TP/SL Yönetimi

### Temel Prensipler
1. **Emir Sayısını Düşük Tutma**: Her pozisyon için sadece 1 TP + 1 SL
2. **Reduce-Only Kullanımı**: Yeni pozisyon açmayı engeller
3. **Idempotency**: Aynı emir ID'si ile tekrar emir gönderilmez

### TP/SL Davranışı
```
[POSITION] BTC-USDT-SWAP: LONG @ 45000 (size: 0.01)
[TP/SL] TP: 45900 (2.0%), SL: 44100 (-2.0%)
[ATTACHED] Bracket orders created successfully
```

### Trailing Stop Davranışı
```
[TRAILING] BTC-USDT-SWAP: +0.5R reached, trailing activated
[TRAILING] BTC-USDT-SWAP: +1.0R reached, moved to breakeven
[TRAILING] BTC-USDT-SWAP: +1.5R reached, tight stop at +0.3R
```

## 📊 Health/Metrics Kontrol Checklist

### 1. **Sistem Sağlığı (Her 15 dakika)**
- [ ] Bot process çalışıyor mu?
- [ ] Log dosyaları güncelleniyor mu?
- [ ] Metrics endpoint yanıt veriyor mu?
- [ ] Exchange bağlantısı aktif mi?

### 2. **Trading Sağlığı (Her 15 dakika)**
- [ ] Sinyaller üretiliyor mu?
- [ ] Pozisyonlar doğru takip ediliyor mu?
- [ ] TP/SL emirleri aktif mi?
- [ ] Risk limitleri aşılmamış mı?

### 3. **Performans Metrikleri (Her saat)**
- [ ] Win rate kabul edilebilir mi? (>50%)
- [ ] Drawdown limitler içinde mi? (<15%)
- [ ] Sharpe ratio pozitif mi? (>0.5)
- [ ] Max consecutive losses kontrol altında mı? (<3)

### 4. **Risk Metrikleri (Sürekli)**
- [ ] Total exposure limitler içinde mi? (<60%)
- [ ] Position size limitler içinde mi? (<10%)
- [ ] Correlation risk kabul edilebilir mi? (<0.8)
- [ ] Volatility risk kontrol altında mı?

## 🚨 Acil Durum Senaryoları

### 1. **Bot Çöktü**
```bash
# Hızlı restart
./scripts/dev.sh start-scheduler

# Health check
./scripts/dev.sh test-health

# Log kontrol
./scripts/dev.sh watch-logs
```

### 2. **Pozisyon Takıldı**
```bash
# Pozisyon durumunu kontrol et
curl http://localhost:8000/metrics | grep aibot_positions

# Manuel pozisyon kapatma (gerekirse)
# Exchange'den manuel kapatma yapılmalı
```

### 3. **Risk Limit Aşıldı**
```bash
# Risk durumunu kontrol et
curl http://localhost:8000/metrics | grep aibot_risk

# Pozisyonları kapat (gerekirse)
# Risk servisini devre dışı bırak
```

### 4. **Exchange Bağlantısı Kesildi**
```bash
# Bağlantı durumunu kontrol et
curl http://localhost:8000/metrics | grep aibot_exchange

# Bot'u durdur ve yeniden başlat
./scripts/dev.sh stop-bot
./scripts/dev.sh start-scheduler
```

## 📈 Operasyon Metrikleri

### 1. **Trading Metrikleri**
- `aibot_open_transitions_total`: Pozisyon açma sayısı
- `aibot_flip_events_total`: Pozisyon çevirme sayısı
- `aibot_entry_skips_total`: Giriş atlama sayısı (reason bazında)
- `aibot_position_tpsl_applied_total`: TP/SL uygulama sayısı

### 2. **Sistem Metrikleri**
- `aibot_scheduler_shutdowns_total`: Scheduler kapanma sayısı
- `aibot_unclosed_sessions_total`: Kapatılmamış session sayısı
- `aibot_llm_requests_total`: LLM istek sayısı
- `aibot_llm_errors_total`: LLM hata sayısı

### 3. **Risk Metrikleri**
- `aibot_risk_score_current`: Mevcut risk skoru
- `aibot_position_exposure_pct`: Pozisyon maruziyet yüzdesi
- `aibot_correlation_risk_score`: Korelasyon risk skoru
- `aibot_volatility_risk_score`: Volatilite risk skoru

## 🔧 Operasyon Araçları

### 1. **Log Analizi**
```bash
# Son 100 satırı göster
tail -100 logs/trading.log

# Hata loglarını filtrele
grep "ERROR\|CRITICAL" logs/trading.log

# Belirli sembol için log
grep "BTC-USDT-SWAP" logs/trading.log
```

### 2. **Metrics Analizi**
```bash
# Tüm metrikleri göster
curl http://localhost:8000/metrics

# Belirli metrikleri filtrele
curl http://localhost:8000/metrics | grep aibot_trading

# Prometheus query (Grafana'da)
rate(aibot_open_transitions_total[5m])
```

### 3. **State Kontrolü**
```bash
# Runtime state kontrol
cat data/runtime_state.json

# Position state kontrol
cat data/position_state.json

# News digest kontrol
cat data/news_llm_digest.json
```

## 📋 Günlük Operasyon Checklist

### Sabah Kontrolü (09:00)
- [ ] Bot durumu kontrol
- [ ] Gece pozisyonları kontrol
- [ ] Risk metrikleri kontrol
- [ ] Log hataları kontrol

### Öğle Kontrolü (12:00)
- [ ] Trading performansı kontrol
- [ ] Pozisyon durumları kontrol
- [ ] Risk limitleri kontrol
- [ ] Sistem sağlığı kontrol

### Akşam Kontrolü (18:00)
- [ ] Günlük performans özeti
- [ ] Risk raporu kontrol
- [ ] Pozisyon kapatma ihtiyacı
- [ ] Gece modu ayarları

### Haftalık Kontrol (Pazar)
- [ ] Haftalık performans analizi
- [ ] Risk parametreleri gözden geçirme
- [ ] Log temizleme
- [ ] Backup kontrolü

## 🚀 Performans Optimizasyonu

### 1. **Log Optimizasyonu**
- Gereksiz log'ları azalt
- Log rotation ayarlarını kontrol et
- Debug log'ları sadece gerektiğinde aç

### 2. **Memory Optimizasyonu**
- Cache TTL'lerini optimize et
- Gereksiz data retention'ı azalt
- Garbage collection'ı izle

### 3. **Network Optimizasyonu**
- API rate limit'lerini optimize et
- Connection pooling kullan
- Timeout değerlerini ayarla

## 📚 Sonraki Adımlar

1. [METRICS_CHEATSHEET.md](METRICS_CHEATSHEET.md) - Detaylı metrik rehberi
2. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Sorun giderme rehberi
3. [POLICY_REFERENCE.md](POLICY_REFERENCE.md) - Konfigürasyon referansı

