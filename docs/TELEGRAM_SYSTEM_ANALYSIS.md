# Telegram System Analysis - Detaylı Özet

## 📋 Genel Bakış

Projede **iki farklı Telegram sistemi** var:
1. **Eski Sistem:** `telegram_bot/bot.py` (kullanılmıyor)
2. **Yeni Sistem:** `adapters/telegram/` (aktif, kullanılıyor)

## 🔄 Telegram Sistem Akışı

### 1. Analysis Cards Flow (15 dakikalık özet kartları)

```
trading_analysis.py (15m job)
  ↓
analysis_cards.send_analysis_cards(analysis_results)
  ↓
analysis_cards_state.set_latest_analysis(bar_id, run_id, results)
  ↓
[State saklanır - in-memory]
  ↓
telegram_summary_15m.py (15m job)
  ↓
analysis_cards.publish_latest_summary()
  ↓
build_analysis_summary_view(context, formatter)
  ↓
TelegramClient.send_text_immediate() veya edit_message()
  ↓
[Telegram'a mesaj gönderilir/güncellenir]
```

### 2. Buton Tıklama Flow (Callback)

```
Kullanıcı butona tıklar (örn: "BTC 65.2")
  ↓
callback_data: "ai:an|s=BTC"
  ↓
TelegramHandlers.handle_callback()
  ↓
CallbackRegistry.resolve() (64 byte kontrolü)
  ↓
_parse_callback() → view_id='an', params={'s': 'BTC'}
  ↓
_build_view() → build_analysis_detail_view()
  ↓
ContextResolver.resolve_analysis_detail_context('BTC')
  ↓
analysis_cards_state.get_detail('BTC')
  ↓
build_analysis_detail_view(context, formatter)
  ↓
query.edit_message_text() (aynı mesajı günceller)
  ↓
[Detay görünümü gösterilir, "⬅️ Geri" butonu ile ana karta dönülür]
```

## 📁 Dosya Yapısı

### Adapters/Telegram (Yeni Sistem)

```
adapters/telegram/
├── client.py                    # TelegramClient (Application wrapper)
├── handlers.py                  # Command ve callback handler'ları
├── keyboards.py                 # Buton builder (64 byte kontrolü)
├── callback_registry.py         # Callback compression (64 byte limit)
├── context_resolver.py          # View'lar için veri çeker (real data)
├── state_manager.py             # Message state tracking (kullanılmıyor gibi)
├── inline_expander.py           # Accordion expansion (kullanılmıyor gibi)
├── formatter.py                 # Message formatter
├── middleware.py                # Rate limiting, error handling, metrics
└── views/                       # 10 farklı view builder
    ├── main.py                  # Ana dashboard
    ├── signals.py               # Trading signals
    ├── risk.py                  # Risk overview
    ├── orders.py                # Open orders
    ├── tp_sl.py                 # TP/SL brackets
    ├── trailing.py              # Trailing stops
    ├── pnl.py                   # P&L breakdown
    ├── settings.py              # User settings
    ├── positions.py             # Current positions
    └── analysis.py              # Analysis summary/detail (YENİ)
```

### Application (Analysis Cards)

```
application/
├── analysis_cards.py            # AnalysisCardsService (kartları gönderir)
├── analysis_cards_state.py      # Shared state (latest analysis snapshot)
└── jobs/
    └── telegram_summary_15m.py  # 15m job (özet kartı gönderir)
```

### Telegram Bot (Eski Sistem - KULLANILMIYOR)

```
telegram_bot/
├── bot.py                       # Eski TelegramBot (kullanılmıyor)
├── commands.py                  # Eski command handler'ları
└── keyboards.py                 # Eski keyboard builder
```

## 🎯 View Sistemi (10 View)

### 1. **Main View** (`build_main_view`)
- Ana dashboard
- Status, portfolio, risk, signals özeti
- Butonlar: Signals, Risk, Positions, Orders, PnL, Settings

### 2. **Signals View** (`build_signals_view`)
- Top 6 trading signals
- Symbol, score, grade, direction
- Butonlar: Symbol detayları, Geri

### 3. **Risk View** (`build_risk_view`)
- Risk exposure, tier allocation, limits, guards
- Butonlar: Geri

### 4. **Orders View** (`build_orders_view`)
- Open orders (paginated)
- Butonlar: Prev/Next, Geri

