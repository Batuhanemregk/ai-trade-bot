# Telegram View Preview Script

Bu script tüm Telegram kartlarını (view'ları) direkt Telegram'a gönderir, formatları görmenizi sağlar.

## Kullanım

### 1. Token ve Chat ID'yi Ayarlayın

```bash
# Windows PowerShell
$env:TELEGRAM_BOT_TOKEN="your_bot_token_here"
$env:TELEGRAM_CHAT_ID="your_chat_id_here"

# Linux/Mac
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

### 2. Chat ID'yi Nasıl Bulursunuz?

1. Telegram'da [@userinfobot](https://t.me/userinfobot) ile sohbet başlatın
2. Bot size user ID'nizi gösterir (örnek: `123456789`)
3. Bu ID'yi `TELEGRAM_CHAT_ID` olarak kullanın

### 3. Script'i Çalıştırın

```bash
# Chat ID'yi environment variable'dan alır
python scripts/send_telegram_views.py

# Veya chat ID'yi direkt parametre olarak verin
python scripts/send_telegram_views.py 123456789
```

## Ne Gönderir?

Script şu tüm view'ları sırayla gönderir:

1. **MAIN** - Ana dashboard
2. **SIGNALS** - Trading sinyalleri
3. **RISK** - Risk yönetimi
4. **ORDERS** - Son emirler
5. **TP/SL** - Take profit / Stop loss seviyeleri
6. **TRAILING** - Trailing stop'lar
7. **PnL** - Kar/Zarar durumu
8. **POSITIONS** - Açık pozisyonlar
9. **SETTINGS** - Ayarlar

Her view, tam formatıyla ve butonlarıyla birlikte gönderilir.

## Örnek Çıktı

```
Sending all views to chat_id: 123456789

✅ MAIN sent successfully
✅ SIGNALS sent successfully
✅ RISK sent successfully
✅ ORDERS sent successfully
✅ TP/SL sent successfully
✅ TRAILING sent successfully
✅ PNL sent successfully
✅ POSITIONS sent successfully
✅ SETTINGS sent successfully

✅ All views sent to chat_id: 123456789
```

## Notlar

- Her view arasında 1 saniye bekleme vardır (rate limit için)
- Tüm view'lar sample data ile gönderilir (gerçek veri değil)
- Formatların nasıl göründüğünü görmek için kullanın
- Bot token'ınızı ve chat ID'nizi güvenli tutun

