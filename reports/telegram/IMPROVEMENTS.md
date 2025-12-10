# Telegram UI İyileştirme Önerileri

## En Yüksek Getiri / En Az Risk

### 🚀 Hemen Yap (Quick Wins)

| # | Öneri | Dosya | Effort | Etki |
|---|-------|-------|--------|------|
| 1 | **persist_max policy'den oku** | `views/signals.py:47` | 5 dk | Doğru değer |
| 2 | **Signals 6→4 sembol** | `views/signals.py:36` | 1 dk | Mesaj boyutu %30↓ |
| 3 | **Message truncation 3500** | `formatter.py` | 15 dk | API hatası önle |

```python
# signals.py:36 değişiklik
for signal in signals[:4]:  # 6'dan 4'e düşür
```

```python
# formatter.py yeni fonksiyon
def truncate_message(text: str, max_bytes: int = 3500) -> str:
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text
    truncated = encoded[:max_bytes-20].decode('utf-8', errors='ignore')
    return truncated + "\n\n(+more…)"
```

---

### 📦 Sonra Yap (Medium Term)

| # | Öneri | Dosya | Effort | Etki |
|---|-------|-------|--------|------|
| 4 | **View-local cache (15sn)** | `context_resolver.py` | 1 saat | Performans %50↑ |
| 5 | **context_resolver bölme** | `context_resolver.py` | 2 saat | Maintainability |
| 6 | **Compact mode footer** | `formatter.py` | 30 dk | UX temiz |
| 7 | **Emoji toggle uygulama** | `views/*.py` | 1 saat | Accessibility |

```python
# View-local cache örneği
from functools import lru_cache
from datetime import datetime

_cache = {}
_cache_ttl = 15  # saniye

def get_cached_context(view: str, key: str):
    cache_key = f"{view}:{key}"
    if cache_key in _cache:
        data, timestamp = _cache[cache_key]
        if (datetime.now() - timestamp).seconds < _cache_ttl:
            return data
    return None

def set_cached_context(view: str, key: str, data: dict):
    cache_key = f"{view}:{key}"
    _cache[cache_key] = (data, datetime.now())
```

---

### 🔮 Vazgeç / Ertele

| # | Öneri | Neden Vazgeç |
|---|-------|--------------|
| 8 | Inline expander tam uygulama | Karmaşık, düşük ROI |
| 9 | WebSocket live updates | Overkill, polling yeterli |
| 10 | Multi-language support | Kullanıcı tek kişi |

---

## Buton Yoğunluğu Optimizasyonu

### Şu An (main.py)
```python
# 2 row × 4 buttons = 8 toplam ✅ İYİ
buttons = [
    ["Signals", "Risk", "Positions", "Orders"],  # 4
    ["PnL", "TP/SL", "Trailing", "Settings"]      # 4
]
```

### Öneri: 3 row × 3 buttons (daha okunabilir)
```python
buttons = [
    ["📡 Signals", "⚠️ Risk", "📊 Positions"],
    ["📋 Orders", "💰 PnL", "🎯 TP/SL"],
    ["📈 Trailing", "⚙️ Settings", "🔄 Refresh"]
]
```

---

## Tablo/Monospace Hizalaması

### Şu An (signals.py)
```
📈🟢 BTCUSDT
   🟩🟩🟩 Score 65.8 ⭐B
   📊 TA 60 | 🤖 ML 70 | 📰 News 55 | ⚠️ Risk 45
```

### Öneri: Monospace tablo
```
📈🟢 BTCUSDT          65.8 (B)
   TA:60 ML:70 News:55 Risk:45
   P:2/2 Age:3/6 Hyst:ok
```

**Avantaj:** Daha kompakt, aynı bilgi, %40 az karakter.

---

## Özet: Öncelik Sırası

1. ✅ **persist_max fix** - 5 dk, kritik doğruluk
2. ✅ **Signals 4 sembol** - 1 dk, boyut azaltma
3. ✅ **Message truncation** - 15 dk, hata önleme
4. 📦 **View cache** - 1 saat, performans
5. 📦 **Compact mode** - 30 dk, UX
6. 📦 **context_resolver split** - 2 saat, maintainability

**Toplam Quick Win süresi: ~20 dakika**
