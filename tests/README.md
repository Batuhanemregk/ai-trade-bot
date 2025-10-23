# AiBotBS Real Data Tests

Bu test suite'i gerçek API'ler ve gerçek market verileri kullanarak botun tüm özelliklerini test eder. Mock veriler kullanılmaz.

## Test Kategorileri

### 1. Integration Tests (`tests/integration/`)

#### `test_real_exchange_api.py`
- **OKX Exchange API** gerçek bağlantı testleri
- Gerçek OHLCV verisi çekme
- Gerçek ticker ve orderbook verileri
- API rate limiting testleri
- Çoklu sembol testleri

#### `test_real_news_api.py`
- **CryptoCompare News API** gerçek bağlantı testleri
- Gerçek haber verisi çekme
- LLM analiz testleri
- Haber kalitesi ve timestamp filtreleme
- API rate limiting testleri

#### `test_real_trading_analysis.py`
- **TA Scorer** gerçek market verisi ile
- **ML Scorer** gerçek market verisi ile
- **News Scorer** gerçek haber verisi ile
- **Risk Scorer** gerçek market verisi ile
- Tam analiz pipeline testi
- Çoklu sembol analizi
- Signal gate persistence testleri

#### `test_real_risk_assessment.py`
- **Risk Service** gerçek market verisi ile
- Volatilite hesaplama testleri
- Likidite değerlendirme testleri
- Korelasyon analizi testleri
- Risk manager testleri
- Position sizing testleri
- Risk threshold testleri

### 2. End-to-End Tests (`tests/e2e/`)

#### `test_real_trading_cycle.py`
- **Tam trading cycle** gerçek verilerle
- Signal generation ve processing
- Portfolio management testleri
- Position monitoring testleri
- Trading orchestrator testleri
- Çoklu sembol trading cycle
- Performance testleri
- Error handling testleri
- Data consistency testleri

## API Gereksinimleri

Testlerin çalışması için gerekli API'ler:

### 1. OKX Exchange API
```bash
# .env dosyasında
OKX_API_KEY=your_api_key
OKX_API_SECRET=your_api_secret
OKX_API_PASSPHRASE=your_passphrase
```

### 2. OpenAI API (LLM için)
```bash
# .env dosyasında
OPENAI_API_KEY=your_openai_key
```

### 3. Internet Bağlantısı
- News API'leri için internet bağlantısı gerekli
- OKX API'leri için internet bağlantısı gerekli

## Test Çalıştırma

### Tüm Testleri Çalıştır
```bash
python scripts/run_tests.py
```

### Belirli Kategorileri Çalıştır
```bash
# Sadece integration testleri
python -m pytest tests/integration/ -v -s

# Sadece E2E testleri
python -m pytest tests/e2e/ -v -s

# Belirli bir test dosyası
python -m pytest tests/integration/test_real_exchange_api.py -v -s
```

### Test Raporları
Testler çalıştırıldıktan sonra HTML raporları `test_reports/` klasöründe oluşturulur:
- `unit_test_report.html`
- `integration_test_report.html`
- `e2e_test_report.html`
- `performance_test_report.html`

## Test Davranışı

### Skip Edilen Testler
API'ler mevcut değilse testler `pytest.skip()` ile atlanır:
```python
except Exception as e:
    pytest.skip(f"OKX connection failed (likely API keys not configured): {e}")
```

### Gerçek Veri Kullanımı
- Tüm testler gerçek market verilerini kullanır
- Mock veriler kullanılmaz
- Gerçek API çağrıları yapılır
- Gerçek hesaplama sonuçları doğrulanır

### Performance Testleri
- API response time'ları ölçülür
- Analysis süreleri kontrol edilir
- Rate limiting davranışı test edilir

## Test Sonuçları

### Başarılı Test
```
✅ Exchange API: Connected to OKX, found 150 markets
✅ OHLCV Data: Retrieved 100 real OHLCV candles for BTC-USDT-SWAP
✅ TA Scorer: Score 75.3 for BTC-USDT-SWAP
```

### Atlanan Test
```
⚠️ OKX connection failed (likely API keys not configured): 50110
```

### Başarısız Test
```
❌ Risk assessment failed: Invalid data format
```

## Önemli Notlar

1. **API Limitleri**: Testler API rate limitlerini aşmamaya dikkat eder
2. **Gerçek Veri**: Tüm testler gerçek market verilerini kullanır
3. **Skip Mekanizması**: API'ler mevcut değilse testler atlanır
4. **Performance**: Testler makul sürelerde tamamlanmalı
5. **Error Handling**: Hata durumları graceful şekilde handle edilir

## Sorun Giderme

### API Key Hatası
```
50110: Invalid API key
```
**Çözüm**: `.env` dosyasında API key'leri kontrol edin

### Bağlantı Hatası
```
Connection timeout
```
**Çözüm**: Internet bağlantısını kontrol edin

### Rate Limit Hatası
```
429: Too many requests
```
**Çözüm**: Testler arasında bekleme süresi ekleyin

## Test Geliştirme

Yeni test eklerken:
1. Gerçek API'leri kullanın
2. Mock veriler kullanmayın
3. API mevcut değilse `pytest.skip()` kullanın
4. Performance threshold'ları belirleyin
5. Error handling ekleyin