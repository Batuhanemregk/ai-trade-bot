"""
Run Watchdog - Monitors job execution and triggers catch-up for missed runs
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class RunWatchdog:
    """Monitors job execution and triggers catch-up for missed runs."""
    
    def __init__(self, policy: Dict, scheduler, jobs: Dict):
        self.policy = policy
        self.scheduler = scheduler
        self.jobs = jobs
        self.miss_threshold = 90  # seconds
        self.history_path = Path("data/run_history.jsonl")
        self.history_path.parent.mkdir(exist_ok=True)
        
        # Critical jobs to monitor
        self.critical_jobs = [
            'trading_analysis',
            'telegram_summary_15m',
            'trailing_5m',
            'news_incremental_5m'
        ]
        
        # Expected intervals (seconds)
        self.expected_intervals = {
            'trading_analysis': 900,      # 15 minutes
            'telegram_summary_15m': 900,  # 15 minutes
            'trailing_5m': 300,           # 5 minutes
            'news_incremental_5m': 300,   # 5 minutes
            'regime_1h': 3600,            # 1 hour
            'risk_monitor': 60            # 1 minute
        }
    
    async def check_missed_runs(self):
        """Check for missed runs and trigger catch-up if needed."""
        try:
            current_time = datetime.now(timezone.utc)
            
            for job_name in self.critical_jobs:
                if job_name not in self.jobs:
                    continue
                    
                expected_interval = self.expected_intervals.get(job_name, 300)
                last_run = await self._get_last_run_time(job_name)
                
                if last_run:
                    time_since_last = (current_time - last_run).total_seconds()
                    expected_next = last_run + timedelta(seconds=expected_interval)
                    
                    if time_since_last > expected_interval + self.miss_threshold:
                        logger.warning(f"[WATCHDOG] missed run for {job_name} expected={expected_next.strftime('%H:%M:%S')} actual={current_time.strftime('%H:%M:%S')}")
                        await self._trigger_catch_up(job_name)
                        
        except Exception as e:
            logger.error(f"[WATCHDOG] error checking missed runs: {e}")
    
    async def _get_last_run_time(self, job_name: str) -> Optional[datetime]:
        """Get the last run time for a job from history."""
        try:
            if not self.history_path.exists():
                return None
                
            last_run = None
            with open(self.history_path, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('name') == job_name and entry.get('status') == 'SUCCESS':
                            started_at = datetime.fromisoformat(entry['started_at'].replace('Z', '+00:00'))
                            if not last_run or started_at > last_run:
                                last_run = started_at
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                        
            return last_run
        except Exception as e:
            logger.error(f"[WATCHDOG] error getting last run time for {job_name}: {e}")
            return None
    
    async def _trigger_catch_up(self, job_name: str):
        """Trigger immediate catch-up for a missed job."""
        try:
            logger.info(f"[WATCHDOG] triggering catch-up for {job_name}")
            
            # Add immediate job execution
            self.scheduler.add_job(
                self._execute_catch_up,
                trigger='date',
                run_date=datetime.now(timezone.utc),
                args=[job_name],
                id=f'catchup_{job_name}_{int(datetime.now().timestamp())}',
                name=f'Catch-up {job_name}',
                replace_existing=True
            )
            
            # Send Telegram notification
            await self._send_missed_run_alert(job_name)
            
        except Exception as e:
            logger.error(f"[WATCHDOG] error triggering catch-up for {job_name}: {e}")
    
    async def _execute_catch_up(self, job_name: str):
        """Execute catch-up job."""
        try:
            logger.info(f"[WATCHDOG] executing catch-up for {job_name}")
            
            # Get the job instance and execute it
            job_instance = self.jobs.get(job_name)
            if job_instance:
                await job_instance.execute()
                logger.info(f"[WATCHDOG] catch-up completed for {job_name}")
            else:
                logger.error(f"[WATCHDOG] job instance not found for {job_name}")
                
        except Exception as e:
            logger.error(f"[WATCHDOG] error executing catch-up for {job_name}: {e}")
    
    async def _send_missed_run_alert(self, job_name: str):
        """Send Telegram alert for missed run."""
        try:
            from application.analysis_cards import AnalysisCardsService
            cards_service = AnalysisCardsService(self.policy)
            
            message = f"⚠️ **Job Missed Run Alert**\n\n"
            message += f"**Job:** {job_name}\n"
            message += f"**Time:** {datetime.now().strftime('%H:%M:%S')}\n"
            message += f"**Status:** Catch-up triggered\n"
            
            await cards_service.telegram_client.send_message(message)
            
        except Exception as e:
            logger.error(f"[WATCHDOG] error sending missed run alert: {e}")
    
    async def log_job_run(self, job_name: str, status: str, duration_ms: int, error: str = None):
        """Log job run to history file."""
        try:
            entry = {
                "name": job_name,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "status": status,
                "duration_ms": duration_ms,
                "error": error
            }
            
            with open(self.history_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')
                
        except Exception as e:
            logger.error(f"[WATCHDOG] error logging job run: {e}")
    
    async def get_recent_runs(self, limit: int = 10) -> list:
        """Get recent job runs for summary."""
        try:
            if not self.history_path.exists():
                return []
                
            runs = []
            with open(self.history_path, 'r') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        entry = json.loads(line.strip())
                        runs.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
                        
            return runs
        except Exception as e:
            logger.error(f"[WATCHDOG] error getting recent runs: {e}")
            return []
