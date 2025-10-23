# UTF-8 / Emoji Kodlama Rehberi
**Created:** 2025-10-21  
**Purpose:** Kapsamlı UTF-8/Unicode/emoji desteği rehberi

## 📋 İçindekiler

1. [Sorunun Kök Nedeni](#sorunun-kök-nedeni)
2. [Kalıcı Çözüm](#kalıcı-çözüm)
3. [Ortam Konfigürasyonu](#ortam-konfigürasyonu)
4. [PowerShell vs Bash](#powershell-vs-bash)
5. [Terminal ve Font Önerileri](#terminal-ve-font-önerileri)
6. [Troubleshooting](#troubleshooting)
7. [Test ve Doğrulama](#test-ve-doğrulama)
8. [CI/CD Entegrasyonu](#cicd-entegrasyonu)

## 🔍 Sorunun Kök Nedeni

### Windows Console Encoding Sorunu
- **Varsayılan Encoding:** Windows PowerShell/CMD `cp1254` (Türkçe) veya `cp1252` (İngilizce) kullanır
- **Emoji Karakterleri:** Unicode UTF-8 karakterleri (`🚀`, `✅`, `❌`, vb.)
- **Uyumsuzluk:** `cp1254` encoding emoji karakterlerini desteklemez
- **Hata:** `UnicodeEncodeError: 'charmap' codec can't encode character`

### Python Encoding Sorunu
- **Varsayılan:** Python varsayılan sistem encoding'ini kullanır
- **Windows:** `cp1254` veya `cp1252`
- **Linux/macOS:** `UTF-8` (genellikle)
- **Docker:** Container locale ayarlarına bağlı

## ✅ Kalıcı Çözüm

### 1. Ortam Değişkenleri
```bash
# Temel UTF-8 ayarları
PYTHONUTF8=1
PYTHONIOENCODING=utf-8
LANG=C.UTF-8
LC_ALL=C.UTF-8

# Opsiyonel emoji kontrolü
LOG_USE_EMOJI=true
```

### 2. Python Kod Seviyesi
```python
# configs/utf8_config.py
import os
import sys

def setup_utf8_environment():
    """Setup UTF-8 environment variables and stdout/stderr configuration."""
    os.environ.setdefault('PYTHONUTF8', '1')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    os.environ.setdefault('LANG', 'C.UTF-8')
    
    # Configure stdout/stderr for UTF-8 (Python 3.7+)
    if sys.version_info >= (3, 7):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception as e:
            print(f"Warning: Could not reconfigure stdout/stderr: {e}")
```

### 3. Logger Konfigürasyonu
```python
# infrastructure/logger.py
# Tüm file handler'larda encoding='utf-8' zorunlu
file_handler = logging.FileHandler(file_path, encoding="utf-8")

# Loguru zaten UTF-8 kullanır
logger.add("file.log", encoding="utf-8")
```

### 4. JSON/CSV İşlemleri
```python
# JSON
json.dump(data, file, ensure_ascii=False, indent=2)

# CSV
with open(file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
```

## 🖥️ Ortam Konfigürasyonu

### Windows PowerShell
```powershell
# scripts/dev.ps1
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:LANG = "C.UTF-8"

# Console encoding
chcp 65001 | Out-Null
$OutputEncoding = [System.Text.UTF8Encoding]::new()
```

### Linux/macOS Bash
```bash
# scripts/dev.sh
export PYTHONUTF8="1"
export PYTHONIOENCODING="utf-8"
export LANG="C.UTF-8"
export LC_ALL="C.UTF-8"
```

### Docker
```dockerfile
# Dockerfile
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUTF8=1
ENV PYTHONIOENCODING=utf-8
```

```yaml
# docker-compose.yml
environment:
  - LANG=C.UTF-8
  - LC_ALL=C.UTF-8
  - PYTHONUTF8=1
  - PYTHONIOENCODING=utf-8
```

## 🔧 PowerShell vs Bash

### PowerShell 5 vs PowerShell 7
- **PowerShell 5:** Windows PowerShell, eski encoding sistemi
- **PowerShell 7:** PowerShell Core, daha iyi UTF-8 desteği
- **Öneri:** PowerShell 7 + Windows Terminal kullanın

### Windows Terminal
- **Avantajlar:** Modern UTF-8 desteği, emoji desteği
- **Kurulum:** Microsoft Store'dan "Windows Terminal"
- **Font:** Cascadia Code veya Segoe UI Emoji

### Bash (WSL/Git Bash)
- **WSL:** Linux subsystem, native UTF-8
- **Git Bash:** MinGW, UTF-8 desteği var
- **Öneri:** WSL2 kullanın

## 🎨 Terminal ve Font Önerileri

### Önerilen Fontlar
1. **Cascadia Code** - Microsoft'un geliştirdiği, emoji desteği
2. **Segoe UI Emoji** - Windows emoji fontu
3. **Fira Code** - Ligature desteği
4. **JetBrains Mono** - IDE fontu

### Terminal Ayarları
```json
// Windows Terminal settings.json
{
    "profiles": {
        "defaults": {
            "fontFace": "Cascadia Code",
            "fontSize": 12
        }
    }
}
```

## 🛠️ Troubleshooting

### "Hâlâ Bozuksa" Kontrol Listesi

1. **Ortam Değişkenleri:**
   ```bash
   echo $PYTHONUTF8        # 1 olmalı
   echo $PYTHONIOENCODING  # utf-8 olmalı
   echo $LANG             # C.UTF-8 olmalı
   ```

2. **Console Encoding:**
   ```powershell
   chcp 65001  # Windows
   locale      # Linux
   ```

3. **Python Encoding:**
   ```python
   import sys
   print(sys.stdout.encoding)  # utf-8 olmalı
   print(sys.stderr.encoding)  # utf-8 olmalı
   ```

4. **Font Kontrolü:**
   - Terminal font'u emoji destekli mi?
   - Windows Terminal kullanıyor musunuz?

5. **Log Dosyası Encoding:**
   ```bash
   file logs/bot.log  # UTF-8 olmalı
   ```

### Yaygın Hatalar

#### UnicodeEncodeError
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'
```
**Çözüm:** `PYTHONIOENCODING=utf-8` ayarlayın

#### Emoji Görünmüyor
```
[?] Test message
```
**Çözüm:** Terminal font'unu değiştirin (Cascadia Code)

#### Log Dosyası Bozuk
```
Test: ðŸš€ðŸŸ¢âš ï¸ðŸŒ
```
**Çözüm:** Logger'da `encoding='utf-8'` kullanın

## 🧪 Test ve Doğrulama

### Otomatik Test
```bash
# UTF-8 round-trip test
python tests/smoke/test_utf8_roundtrip.py

# Pytest ile
pytest tests/smoke/test_utf8_roundtrip.py -v
```

### Manuel Test
```python
# Test script
python -c "
import sys
print('🚀🟢⚠️❌✅📊💾🎯')
print('Türkçe: ğüşıöç')
print('Русский: йцукен')
print('中文: 你好世界')
print(f'Encoding: {sys.stdout.encoding}')
"
```

### Log Test
```python
from loguru import logger
logger.info("🚀 Test message with emoji")
logger.warning("⚠️ Warning with Unicode: Türkçe")
```

## 🔄 CI/CD Entegrasyonu

### GitHub Actions
```yaml
# .github/workflows/test.yml
- name: Test UTF-8 Support
  run: |
    export PYTHONUTF8=1
    export PYTHONIOENCODING=utf-8
    export LANG=C.UTF-8
    python tests/smoke/test_utf8_roundtrip.py
```

### Docker CI
```dockerfile
# Test stage
FROM python:3.11-slim
ENV LANG=C.UTF-8 PYTHONUTF8=1 PYTHONIOENCODING=utf-8
RUN python tests/smoke/test_utf8_roundtrip.py
```

### Local CI
```bash
# scripts/test_utf8.sh
#!/bin/bash
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
python tests/smoke/test_utf8_roundtrip.py
```

## 📊 Performans ve Optimizasyon

### Encoding Overhead
- **UTF-8:** Minimal overhead, modern standart
- **Emoji:** 4-byte UTF-8 karakterler
- **Log Dosyaları:** ~10-15% daha büyük

### Öneriler
1. **Log Rotation:** UTF-8 dosyaları daha büyük olabilir
2. **Compression:** Gzip ile sıkıştırma etkili
3. **Caching:** Unicode string'leri cache'leyin

## 🔒 Güvenlik Notları

### Log Redaction
```python
# Hassas verileri emoji ile maskeleyin
def redact_sensitive_data(text):
    return text.replace("API_KEY", "🔑")
```

### File Permissions
```bash
# Log dosyalarını güvenli tutun
chmod 600 logs/*.log
```

## 📚 Kaynaklar

- [Python Unicode HOWTO](https://docs.python.org/3/howto/unicode.html)
- [UTF-8 Everywhere](https://utf8everywhere.org/)
- [Windows Terminal](https://github.com/microsoft/terminal)
- [PowerShell 7](https://github.com/PowerShell/PowerShell)

## 🆘 Destek

### Hâlâ Sorun Var mı?

1. **Test Çalıştırın:**
   ```bash
   python tests/smoke/test_utf8_roundtrip.py
   ```

2. **Ortam Kontrolü:**
   ```bash
   python -c "import sys, os; print(f'Python: {sys.version}'); print(f'Encoding: {sys.stdout.encoding}'); print(f'Env: {os.environ.get(\"PYTHONIOENCODING\")}')"
   ```

3. **Log Kontrolü:**
   ```bash
   tail -f logs/bot.log | grep -E "🚀|✅|❌"
   ```

4. **Issue Açın:** GitHub'da issue açın ve test sonuçlarını ekleyin

---

**Son Güncelleme:** 2025-10-21  
**Versiyon:** 1.0.0  
**Durum:** ✅ Tamamlandı