### 5. **TP/SL View** (`build_tpsl_view`)
- TP/SL brackets for positions
- Entry, SL, TP, R:R
- Butonlar: Geri

### 6. **Trailing View** (`build_trailing_view`)
- Trailing stops status
- Base SL, trail price, gain R
- Butonlar: Geri

### 7. **PnL View** (`build_pnl_view`)
- Balance, unrealized/realized PnL
- Position breakdown
- Butonlar: Geri

### 8. **Settings View** (`build_settings_view`)
- User preferences
- Compact mode, emojis, confirmations, timeframe
- Butonlar: Geri

### 9. **Positions View** (`build_positions_view`)
- Current open positions
- Symbol, side, size, entry, current, UPNL
- Butonlar: Geri

### 10. **Analysis View** (`build_analysis_summary_view`, `build_analysis_detail_view`)
- **Summary:** 15m analysis summary (tüm semboller)
- **Detail:** Symbol detay görünümü
- Butonlar: Symbol butonları (summary), Geri (detail)

## 🔘 Buton Sistemi

### Callback Schema: `ai:*`

```
ai:<view>|param1=value1|param2=value2
```

**Örnekler:**
- `ai:main` → Ana dashboard
- `ai:sig` → Signals view
- `ai:an` → Analysis summary
- `ai:an|s=BTC` → Analysis detail for BTC
- `ai:ord|p=1` → Orders view, page 1
- `ai:risk` → Risk view

### Callback Registry (64 Byte Limit)

- **Amaç:** Telegram callback data 64 byte limit
- **Çözüm:** Key shortening + base62 encoding
- **Örnek:** `ai:sig|sym=BTC` → `ai:sig|s=BTC` (key shortening)
- **Eğer hala >64 byte:** `cb0`, `cb1`, ... (base62 ID)

### Buton Layout

- **Max 8 rows**
- **3-5 buttons per row** (önerilen: 2-3)
- **Analysis summary:** Symbol butonları (2x2 grid), Refresh butonu
- **Analysis detail:** Geri butonu

## 🔄 Idempotency & State Management

### Analysis Cards State

- **Storage:** `application/analysis_cards_state.py` (in-memory)
- **Data:** `{bar_id, run_id, results, updated_at}`
- **Access:** `get_latest_analysis()`, `get_detail(symbol)`

### Message State (Analysis Cards)

- **Storage:** `AnalysisCardsService.summary_state` (in-memory)
- **Data:** `{message_id, bar_id, text, keyboard_signature}`
- **Purpose:** Edit message instead of sending new one

### Idempotency Checks

1. **Bar-level:** `is_bar_already_processed(job_id, '15m')`
2. **Message-level:** `summary_state['bar_id'] == current_bar_id`
3. **Content-level:** `summary_state['text'] == new_text && keyboard_signature == new_signature`

## 🚨 Kod Kopyaları ve Sorunlar

### 1. **İki Telegram Bot Sistemi**

**Eski Sistem (kullanılmıyor):**
- `telegram_bot/bot.py`
- `telegram_bot/commands.py`
- `telegram_bot/keyboards.py`

**Yeni Sistem (aktif):**
- `adapters/telegram/client.py`
- `adapters/telegram/handlers.py`
- `adapters/telegram/keyboards.py`

**Sorun:** Eski sistem hala kodda, kullanılmıyor ama import edilebiliyor.

### 2. **Runtime.py'de Eski Kod**

**Dosya:** `infrastructure/runtime.py:1383-1483`

**Fonksiyonlar:**
- `_send_telegram_analysis_card()` → Eski `telegram_bot.bot.TelegramBot` kullanıyor
- `_send_telegram_execution_card()` → Eski sistem kullanıyor
- `_send_telegram_error_card()` → Eski sistem kullanıyor

**Durum:** Bu fonksiyonlar çağrılmıyor (yeni sistem `analysis_cards.py` kullanıyor).

### 3. **Kullanılmayan Modüller**

**State Manager:** `adapters/telegram/state_manager.py`
- Message state tracking için
- **Durum:** Analysis cards kendi state'ini yönetiyor, bu modül kullanılmıyor

**Inline Expander:** `adapters/telegram/inline_expander.py`
- Accordion-style expansion için
- **Durum:** Kullanılmıyor, view'lar direkt değişiyor

