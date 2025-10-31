# AiBotBS Policy Referansı

> **policy.yaml şeması, öncelik sırası ve konfigürasyon rehberi**

## 🎯 Policy Yapısı

### Öncelik Sırası
```
1. ENV Variables (En yüksek öncelik)
2. policy.yaml (Orta öncelik)
3. Default Values (En düşük öncelik)
```

### Konfigürasyon Kaynağı Banner'ı
```
[SOURCE] ENV → policy.yaml → default
```

## 📋 Policy Şeması

### 1. **Trading Konfigürasyonu**

#### `trading.mode`
**Açıklama**: Trading modu
**Değerler**: `LIVE`, `PAPER`, `DRY_RUN`
**Varsayılan**: `PAPER`
**ENV Override**: `TRADING_MODE`

```yaml
trading:
  mode: PAPER  # LIVE | PAPER | DRY_RUN
```

#### `trading.use_position_tpsl`
**Açıklama**: Position-level TP/SL kullanımı
**Değerler**: `true`, `false`
**Varsayılan**: `true`
**ENV Override**: `USE_POSITION_TPSL`

```yaml
trading:
  use_position_tpsl: true
```

#### `trading.reduce_only`
**Açıklama**: TP/SL emirlerinde reduce-only kullanımı
**Değerler**: `true`, `false`
**Varsayılan**: `true`
**ENV Override**: `REDUCE_ONLY`

```yaml
trading:
  reduce_only: true
```

#### `trading.entry_cooldown_bars`
**Açıklama**: Giriş sonrası bekleme süresi (bar cinsinden)
**Değerler**: `1-10`
**Varsayılan**: `2`
**ENV Override**: `ENTRY_COOLDOWN_BARS`

```yaml
trading:
  entry_cooldown_bars: 2
```

### 2. **Strateji Konfigürasyonu**

#### `trading.strategy.type`
**Açıklama**: Strateji türü
**Değerler**: `single_flip`, `scale_in`
**Varsayılan**: `single_flip`
**ENV Override**: `STRATEGY_MODE`

```yaml
trading:
  strategy:
    type: single_flip  # single_flip | scale_in
```

#### `trading.strategy.once_per_bar`
**Açıklama**: Her bar'da sadece 1 karar
**Değerler**: `true`, `false`
**Varsayılan**: `true`
**ENV Override**: `ONCE_PER_BAR`

```yaml
trading:
  strategy:
    once_per_bar: true
```

#### `trading.strategy.same_direction_block`
**Açıklama**: Aynı yönde tekrar giriş engeli
**Değerler**: `true`, `false`
**Varsayılan**: `true`
**ENV Override**: `SAME_DIRECTION_BLOCK`

```yaml
trading:
  strategy:
    same_direction_block: true
```

#### `trading.strategy.reversal_enabled`
**Açıklama**: Pozisyon tersine çevirme
**Değerler**: `true`, `false`
**Varsayılan**: `true`
**ENV Override**: `REVERSAL_ENABLED`

```yaml
trading:
  strategy:
    reversal_enabled: true
```

### 3. **Scale-in Strateji Konfigürasyonu**

#### `trading.strategy.scale_in.enabled`
**Açıklama**: Scale-in stratejisi aktif mi
**Değerler**: `true`, `false`
**Varsayılan**: `false`
**ENV Override**: `SCALE_IN_ENABLED`

```yaml
trading:
  strategy:
    scale_in:
      enabled: false
```

#### `trading.strategy.scale_in.max_ladders`
**Açıklama**: Maksimum ekleme seviyesi
**Değerler**: `1-5`
**Varsayılan**: `2`
**ENV Override**: `MAX_LADDERS`

```yaml
trading:
  strategy:
    scale_in:
      max_ladders: 2
```

#### `trading.strategy.scale_in.ladder_size_usdt`
**Açıklama**: Her ekleme miktarı (USDT)
**Değerler**: `1-100`
**Varsayılan**: `5`
**ENV Override**: `LADDER_SIZE_USDT`

```yaml
trading:
  strategy:
    scale_in:
      ladder_size_usdt: 5
```

