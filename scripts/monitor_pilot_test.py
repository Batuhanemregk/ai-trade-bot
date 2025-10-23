#!/usr/bin/env python3
"""
Pilot Test Monitor - 90 dakikalık test süresince kanıtları toplar
"""

import os
import time
import json
import asyncio
from datetime import datetime
from pathlib import Path

class PilotTestMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.pilot_dir = Path("reports/pilot")
        self.pilot_dir.mkdir(exist_ok=True)
        
        # Kanıt toplama
        self.pass_to_open_events = []
        self.same_dir_blocks = []
        self.once_per_bar_hits = []
        self.safety_logs = []
        self.risk_clamps = []
        self.order_summaries = []
        
    async def monitor_loop(self):
        """Ana monitoring döngüsü"""
        print(f"🔍 Pilot test monitoring başladı: {self.start_time}")
        
        while True:
            try:
                # Log dosyalarını kontrol et
                await self.check_logs()
                
                # Metrics'i kontrol et
                await self.check_metrics()
                
                # 60 saniye bekle
                await asyncio.sleep(60)
                
                elapsed = datetime.now() - self.start_time
                print(f"⏱️  Monitoring: {elapsed.total_seconds()/60:.1f} dakika geçti")
                
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                await asyncio.sleep(30)
    
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
                
                # Risk clamps
                if "risk clamp" in line or "SKIP: risk" in line or "exposure limit" in line:
                    self.risk_clamps.append({
                        'timestamp': datetime.now().isoformat(),
                        'line': line
                    })
                    
        except Exception as e:
            print(f"❌ Log check error: {e}")
    
    async def check_metrics(self):
        """Prometheus metrics'lerini kontrol et"""
        try:
            import requests
            
            # Metrics endpoint'i kontrol et
            response = requests.get("http://localhost:8000/metrics", timeout=5)
            if response.status_code == 200:
                metrics_text = response.text
                
                # Metrics'i dosyaya kaydet
                with open(self.pilot_dir / "METRICS_SNAPSHOT.txt", "w", encoding="utf-8") as f:
                    f.write(f"# Pilot Test Metrics - {datetime.now()}\n\n")
                    f.write(metrics_text)
                    
        except Exception as e:
            print(f"❌ Metrics check error: {e}")
    
    def generate_reports(self):
        """Test bitiminde raporları oluştur"""
        print("📊 Pilot test raporları oluşturuluyor...")
        
        # PAPER_EVIDENCE.md
        self.create_paper_evidence()
        
        # OPEN_EVENTS.jsonl
        self.create_open_events()
        
        # ORDER_SUMMARY.txt
        self.create_order_summary()
        
        print("✅ Pilot test raporları tamamlandı!")
    
    def create_paper_evidence(self):
        """PAPER_EVIDENCE.md raporunu oluştur"""
        evidence_file = self.pilot_dir / "PAPER_EVIDENCE.md"
        
        with open(evidence_file, "w", encoding="utf-8") as f:
            f.write("# Pilot Test Evidence Report\n\n")
            f.write(f"**Test Duration**: {datetime.now() - self.start_time}\n")
            f.write(f"**Mode**: PAPER\n")
            f.write(f"**Symbols**: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP\n\n")
            
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
            f.write("## 4. Safety Log Examples\n\n")
            if self.safety_logs:
                for i, safety in enumerate(self.safety_logs[:3], 1):
                    f.write(f"### Example {i}\n")
                    f.write(f"```\n{safety['line']}\n```\n")
                    f.write(f"**Explanation**: PAPER modda gerçek emirler güvenlik nedeniyle engellendi.\n\n")
            else:
                f.write("❌ No safety logs found\n\n")
            
            # Risk clamps
            f.write("## 5. Risk Clamp/Skip Examples\n\n")
            if self.risk_clamps:
                for i, risk in enumerate(self.risk_clamps[:2], 1):
                    f.write(f"### Example {i}\n")
                    f.write(f"```\n{risk['line']}\n```\n")
                    f.write(f"**Explanation**: Risk limitleri aşıldığı için işlem engellendi.\n\n")
            else:
                f.write("❌ No risk clamps found\n\n")
    
    def create_open_events(self):
        """OPEN_EVENTS.jsonl dosyasını oluştur"""
        events_file = self.pilot_dir / "OPEN_EVENTS.jsonl"
        
        with open(events_file, "w", encoding="utf-8") as f:
            for event in self.pass_to_open_events:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    
    def create_order_summary(self):
        """ORDER_SUMMARY.txt dosyasını oluştur"""
        summary_file = self.pilot_dir / "ORDER_SUMMARY.txt"
        
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write("# Pilot Test Order Summary\n\n")
            f.write(f"**Test Duration**: {datetime.now() - self.start_time}\n")
            f.write(f"**Mode**: PAPER\n\n")
            
            f.write("## Order Statistics\n\n")
            f.write(f"- PASS→OPEN Events: {len(self.pass_to_open_events)}\n")
            f.write(f"- Same-Direction Blocks: {len(self.same_dir_blocks)}\n")
            f.write(f"- Once-per-bar Hits: {len(self.once_per_bar_hits)}\n")
            f.write(f"- Safety Logs: {len(self.safety_logs)}\n")
            f.write(f"- Risk Clamps: {len(self.risk_clamps)}\n\n")
            
            f.write("## Detailed Events\n\n")
            
            if self.pass_to_open_events:
                f.write("### PASS→OPEN Events\n")
                for event in self.pass_to_open_events:
                    f.write(f"- {event['timestamp']}: {event['line']}\n")
                f.write("\n")
            
            if self.same_dir_blocks:
                f.write("### Same-Direction Blocks\n")
                for block in self.same_dir_blocks:
                    f.write(f"- {block['timestamp']}: {block['line']}\n")
                f.write("\n")
            
            if self.once_per_bar_hits:
                f.write("### Once-per-bar Hits\n")
                for hit in self.once_per_bar_hits:
                    f.write(f"- {hit['timestamp']}: {hit['line']}\n")
                f.write("\n")

async def main():
    monitor = PilotTestMonitor()
    
    try:
        # 90 dakika monitoring
        await asyncio.wait_for(monitor.monitor_loop(), timeout=5400)  # 90 dakika
    except asyncio.TimeoutError:
        print("⏰ 90 dakika tamamlandı, raporlar oluşturuluyor...")
    except KeyboardInterrupt:
        print("🛑 Test durduruldu, raporlar oluşturuluyor...")
    finally:
        monitor.generate_reports()

if __name__ == "__main__":
    asyncio.run(main())
