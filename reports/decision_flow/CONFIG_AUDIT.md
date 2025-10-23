# CONFIG AUDIT RAPORU

**Tarih:** 2025-10-22 15:40:08

## Kritik Parametreler

### Gating Parametreleri
| Parametre | Değer | Kaynak | Enforcement |
|-----------|-------|--------|-------------|
| persist_bars | 2 | policy.yaml | ✅ |
| confirmation_bars | 2 | policy.yaml | ✅ |
| signal_age_max | 6 | policy.yaml | ✅ |
| hysteresis_enabled | N/A | policy.yaml | ✅ |

### Threshold Parametreleri
| Parametre | Değer | Kaynak | Enforcement |
|-----------|-------|--------|-------------|
| enter_long | 60 | policy.yaml | ✅ |
| enter_short | 40 | policy.yaml | ✅ |
| exit_long | 45 | policy.yaml | ✅ |
| exit_short | 55 | policy.yaml | ✅ |

### Risk Parametreleri
| Parametre | Değer | Kaynak | Enforcement |
|-----------|-------|--------|-------------|
| max_position_size_pct | N/A | policy.yaml | ✅ |
| max_total_risk | N/A | policy.yaml | ✅ |
| max_leverage | 3.0 | policy.yaml | ✅ |

### Mode Bayrakları
| Bayrak | Değer | Kaynak | Enforcement |
|--------|-------|--------|-------------|
| trading_mode | N/A | ENV | ✅ |
| paper_trading | paper | policy.yaml | ✅ |
| testnet | False | policy.yaml | ✅ |
| sandbox | False | policy.yaml | ✅ |

### Guard Parametreleri
| Parametre | Değer | Kaynak | Enforcement |
|-----------|-------|--------|-------------|
| once_per_bar_enabled | False | Kod | ❌ |
| client_order_id_format | E{timestamp}{random} | Kod | ✅ |
| reversal_enabled | True | Kod | ✅ |
| same_direction_block | True | Kod | ✅ |

## ENV Değişkenleri
```
TRADING_MODE=Not set
SYMBOLS=Not set
TIMEFRAME=Not set
DECISION_TRACE_ENABLED=Not set
```

## Öneriler
1. **once_per_bar_enabled**: Implement edilmeli
2. **client_order_id**: Daha detaylı format gerekli
3. **bias_penalty**: Trace'e eklenmeli
4. **position_size_validation**: Daha sıkı kontrol gerekli
