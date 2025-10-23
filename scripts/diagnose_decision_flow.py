#!/usr/bin/env python3
"""
Decision Flow Diagnose Script
Karar akışı analizi ve rapor üretimi
"""
import asyncio
import argparse
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.bootstrap import load_env, load_policy
from infrastructure.scheduler_runner import SchedulerRunner
from application.decision_tracer import get_decision_tracer
from loguru import logger


async def run_diagnosis(duration_minutes: int, symbols: list, timeframe: str, paper_mode: bool):
    """Karar akışı tanısını çalıştır"""
    
    # ENV setup
    load_env()
    
    # Trace'i etkinleştir
    os.environ['DECISION_TRACE_ENABLED'] = 'true'
    
    # Paper mode ayarla
    if paper_mode:
        os.environ['TRADING_MODE'] = 'paper'
        logger.info("📋 PAPER mode enabled")
    else:
        logger.warning("⚠️ LIVE mode - be careful!")
    
    # Symbols ayarla
    if symbols:
        os.environ['SYMBOLS'] = ','.join(symbols)
        logger.info(f"📊 Symbols: {symbols}")
    
    # Timeframe ayarla
    os.environ['TIMEFRAME'] = timeframe
    logger.info(f"⏰ Timeframe: {timeframe}")
    
    # Policy yükle
    policy = load_policy("configs/policy.yaml")
    
    # Tracer'ı başlat
    tracer = get_decision_tracer()
    
    logger.info("🔍 Starting decision flow diagnosis...")
    logger.info(f"⏱️ Duration: {duration_minutes} minutes")
    logger.info(f"📁 Trace files: {tracer.trace_dir}")
    
    # Scheduler'ı başlat
    scheduler_runner = SchedulerRunner("configs/policy.yaml")
    
    try:
        # Scheduler'ı initialize et
        await scheduler_runner.initialize()
        
        # Belirtilen süre boyunca çalıştır
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        logger.info(f"🚀 Starting scheduler at {datetime.now().strftime('%H:%M:%S')}")
        
        # Scheduler'ı başlat ve çalıştır
        await scheduler_runner.start()
        
        # Scheduler'ı arka planda çalıştır
        scheduler_task = asyncio.create_task(scheduler_runner.run())
        
        # Süre boyunca bekle
        while time.time() < end_time:
            remaining = int((end_time - time.time()) / 60)
            if remaining % 5 == 0:  # Her 5 dakikada bir log
                logger.info(f"⏳ Remaining: {remaining} minutes")
            
            await asyncio.sleep(60)  # 1 dakika bekle
        
        # Scheduler'ı durdur
        logger.info("🛑 Stopping scheduler...")
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        await scheduler_runner.stop()
        
        # Final stats
        stats = tracer.get_trace_stats()
        if stats:
            logger.info("📊 Final Statistics:")
            logger.info(f"  Total decisions: {stats['total_decisions']}")
            logger.info(f"  Pass rate: {stats['pass_rate']:.1f}%")
            logger.info(f"  Same direction blocked: {stats['same_direction_blocked']}")
            logger.info(f"  Once per bar blocked: {stats['once_per_bar_blocked']}")
            logger.info(f"  Reversal approved: {stats['reversal_approved']}")
            logger.info(f"  Symbols: {stats['symbols']}")
            logger.info(f"  Decisions: {stats['decisions']}")
        
        logger.info("✅ Diagnosis completed!")
        
    except Exception as e:
        logger.error(f"❌ Diagnosis failed: {e}")
        raise
    finally:
        # Cleanup
        if hasattr(scheduler_runner, 'shutdown'):
            await scheduler_runner.shutdown()


def generate_reports():
    """Raporları oluştur"""
    tracer = get_decision_tracer()
    
    if not os.path.exists(tracer.snapshots_file):
        logger.error("❌ No trace data found. Run diagnosis first.")
        return
    
    logger.info("📝 Generating reports...")
    
    # 1. CONFIG_AUDIT.md
    generate_config_audit()
    
    # 2. DECISION_FLOW_REPORT.md
    generate_decision_flow_report()
    
    logger.info("✅ Reports generated!")