### 4. **Duplicate Functionality**

**Analysis Cards:**
- `application/analysis_cards.py` → Kartları gönderir
- `adapters/telegram/views/analysis.py` → View'ları build eder
- **Sorun:** İki farklı yerde analysis kartları var gibi görünüyor, ama aslında birbirini tamamlıyor.

## ✅ Çalışan Sistem

### Analysis Cards (15m Özet)

1. **Trading Analysis Job** (`trading_analysis.py`)
   - Analysis yapar
   - `analysis_cards.send_analysis_cards()` çağırır
   - State'e kaydeder

2. **Telegram Summary Job** (`telegram_summary_15m.py`)
   - 15 dakikada bir çalışır
   - `analysis_cards.publish_latest_summary()` çağırır
   - Telegram'a özet kartı gönderir/günceller

3. **Buton Tıklama**
   - Kullanıcı symbol butonuna tıklar
   - `handlers.handle_callback()` → `build_analysis_detail_view()`
   - Mesaj `edit_message()` ile güncellenir
   - "⬅️ Geri" butonu ile ana karta dönülür

### View System (Interaktif Komutlar)

1. **Command Handler'lar:** `/start`, `/help`, `/portfolio`, `/positions`, `/risk`, `/health`
2. **Callback Handler'lar:** `ai:*` schema ile routing
3. **Context Resolver:** Real data çeker (exchange, portfolio, risk, etc.)
4. **View Builders:** 10 farklı view (main, signals, risk, orders, tp_sl, trailing, pnl, settings, positions, analysis)

## 🔧 Önerilen İyileştirmeler

### 1. **Eski Kodları Temizle**

- `infrastructure/runtime.py` → `_send_telegram_*` fonksiyonlarını kaldır
- `telegram_bot/` klasörünü kaldır (veya deprecated olarak işaretle)
- `adapters/telegram/state_manager.py` ve `inline_expander.py` kullanılmıyorsa kaldır

### 2. **Kod Tekrarlarını Azalt**

- Analysis cards ve view system'i birleştir (zaten birbirini tamamlıyor)
- Context resolver'ı tek bir yerden yönet

### 3. **Dokümantasyon**

- View system'i dokümante et
- Callback schema'yı dokümante et
- Analysis cards flow'unu dokümante et

## 📊 Özet Tablo

| Özellik | Eski Sistem | Yeni Sistem | Durum |
|---------|-------------|-------------|-------|
| Bot | `telegram_bot/bot.py` | `adapters/telegram/client.py` | ✅ Yeni aktif |
| Handlers | `telegram_bot/commands.py` | `adapters/telegram/handlers.py` | ✅ Yeni aktif |
| Keyboards | `telegram_bot/keyboards.py` | `adapters/telegram/keyboards.py` | ✅ Yeni aktif |
| Views | Yok | `adapters/telegram/views/` | ✅ 10 view |
| Analysis Cards | Yok | `application/analysis_cards.py` | ✅ Aktif |
| Callback Registry | Yok | `adapters/telegram/callback_registry.py` | ✅ Aktif |
| Context Resolver | Yok | `adapters/telegram/context_resolver.py` | ✅ Aktif |
| State Manager | Yok | `adapters/telegram/state_manager.py` | ❌ Kullanılmıyor |
| Inline Expander | Yok | `adapters/telegram/inline_expander.py` | ❌ Kullanılmıyor |

## 🎯 Sonuç

**Çalışan Sistem:**
- ✅ Yeni Telegram sistemi (`adapters/telegram/`) aktif ve çalışıyor
- ✅ Analysis cards 15m job ile gönderiliyor
- ✅ Butonlar çalışıyor, callback routing çalışıyor
- ✅ 10 farklı view mevcut ve çalışıyor

**Sorunlar:**
- ❌ Eski sistem (`telegram_bot/`) hala kodda, kullanılmıyor
- ❌ `runtime.py`'de eski telegram fonksiyonları var, kullanılmıyor
- ❌ Bazı modüller (state_manager, inline_expander) kullanılmıyor
- ❌ Kod kopyaları var, temizlenmeli

**Öneriler:**
1. Eski kodları temizle
2. Kullanılmayan modülleri kaldır
3. Dokümantasyon ekle
4. Kod tekrarlarını azalt

