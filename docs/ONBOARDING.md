# AiBotBS Onboarding Rehberi

> **"İlk kez gelen biri her şeyi 30 dakikada kavrasın" seviyesinde sistem rehberi**

## 🎯 Bu Bot Nedir?

**AiBotBS**, kripto para piyasalarında otomatik trading yapan gelişmiş bir AI botudur. Sistem, teknik analiz, makine öğrenmesi, haber analizi ve risk yönetimini birleştirerek akıllı trading kararları verir.

### Temel Özellikler
- **Multi-Agent Mimarisi**: Her biri özel görevlere sahip agent'lar
- **Composite Scoring**: TA + ML + News + Risk skorlarının birleşimi
- **Position-Level TP/SL**: Pozisyon bazlı take profit/stop loss yönetimi
- **Risk Management**: Çok katmanlı risk kontrolü
- **Real-time Monitoring**: Prometheus/Grafana ile canlı izleme

## 🏗️ Sistem Mimarisi

### Katmanlar
```
┌─────────────────────────────────────────┐
│           Infrastructure Layer          │
│  (Bootstrap, Logging, Monitoring)      │
├─────────────────────────────────────────┤
│            Application Layer            │
│  (Services, Jobs, Orchestrator)        │
├─────────────────────────────────────────┤
│              Domain Layer               │
│  (Models, Strategies, Events)          │
├─────────────────────────────────────────┤
│             Adapters Layer              │
│  (Exchange, News, Telegram, LLM)       │
└─────────────────────────────────────────┘
```

### Ana Bileşenler

#### 1. **Agent Sistemi**
- **Orchestrator Agent**: Ana koordinatör, karar verici
- **Technical Analyzer**: RSI, MACD, Bollinger Bands analizi
- **ML Agent**: Makine öğrenmesi tahminleri
- **News Agent**: Haber sentiment analizi
- **Risk Agent**: Risk değerlendirmesi
- **Execution Agent**: Emir yürütme

#### 2. **Veri Akışı (15 Dakika Döngüsü)**
```
Market Data → Technical Analysis → ML Prediction → News Analysis → Risk Assessment → Composite Score → Trading Decision → Order Execution → Position Management
```

#### 3. **Sinyal Bileşenleri**
- **Technical Analysis (40%)**: RSI, MACD, ADX, Bollinger Bands
- **Machine Learning (25%)**: Random Forest modeli ile tahmin
- **News Sentiment (20%)**: Kripto haberlerinin duygu analizi
- **Risk Score (15%)**: Pozisyon, korelasyon, volatilite riski

## 📊 Strateji Modları

### 1. **single_flip** (Varsayılan)
**Amaç**: Tek pozisyon, basit flip stratejisi

**Özellikler**:
- Aynı anda sadece 1 pozisyon
- `same_direction_block`: Aynı yönde tekrar giriş engeli
- `reversal_enabled`: Pozisyon tersine çevirme
- Position-level TP/SL (1+1): Her pozisyon için 1 TP + 1 SL
- `trailing modify-only`: Sadece mevcut emirleri güncelle

**Karar Kalkanları**:
- `once_per_bar`: Her bar'da sadece 1 karar
- `entry_cooldown_bars`: Giriş sonrası bekleme süresi
- `same_direction_block`: Aynı yönde tekrar giriş engeli
- `reversal`: Pozisyon tersine çevirme kontrolü

### 2. **scale_in** (Opsiyonel)
**Amaç**: Anti-martingale stratejisi ile pozisyon büyütme

**Özellikler**:
- `max_ladders`: Maksimum ekleme seviyesi (varsayılan: 2)
- `ladder_size_usdt`: Her ekleme miktarı (varsayılan: 5 USDT)
- `min_dist_pct`: Minimum mesafe yüzdesi (varsayılan: %0.5)
- `add_on_profit_only`: Sadece kârda ekleme
- Position-level TP/SL korunur

**Çalışma Mantığı**:
1. İlk pozisyon açılır
2. Kârda ise ve mesafe yeterli ise ekleme yapılır
3. Her ekleme önceki ortalama fiyattan en az %0.5 uzak olmalı
4. Maksimum 2 seviye ekleme yapılabilir

## 🛡️ Karar Kalkanları

### 1. **once_per_bar**
- Her 15 dakikalık bar'da sadece 1 karar
- Aynı bar içinde tekrar analiz yapılmaz
- Gereksiz işlemleri önler

### 2. **entry_cooldown_bars**
- Giriş sonrası 2 bar bekleme (30 dakika)
- Ardışık kayıplarda cooldown artar
- Aşırı işlem yapmayı engeller

### 3. **same_direction_block**
- Aynı yönde tekrar giriş engeli
- LONG pozisyondayken yeni LONG girişi yasak
- Sadece reversal veya exit'e izin verir

### 4. **reversal**
- Pozisyon tersine çevirme kontrolü
- Edge/cost ratio hesaplaması
- Sadece kârlı reversal'lara izin verir

### 5. **idempotent client_order_id**
- Aynı emir ID'si ile tekrar emir gönderilmez
- Duplicate emirleri önler
- `data/runtime_state.json`'da takip edilir

## 🎮 Çalışma Modları

### 1. **LIVE** (Gerçek Trading)
- Gerçek emirler gönderilir
- Gerçek para kullanılır
- **DİKKAT**: Sadece test edilmiş stratejilerle kullanın