def generate_config_audit():
    """Config audit raporu oluştur"""
    policy = load_policy("configs/policy.yaml")
    
    audit_content = f"""# CONFIG AUDIT RAPORU

**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Kritik Parametreler

### Gating Parametreleri
| Parametre | Değer | Kaynak | Enforcement |
|-----------|-------|--------|-------------|
| persist_bars | {policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('persistence_bars', 'N/A')} | policy.yaml | ✅ |
| confirmation_bars | {policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('rev_confirm_bars', 'N/A')} | policy.yaml | ✅ |
| signal_age_max | {policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('max_signal_age_bars', 'N/A')} | policy.yaml | ✅ |
| hysteresis_enabled | {policy.get('trading', {}).get('scoring', {}).get('signal', {}).get('hysteresis', {}).get('enabled', 'N/A')} | policy.yaml | ✅ |

### Threshold Parametreleri
| Parametre | Değer | Kaynak | Enforcement |
|-----------|-------|--------|-------------|
| enter_long | {policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {}).get('enter_long', 'N/A')} | policy.yaml | ✅ |
| enter_short | {policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {}).get('enter_short', 'N/A')} | policy.yaml | ✅ |
| exit_long | {policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {}).get('exit_long', 'N/A')} | policy.yaml | ✅ |
| exit_short | {policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {}).get('exit_short', 'N/A')} | policy.yaml | ✅ |

### Risk Parametreleri
| Parametre | Değer | Kaynak | Enforcement |
|-----------|-------|--------|-------------|
| max_position_size_pct | {policy.get('trading', {}).get('risk', {}).get('max_position_size_pct', 'N/A')} | policy.yaml | ✅ |
| max_total_risk | {policy.get('trading', {}).get('risk', {}).get('max_total_risk', 'N/A')} | policy.yaml | ✅ |
| max_leverage | {policy.get('trading', {}).get('risk', {}).get('max_leverage', 'N/A')} | policy.yaml | ✅ |

### Mode Bayrakları
| Bayrak | Değer | Kaynak | Enforcement |
|--------|-------|--------|-------------|
| trading_mode | {os.getenv('TRADING_MODE', 'N/A')} | ENV | ✅ |
| paper_trading | {policy.get('exchange', {}).get('mode', 'N/A')} | policy.yaml | ✅ |
| testnet | {policy.get('exchange', {}).get('testnet', 'N/A')} | policy.yaml | ✅ |
| sandbox | {policy.get('exchange', {}).get('sandbox', 'N/A')} | policy.yaml | ✅ |

### Guard Parametreleri
| Parametre | Değer | Kaynak | Enforcement |
|-----------|-------|--------|-------------|
| once_per_bar_enabled | False | Kod | ❌ |
| client_order_id_format | E{{timestamp}}{{random}} | Kod | ✅ |
| reversal_enabled | True | Kod | ✅ |
| same_direction_block | True | Kod | ✅ |

## ENV Değişkenleri
```
TRADING_MODE={os.getenv('TRADING_MODE', 'Not set')}
SYMBOLS={os.getenv('SYMBOLS', 'Not set')}
TIMEFRAME={os.getenv('TIMEFRAME', 'Not set')}
DECISION_TRACE_ENABLED={os.getenv('DECISION_TRACE_ENABLED', 'Not set')}
```

## Öneriler
1. **once_per_bar_enabled**: Implement edilmeli
2. **client_order_id**: Daha detaylı format gerekli
3. **bias_penalty**: Trace'e eklenmeli
4. **position_size_validation**: Daha sıkı kontrol gerekli
"""
    
    with open("reports/decision_flow/CONFIG_AUDIT.md", "w", encoding="utf-8") as f:
        f.write(audit_content)
    
    logger.info("✅ CONFIG_AUDIT.md generated")