#### `trading.strategy.scale_in.min_dist_pct`
**Açıklama**: Minimum mesafe yüzdesi
**Değerler**: `0.1-2.0`
**Varsayılan**: `0.5`
**ENV Override**: `MIN_DIST_PCT`

```yaml
trading:
  strategy:
    scale_in:
      min_dist_pct: 0.5
```

#### `trading.strategy.scale_in.add_on_profit_only`
**Açıklama**: Sadece kârda ekleme
**Değerler**: `true`, `false`
**Varsayılan**: `true`
**ENV Override**: `ADD_ON_PROFIT_ONLY`

```yaml
trading:
  strategy:
    scale_in:
      add_on_profit_only: true
```

### 4. **Risk Yönetimi Konfigürasyonu**

#### `trading.risk.max_position_size_pct`
**Açıklama**: Maksimum pozisyon büyüklüğü (%)
**Değerler**: `0.01-0.50`
**Varsayılan**: `0.01`
**ENV Override**: `MAX_POSITION_SIZE_PCT`

```yaml
trading:
  risk:
    max_position_size_pct: 0.01  # %1
```

#### `trading.risk.max_total_risk_pct`
**Açıklama**: Maksimum toplam risk (%)
**Değerler**: `0.10-1.00`
**Varsayılan**: `0.60`
**ENV Override**: `MAX_TOTAL_RISK_PCT`

```yaml
trading:
  risk:
    max_total_risk_pct: 0.60  # %60
```

#### `trading.risk.max_leverage`
**Açıklama**: Maksimum kaldıraç
**Değerler**: `1.0-10.0`
**Varsayılan**: `3.0`
**ENV Override**: `MAX_LEVERAGE`

```yaml
trading:
  risk:
    max_leverage: 3.0
```

#### `trading.risk.max_drawdown`
**Açıklama**: Maksimum drawdown (%)
**Değerler**: `0.05-0.50`
**Varsayılan**: `0.15`
**ENV Override**: `MAX_DRAWDOWN`

```yaml
trading:
  risk:
    max_drawdown: 0.15  # %15
```

### 5. **Skorlama Konfigürasyonu**

#### `trading.scoring.ta_weight`
**Açıklama**: Technical Analysis ağırlığı
**Değerler**: `0.0-1.0`
**Varsayılan**: `0.4`
**ENV Override**: `TA_WEIGHT`

```yaml
trading:
  scoring:
    ta_weight: 0.4  # %40
```

#### `trading.scoring.ml_weight`
**Açıklama**: Machine Learning ağırlığı
**Değerler**: `0.0-1.0`
**Varsayılan**: `0.25`
**ENV Override**: `ML_WEIGHT`

```yaml
trading:
  scoring:
    ml_weight: 0.25  # %25
```

#### `trading.scoring.news_weight`
**Açıklama**: News sentiment ağırlığı
**Değerler**: `0.0-1.0`
**Varsayılan**: `0.2`
**ENV Override**: `NEWS_WEIGHT`

```yaml
trading:
  scoring:
    news_weight: 0.2  # %20
```

#### `trading.scoring.risk_weight`
**Açıklama**: Risk skoru ağırlığı
**Değerler**: `0.0-1.0`
**Varsayılan**: `0.15`
**ENV Override**: `RISK_WEIGHT`

```yaml
trading:
  scoring:
    risk_weight: 0.15  # %15
```

### 6. **Karar Eşikleri**

#### `trading.scoring.decision_thresholds.enter_long`
**Açıklama**: LONG giriş eşiği
**Değerler**: `50-100`
**Varsayılan**: `60`
**ENV Override**: `ENTER_LONG_THRESHOLD`

```yaml
trading:
  scoring:
    decision_thresholds:
      enter_long: 60  # Score >= 60: LONG entry
```

#### `trading.scoring.decision_thresholds.exit_long`
**Açıklama**: LONG çıkış eşiği
**Değerler**: `0-50`
**Varsayılan**: `45`
**ENV Override**: `EXIT_LONG_THRESHOLD`

```yaml
trading:
  scoring:
    decision_thresholds:
      exit_long: 45  # Score <= 45: LONG exit
```

