"""
Otomatik ML Model Yeniden Eğitim Scheduler
Haftalık/aylık otomatik model yeniden eğitimi için scheduler.
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from typing import Dict, Any

from ml.run_training_pipeline import MLTrainingPipeline
from ml.model_version_manager import MLModelVersionManager
from ml.ml_monitor import MLMonitor

class AutoRetrainScheduler:
    """Otomatik ML model yeniden eğitim scheduler'ı."""
    
    def __init__(self, retrain_frequency: str = "weekly"):
        """
        Args:
            retrain_frequency: "weekly" veya "monthly"
        """
        self.retrain_frequency = retrain_frequency
        self.pipeline = MLTrainingPipeline()
        self.model_manager = MLModelVersionManager()
        self.ml_monitor = MLMonitor()
        
        # Retrain geçmişi
        self.retrain_history_file = Path("reports/retrain_history.jsonl")
        self.retrain_history_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🔄 Auto-retrain scheduler initialized: {retrain_frequency}")
    
    def schedule_retrain(self):
        """Retrain işlemini zamanla."""
        if self.retrain_frequency == "weekly":
            # Her Pazar gecesi 02:00'da
            schedule.every().sunday.at("02:00").do(self._run_retrain)
            logger.info("📅 Weekly retrain scheduled: Every Sunday at 02:00")
            
        elif self.retrain_frequency == "monthly":
            # Her ayın 1'inde 02:00'da
            schedule.every().month.do(self._run_retrain)
            logger.info("📅 Monthly retrain scheduled: 1st of every month at 02:00")
        
        else:
            raise ValueError(f"Invalid retrain_frequency: {self.retrain_frequency}")
    
    def _run_retrain(self):
        """Retrain işlemini çalıştır."""
        logger.info("🚀 Starting scheduled retrain...")
        
        retrain_start = datetime.now()
        retrain_id = f"retrain_{retrain_start.strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Mevcut aktif modeli kaydet
            current_active = self.model_manager.get_active_model_version()
            current_metadata = self.model_manager.get_model_metadata(current_active) if current_active else {}
            
            # Yeni model eğit
            results = asyncio.run(self.pipeline.run_complete_pipeline())
            
            # Retrain geçmişini kaydet
            retrain_record = {
                "retrain_id": retrain_id,
                "start_time": retrain_start.isoformat(),
                "end_time": datetime.now().isoformat(),
                "previous_active": current_active,
                "new_active": results.get("steps", {}).get("auto_deployment", {}).get("status"),
                "status": results.get("final_status"),
                "metrics": results.get("steps", {}).get("model_training", {}).get("metrics", {}),
                "total_bars": results.get("steps", {}).get("data_collection", {}).get("total_bars", 0)
            }
            
            # JSONL formatında kaydet
            with open(self.retrain_history_file, 'a') as f:
                import json
                f.write(json.dumps(retrain_record) + '\n')
            
            logger.info(f"✅ Scheduled retrain completed: {retrain_id}")
            logger.info(f"📊 New model metrics: {retrain_record['metrics']}")
            
        except Exception as e:
            logger.error(f"❌ Scheduled retrain failed: {e}")
            
            # Hata kaydı
            error_record = {
                "retrain_id": retrain_id,
                "start_time": retrain_start.isoformat(),
                "end_time": datetime.now().isoformat(),
                "status": "FAILED",
                "error": str(e)
            }
            
            with open(self.retrain_history_file, 'a') as f:
                import json
                f.write(json.dumps(error_record) + '\n')
    
    def run_scheduler(self):
        """Scheduler'ı çalıştır (sonsuz döngü)."""
        logger.info("🔄 Starting auto-retrain scheduler...")
        
        # İlk retrain'i zamanla
        self.schedule_retrain()
        
        # Scheduler döngüsü
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Her dakika kontrol et
            except KeyboardInterrupt:
                logger.info("🛑 Auto-retrain scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                time.sleep(300)  # 5 dakika bekle ve tekrar dene
    
    def get_retrain_history(self, limit: int = 10) -> list:
        """Retrain geçmişini getir."""
        if not self.retrain_history_file.exists():
            return []
        
        history = []
        with open(self.retrain_history_file, 'r') as f:
            for line in f:
                try:
                    import json
                    history.append(json.loads(line.strip()))
                except:
                    continue
        
        return history[-limit:]  # Son N kayıt
    
    def get_next_retrain_time(self) -> str:
        """Bir sonraki retrain zamanını getir."""
        if self.retrain_frequency == "weekly":
            next_run = schedule.next_run()
            return next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "Not scheduled"
        elif self.retrain_frequency == "monthly":
            return "1st of next month at 02:00"
        return "Unknown"

def main():
    """Ana fonksiyon - scheduler'ı çalıştır."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-retrain scheduler")
    parser.add_argument("--frequency", choices=["weekly", "monthly"], 
                       default="weekly", help="Retrain frequency")
    parser.add_argument("--run-once", action="store_true", 
                       help="Run retrain once and exit")
    
    args = parser.parse_args()
    
    scheduler = AutoRetrainScheduler(retrain_frequency=args.frequency)
    
    if args.run_once:
        logger.info("🔄 Running one-time retrain...")
        scheduler._run_retrain()
    else:
        scheduler.run_scheduler()

if __name__ == "__main__":
    main()

