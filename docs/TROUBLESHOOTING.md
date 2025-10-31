# AiBotBS Sorun Giderme Rehberi

> **Yaygın sorunlar ve çözümleri için kapsamlı rehber**

## 🚨 Acil Durum Sorunları

### Bot Çöktü
**Belirtiler**: Process çalışmıyor, log'lar durdu, metrics yanıt vermiyor

**Hızlı Çözüm**:
```bash
# Process'i kontrol et
ps aux | grep python | grep scheduler

# Yeniden başlat
./scripts/dev.sh start-scheduler

# Health check
./scripts/dev.sh test-health
```

**Detaylı Çözüm**:
1. Log dosyalarını kontrol et: `tail -100 logs/trading.log`
2. Hata mesajlarını analiz et
3. Gerekirse state'i temizle: `rm -f data/runtime_state.json`
4. Bot'u yeniden başlat

### Pozisyon Takıldı
**Belirtiler**: Pozisyon açıldı ama kapanmıyor, TP/SL çalışmıyor

**Hızlı Çözüm**:
```bash
# Pozisyon durumunu kontrol et
curl http://localhost:8000/metrics | grep aibot_positions

# Manuel pozisyon kapatma (gerekirse)
# Exchange'den manuel kapatma yapılmalı
```

**Detaylı Çözüm**:
1. Pozisyon state'ini kontrol et: `cat data/position_state.json`
2. Exchange'de pozisyon durumunu kontrol et
3. TP/SL emirlerini kontrol et
4. Gerekirse manuel kapatma yap

## 🔍 Yaygın Sorunlar

### 1. **"Hiç OPEN olmuyor"**

#### Olası Nedenler:
- **Gating**: `once_per_bar`, `cooldown`, `same_direction_block`
- **Skor**: `below_min_score` (skor eşiğin altında)
- **Risk**: Risk limitleri aşıldı
- **Veri**: Yetersiz market data

#### Çözüm Adımları:

**1. Skip Reason'ları Kontrol Et**:
```bash
# Son skip'leri görüntüle
grep "SKIP" logs/trading.log | tail -20

# En yaygın skip nedenleri
grep "SKIP" logs/trading.log | cut -d: -f3 | sort | uniq -c | sort -nr
```

**2. Skorları Kontrol Et**:
```bash
# Mevcut skorları görüntüle
curl http://localhost:8000/metrics | grep aibot_composite_score

# Skor eşiklerini kontrol et
grep "decision_thresholds" configs/policy.yaml
```

**3. Risk Durumunu Kontrol Et**:
```bash
# Risk metriklerini kontrol et
curl http://localhost:8000/metrics | grep aibot_risk

# Maruziyet durumunu kontrol et
curl http://localhost:8000/metrics | grep aibot_exposure
```

**4. Veri Kalitesini Kontrol Et**:
```bash
# Market data durumunu kontrol et
grep "OHLCV" logs/trading.log | tail -10

# API bağlantısını kontrol et
grep "exchange" logs/trading.log | tail -10
```

### 2. **"TP/SL Patladı"**

#### Olası Nedenler:
- **Partial TP/SL Kapalı**: Position-level TP/SL kullanılıyor
- **Position-level Aktif Değil**: `use_position_tpsl=false`
- **Idempotency Sorunu**: Aynı emir ID'si tekrar gönderildi
- **Reduce-only Kontrolü**: `reduce_only=true` ayarı

#### Çözüm Adımları:

**1. TP/SL Ayarlarını Kontrol Et**:
```bash
# Policy'de TP/SL ayarlarını kontrol et
grep -A 10 "position_management" configs/policy.yaml

# Position-level TP/SL aktif mi?
grep "use_position_tpsl" configs/policy.yaml
```

**2. Emir Durumunu Kontrol Et**:
```bash
# TP/SL emirlerini kontrol et
grep "TP/SL" logs/trading.log | tail -20

# Emir hatalarını kontrol et
grep "order.*error" logs/trading.log | tail -10
```

