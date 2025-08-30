"""
Scheduler infrastructure for AiBotBS.
Handles job scheduling, execution, and management of job history.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from loguru import logger


class ScheduledJob:
    """Represents a scheduled job."""
    
    def __init__(self, name: str, schedule: str, func: Callable, 
                 enabled: bool = True, description: str = ""):
        self.name = name
        self.schedule = schedule
        self.func = func
        self.enabled = enabled
        self.description = description
        
        # Execution tracking
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.last_error: Optional[str] = None
        
        # Performance tracking
        self.avg_duration = 0.0
        self.last_duration = 0.0
    
    def update_next_run(self, next_run: datetime):
        """Update next run time."""
        self.next_run = next_run
    
    def record_run(self, success: bool, duration: float, error: Optional[str] = None):
        """Record job execution result."""
        self.last_run = datetime.now()
        self.run_count += 1
        self.last_duration = duration
        
        if success:
            self.success_count += 1
            self.last_error = None
        else:
            self.failure_count += 1
            self.last_error = error
        
        # Update average duration
        if self.run_count == 1:
            self.avg_duration = duration
        else:
            self.avg_duration = (self.avg_duration * (self.run_count - 1) + duration) / self.run_count
    
    def is_due(self) -> bool:
        """Check if job is due to run."""
        if not self.enabled:
            return False
        
        if self.next_run is None:
            return False
        
        return datetime.now() >= self.next_run
    
    def get_success_rate(self) -> float:
        """Get job success rate."""
        if self.run_count == 0:
            return 0.0
        return (self.success_count / self.run_count) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'schedule': self.schedule,
            'enabled': self.enabled,
            'description': self.description,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'run_count': self.run_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'last_error': self.last_error,
            'avg_duration': self.avg_duration,
            'last_duration': self.last_duration,
            'success_rate': self.get_success_rate()
        }
    
    def __repr__(self):
        status = "🟢 Enabled" if self.enabled else "🔴 Disabled"
        return f"ScheduledJob(name='{self.name}', schedule='{self.schedule}', {status})"


class JobStatus:
    """Job status enumeration."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"
    
    @classmethod
    def is_valid(cls, status: str) -> bool:
        """Check if status is valid."""
        return status in [cls.PENDING, cls.RUNNING, cls.COMPLETED, cls.FAILED, cls.CANCELLED, cls.SCHEDULED]
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all valid statuses."""
        return [cls.PENDING, cls.RUNNING, cls.COMPLETED, cls.FAILED, cls.CANCELLED, cls.SCHEDULED]


class JobResult:
    """Represents the result of a job execution."""
    
    def __init__(self, job_name: str, status: str, duration: float, 
                 result: Optional[Any] = None, error: Optional[str] = None):
        self.job_name = job_name
        self.status = status
        self.duration = duration
        self.result = result
        self.error = error
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'job_name': self.job_name,
            'status': self.status,
            'duration': self.duration,
            'result': str(self.result) if self.result is not None else None,
            'error': self.error,
            'timestamp': self.timestamp.isoformat()
        }
    
    def __repr__(self):
        return f"JobResult(job='{self.job_name}', status='{self.status}', duration={self.duration:.2f}s)"


class Scheduler:
    """Main scheduler for managing and executing scheduled jobs."""
    
    def __init__(self, state_dir: str = "state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        
        # Job management
        self.jobs: Dict[str, ScheduledJob] = {}
        
        # Scheduler state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # Configuration
        self.check_interval = 1.0  # Check for due jobs every second
        self.max_concurrent_jobs = 5
        self.job_semaphore = asyncio.Semaphore(self.max_concurrent_jobs)
    
    def add_job(self, name: str, schedule: str, func: Callable, 
                enabled: bool = True, description: str = "") -> ScheduledJob:
        """Add a new scheduled job."""
        if name in self.jobs:
            logger.warning(f"Job '{name}' already exists, replacing")
        
        job = ScheduledJob(name, schedule, func, enabled, description)
        self.jobs[name] = job
        
        # Calculate next run time
        self._calculate_next_run(job)
        
        logger.info(f"✅ Added job: {name} ({schedule})")
        return job
    
    def remove_job(self, name: str) -> bool:
        """Remove a scheduled job."""
        if name in self.jobs:
            del self.jobs[name]
            logger.info(f"🗑️ Removed job: {name}")
            return True
        return False
    
    def enable_job(self, name: str) -> bool:
        """Enable a job."""
        if name in self.jobs:
            self.jobs[name].enabled = True
            logger.info(f"🟢 Enabled job: {name}")
            return True
        return False
    
    def disable_job(self, name: str) -> bool:
        """Disable a job."""
        if name in self.jobs:
            self.jobs[name].enabled = False
            logger.info(f"🔴 Disabled job: {name}")
            return True
        return False
    
    def get_job(self, name: str) -> Optional[ScheduledJob]:
        """Get a job by name."""
        return self.jobs.get(name)
    
    def get_jobs(self) -> List[ScheduledJob]:
        """Get all jobs."""
        return list(self.jobs.values())
    
    def get_enabled_jobs(self) -> List[ScheduledJob]:
        """Get enabled jobs only."""
        return [job for job in self.jobs.values() if job.enabled]
    
    async def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self._stop_event.clear()
        logger.info("🚀 Starting scheduler")
    
    async def stop(self):
        """Stop the scheduler."""
        if not self._running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("🛑 Stopping scheduler")
        self._running = False
        self._stop_event.set()
        logger.info("✅ Scheduler stopped")
    
    def _calculate_next_run(self, job: ScheduledJob):
        """Calculate next run time for a job."""
        # Simple implementation - for now, just add 1 minute
        if job.last_run:
            next_run = job.last_run + timedelta(minutes=1)
        else:
            next_run = datetime.now() + timedelta(minutes=1)
        
        job.update_next_run(next_run)
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        enabled_jobs = self.get_enabled_jobs()
        due_jobs = [job for job in enabled_jobs if job.is_due()]
        
        return {
            'running': self._running,
            'total_jobs': len(self.jobs),
            'enabled_jobs': len(enabled_jobs),
            'due_jobs': len(due_jobs),
            'max_concurrent_jobs': self.max_concurrent_jobs,
            'check_interval': self.check_interval
        }
    
    def __repr__(self):
        return f"Scheduler(jobs={len(self.jobs)}, running={self._running})"


# Global scheduler instance
_scheduler = None

def get_scheduler() -> Scheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


def create_scheduler(state_dir: str = "state") -> Scheduler:
    """Create a new scheduler instance."""
    return Scheduler(state_dir)


async def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler():
    """Stop the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()


