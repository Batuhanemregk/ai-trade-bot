#!/usr/bin/env python3
"""
Professional Scheduler Runner for AiBotBS
Production-ready multi-job architecture with bar-aligned execution
"""

import asyncio
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from infrastructure.bootstrap import load_env, load_policy, init_logging
from application.jobs.trading_analysis import TradingAnalysisJob
from application.jobs.trailing_5m import Trailing5mJob
from application.jobs.regime_1h import Regime1hJob
from application.jobs.risk_monitor import RiskMonitorJob
from application.jobs.market_overview import MarketOverviewJob
from application.jobs.news_incremental_5m import NewsIncremental5mJob


class SchedulerRunner:
    """Professional scheduler runner with production features."""
    
    def __init__(self, policy_path: str = "configs/policy.yaml"):
        self.policy_path = policy_path
        self.policy = None
        self.scheduler = None
        self.semaphore = None
        self.jobs = {}
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # State persistence
        self.state_file = None
        self.runtime_state = {}
        
    async def initialize(self):
        """Initialize scheduler and load configuration."""
        try:
            # Load environment and policy
            load_env()
            self.policy = load_policy(self.policy_path)
            
            # Initialize state persistence
            self.state_file = Path(self.policy['idempotency']['persist_path'])
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            await self._load_runtime_state()
            
            # Initialize semaphore for concurrency control
            semaphore_limit = self.policy['scheduler']['semaphore_limit']
            self.semaphore = asyncio.Semaphore(semaphore_limit)
            
            # Initialize scheduler
            self.scheduler = AsyncIOScheduler(
                timezone=timezone.utc,
                job_defaults=self.policy['scheduler']['job_defaults']
            )
            
            # Initialize job classes
            await self._initialize_jobs()
            
            # Register jobs
            await self._register_jobs()
            
            logger.info("✅ Scheduler initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize scheduler: {e}")
            raise
    
    async def _initialize_jobs(self):
        """Initialize all job classes."""
        try:
            self.jobs = {
                'trading_analysis': TradingAnalysisJob(self.policy, self.semaphore, self.runtime_state),
                'trailing_5m': Trailing5mJob(self.policy, self.semaphore, self.runtime_state),
                'regime_1h': Regime1hJob(self.policy, self.semaphore, self.runtime_state),
                'risk_monitor': RiskMonitorJob(self.policy, self.semaphore, self.runtime_state),
                'market_overview': MarketOverviewJob(self.policy, self.semaphore, self.runtime_state),
                'news_incremental_5m': NewsIncremental5mJob(self.policy, self.semaphore, self.runtime_state),
            }
            
            # Initialize each job
            for job_name, job_instance in self.jobs.items():
                if hasattr(job_instance, 'initialize'):
                    await job_instance.initialize()
                logger.info(f"✅ Initialized job: {job_name}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize jobs: {e}")
            raise
    
    async def _register_jobs(self):
        """Register all jobs with the scheduler."""
        schedule_config = self.policy['schedule']
        
        # Trading Analysis (15m)
        self.scheduler.add_job(
            self._execute_job,
            CronTrigger.from_crontab(schedule_config['trading_15m']),
            args=['trading_analysis'],
            id='trading_analysis',
            name='Trading Analysis (15m)',
            replace_existing=True,
            second=7  # Align to 15m boundaries
        )
        
        # Trailing Stops (5m)
        self.scheduler.add_job(
            self._execute_job,
            CronTrigger.from_crontab(schedule_config['trailing_5m']),
            args=['trailing_5m'],
            id='trailing_5m',
            name='Trailing Stops (5m)',
            replace_existing=True,
            second=5  # Align to 5m boundaries
        )
        
        # News Incremental Update (5m)
        self.scheduler.add_job(
            self._execute_job,
            CronTrigger.from_crontab(schedule_config['trailing_5m']),  # Same schedule as trailing
            args=['news_incremental_5m'],
            id='news_incremental_5m',
            name='News Incremental Update (5m)',
            replace_existing=True,
            second=3  # Align to 5m boundaries, slightly offset
        )
        
        # Regime Update (1h)
        self.scheduler.add_job(
            self._execute_job,
            CronTrigger.from_crontab(schedule_config['regime_1h']),
            args=['regime_1h'],
            id='regime_1h',
            name='Regime Update (1h)',
            replace_existing=True,
            second=9  # Align to 1h boundaries
        )
        
        # Risk Monitor (1m)
        self.scheduler.add_job(
            self._execute_job,
            CronTrigger.from_crontab(schedule_config['risk_1m']),
            args=['risk_monitor'],
            id='risk_monitor',
            name='Risk Monitor (1m)',
            replace_existing=True,
            second=12  # Align to 1m boundaries
        )
        
        # Market Overview (15m)
        self.scheduler.add_job(
            self._execute_job,
            CronTrigger.from_crontab(schedule_config['market_overview']),
            args=['market_overview'],
            id='market_overview',
            name='Market Overview (15m)',
            replace_existing=True,
            second=3  # Align to 15m boundaries
        )
        
        logger.info("✅ All jobs registered with scheduler")
    
    async def _execute_job(self, job_name: str):
        """Execute a job with retry logic and monitoring."""
        start_time = datetime.now(timezone.utc)
        job_instance = self.jobs.get(job_name)
        
        if not job_instance:
            logger.error(f"❌ Job not found: {job_name}")
            return
        
        try:
            # Acquire semaphore for concurrency control
            async with self.semaphore:
                logger.info(f"[JOB] name={job_name} status=STARTING")
                
                # Execute job with retry logic
                await self._execute_with_retry(job_instance, job_name)
                
                # Log success
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(f"[JOB] name={job_name} status=SUCCESS dur={duration:.2f}s")
                
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"[JOB] name={job_name} status=FAILED dur={duration:.2f}s error={e}")
            
            # Save error state
            await self._save_runtime_state()
    
    async def _execute_with_retry(self, job_instance, job_name: str):
        """Execute job with exponential backoff retry."""
        retry_config = self.policy['scheduler']['retry']
        attempts = retry_config['attempts']
        backoff_seconds = retry_config['backoff_seconds']
        
        for attempt in range(attempts):
            try:
                await job_instance.execute()
                return  # Success
                
            except Exception as e:
                if attempt == attempts - 1:  # Last attempt
                    raise e
                
                # Wait before retry
                wait_time = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                logger.warning(f"[JOB] name={job_name} attempt={attempt + 1} retry_in={wait_time}s error={e}")
                await asyncio.sleep(wait_time)
    
    async def _load_runtime_state(self):
        """Load runtime state from persistent storage."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    self.runtime_state = json.load(f)
                logger.info(f"✅ Loaded runtime state from {self.state_file}")
            else:
                self.runtime_state = {
                    'last_processed_bars': {},
                    'job_status': {},
                    'position_states': {},
                    'last_cleanup': datetime.now(timezone.utc).isoformat()
                }
                logger.info("✅ Initialized new runtime state")
                
        except Exception as e:
            logger.error(f"❌ Failed to load runtime state: {e}")
            self.runtime_state = {}
    
    async def _save_runtime_state(self):
        """Save runtime state to persistent storage."""
        try:
            self.runtime_state['last_save'] = datetime.now(timezone.utc).isoformat()
            
            with open(self.state_file, 'w') as f:
                json.dump(self.runtime_state, f, indent=2)
                
        except Exception as e:
            logger.error(f"❌ Failed to save runtime state: {e}")
    
    async def start(self):
        """Start the scheduler."""
        try:
            self.scheduler.start()
            self.running = True
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            logger.info("🚀 Scheduler started successfully")
            logger.info("📊 Registered jobs:")
            for job in self.scheduler.get_jobs():
                logger.info(f"  - {job.name} ({job.id}): {job.next_run_time}")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the scheduler gracefully."""
        try:
            logger.info("🛑 Shutting down scheduler...")
            
            # Save final state
            await self._save_runtime_state()
            
            # Shutdown scheduler
            if self.scheduler:
                self.scheduler.shutdown(wait=True)
            
            self.running = False
            logger.info("✅ Scheduler stopped gracefully")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.stop())
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for scheduler runner."""
    try:
        # Initialize logging
        init_logging()
        
        # Create and initialize scheduler
        runner = SchedulerRunner()
        await runner.initialize()
        
        # Start scheduler
        await runner.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Scheduler runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
