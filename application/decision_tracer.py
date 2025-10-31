"""
Decision Tracer - Karar akışı izleme sistemi
Minimal telemetri ve trace log'ları için
"""
import os
import json
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from loguru import logger


@dataclass
class DecisionSnapshot:
    """Karar anındaki tüm verilerin snapshot'ı"""
    timestamp: str
    symbol: str
    timeframe: str
    bar_id: str
    
    # Giriş skorları
    ta_score: float
    ml_score: float
    news_score: float
    risk_score: float
    final_score: float
    grade: str
    decision: str
    confidence_pct: float
    
    # Gating durumu
    persistence_bars: int
    persistence_required: int
    confirmation_bars: int
    confirmation_required: int
    signal_age: int
    signal_age_max: int
    hysteresis_ok: bool
    
    # State machine
    state_before: str
    state_after: str
    transition_action: str
    transition_reason: str
    
    # Risk/Size
    position_size_usdt: float
    position_size_pct: float
    leverage: float
    balance_usdt: float
    total_risk_usdt: float
    max_risk_limit: float
    
    # TP/SL
    tp_distance_atr: float
    sl_distance_atr: float
    tp_price: float
    sl_price: float
    
    # Guards
    same_direction_blocked: bool
    once_per_bar_blocked: bool
    reversal_approved: bool
    bias_penalty: float
    bias_reason: str
    
    # Sonuç
    execution_result: str
    skip_reason: str
    client_order_id: str
    
    # Metadata
    regime: str
    adx_1h: float
    confidence_multiplier: float


