# E2E Test Reports

Bu klasör E2E (End-to-End) test raporlarını ve artefaktlarını içerir.

## Klasör Yapısı

```
reports/e2e/
├── README.md                    # Bu dosya
├── E2E_REPORT.md               # Ana test raporu
├── orders.jsonl                # Emir yaşam döngü kaydı
├── trades.csv                  # İşlem özeti
├── metrics_snapshot.txt        # Prometheus metrikleri
├── grafana_notes.md            # Grafana panel doğrulama notları
├── logs/                       # Test logları
│   ├── e2e_test.log           # Ana test logu
│   └── ...                    # Diğer log dosyaları
└── screens/                    # Ekran görüntüsü notları (opsiyonel)
    └── ...
```

## Dosya Açıklamaları

### E2E_REPORT.md
Ana test raporu. Test sonuçları, özet bilgiler ve detaylı analiz içerir.

### orders.jsonl
Emir yaşam döngü kaydı. Her satır bir emir olayını JSON formatında içerir:
- Entry orders
- Bracket orders (TP/SL)
- Trailing stop updates
- Exit orders
- Order cancellations

### trades.csv
İşlem özeti. CSV formatında:
- Symbol
- Side (LONG/SHORT)
- Entry time
- Exit time
- Entry price
- Exit price
- PnL
- Fees
- Duration

### metrics_snapshot.txt
Prometheus metrikleri anlık görüntüsü. Test sırasında toplanan metrikler.

### grafana_notes.md
Grafana panel doğrulama notları. Dashboard'ların doğru çalıştığını doğrular.

### logs/
Test logları. Detaylı debug bilgileri ve hata mesajları.

## Test Sonuçları

### Başarı Kriterleri
- ✅ Tüm testler geçti
- ⚠️ Bazı testler uyarı verdi
- ❌ Testler başarısız oldu

### Test Kapsamı
1. **Veri Toplama**: OHLCV, ticker, balance verileri
2. **Signal Üretimi**: TA/ML/News/Risk skorları
3. **Gating Kuralları**: Persist/age/conf/hysteresis
4. **Order Lifecycle**: Entry → Bracket → Trailing → Exit
5. **Risk Yönetimi**: Position sizing, limits, circuit breaker
6. **State Machine**: Geçişler ve tutarlılık
7. **Bildirimler**: Telegram mesajları
8. **Scheduler**: Job'lar ve watchdog
9. **Monitoring**: Prometheus ve Grafana

## Kullanım

1. Test çalıştırma:
   ```bash
   # PowerShell
   .\scripts\run_e2e_real.ps1 -Mode paper -Duration 30
   
   # Bash
   ./scripts/run_e2e_real.sh --mode paper --duration 30
   ```

2. Raporları inceleme:
   - `E2E_REPORT.md` - Ana rapor
   - `orders.jsonl` - Emir detayları
   - `trades.csv` - İşlem özeti
   - `logs/e2e_test.log` - Detaylı loglar

3. Metrikleri kontrol etme:
   - `metrics_snapshot.txt` - Anlık metrikler
   - Grafana dashboard'ları

## Güvenlik Notları

- Test raporları hassas bilgiler içerebilir
- API anahtarları loglanmaz
- Gerçek işlem miktarları gizlenir
- Raporları güvenli şekilde saklayın

## Sorun Giderme

### Yaygın Hatalar
1. **API Bağlantı Hatası**: OKX API anahtarlarını kontrol edin
2. **Metrik Endpoint Hatası**: Prometheus'un çalıştığını kontrol edin
3. **Telegram Hatası**: Bot token'ını kontrol edin
4. **Veri Hatası**: Sembol ve timeframe'leri kontrol edin

### Log Analizi
- `logs/e2e_test.log` dosyasını inceleyin
- Hata mesajlarını arayın
- API yanıtlarını kontrol edin
- Metrik değerlerini doğrulayın

## İletişim

Sorunlar için:
- GitHub Issues
- Telegram grubu
- Dokümantasyon

## Sürüm Geçmişi

- v1.0.0 - İlk sürüm
- E2E test altyapısı
- Gerçek API entegrasyonu
- Kapsamlı raporlama