#### `trading.scoring.decision_thresholds.enter_short`
**Açıklama**: SHORT giriş eşiği
**Değerler**: `0-50`
**Varsayılan**: `40`
**ENV Override**: `ENTER_SHORT_THRESHOLD`

```yaml
trading:
  scoring:
    decision_thresholds:
      enter_short: 40  # Score <= 40: SHORT entry
```

#### `trading.scoring.decision_thresholds.exit_short`
**Açıklama**: SHORT çıkış eşiği
**Değerler**: `50-100`
**Varsayılan**: `55`
**ENV Override**: `EXIT_SHORT_THRESHOLD`

```yaml
trading:
  scoring:
    decision_thresholds:
      exit_short: 55  # Score >= 55: SHORT exit
```

#### `trading.scoring.decision_thresholds.flat_range`
**Açıklama**: FLAT (nötr) bölge
**Değerler**: `[min, max]` (0-100 arası)
**Varsayılan**: `[45, 55]`
**ENV Override**: `FLAT_RANGE`

```yaml
trading:
  scoring:
    decision_thresholds:
      flat_range: [45, 55]  # 45-55 arası: FLAT
```

### 7. **Sembol Konfigürasyonu**

#### `exchange.symbols.supported_pairs`
**Açıklama**: Desteklenen semboller
**Değerler**: `["BTC", "ETH", "SOL", ...]`
**Varsayılan**: `["BTC", "ETH", "SOL"]`
**ENV Override**: `SYMBOLS`

```yaml
exchange:
  symbols:
    supported_pairs: ["BTC", "ETH", "SOL"]
```

#### `exchange.symbols.trading_pairs`
**Açıklama**: Trading sembolleri (futures)
**Değerler**: `["BTC-USDT-SWAP", "ETH-USDT-SWAP", ...]`
**Varsayılan**: `["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]`
**ENV Override**: `TRADING_PAIRS`

```yaml
exchange:
  symbols:
    trading_pairs: ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
```

## 🔧 ENV Override Örnekleri

### 1. **Trading Modu Değiştirme**
```bash
# PAPER modundan LIVE moduna geç
export TRADING_MODE=LIVE
export USE_POSITION_TPSL=true
export REDUCE_ONLY=true

# Bot'u başlat
./scripts/dev.sh start-scheduler
```

### 2. **Strateji Modu Değiştirme**
```bash
# single_flip'ten scale_in'e geç
export STRATEGY_MODE=scale_in
export SCALE_IN_ENABLED=true
export MAX_LADDERS=3
export LADDER_SIZE_USDT=10

# Bot'u başlat
./scripts/dev.sh start-scheduler
```

### 3. **Risk Parametreleri Değiştirme**
```bash
# Daha konservatif risk ayarları
export MAX_POSITION_SIZE_PCT=0.005  # %0.5
export MAX_TOTAL_RISK_PCT=0.30     # %30
export MAX_LEVERAGE=2.0             # 2x

# Bot'u başlat
./scripts/dev.sh start-scheduler
```

### 4. **Skorlama Ağırlıkları Değiştirme**
```bash
# ML ağırlığını artır
export ML_WEIGHT=0.4
export TA_WEIGHT=0.3
export NEWS_WEIGHT=0.2
export RISK_WEIGHT=0.1

# Bot'u başlat
./scripts/dev.sh start-scheduler
```

### 5. **Sembol Listesi Değiştirme**
```bash
# Sadece BTC ve ETH işle
export SYMBOLS="BTC,ETH"
export TRADING_PAIRS="BTC-USDT-SWAP,ETH-USDT-SWAP"

# Bot'u başlat
./scripts/dev.sh start-scheduler
```

## 📊 Başlangıç Banner'ı