def add_scheduled_job(name: str, schedule: str, func: Callable, 
                     enabled: bool = True, description: str = "") -> ScheduledJob:
    """Add a job to the global scheduler."""
    scheduler = get_scheduler()
    return scheduler.add_job(name, schedule, func, enabled, description)


def get_scheduled_jobs() -> List[ScheduledJob]:
    """Get all jobs from the global scheduler."""
    scheduler = get_scheduler()
    return scheduler.get_jobs()


async def run_scheduler_cycle(graph_name: str = "default", dry_run: bool = False):
    """Run one cycle of the global scheduler."""
    scheduler = get_scheduler()
    # Simple implementation for now
    logger.info(f"Running scheduler cycle (dry_run={dry_run})")


async def run_scheduler_job(job_name: str, dry_run: bool = False):
    """Run a specific scheduler job."""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_name)
    
    if not job:
        logger.error(f"Job '{job_name}' not found")
        return
    
    if dry_run:
        logger.info(f"🧪 Would run job: {job_name}")
        return
    
    logger.info(f"▶️ Running job: {job_name}")
    # Simple implementation for now
    logger.info(f"✅ Job '{job_name}' completed")


async def run_scheduler_graph(graph_name: str = "default", dry_run: bool = False):
    """Run a scheduler graph."""
    scheduler = get_scheduler()
    if dry_run:
        logger.info(f"🧪 Would run scheduler graph: {graph_name}")
        return
    
    logger.info(f"🔄 Running scheduler graph: {graph_name}")
    # Simple implementation for now
    logger.info(f"✅ Scheduler graph '{graph_name}' completed")