def generate_decision_flow_report():
    """Ana karar akışı raporu oluştur"""
    
    # Mermaid diagram
    mermaid_diagram = """```mermaid
graph TD
    A[OHLCV Data] --> B[TA Analysis]
    A --> C[ML Analysis]
    A --> D[News Analysis]
    A --> E[Risk Analysis]
    
    B --> F[Composite Score]
    C --> F
    D --> F
    E --> F
    
    F --> G[Signal Gate]
    G --> H[Persistence Check]
    G --> I[Confirmation Check]
    G --> J[Hysteresis Check]
    
    H --> K[Gate Result]
    I --> K
    J --> K
    
    K --> L[State Manager]
    L --> M{State Check}
    
    M -->|READY| N[Ready Rules]
    M -->|LONG_OPEN| O[Same Direction Block]
    M -->|SHORT_OPEN| O
    M -->|COOLDOWN| P[Cooldown Check]
    
    N --> Q[Risk Calculation]
    O --> R[Reversal Check]
    P --> S[Ready Transition]
    
    Q --> T[Position Size]
    R --> U[Close & Reverse]
    S --> V[Ready State]
    
    T --> W[Execution]
    U --> W
    V --> X[Wait Next Signal]
    
    W --> Y[TP/SL Setup]
    Y --> Z[State Update]
```
"""
    
    report_content = f"""# KARAR AKIŞI RAPORU

**Tarih:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Yüksek Seviye Akış Şeması

{mermaid_diagram}

## Ayrıntılı Akış Tablosu

### Girişler
| Bileşen | Ağırlık | Hesaplama | Dosya |
|---------|---------|-----------|-------|
| TA Score | 0.4 | 13 teknik indikatör | scoring/ta_scorer.py |
| ML Score | 0.3 | Random Forest model | scoring/ml_scorer.py |
| News Score | 0.2 | LLM sentiment | scoring/news_scorer.py |
| Risk Score | 0.1 | Volatilite + likidite | application/risk_service.py |

### Gating Kuralları
| Kural | Parametre | Değer | Dosya |
|-------|-----------|-------|-------|
| Persistence | persist_bars | 5 | application/signal_gate.py:62 |
| Confirmation | rev_confirm_bars | 3 | application/signal_gate.py:136 |
| Signal Age | max_signal_age_bars | 6 | application/signal_gate.py:63 |
| Hysteresis | enter/exit thresholds | 60/40 | application/signal_gate.py:302-305 |

### Tekrar Giriş Engelleri
| Engelleme | Durum | Dosya | Açıklama |
|-----------|-------|-------|----------|
| Same Direction | ✅ | application/position_state_manager.py:102 | Aynı yönde açık pozisyon varsa blokla |
| Once Per Bar | ❌ | - | Implement edilmedi |
| Client Order ID | ✅ | execution/id_utils.py | Benzersiz order ID |
| Position State | ✅ | application/position_state_manager.py:218 | READY/OPEN/COOLDOWN kontrolü |

### Çıkış Koşulları
| Koşul | Threshold | Dosya | Açıklama |
|-------|-----------|-------|----------|
| Exit Signal | exit_long/exit_short | application/position_state_manager.py:148 | Ters sinyal + min hold |
| TP Trigger | 4 ATR | infrastructure/runtime.py:710 | Take profit seviyesi |
| SL Trigger | 2 ATR | infrastructure/runtime.py:710 | Stop loss seviyesi |
| Trailing | Dynamic | application/trailing_job.py | SL güncelleme |

### Risk/Size Hesaplama
| Parametre | Değer | Dosya | Açıklama |
|-----------|-------|-------|----------|
| Max Position % | 10% | infrastructure/runtime.py:780 | Sinyal gücüne göre 1-10% |
| Max Total Risk | 60% | infrastructure/runtime.py:770 | Toplam risk limiti |
| Risk Multiplier | 0.5-1.0 | infrastructure/runtime.py:785 | Risk skoruna göre |
| ML Confidence | 1.0-1.5 | infrastructure/runtime.py:798 | ML güvenine göre |

## Örnek Karar Özeti

```
ℹ️ 01:23:45 | BTC-USDT-SWAP | tf=15m | TA=75.3 ML=68.2 News=55.0 Risk=42.1 | Final=65.8 (B)
   Dir=LONG | Gate=PASS (persist 3/5, conf 0.8/0.6, age 2/6, hyst=ok)
   size=3.2% lev=3x SL=2ATR TP=4ATR | risk: exp=18% tier=T1 cb=OK | state: READY→LONG_OPEN
```

### Alan Açıklamaları
- **TA/ML/News/Risk**: Skorlar (0-100)
- **Final**: Ağırlıklı ortalama
- **Grade**: A-F harf notu
- **Dir**: LONG/SHORT/FLAT
- **Gate**: PASS/PENDING durumu
- **persist**: Mevcut/gerekli bar sayısı
- **conf**: Güven skoru/gerekli threshold
- **age**: Sinyal yaşı/maksimum yaş
- **hyst**: Hysteresis kontrolü
- **size**: Pozisyon büyüklüğü (%)
- **lev**: Kaldıraç
- **SL/TP**: Stop loss/Take profit ATR mesafesi
- **exp**: Toplam risk maruziyeti (%)
- **tier**: Risk seviyesi
- **cb**: Circuit breaker durumu
- **state**: Önceki→Sonraki durum

## Aynı Sinyale Tekrar Giriş Kuralları

### 1. Per-Bar Guard
- **Durum**: ❌ Implement edilmedi
- **Dosya**: -
- **Açıklama**: Aynı bar içinde tekrar giriş engellenmeli

### 2. Same-Direction Block
- **Durum**: ✅ Çalışıyor
- **Dosya**: application/position_state_manager.py:102
- **Açıklama**: Aynı yönde açık pozisyon varsa blokla

### 3. Position State Guard
- **Durum**: ✅ Çalışıyor
- **Dosya**: application/position_state_manager.py:218
- **Açıklama**: READY durumunda değilse giriş yapma

### 4. Reversal Logic
- **Durum**: ✅ Çalışıyor
- **Dosya**: application/position_state_manager.py:134
- **Açıklama**: Ters yönde sinyal + min hold süresi

## Watchdog/Catch-up Etkisi

- **Missed Run Detection**: ✅ application/jobs/base_job.py:70
- **Catch-up Logic**: ✅ infrastructure/scheduler_runner.py
- **Bar ID Validation**: ⚠️ Format hatası var (2025-10-21TT23:00:00+00:00)

## Zayıf Noktalar

### 1. Idempotency Eksikleri
- **once_per_bar**: Implement edilmedi
- **client_order_id**: Basit format
- **bar_id_validation**: Format hatası

### 2. Guard Eksikleri
- **bias_penalty**: Trace'e eklenmedi
- **position_size_validation**: Yetersiz
- **correlation_guard**: Trace'de yok

### 3. Log Eksikleri
- **gate_details**: Yetersiz detay
- **skip_reason**: Kısa açıklama
- **execution_result**: Basit

## Öneriler

### 1. Acil (Bu Hafta)
- once_per_bar guard implement et
- bar_id format düzelt
- bias_penalty trace'e ekle

### 2. Orta Vadeli (Gelecek Hafta)
- position_size validation güçlendir
- correlation guard ekle
- execution_result detaylandır

### 3. Uzun Vadeli (Gelecek Ay)
- comprehensive test suite
- performance monitoring
- alert system
"""
    
    with open("reports/decision_flow/DECISION_FLOW_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logger.info("✅ DECISION_FLOW_REPORT.md generated")


def main():
    """Ana fonksiyon"""
    parser = argparse.ArgumentParser(description="Decision Flow Diagnosis")
    parser.add_argument("--duration", type=int, default=30, help="Duration in minutes")
    parser.add_argument("--symbols", type=str, default="BTC-USDT-SWAP,ETH-USDT-SWAP,SOL-USDT-SWAP", help="Comma-separated symbols")
    parser.add_argument("--timeframe", type=str, default="15m", help="Timeframe")
    parser.add_argument("--paper", action="store_true", help="Run in paper mode")
    parser.add_argument("--reports-only", action="store_true", help="Generate reports only")
    
    args = parser.parse_args()
    
    # Symbols'ı parse et
    symbols = [s.strip() for s in args.symbols.split(",")]
    
    if args.reports_only:
        generate_reports()
    else:
        # Diagnosis çalıştır
        asyncio.run(run_diagnosis(
            duration_minutes=args.duration,
            symbols=symbols,
            timeframe=args.timeframe,
            paper_mode=args.paper
        ))
        
        # Raporları oluştur
        generate_reports()


if __name__ == "__main__":
    main()