### Banner Bileşenleri
```
[MODE] TRADING_MODE=PAPER STRATEGY_MODE=single_flip USE_POSITION_TPSL=true REDUCE_ONLY=true
[GATING] once_per_bar=true entry_cooldown_bars=2 same_direction_block=true reversal_enabled=true
[SCORING] ta_weight=0.4 ml_weight=0.25 news_weight=0.2 risk_weight=0.15
[THRESHOLDS] enter_long=60 exit_long=45 enter_short=40 exit_short=55 flat_range=[45,55]
[RISK] max_position_size_pct=0.01 max_total_risk_pct=0.60 max_leverage=3.0 max_drawdown=0.15
[SYMBOLS] BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP
[SOURCE] ENV → policy.yaml → default
```

### Banner Kaynak Etiketi
- **ENV**: Environment variable'dan alındı
- **policy.yaml**: policy.yaml dosyasından alındı
- **default**: Varsayılan değer kullanıldı

## 🔍 Konfigürasyon Doğrulama

### 1. **Policy Validation**
```bash
# Policy dosyasını doğrula
python -c "
from configs.schemas import validate_policy_dict
import yaml

with open('configs/policy.yaml', 'r') as f:
    policy = yaml.safe_load(f)

is_valid, error = validate_policy_dict(policy)
if is_valid:
    print('✅ Policy is valid')
else:
    print(f'❌ Policy error: {error}')
"
```

### 2. **ENV Override Kontrolü**
```bash
# Aktif ENV değişkenlerini kontrol et
env | grep -E "(TRADING_|STRATEGY_|MAX_|MIN_|WEIGHT_)"

# Policy ile karşılaştır
grep -E "(mode|type|weight|threshold)" configs/policy.yaml
```

### 3. **Banner Kontrolü**
```bash
# Banner'ı kontrol et
grep "\[MODE\]" logs/trading.log | tail -1
grep "\[SOURCE\]" logs/trading.log | tail -1
```

## 📚 Örnek Konfigürasyonlar

### 1. **Konservatif Trading**
```yaml
trading:
  mode: PAPER
  strategy:
    type: single_flip
    once_per_bar: true
    same_direction_block: true
    reversal_enabled: true
  risk:
    max_position_size_pct: 0.005  # %0.5
    max_total_risk_pct: 0.30     # %30
    max_leverage: 2.0
    max_drawdown: 0.10           # %10
  scoring:
    ta_weight: 0.5
    ml_weight: 0.3
    news_weight: 0.15
    risk_weight: 0.05
    decision_thresholds:
      enter_long: 70
      exit_long: 40
      enter_short: 30
      exit_short: 60
      flat_range: [40, 60]
```

### 2. **Agresif Trading**
```yaml
trading:
  mode: PAPER
  strategy:
    type: scale_in
    scale_in:
      enabled: true
      max_ladders: 3
      ladder_size_usdt: 10
      min_dist_pct: 0.3
      add_on_profit_only: true
  risk:
    max_position_size_pct: 0.02  # %2
    max_total_risk_pct: 0.80    # %80
    max_leverage: 5.0
    max_drawdown: 0.25          # %25
  scoring:
    ta_weight: 0.3
    ml_weight: 0.4
    news_weight: 0.2
    risk_weight: 0.1
    decision_thresholds:
      enter_long: 55
      exit_long: 50
      enter_short: 45
      exit_short: 50
      flat_range: [45, 55]
```

### 3. **News Odaklı Trading**
```yaml
trading:
  mode: PAPER
  strategy:
    type: single_flip
    once_per_bar: true
    same_direction_block: true
    reversal_enabled: true
  risk:
    max_position_size_pct: 0.01
    max_total_risk_pct: 0.50
    max_leverage: 3.0
    max_drawdown: 0.15
  scoring:
    ta_weight: 0.2
    ml_weight: 0.2
    news_weight: 0.5
    risk_weight: 0.1
    decision_thresholds:
      enter_long: 60
      exit_long: 45
      enter_short: 40
      exit_short: 55
      flat_range: [45, 55]
```

## 📚 Sonraki Adımlar

1. [ONBOARDING.md](ONBOARDING.md) - Sistem genel bakışı
2. [RUN_GUIDE_CURRENT.md](RUN_GUIDE_CURRENT.md) - Çalıştırma rehberi
3. [OPERATIONS_PLAYBOOK.md](OPERATIONS_PLAYBOOK.md) - Operasyon pratikleri
4. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Sorun giderme