**3. Idempotency Kontrolü**:
```bash
# Runtime state'i kontrol et
cat data/runtime_state.json | grep -A 5 "orders"

# Duplicate emir ID'lerini kontrol et
grep "duplicate.*order" logs/trading.log
```

### 3. **"Prometheus Boş"**

#### Olası Nedenler:
- **Exporter Çalışmıyor**: Metrics server başlamadı
- **Port Sorunu**: 8000 portu kullanımda
- **Firewall**: Port erişimi engellenmiş
- **Scrape Job**: Prometheus scrape job yanlış

#### Çözüm Adımları:

**1. Exporter Durumunu Kontrol Et**:
```bash
# Metrics endpoint'i test et
curl http://localhost:8000/metrics

# Process'i kontrol et
ps aux | grep prometheus
```

**2. Port Kontrolü**:
```bash
# Port kullanımını kontrol et
netstat -tlnp | grep 8000

# Farklı port dene
curl http://localhost:8001/metrics
```

**3. Prometheus Konfigürasyonu**:
```yaml
# prometheus.yml kontrol et
scrape_configs:
  - job_name: 'aibot'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
```

**4. Firewall Kontrolü**:
```bash
# Windows
netsh advfirewall firewall show rule name="Port 8000"

# Linux
sudo ufw status | grep 8000
```

### 4. **"Unicode/Emoji Görünmüyor (Windows)"**

#### Olası Nedenler:
- **Terminal Encoding**: UTF-8 desteği yok
- **PowerShell Version**: Eski PowerShell sürümü
- **Environment Variables**: UTF-8 değişkenleri ayarlanmamış

#### Çözüm Adımları:

**1. Environment Variables Ayarla**:
```powershell
# PowerShell'de
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LANG = "C.UTF-8"

# Kalıcı olarak ayarla
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
[Environment]::SetEnvironmentVariable("PYTHONIOENCODING", "utf-8", "User")
```

**2. Terminal Encoding Ayarla**:
```powershell
# Code page'i UTF-8 yap
chcp 65001

# PowerShell encoding'i ayarla
$OutputEncoding = [System.Text.UTF8Encoding]::new()
```

**3. PowerShell 7+ Kullan**:
```powershell
# PowerShell 7+ yükle
winget install Microsoft.PowerShell

# PowerShell 7 ile çalıştır
pwsh -File scripts/dev.ps1 -Start-Trading -Once
```

**4. Terminal Seçimi**:
- **Windows Terminal** kullan (önerilen)
- **VS Code Terminal** kullan
- **Git Bash** kullan

### 5. **"Windows Sinyalleri"**

#### Olası Nedenler:
- **pywin32 Eksik**: Windows signal handling yok
- **Graceful Fallback**: Signal handling devre dışı
- **Process Termination**: Ctrl+C çalışmıyor

#### Çözüm Adımları:

**1. pywin32 Yükle**:
```bash
# pywin32 yükle
pip install pywin32

# Veya requirements.txt'e ekle
echo "pywin32" >> requirements.txt
pip install -r requirements.txt
```

**2. Graceful Fallback Kontrolü**:
```python
# Signal handling kontrol et
import signal
import sys

def signal_handler(sig, frame):
    print('Graceful shutdown...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
```

**3. Process Termination**:
```bash
# Process'i manuel durdur
taskkill /F /IM python.exe

# Veya PowerShell ile
Get-Process python | Stop-Process -Force
```

## 🔧 Sistem Sorunları

### 1. **Memory Kullanımı Yüksek**

**Belirtiler**: Yavaş performans, memory warning'leri

**Çözüm**:
```bash
# Memory kullanımını kontrol et
ps aux | grep python | awk '{print $4, $11}'

# Cache'i temizle
rm -rf data/cache/*

# Log dosyalarını temizle
find logs/ -name "*.log" -mtime +7 -delete
```

### 2. **Disk Alanı Dolu**

