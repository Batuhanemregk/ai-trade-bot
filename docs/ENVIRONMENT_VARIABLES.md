# Environment Variables Açıklaması

## PYTHONPATH

### Ne İşe Yarar?
Python'un modül import path'ini belirler. Proje kök dizinini Python'a tanıtır.

### Neden Gerekli?
Kodda şu şekilde import'lar var:
```python
from infrastructure.bootstrap import load_env
from application.jobs.trading_analysis import TradingAnalysisJob
```

Python bu modülleri bulmak için proje kök dizinini (`ai-trade-bot/`) import path'ine eklemelidir.

### PowerShell'de Kullanımı:
```powershell
$env:PYTHONPATH = "$PWD"  # Mevcut dizin
# Veya
$env:PYTHONPATH = "C:\Users\batuhan\Desktop\ai_bot_trader\ai-trade-bot"
```

### Alternatif Çözümler:

#### 1. Python Modülü Olarak Çalıştırma (ÖNERİLEN):
```powershell
# PYTHONPATH'e gerek yok!
python -m infrastructure.scheduler_runner
```

#### 2. sys.path'e Ekleme (Kod İçinde):
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

#### 3. setup.py veya pyproject.toml ile Kurulum:
```bash
pip install -e .
```

## PYTHONIOENCODING

### Ne İşe Yarar?
Python'un stdout/stderr encoding'ini belirler. Windows'ta UTF-8 karakterlerin doğru gösterilmesi için gereklidir.

### Neden Gerekli?
- Windows'ta Python varsayılan olarak sistem kod sayfasını kullanır (cp1252)
- Emojiler ve Türkçe karakterler bozulabilir
- Loglarda `📊` yerine `Y"S` görünebilir

### PowerShell'de Kullanımı:
```powershell
$env:PYTHONIOENCODING = "utf-8"
```

### Alternatif Çözümler:

#### 1. Python 3.7+ UTF-8 Modu:
```powershell
$env:PYTHONUTF8 = "1"  # Python 3.7+
```

#### 2. PowerShell Console Encoding:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001  # UTF-8 kod sayfası
```

#### 3. Kod İçinde Encoding:
```python
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

## Önerilen Kullanım

### PowerShell Script (start_bot.ps1):
```powershell
# Proje kök dizinine git
Set-Location "C:\Users\batuhan\Desktop\ai_bot_trader\ai-trade-bot"

# Environment variables ayarla
$env:PYTHONPATH = $PWD
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Console encoding ayarla
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

# Python modülü olarak çalıştır (PYTHONPATH'e gerek yok!)
python -m infrastructure.scheduler_runner
```

### En İyi Pratik: Python Modülü Kullanımı
```powershell
# PYTHONPATH'e GEREK YOK!
python -m infrastructure.scheduler_runner
```

Bu yöntem daha temiz ve taşınabilir. Python otomatik olarak proje kök dizinini bulur.

## VS Code Launch Configuration

`.vscode/launch.json` içinde zaten ayarlanmış:
```json
{
    "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "PYTHONIOENCODING": "utf-8"
    }
}
```

## Özet

| Değişken | Gerekli Mi? | Alternatif |
|----------|-------------|------------|
| `PYTHONPATH` | Evet (dosya olarak çalıştırıyorsan) | `python -m infrastructure.scheduler_runner` kullan |
| `PYTHONIOENCODING` | Evet (Windows'ta) | `PYTHONUTF8=1` veya console encoding |

## Sonuç

**En iyi çözüm:** `python -m infrastructure.scheduler_runner` kullanmak. Bu durumda `PYTHONPATH`'e gerek yok, sadece `PYTHONIOENCODING="utf-8"` yeterli.

