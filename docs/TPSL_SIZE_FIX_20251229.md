# TP/SL Emir Boyutu Bug Fix
**Tarih:** 2025-12-29
**Dosya:** `adapters/exchange_okx_ccxt.py`

## Problem
TP/SL emirleri yanlış contract boyutuyla oluşturuluyordu. Örnek:
- ETH: 0.62 contract pozisyon → 1 contract TP/SL emri
- AVAX: 0.9 contract pozisyon → 14 contract TP/SL emri

Bu yüzden TP veya SL tetiklendiğinde pozisyonun tamamı kapanmıyordu.

## Sebep
`create_algo_stop_loss` ve `create_algo_take_profit` fonksiyonlarında:
```python
# YANLIŞ (lines 1326, 1398):
contracts = int(size / ct_val)
```

`size` parametresi zaten **contracts** cinsinden geliyor (runtime.py'den), 
ama kod bunu tekrar ct_val'e bölüp int() ile yuvarladığı için yanlış değer hesaplıyordu.

## Çözüm
`size` değerini doğrudan kullanmak:
```python
# DOĞRU:
contracts = int(round(size))  # size zaten contracts, sadece yuvarla
```

---

## DEĞİŞİKLİKLER

### Dosya: `adapters/exchange_okx_ccxt.py`

#### Değişiklik 1: create_algo_stop_loss (line ~1322-1332)

**ESKİ KOD:**
```python
# Convert size to contracts for swaps - MUST be integer (lot size multiple)
market = self.exchange.market(symbol if '/' in symbol else f"{symbol.split('-')[0]}/USDT:USDT")
ct_val = float(market.get('info', {}).get('ctVal', 1))
if ct_val != 1.0:
    contracts = int(size / ct_val)  # Must be integer for lot size
else:
    contracts = int(size)  # Must be integer

# Ensure at least 1 contract
if contracts < 1:
    contracts = 1
```

**YENİ KOD:**
```python
# Size is already in contracts from runtime.py
# Just round to integer (OKX requires integer for algo orders)
contracts = int(round(size))

# Ensure at least 1 contract
if contracts < 1:
    contracts = 1

logger.debug(f"[ALGO_SL] {symbol}: input_size={size}, contracts={contracts}")
```

---

#### Değişiklik 2: create_algo_take_profit (line ~1394-1404)

**ESKİ KOD:**
```python
# Convert size to contracts for swaps - MUST be integer (lot size multiple)
market = self.exchange.market(symbol if '/' in symbol else f"{symbol.split('-')[0]}/USDT:USDT")
ct_val = float(market.get('info', {}).get('ctVal', 1))
if ct_val != 1.0:
    contracts = int(size / ct_val)  # Must be integer for lot size
else:
    contracts = int(size)  # Must be integer

# Ensure at least 1 contract
if contracts < 1:
    contracts = 1
```

**YENİ KOD:**
```python
# Size is already in contracts from runtime.py
# Just round to integer (OKX requires integer for algo orders)
contracts = int(round(size))

# Ensure at least 1 contract
if contracts < 1:
    contracts = 1

logger.debug(f"[ALGO_TP] {symbol}: input_size={size}, contracts={contracts}")
```

---

## GERİ ALMA TALİMATLARI

Değişikliği geri almak için yukarıdaki "ESKİ KOD" bloklarını tekrar yerine koyun.

## TEST

Değişiklik sonrası şu script ile doğrulayın:
```bash
$env:PYTHONPATH = "."; python scripts/check_algo_orders.py
```

Beklenen: Algo order sz değerleri pozisyon contract değerlerine eşit olmalı.