### 2. **PAPER** (Sanal Trading)
- Sanal fill simülasyonu
- TP/SL ve trailing çalışır
- Gerçek para kullanılmaz
- **Güvenli test modu**

### 3. **DRY-RUN** (Analiz Only)
- Sadece analiz yapılır
- Hiç emir gönderilmez
- Sinyal kalitesini test eder

## 🔧 OKX Emir Mantığı

### Position-Level TP/SL
- **Neden**: Emir sayısını düşük tutmak
- **Nasıl**: Her pozisyon için 1 TP + 1 SL
- **Avantaj**: Daha az emir, daha az komisyon

### reduce_only
- **Neden**: Yeni pozisyon açmayı engeller
- **Nasıl**: TP/SL emirleri sadece mevcut pozisyonu kapatır
- **Güvenlik**: Yanlışlıkla yeni pozisyon açılmasını önler

### Partial TP/SL Neden Kapalı?
- **Karmaşıklık**: Çok fazla emir yönetimi
- **Maliyet**: Yüksek komisyon maliyeti
- **Risk**: Daha fazla hata riski
- **Basitlik**: Position-level daha basit ve güvenli

## 🤖 LLM/News Özeti

### Digest Sistemi
- **TTL**: 120 dakika cache süresi
- **Model**: GPT-5-nano (hızlı ve ucuz)
- **Rate-limit**: API limitlerini aşmamak için
- **Parse/Fallback**: Hata durumunda varsayılan değerler

### Çalışma Prensibi
1. Her 15 dakikada haber toplanır
2. LLM ile özetlenir ve skorlanır
3. Cache'de saklanır (120 dk)
4. Composite score'a dahil edilir

## 🚀 Hızlı Başlangıç

### 1. Gereksinimler
```bash
# Python 3.11+
# PowerShell 7+ (Windows)
# Git
```

### 2. Kurulum
```bash
git clone <repo>
cd ai-trade-bot
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Konfigürasyon
```bash
# .env dosyası oluştur
cp env.example .env
# API anahtarlarını düzenle
```

### 4. Test Çalıştırma
```powershell
# PowerShell
.\scripts\dev.ps1 -Start-Trading -Once -Mode PAPER

# Bash
./scripts/dev.sh start-trading-once PAPER
```

### 5. İzleme
```powershell
# Logları izle
.\scripts\dev.ps1 -Watch-Logs -Follow

# Health check
.\scripts\dev.ps1 -Test-Health
```

## 📈 Başlangıç Banner'ı

Sistem başlarken aktif değerleri gösterir:

```
[MODE] TRADING_MODE=PAPER STRATEGY_MODE=single_flip USE_POSITION_TPSL=true REDUCE_ONLY=true
[GATING] once_per_bar=true entry_cooldown_bars=2 same_direction_block=true reversal_enabled=true
[SOURCE] ENV → policy.yaml → default
```

## 🔍 Smoke Test Özeti

**Test Tarihi**: 2025-10-24 02:20:47  
**Mod**: PAPER (Güvenli Test)  
**Süre**: ~5 saniye (tek seferlik analiz)  
**Semboller**: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP

### ✅ Test Sonuçları

**Sistem Durumu**:
- Bot başarıyla çalıştı (exit code: 0)
- Prometheus metrics aktif (port 8000)
- Tüm bileşenler başlatıldı
- Konfigürasyon doğru yüklendi

**Analiz Sonuçları**:
- **BTC-USDT-SWAP**: Final skor 61.5 (LONG sinyali, gate pending)
- **ETH-USDT-SWAP**: Final skor 46.3 (FLAT, eşiğin altında)
- **SOL-USDT-SWAP**: Final skor 46.5 (FLAT, eşiğin altında)

**Skip Reason Örnekleri**:
- `once_per_bar`: Henüz bar işlenmedi
- `below_min_score`: ETH ve SOL skorları eşiğin altında
- `cooldown`: Henüz giriş yapılmadı

**Position-Level TP/SL**:
- `use_position_tpsl=true` aktif
- `reduce_only=true` aktif
- Pozisyon açılmadığı için TP/SL emri oluşturulmadı

**Güvenlik Kontrolü**:
- ✅ PAPER modu aktif (gerçek emir gönderilmedi)
- ✅ Risk limitleri aktif (max 1% pozisyon, 60% toplam risk)
- ✅ Gate kontrolleri aktif (persistence, confirmation, hysteresis)

**Performans**:
- Sistem başlatma: ~2 saniye
- Market data fetch: ~3 saniye (3 sembol)
- ML model loading: ~0.5 saniye
- Toplam analiz: ~5 saniye

**Sonuç**: Smoke test başarılı! Sistem PAPER modunda güvenli şekilde çalışıyor ve gerçek emir göndermiyor.

---

## 📚 Sonraki Adımlar

1. [RUN_GUIDE_CURRENT.md](RUN_GUIDE_CURRENT.md) - Detaylı çalıştırma rehberi
2. [ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md) - Sistem mimarisi
3. [OPERATIONS_PLAYBOOK.md](OPERATIONS_PLAYBOOK.md) - Operasyon pratikleri
4. [METRICS_CHEATSHEET.md](METRICS_CHEATSHEET.md) - Metrik rehberi
5. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Sorun giderme
6. [POLICY_REFERENCE.md](POLICY_REFERENCE.md) - Konfigürasyon referansı