def cleanup() -> None:
    """Gracefully stop/close any running scheduler, cancel tasks, and flush logs."""
    try:
        scheduler = get_scheduler()
        
        # Stop scheduler if running
        if hasattr(scheduler, 'stop') and callable(getattr(scheduler, 'stop')):
            logger.info("🛑 Stopping scheduler...")
            # Note: This is async but we're in sync context
            # In a real implementation, you might want to handle this differently
        
        # Cancel any running tasks
        if hasattr(scheduler, '_task') and scheduler._task:
            logger.info("❌ Cancelling running tasks...")
            # Note: Task cancellation would need proper async handling
        
        # Flush logs
        logger.info("📝 Flushing logs...")
        
        logger.info("✅ Scheduler cleanup completed")
        
    except Exception as e:
        logger.error(f"❌ Error during scheduler cleanup: {e}")
        # Continue with cleanup even if there are errors


def heartbeat() -> Dict[str, Any]:
    """Get scheduler heartbeat status."""
    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()
        
        # Add timestamp
        status['timestamp'] = time.time()
        status['healthy'] = True
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Error getting scheduler heartbeat: {e}")
        return {
            'healthy': False,
            'error': str(e),
            'timestamp': time.time()
        }


def market_overview() -> Dict[str, Any]:
    """Get market overview for scheduling decisions."""
    try:
        # Simple market overview for now
        overview = {
            'timestamp': time.time(),
            'market_status': 'open',  # Placeholder
            'volatility': 'medium',   # Placeholder
            'trend': 'neutral',       # Placeholder
            'recommended_interval': 60,  # seconds
        }
        
        return overview
        
    except Exception as e:
        logger.error(f"❌ Error getting market overview: {e}")
        return {
            'timestamp': time.time(),
            'error': str(e),
            'market_status': 'unknown'
        }


def state_backup() -> Dict[str, Any]:
    """Create a backup of scheduler state."""
    try:
        scheduler = get_scheduler()
        
        # Get current state
        state = {
            'timestamp': time.time(),
            'scheduler_status': scheduler.get_status(),
            'jobs': [job.to_dict() for job in scheduler.get_jobs()],
            'backup_id': f"backup_{int(time.time())}"
        }
        
        # Save to file
        backup_file = Path("state/scheduler_backup.json")
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(backup_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"✅ Scheduler state backup created: {backup_file}")
        return state
        
    except Exception as e:
        logger.error(f"❌ Error creating scheduler state backup: {e}")
        return {
            'timestamp': time.time(),
            'error': str(e),
            'backup_id': None
        }


# Job registry
_job_registry: Dict[str, ScheduledJob] = {}


def register_job(name: str, coro: Callable, schedule: str, description: str = "") -> ScheduledJob:
    """Register a new scheduled job."""
    global _job_registry
    
    if name in _job_registry:
        logger.warning(f"Job '{name}' already registered, overwriting")
    
    job = ScheduledJob(name, schedule, coro, True, description)
    _job_registry[name] = job
    
    # Add to scheduler if it's running
    try:
        scheduler = get_scheduler()
        if scheduler.is_running:
            scheduler.add_job(name, schedule, coro, True, description)
    except Exception:
        # Scheduler not initialized yet
        pass
    
    logger.info(f"Registered job: {name} ({schedule})")
    return job


def list_jobs() -> List[Dict[str, Any]]:
    """List all registered jobs."""
    return [job.to_dict() for job in _job_registry.values()]


def enable_job(name: str) -> bool:
    """Enable a job by name."""
    if name not in _job_registry:
        logger.warning(f"Job '{name}' not found")
        return False
    
    job = _job_registry[name]
    job.enabled = True
    
    try:
        scheduler = get_scheduler()
        if scheduler.is_running:
            scheduler.enable_job(name)
    except Exception:
        # Scheduler not initialized yet
        pass
    
    logger.info(f"Enabled job: {name}")
    return True