**Belirtiler**: Log yazma hatası, state kaydetme hatası

**Çözüm**:
```bash
# Disk kullanımını kontrol et
df -h

# Büyük dosyaları bul
find . -type f -size +100M

# Log rotation ayarla
# configs/logging.yaml'da max_size ve backup_count ayarla
```

### 3. **API Rate Limit**

**Belirtiler**: API hataları, 429 status code

**Çözüm**:
```bash
# Rate limit hatalarını kontrol et
grep "429" logs/trading.log

# API çağrı oranını azalt
# configs/policy.yaml'da rate_limit ayarlarını düzenle
```

### 4. **Database Lock**

**Belirtiler**: SQLite lock hatası, state kaydetme hatası

**Çözüm**:
```bash
# Database lock'u kontrol et
lsof data/*.db

# Process'i durdur ve yeniden başlat
./scripts/dev.sh stop-bot
./scripts/dev.sh start-scheduler
```

## 📊 Debug Komutları

### 1. **Sistem Durumu**
```bash
# Health check
./scripts/dev.sh test-health

# Process durumu
ps aux | grep python

# Port durumu
netstat -tlnp | grep -E "(8000|9090|3000)"
```

### 2. **Log Analizi**
```bash
# Son hatalar
grep "ERROR\|CRITICAL" logs/trading.log | tail -20

# Belirli sembol için log
grep "BTC-USDT-SWAP" logs/trading.log | tail -20

# Skip reason'ları
grep "SKIP" logs/trading.log | cut -d: -f3 | sort | uniq -c
```

### 3. **Metrics Analizi**
```bash
# Tüm metrikler
curl http://localhost:8000/metrics

# Belirli metrikler
curl http://localhost:8000/metrics | grep aibot_trading

# Prometheus query
curl "http://localhost:9090/api/v1/query?query=aibot_positions_open"
```

### 4. **State Kontrolü**
```bash
# Runtime state
cat data/runtime_state.json

# Position state
cat data/position_state.json

# News digest
cat data/news_llm_digest.json
```

## 🚨 Acil Durum Komutları

### Bot Durdurma
```bash
# Graceful shutdown
pkill -TERM -f "infrastructure.scheduler_runner"

# Force kill
pkill -KILL -f "infrastructure.scheduler_runner"

# Windows
taskkill /F /IM python.exe
```

### State Reset
```bash
# Runtime state'i temizle
rm -f data/runtime_state.json

# Position state'i temizle
rm -f data/position_state.json

# Tüm state'i temizle
rm -rf data/*.json
```

### Log Temizleme
```bash
# Log dosyalarını temizle
rm -f logs/*.log

# Eski log'ları temizle
find logs/ -name "*.log" -mtime +7 -delete
```

### Cache Temizleme
```bash
# Cache'i temizle
rm -rf data/cache/*

# News cache'i temizle
rm -f data/news_*.json
```

## 📞 Destek ve Kaynaklar

### 1. **Log Dosyaları**
- `logs/trading.log`: Ana trading log'u
- `logs/error.log`: Hata log'ları
- `logs/debug.log`: Debug log'ları

### 2. **State Dosyaları**
- `data/runtime_state.json`: Runtime state
- `data/position_state.json`: Pozisyon state'i
- `data/news_llm_digest.json`: News digest

### 3. **Konfigürasyon Dosyaları**
- `configs/policy.yaml`: Ana konfigürasyon
- `configs/logging.yaml`: Logging ayarları
- `.env`: Environment variables

### 4. **Monitoring**
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Metrics**: http://localhost:8000/metrics

## 📚 Sonraki Adımlar

1. [POLICY_REFERENCE.md](POLICY_REFERENCE.md) - Konfigürasyon referansı
2. [OPERATIONS_PLAYBOOK.md](OPERATIONS_PLAYBOOK.md) - Operasyon pratikleri
3. [METRICS_CHEATSHEET.md](METRICS_CHEATSHEET.md) - Metrik rehberi

