# Telegram UI Audit Report

## Değerlendirme Özeti

| Katman | Dosya Sayısı | Durum |
|--------|--------------|-------|
| Views | 9 | ✅ İyi yapılandırılmış |
| Handlers | 1 | ⚠️ Monolitik, bölünebilir |
| Middleware | 4 (Rate/Error/Log/Metrics) | ✅ Tam |
| Callback Registry | 1 | ✅ 64B compression aktif |
| Keyboards | 2 | ✅ Builder pattern |

---

## Akış Diyagramı

```
/start → TelegramHandlers.register_handlers()
       → handle_start() → build_main_view()
       → formatter.add_footer() → send_message()

callback ai:sig → handle_callback()
               → _parse_callback() → view_id + params
               → ContextResolver.resolve_*_context()
               → build_*_view() → edit_message()
               → MetricsHook.record_view_render()
```

---

## Bulgular

### 🔴 Bug (Kritik)

| # | Sorun | Dosya:Satır | Etki |
|---|-------|-------------|------|
| 1 | `ContextResolver` 38KB - çok büyük, memory pressure | `context_resolver.py:*` | Performans |
| 2 | `Unclosed client session` uyarıları | Bot çıkışında | Memory leak |
| 3 | `confirm_max` değeri signals_view'da hardcoded 5 | `signals.py:49-51` | Yanlış gösterim |

### 🟡 UX Sorunları

| # | Sorun | Dosya:Satır | Öneri |
|---|-------|-------------|-------|
| 1 | Signals view'da 6 sembol çok uzun | `signals.py:36` | 4'e düşür |
| 2 | Footer her mesajda tekrar | `formatter.py` | Compact mode'da gizle |
| 3 | Emoji yoğunluğu yüksek | Tüm views | Settings'de toggle |

### 🟢 Smell (Kod Kokusu)

| # | Sorun | Dosya:Satır | Öneri |
|---|-------|-------------|-------|
| 1 | Global singletons (_handlers, _registry) | Tüm modüller | Dependency injection |
| 2 | context_resolver.py 38KB | `context_resolver.py` | 4 dosyaya böl |
| 3 | Hardcoded persist_max=5 | `signals.py:47` | Policy'den oku |

---

## Tut / Çıkar / Yeniden-İşle

### ✅ Tut (Olduğu Gibi)

| Bileşen | Neden |
|---------|-------|
| `CallbackRegistry` 64B compression | Çalışıyor, test edilmiş |
| `RateLimiter` token bucket | Yeterli |
| `MetricsHook` Prometheus entegrasyonu | Tam |
| `ErrorHandler` retry callback | UX iyi |

### ❌ Çıkar

| Bileşen | Neden |
|---------|-------|
| `ConfirmationProcessor` | Zaten kaldırıldı (persist ile birleşti) |
| 6 signal limit | 4'e düşür (mesaj boyutu) |

### 🔄 Yeniden-İşle

| Bileşen | Aksiyon |
|---------|---------|
| `context_resolver.py` | 4 dosyaya böl: positions, signals, risk, orders |
| `signals.py` view | persist/age/confirm değerlerini policy'den oku |
| Footer | Compact mode ekle |

---

## Metrik Kontrol

### Beklenen Metrikler

```python
# aibot_tg_views_render_total{view="main|sig|risk|..."} 
# aibot_tg_callbacks_total{view="sig", act="open"}
# aibot_tg_latency_ms_bucket{le="100|500|1000"}
# aibot_tg_errors_total{type="rate_limit|timeout|parse"}
```

### Log Örnekleri

**Başarı:**
```
tg view=main ms=45 size=892 err=0
```

**Rate Limit (429):**
```
⚠️ Rate limit exceeded for key=123456789
TG callback=ai:sig view=sig t=0ms [RATE_LIMITED]
```

**Hata Fallback:**
```
❌ Error in handle_callback: Connection timeout
→ "Couldn't load data (timeout). Tap to retry." + [Retry] button
```