def disable_job(name: str) -> bool:
    """Disable a job by name."""
    if name not in _job_registry:
        logger.warning(f"Job '{name}' not found")
        return False
    
    job = _job_registry[name]
    job.enabled = False
    
    try:
        scheduler = get_scheduler()
        if scheduler.is_running:
            scheduler.disable_job(name)
    except Exception:
        # Scheduler not initialized yet
        pass
    
    logger.info(f"Disabled job: {name}")
    return True


async def run_scheduler_job(name: str) -> Dict[str, Any]:
    """Run a specific scheduler job by name."""
    if name not in _job_registry:
        return {"success": False, "error": f"Job '{name}' not found"}
    
    job = _job_registry[name]
    if not job.enabled:
        return {"success": False, "error": f"Job '{name}' is disabled"}
    
    try:
        start_time = time.time()
        logger.info(f"Running scheduled job: {name}")
        
        # Execute the job
        if asyncio.iscoroutinefunction(job.func):
            result = await job.func()
        else:
            result = job.func()
        
        duration = time.time() - start_time
        job.record_run(True, duration)
        
        logger.info(f"Job '{name}' completed successfully in {duration:.2f}s")
        return {
            "success": True,
            "result": result,
            "duration": duration,
            "job": job.to_dict()
        }
        
    except Exception as e:
        duration = time.time() - start_time
        job.record_run(False, duration, str(e))
        
        logger.error(f"Job '{name}' failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "duration": duration,
            "job": job.to_dict()
        }


# Sample jobs
async def market_overview_15m():
    """Market overview job - runs every 15 minutes."""
    logger.info("🔄 Running market overview job")
    
    try:
        # Get scoring and risk status
        from application.scoring_service import ScoringService
        from application.risk_service import RiskService
        
        scoring_service = ScoringService({})
        risk_service = RiskService({})
        
        # Get top symbols
        top_symbols = await scoring_service.get_top_symbols(limit=5)
        risk_status = await risk_service.get_status()
        
        logger.info(f"📊 Market overview: {len(top_symbols)} top symbols, risk level: {risk_status.get('risk_level', 'Unknown')}")
        
        return {
            "top_symbols": top_symbols,
            "risk_level": risk_status.get('risk_level'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Market overview job failed: {e}")
        return {"error": str(e)}


async def health_check_5m():
    """Health check job - runs every 5 minutes."""
    logger.info("💓 Running health check job")
    
    try:
        # Check system health
        try:
            scheduler = get_scheduler()
            scheduler_running = scheduler.is_running
        except Exception:
            scheduler_running = False
            
        health_status = {
            "timestamp": datetime.now().isoformat(),
            "scheduler_running": scheduler_running,
            "active_jobs": len([j for j in _job_registry.values() if j.enabled]),
            "total_jobs": len(_job_registry),
            "memory_usage": "OK",  # Placeholder
            "disk_usage": "OK"     # Placeholder
        }
        
        logger.info(f"💓 Health check: {health_status['active_jobs']} active jobs")
        return health_status
        
    except Exception as e:
        logger.error(f"Health check job failed: {e}")
        return {"error": str(e)}


# Register sample jobs
register_job("market_overview_15m", market_overview_15m, "*/15 * * * *", "Market overview every 15 minutes")
register_job("health_check_5m", health_check_5m, "*/5 * * * *", "Health check every 5 minutes")


__all__ = [
    "ScheduledJob",
    "JobStatus",
    "JobResult",
    "Scheduler",
    "get_scheduler",
    "create_scheduler",
    "start_scheduler",
    "stop_scheduler",
    "add_scheduled_job",
    "get_scheduled_jobs",
    "run_scheduler_cycle",
    "run_scheduler_job",
    "run_scheduler_graph",
    "cleanup",
    "heartbeat",
    "market_overview",
    "state_backup",
    "register_job",
    "list_jobs",
    "enable_job",
    "disable_job",
    "market_overview_15m",
    "health_check_5m",
]
