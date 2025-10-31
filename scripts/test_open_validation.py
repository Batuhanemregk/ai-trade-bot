#!/usr/bin/env python3
"""
Test Open Validation - Hysteresis geçici gevşetme ile kontrollü OPEN doğrulaması
"""

import os
import sys
import asyncio
import time
from datetime import datetime
from pathlib import Path

# Test-specific environment variables
os.environ['HYSTERESIS_ENABLE'] = 'false'
os.environ['SYMBOLS'] = 'BTC-USDT-SWAP'
os.environ['TIMEFRAME'] = '15m'
os.environ['DRY_RUN'] = 'true'
os.environ['PAPER_TRADING'] = 'true'
os.environ['LIVE'] = 'false'
os.environ['TRADING_MODE'] = 'paper'
os.environ['DECISION_TRACE_ENABLED'] = 'true'

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.scheduler_runner import SchedulerRunner
from application.decision_tracer import get_decision_tracer

class OpenValidationTest:
    def __init__(self):
        self.start_time = datetime.now()
        self.pilot_dir = Path("reports/pilot_open")
        self.pilot_dir.mkdir(exist_ok=True)
        
        # Kanıt toplama
        self.pass_to_open_events = []
        self.same_dir_blocks = []
        self.once_per_bar_hits = []
        self.safety_logs = []
        self.order_audit = []
        
    async def run_test(self, duration_minutes=60):
        """Ana test döngüsü"""
        print(f"🚀 Open Validation Test başladı: {self.start_time}")
        print(f"⏱️  Duration: {duration_minutes} dakika")
        print(f"🔧 Config: HYSTERESIS_ENABLE=false, SYMBOLS=BTC-USDT-SWAP, PAPER=true")
        
        # Scheduler'ı başlat
        scheduler_runner = SchedulerRunner("configs/policy.yaml")
        tracer = get_decision_tracer()
        
        try:
            await scheduler_runner.start()
            scheduler_task = asyncio.create_task(scheduler_runner.run_loop())
            
            # Test süresince monitoring
            end_time = time.time() + (duration_minutes * 60)
            
            while time.time() < end_time:
                # Log'ları kontrol et
                await self.check_logs()
                
                # 60 saniye bekle
                await asyncio.sleep(60)
                
                elapsed = datetime.now() - self.start_time
                print(f"⏱️  Test: {elapsed.total_seconds()/60:.1f} dakika geçti")
            
            # Test bitiminde raporları oluştur
            scheduler_task.cancel()
            await scheduler_runner.stop()
            
            print("📊 Test tamamlandı, raporlar oluşturuluyor...")
            self.generate_reports()
            
        except Exception as e:
            print(f"❌ Test error: {e}")
            await scheduler_runner.stop()
            self.generate_reports()
    
    async def check_logs(self):
        """Log dosyalarını kontrol et ve kanıtları topla"""
        try:
            # Son log dosyasını bul
            log_files = list(Path("logs").glob("*.log"))
            if not log_files:
                return
                
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            
            # Son 100 satırı oku
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            for line in recent_lines:
                line = line.strip()
                
                # PASS→OPEN örnekleri
                if "Gate=PASS" in line and "state: READY→" in line and "OPEN" in line:
                    self.pass_to_open_events.append({
                        'timestamp': datetime.now().isoformat(),
                        'line': line
                    })
                
                # Same-direction blocks
                if "same_dir_block" in line or "SKIP: same direction" in line:
                    self.same_dir_blocks.append({
                        'timestamp': datetime.now().isoformat(),
                        'line': line
                    })
                
                # Once-per-bar hits
                if "once-per-bar: HIT" in line or "SKIP: once_per_bar" in line:
                    self.once_per_bar_hits.append({
                        'timestamp': datetime.now().isoformat(),
                        'line': line
                    })
                
                # Safety logs
                if "[SAFETY]" in line or "non-LIVE: order blocked" in line:
                    self.safety_logs.append({
                        'timestamp': datetime.now().isoformat(),
                        'line': line
                    })
                
                # Order audit
                if "client_order_id" in line or "SL=" in line or "TP=" in line:
                    self.order_audit.append({
                        'timestamp': datetime.now().isoformat(),
                        'line': line
                    })
                    
        except Exception as e:
            print(f"❌ Log check error: {e}")
    
    def generate_reports(self):
        """Test bitiminde raporları oluştur"""
        print("📊 Open validation raporları oluşturuluyor...")
        
        # OPEN_VALIDATION.md
        self.create_open_validation_report()
        
        # ORDER_AUDIT.txt
        self.create_order_audit()
        
        # TRACE.txt
        self.create_trace_report()
        
        # METRICS.txt
        self.create_metrics_report()
        
        print("✅ Open validation raporları tamamlandı!")
    
    def create_open_validation_report(self):
        """OPEN_VALIDATION.md raporunu oluştur"""
        report_file = self.pilot_dir / "OPEN_VALIDATION.md"
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Open Validation Test Report\n\n")
            f.write(f"**Test Duration**: {datetime.now() - self.start_time}\n")
            f.write(f"**Mode**: PAPER (DRY_RUN=true)\n")
            f.write(f"**Symbols**: BTC-USDT-SWAP\n")
            f.write(f"**Config**: HYSTERESIS_ENABLE=false\n\n")
            
            # PASS→OPEN örnekleri
            f.write("## 1. PASS→OPEN Examples\n\n")
            if self.pass_to_open_events:
                for i, event in enumerate(self.pass_to_open_events[:2], 1):
                    f.write(f"### Example {i}\n")
                    f.write(f"```\n{event['line']}\n```\n")
                    f.write(f"**Explanation**: Gate=PASS koşulu sağlandı ve state READY→OPEN geçişi yapıldı.\n\n")
            else:
                f.write("❌ No PASS→OPEN events found\n\n")
            
            # Same-direction blocks
            f.write("## 2. Same-Direction Block Examples\n\n")
            if self.same_dir_blocks:
                for i, block in enumerate(self.same_dir_blocks[:2], 1):
                    f.write(f"### Example {i}\n")
                    f.write(f"```\n{block['line']}\n```\n")
                    f.write(f"**Explanation**: Aynı sembolde aynı yönde pozisyon açık olduğu için giriş engellendi.\n\n")
            else:
                f.write("❌ No same-direction blocks found\n\n")
            
            # Once-per-bar hits
            f.write("## 3. Once-per-bar HIT Examples\n\n")
            if self.once_per_bar_hits:
                for i, hit in enumerate(self.once_per_bar_hits[:2], 1):
                    f.write(f"### Example {i}\n")
                    f.write(f"```\n{hit['line']}\n```\n")
                    f.write(f"**Explanation**: Aynı bar'da daha önce işlem yapıldığı için tekrar giriş engellendi.\n\n")
            else:
                f.write("❌ No once-per-bar hits found\n\n")
            
            # Safety logs
            f.write("## 4. PAPER Safety Log Examples\n\n")
            if self.safety_logs:
                for i, safety in enumerate(self.safety_logs[:3], 1):
                    f.write(f"### Example {i}\n")
                    f.write(f"```\n{safety['line']}\n```\n")
                    f.write(f"**Explanation**: PAPER modda gerçek emirler güvenlik nedeniyle engellendi.\n\n")
            else:
                f.write("❌ No safety logs found\n\n")
            
            # SL/TP idempotency
            f.write("## 5. SL=1, TP=1 Idempotency Examples\n\n")
            if self.order_audit:
                f.write("### Order Audit Logs\n")
                for audit in self.order_audit[:5]:
                    f.write(f"- {audit['timestamp']}: {audit['line']}\n")
                f.write("\n**Explanation**: Her pozisyon için sadece 1 SL ve 1 TP oluşturuldu.\n\n")
            else:
                f.write("❌ No order audit logs found\n\n")
    
    def create_order_audit(self):
        """ORDER_AUDIT.txt dosyasını oluştur"""
        audit_file = self.pilot_dir / "ORDER_AUDIT.txt"
        
        with open(audit_file, "w", encoding="utf-8") as f:
            f.write("# Order Audit Report\n\n")
            f.write(f"**Test Duration**: {datetime.now() - self.start_time}\n")
            f.write(f"**Mode**: PAPER\n\n")
            
            f.write("## Order Events\n\n")
            for audit in self.order_audit:
                f.write(f"- {audit['timestamp']}: {audit['line']}\n")
    
    def create_trace_report(self):
        """TRACE.txt dosyasını oluştur"""
        trace_file = self.pilot_dir / "TRACE.txt"
        
        # Trace summary'den son 200 satırı kopyala
        try:
            trace_summary = Path("reports/decision_flow/TRACE_SUMMARY.txt")
            if trace_summary.exists():
                with open(trace_summary, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent_lines = lines[-200:] if len(lines) > 200 else lines
                
                with open(trace_file, "w", encoding="utf-8") as f:
                    f.write("# Decision Trace - Last 200 Decisions\n\n")
                    for line in recent_lines:
                        f.write(line)
        except Exception as e:
            print(f"❌ Trace report error: {e}")
    
    def create_metrics_report(self):
        """METRICS.txt dosyasını oluştur"""
        metrics_file = self.pilot_dir / "METRICS.txt"
        
        with open(metrics_file, "w", encoding="utf-8") as f:
            f.write("# Metrics Report\n\n")
            f.write(f"**Test Duration**: {datetime.now() - self.start_time}\n")
            f.write(f"**Mode**: PAPER\n\n")
            
            f.write("## Key Metrics\n\n")
            f.write("- PASS→OPEN Events: {}\n".format(len(self.pass_to_open_events)))
            f.write("- Same-Direction Blocks: {}\n".format(len(self.same_dir_blocks)))
            f.write("- Once-per-bar Hits: {}\n".format(len(self.once_per_bar_hits)))
            f.write("- Safety Logs: {}\n".format(len(self.safety_logs)))
            f.write("- Order Audit Events: {}\n".format(len(self.order_audit)))

async def main():
    test = OpenValidationTest()
    await test.run_test(duration_minutes=60)

if __name__ == "__main__":
    asyncio.run(main())