class DecisionTracer:
    """Karar akışı izleme sınıfı"""
    
    def __init__(self):
        self.enabled = os.getenv('DECISION_TRACE_ENABLED', 'false').lower() == 'true'
        self.trace_dir = "reports/decision_flow"
        self.snapshots_file = f"{self.trace_dir}/RAW_SNAPSHOTS.jsonl"
        self.trace_file = f"{self.trace_dir}/TRACE_SUMMARY.txt"
        
        # Trace dizinini oluştur
        os.makedirs(self.trace_dir, exist_ok=True)
        
        if self.enabled:
            logger.info("🔍 Decision tracing ENABLED")
        else:
            logger.info("🔍 Decision tracing DISABLED (set DECISION_TRACE_ENABLED=true to enable)")
    
    def trace_decision(self, snapshot: DecisionSnapshot) -> None:
        """Karar snapshot'ını kaydet"""
        if not self.enabled:
            return
        
        try:
            # JSONL dosyasına ekle
            with open(self.snapshots_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(snapshot), ensure_ascii=False) + '\n')
            
            # Trace summary'ye ekle
            self._write_trace_summary(snapshot)
            
        except Exception as e:
            logger.error(f"❌ Decision trace failed: {e}")
    
    def _write_trace_summary(self, snapshot: DecisionSnapshot) -> None:
        """Trace summary dosyasına tek satır ekle"""
        try:
            # Tek satır karar özeti
            trace_line = self._format_decision_line(snapshot)
            
            with open(self.trace_file, 'a', encoding='utf-8') as f:
                f.write(trace_line + '\n')
                
        except Exception as e:
            logger.error(f"❌ Trace summary write failed: {e}")
    
    def _format_decision_line(self, snapshot: DecisionSnapshot) -> str:
        """Karar satırını formatla"""
        # Ana karar satırı
        main_line = (
            f"ℹ️ {snapshot.timestamp} | {snapshot.symbol} | tf={snapshot.timeframe} | "
            f"TA={snapshot.ta_score:.1f} ML={snapshot.ml_score:.1f} News={snapshot.news_score:.1f} Risk={snapshot.risk_score:.1f} | "
            f"Final={snapshot.final_score:.1f} ({snapshot.grade}) | "
            f"Dir={snapshot.decision} | "
            f"Gate={'PASS' if snapshot.persistence_bars >= snapshot.persistence_required else 'PENDING'} "
            f"(persist {snapshot.persistence_bars}/{snapshot.persistence_required}, "
            f"conf {snapshot.confirmation_bars}/{snapshot.confirmation_required}, "
            f"age {snapshot.signal_age}/{snapshot.signal_age_max}, "
            f"hyst={'ok' if snapshot.hysteresis_ok else 'fail'}) | "
            f"size={snapshot.position_size_pct:.1f}% lev={snapshot.leverage}x "
            f"SL={snapshot.sl_distance_atr:.1f}ATR TP={snapshot.tp_distance_atr:.1f}ATR | "
            f"risk: exp={snapshot.total_risk_usdt/snapshot.balance_usdt*100:.0f}% "
            f"tier=T1 cb=OK | state: {snapshot.state_before}→{snapshot.state_after}"
        )
        
        # Skip reason varsa ekle
        if snapshot.skip_reason:
            main_line += f" | SKIP: {snapshot.skip_reason}"
        
        # Guards varsa ekle
        guards = []
        if snapshot.same_direction_blocked:
            guards.append("same-dir-block")
        if snapshot.once_per_bar_blocked:
            guards.append("once-per-bar")
        if snapshot.reversal_approved:
            guards.append("reversal-ok")
        if snapshot.bias_penalty > 0:
            guards.append(f"bias-{snapshot.bias_penalty}")
        
        if guards:
            main_line += f" | guards: {','.join(guards)}"
        
        return main_line
    
    def log_console_summary(self, snapshot: DecisionSnapshot) -> None:
        """Console'a kısa özet log"""
        if not self.enabled:
            return
        
        # Kısa console log
        console_line = (
            f"🔍 {snapshot.symbol} | {snapshot.decision} | "
            f"Score={snapshot.final_score:.1f} | "
            f"Gate={'PASS' if snapshot.persistence_bars >= snapshot.persistence_required else 'PENDING'} | "
            f"State={snapshot.state_before}→{snapshot.state_after} | "
            f"Size={snapshot.position_size_pct:.1f}%"
        )
        
        if snapshot.skip_reason:
            console_line += f" | SKIP: {snapshot.skip_reason}"
        
        logger.info(console_line)
    
    def get_trace_stats(self) -> Dict[str, Any]:
        """Trace istatistiklerini döndür"""
        if not self.enabled or not os.path.exists(self.snapshots_file):
            return {}
        
        try:
            with open(self.snapshots_file, 'r', encoding='utf-8') as f:
                snapshots = [json.loads(line) for line in f if line.strip()]
            
            if not snapshots:
                return {}
            
            # İstatistikler
            total_decisions = len(snapshots)
            pass_count = sum(1 for s in snapshots if s['persistence_bars'] >= s['persistence_required'])
            fail_count = total_decisions - pass_count
            
            same_dir_blocked = sum(1 for s in snapshots if s['same_direction_blocked'])
            once_per_bar_blocked = sum(1 for s in snapshots if s['once_per_bar_blocked'])
            reversal_approved = sum(1 for s in snapshots if s['reversal_approved'])
            
            symbols = set(s['symbol'] for s in snapshots)
            decisions = set(s['decision'] for s in snapshots)
            
            return {
                'total_decisions': total_decisions,
                'pass_count': pass_count,
                'fail_count': fail_count,
                'pass_rate': pass_count / total_decisions * 100 if total_decisions > 0 else 0,
                'same_direction_blocked': same_dir_blocked,
                'once_per_bar_blocked': once_per_bar_blocked,
                'reversal_approved': reversal_approved,
                'symbols': list(symbols),
                'decisions': list(decisions),
                'timeframe': snapshots[0]['timeframe'] if snapshots else 'unknown'
            }
            
        except Exception as e:
            logger.error(f"❌ Trace stats failed: {e}")
            return {}


# Global tracer instance
_tracer = None

def get_decision_tracer() -> DecisionTracer:
    """Global tracer instance'ını döndür"""
    global _tracer
    if _tracer is None:
        _tracer = DecisionTracer()
    return _tracer

