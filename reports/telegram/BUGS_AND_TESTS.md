# Telegram Bugs & Test Plan

## İlk 10 Kritik Sorun

### 1. 🔴 ContextResolver Çok Büyük (38KB)
- **Dosya:** `adapters/telegram/context_resolver.py`
- **Repro:** Her callback'te tüm 38KB parse ediliyor
- **Beklenen:** Lazy load, bölünmüş resolver'lar
- **Gerçek:** Monolitik, memory pressure

### 2. 🔴 Unclosed Client Session Uyarıları
- **Dosya:** Bot shutdown logs
- **Repro:** Ctrl+C ile çıkış
- **Beklenen:** Clean shutdown, no warnings
- **Gerçek:** `Unclosed client session` uyarıları

### 3. 🟡 Signals View persist_max Hardcoded
- **Dosya:** `adapters/telegram/views/signals.py:47-51`
- **Repro:** View'da persist 5/5 gösterir ama policy 2
- **Beklenen:** Policy'den oku (`persistence_bars: 2`)
- **Gerçek:** Hardcoded `persist_max=5`

### 4. 🟡 Message Size 3500 Limiti Kontrol Yok
- **Dosya:** Tüm view builders
- **Repro:** 6+ pozisyon veya order ile
- **Beklenen:** `(+more…)` ile kesilme
- **Gerçek:** Telegram API hatası riski

### 5. 🟡 Footer Her Mesajda Tekrar
- **Dosya:** `adapters/telegram/formatter.py`
- **Repro:** Her view switch
- **Beklenen:** Compact mode seçeneği
- **Gerçek:** Her zaman footer ekleniyor

### 6. 🟢 View-Local Cache Yok
- **Dosya:** `context_resolver.py`
- **Repro:** Aynı view'ı 2x açma
- **Beklenen:** 5-15sn cache
- **Gerçek:** Her seferinde fresh fetch

### 7. 🟢 Emoji Toggle Eksik
- **Dosya:** `adapters/telegram/views/settings.py`
- **Repro:** Settings view'da emojis toggle var ama çalışmıyor
- **Beklenen:** Toggle'ı uygula
- **Gerçek:** UI'da var, backend'de yok

### 8. 🟢 Orders/Positions Pagination Kapasitesi
- **Dosya:** `orders.py`, `positions.py`
- **Repro:** 10+ order ile
- **Beklenen:** Sayfalama çalışsın
- **Gerçek:** Test edilmemiş

### 9. 🟢 Callback Retry Logic
- **Dosya:** `adapters/telegram/middleware.py`
- **Repro:** Network timeout
- **Beklenen:** Retry button çalışsın
- **Gerçek:** `ai:retry` callback handler yok

### 10. 🟢 Rate Limit Graceful Fallback
- **Dosya:** `adapters/telegram/middleware.py:57`
- **Repro:** 10+ istek/60sn
- **Beklenen:** Kullanıcıya bilgi ver
- **Gerçek:** Sadece log, UI feedback yok

---

## Test Planı

### 1. Callback Uzunluğu Testi (≤64B)
```python
# tests/telegram/test_callbacks_len.py - MEVCUT ✅
# Tüm view'ların callback'leri 64B altında mı?
pytest tests/telegram/test_callbacks_len.py -v
```

### 2. Render Smoke Testi (≤3500 char)
```python
# tests/telegram/test_render_smoke.py - YENİ
@pytest.mark.parametrize("view", ALL_VIEWS)
def test_view_render_under_3500_chars(view):
    text, buttons = view.build(LARGE_CONTEXT)
    assert len(text.encode('utf-8')) <= 3500
```

### 3. Navigasyon Duman Testi
```python
# tests/telegram/test_navigation.py - YENİ
def test_main_to_signals_to_positions():
    # main → ai:sig → sig view
    # sig → ai:pos → pos view
    # pos → ai:main → main view
    pass
```

### 4. Metrik Artışı Testi
```python
# tests/telegram/test_metrics.py - MEVCUT ✅
def test_view_render_increments_metric():
    initial = get_metric('aibot_tg_views_render_total')
    handlers.handle_start(mock_update, mock_context)
    assert get_metric('aibot_tg_views_render_total') > initial
```

### 5. Hata Fallback Testi
```python
# tests/telegram/test_error_fallback.py - YENİ
def test_timeout_shows_retry_button():
    with mock.patch('context_resolver.resolve', side_effect=TimeoutError):
        text, buttons = handlers.handle_callback(mock_update, mock_ctx)
        assert "retry" in text.lower() or any("retry" in b for row in buttons for b in row)
```

---

## Eklenecek Test Dosyaları

| Dosya | Amaç |
|-------|------|
| `tests/telegram/test_render_smoke.py` | Tüm view'lar ≤3500 char |
| `tests/telegram/test_navigation.py` | Footer navigasyon akışı |
| `tests/telegram/test_error_fallback.py` | Timeout/error graceful handling |
| `tests/telegram/test_pagination.py` | Orders/positions sayfalama |
| `tests/telegram/test_cache.py` | View-local cache (after impl) |
