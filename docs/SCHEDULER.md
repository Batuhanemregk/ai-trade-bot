# ⏰ Scheduler Guide

> **Job Scheduling and Task Management System**

## 🎯 Overview

The AiBotBS scheduler system provides a robust job management platform for executing periodic tasks, scheduled operations, and system maintenance. It supports both cron-style scheduling and interval-based execution.

## 🏗️ Scheduler Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Trade Service  │  │ Portfolio Svc   │  │  Risk Svc   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Scheduler Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Job Registry    │  │ Job Executor    │  │ Job Monitor │ │
│  │   Registration  │  │   Execution     │  │   Health    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Cron Parser     │  │ Interval Timer  │  │ Job Queue   │ │
│  │   Schedule      │  │   Execution     │  │  Management │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Logging       │  │   Metrics       │  │   Storage   │ │
│  │   System        │  │   Collection    │  │   State     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Job API

### Core Functions

#### `register_job(name, coro, schedule, **kwargs)`
Register a new scheduled job.

```python
from infrastructure.scheduler import register_job

# Register cron job
await register_job(
    name="market_overview_15m",
    coro=market_overview_task,
    schedule="*/15 * * * *",  # Every 15 minutes
    description="Market overview analysis"
)

# Register interval job
await register_job(
    name="health_check_5m",
    coro=health_check_task,
    schedule=300,  # Every 300 seconds (5 minutes)
    description="System health check"
)
```

#### `list_jobs()`
List all registered jobs with their status.

```python
from infrastructure.scheduler import list_jobs

jobs = await list_jobs()
for job in jobs:
    print(f"{job['name']}: {job['status']} ({job['schedule']})")
```

#### `enable_job(name)` / `disable_job(name)`
Enable or disable specific jobs.

```python
from infrastructure.scheduler import enable_job, disable_job

# Disable job temporarily
await disable_job("market_overview_15m")

# Re-enable job
await enable_job("market_overview_15m")
```

#### `run_scheduler_job(name)`
Manually execute a specific job.

```python
from infrastructure.scheduler import run_scheduler_job

# Run job immediately
result = await run_scheduler_job("market_overview_15m")
print(f"Job result: {result}")
```

#### `cleanup()`
Clean up completed jobs and free resources.

```python
from infrastructure.scheduler import cleanup

# Clean up scheduler
await cleanup()
```

## ⏰ Schedule Types

### 1. Cron Schedule
Standard cron format: `minute hour day month weekday`

```python
# Examples
"*/15 * * * *"      # Every 15 minutes
"0 */2 * * *"       # Every 2 hours
"0 9 * * 1-5"       # 9 AM on weekdays
"0 0 1 * *"         # First day of each month
"0 12 * * 0"        # Noon on Sundays
```

### 2. Interval Schedule
Time-based intervals in seconds.

```python
# Examples
300                 # Every 5 minutes
3600                # Every hour
86400               # Daily
604800              # Weekly
```

### 3. Custom Schedule
Advanced scheduling patterns.

```python
# Market hours only (9 AM - 5 PM UTC)
"0 9-17 * * 1-5"   # Every hour during market hours

# Multiple times per day
"0 9,12,15,18 * * *"  # 9 AM, 12 PM, 3 PM, 6 PM

# Weekend special
"0 10 * * 6,0"     # 10 AM on weekends
```

## 📋 Built-in Jobs

### 1. Market Overview Job
**Name**: `market_overview_15m`  
**Schedule**: `*/15 * * * *` (Every 15 minutes)  
**Purpose**: Generate market overview and scoring updates

```python
async def market_overview_task():
    """Generate market overview every 15 minutes."""
    
    try:
        # Get market data
        symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
        market_data = await get_market_data(symbols)
        
        # Generate scoring
        scoring_results = await scoring_service.analyze_markets(market_data)
        
        # Update portfolio
        await portfolio_service.update_positions()
        
        # Log results
        logger.info(f"Market overview completed: {len(symbols)} symbols analyzed")
        
        return {
            "status": "success",
            "symbols_analyzed": len(symbols),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Market overview failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### 2. Health Check Job
**Name**: `health_check_5m`  
**Schedule**: `*/5 * * * *` (Every 5 minutes)  
**Purpose**: Monitor system health and dependencies

```python
async def health_check_task():
    """Perform system health check every 5 minutes."""
    
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "overall": "healthy",
        "components": {},
        "warnings": []
    }
    
    try:
        # Check exchange connectivity
        exchange_health = await check_exchange_health()
        health_status["components"]["exchange"] = exchange_health
        
        # Check agent system
        agent_health = await check_agent_health()
        health_status["components"]["agents"] = agent_health
        
        # Check database connectivity
        db_health = await check_database_health()
        health_status["components"]["database"] = db_health
        
        # Determine overall status
        if any(comp.get("status") == "error" for comp in health_status["components"].values()):
            health_status["overall"] = "error"
        elif any(comp.get("status") == "warning" for comp in health_status["components"].values()):
            health_status["overall"] = "warning"
        
        # Log status
        if health_status["overall"] != "healthy":
            logger.warning(f"Health check: {health_status['overall']}")
        else:
            logger.debug("Health check: all systems healthy")
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

### 3. Data Cleanup Job
**Name**: `data_cleanup_daily`  
**Schedule**: `0 2 * * *` (2 AM daily)  
**Purpose**: Clean up old data and logs

```python
async def data_cleanup_task():
    """Clean up old data daily at 2 AM."""
    
    try:
        cleanup_results = {
            "timestamp": datetime.now().isoformat(),
            "logs_cleaned": 0,
            "data_cleaned": 0,
            "storage_freed": 0
        }
        
        # Clean old log files
        logs_cleaned = await cleanup_old_logs(days_to_keep=30)
        cleanup_results["logs_cleaned"] = logs_cleaned
        
        # Clean old market data
        data_cleaned = await cleanup_old_market_data(days_to_keep=7)
        cleanup_results["data_cleaned"] = data_cleaned
        
        # Clean temporary files
        temp_cleaned = await cleanup_temp_files()
        cleanup_results["temp_cleaned"] = temp_cleaned
        
        # Calculate storage freed
        storage_freed = await calculate_storage_freed()
        cleanup_results["storage_freed"] = storage_freed
        
        logger.info(f"Data cleanup completed: {logs_cleaned} logs, {data_cleaned} datasets, {storage_freed} MB freed")
        
        return cleanup_results
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
```

## 🚀 Custom Job Creation

### 1. Define Job Function
```python
async def custom_market_analysis():
    """Custom market analysis job."""
    
    # Your custom logic here
    symbols = ["BTC-USDT", "ETH-USDT"]
    
    for symbol in symbols:
        # Perform analysis
        analysis = await analyze_symbol(symbol)
        
        # Store results
        await store_analysis_results(symbol, analysis)
        
        # Send notifications if needed
        if analysis.get("alert"):
            await send_alert(symbol, analysis)
    
    return {"status": "success", "symbols_analyzed": len(symbols)}
```

### 2. Register Custom Job
```python
from infrastructure.scheduler import register_job

# Register custom job
await register_job(
    name="custom_market_analysis",
    coro=custom_market_analysis,
    schedule="0 */4 * * *",  # Every 4 hours
    description="Custom market analysis",
    enabled=True,
    max_retries=3,
    timeout=300
)
```

### 3. Job Configuration Options
```python
job_config = {
    "name": "job_name",           # Unique job identifier
    "coro": job_function,         # Async function to execute
    "schedule": "*/15 * * * *",   # Cron or interval schedule
    "description": "Job description",  # Human-readable description
    "enabled": True,              # Whether job is active
    "max_retries": 3,             # Maximum retry attempts
    "timeout": 300,               # Execution timeout (seconds)
    "retry_delay": 60,            # Delay between retries (seconds)
    "tags": ["trading", "analysis"],  # Job categorization
    "priority": "normal"          # Job priority (low/normal/high)
}
```

## 📊 Job Monitoring

### 1. Job Status
```python
from infrastructure.scheduler import get_job_status

# Get specific job status
status = await get_job_status("market_overview_15m")
print(f"Status: {status['status']}")
print(f"Last Run: {status['last_run']}")
print(f"Next Run: {status['next_run']}")
print(f"Success Count: {status['success_count']}")
print(f"Error Count: {status['error_count']}")
```

### 2. Job Metrics
```python
from infrastructure.scheduler import get_job_metrics

# Get job performance metrics
metrics = await get_job_metrics("market_overview_15m")
print(f"Average Runtime: {metrics['avg_runtime']:.2f}s")
print(f"Success Rate: {metrics['success_rate']:.1%}")
print(f"Last Error: {metrics['last_error']}")
```

### 3. System Health
```python
from infrastructure.scheduler import get_system_health

# Get overall scheduler health
health = await get_system_health()
print(f"Total Jobs: {health['total_jobs']}")
print(f"Running Jobs: {health['running_jobs']}")
print(f"Failed Jobs: {health['failed_jobs']}")
print(f"System Status: {health['status']}")
```

## 🔧 Job Management

### 1. Start/Stop Scheduler
```python
from infrastructure.scheduler import start_scheduler, stop_scheduler

# Start scheduler
await start_scheduler()

# Stop scheduler gracefully
await stop_scheduler()
```

### 2. Job Lifecycle
```python
from infrastructure.scheduler import (
    register_job, enable_job, disable_job, 
    run_scheduler_job, remove_job
)

# Complete job lifecycle
job_name = "test_job"

# 1. Register job
await register_job(
    name=job_name,
    coro=test_function,
    schedule="*/5 * * * *"
)

# 2. Enable job
await enable_job(job_name)

# 3. Run job manually
result = await run_scheduler_job(job_name)

# 4. Disable job
await disable_job(job_name)

# 5. Remove job
await remove_job(job_name)
```

### 3. Batch Operations
```python
from infrastructure.scheduler import batch_operation

# Enable multiple jobs
await batch_operation(
    operation="enable",
    job_names=["market_overview_15m", "health_check_5m"]
)

# Disable all jobs
await batch_operation(operation="disable", job_names="all")

# Restart failed jobs
await batch_operation(operation="restart", job_names="failed")
```

## 🚨 Error Handling

### 1. Job Retry Logic
```python
async def resilient_job():
    """Job with automatic retry logic."""
    
    max_attempts = 3
    attempt = 1
    
    while attempt <= max_attempts:
        try:
            # Job logic here
            result = await perform_job_task()
            
            # Success - return result
            return result
            
        except Exception as e:
            logger.warning(f"Job attempt {attempt} failed: {e}")
            
            if attempt == max_attempts:
                # Final attempt failed
                logger.error(f"Job failed after {max_attempts} attempts: {e}")
                raise
            
            # Wait before retry
            await asyncio.sleep(60 * attempt)  # Exponential backoff
            attempt += 1
```

### 2. Error Notifications
```python
async def notify_job_failure(job_name: str, error: Exception):
    """Notify administrators of job failures."""
    
    error_message = {
        "job_name": job_name,
        "error": str(error),
        "timestamp": datetime.now().isoformat(),
        "stack_trace": traceback.format_exc()
    }
    
    # Send Telegram notification
    await telegram_bot.send_message(
        f"🚨 Job Failure: {job_name}\n"
        f"Error: {error}\n"
        f"Time: {error_message['timestamp']}"
    )
    
    # Log error
    logger.error(f"Job {job_name} failed: {error}")
    
    # Store error for analysis
    await store_job_error(job_name, error_message)
```

## 📈 Performance Optimization

### 1. Job Concurrency
```python
# Configure concurrent job execution
scheduler_config = {
    "max_concurrent_jobs": 5,
    "job_queue_size": 100,
    "worker_timeout": 300
}

# Start scheduler with configuration
await start_scheduler(config=scheduler_config)
```

### 2. Resource Management
```python
async def resource_aware_job():
    """Job that manages its own resources."""
    
    # Check available resources
    if not await check_system_resources():
        logger.warning("Insufficient resources, skipping job")
        return {"status": "skipped", "reason": "insufficient_resources"}
    
    try:
        # Acquire resources
        await acquire_resources()
        
        # Execute job
        result = await execute_job_logic()
        
        return result
        
    finally:
        # Always release resources
        await release_resources()
```

### 3. Job Prioritization
```python
# High priority jobs
await register_job(
    name="critical_health_check",
    coro=critical_health_check,
    schedule="*/1 * * * *",  # Every minute
    priority="high"
)

# Normal priority jobs
await register_job(
    name="market_overview_15m",
    coro=market_overview,
    schedule="*/15 * * * *",  # Every 15 minutes
    priority="normal"
)

# Low priority jobs
await register_job(
    name="data_cleanup_daily",
    coro=data_cleanup,
    schedule="0 2 * * *",  # 2 AM daily
    priority="low"
)
```

## 🔧 Configuration

### Scheduler Configuration
```yaml
scheduler:
  # General settings
  enabled: true
  max_concurrent_jobs: 5
  job_queue_size: 100
  
  # Job settings
  default_timeout: 300
  default_max_retries: 3
  default_retry_delay: 60
  
  # Performance settings
  worker_timeout: 300
  cleanup_interval: 3600
  
  # Monitoring settings
  enable_metrics: true
  enable_health_checks: true
  health_check_interval: 300
```

### Environment Variables
```bash
# Scheduler settings
SCHEDULER_ENABLED=true
SCHEDULER_MAX_CONCURRENT_JOBS=5
SCHEDULER_DEFAULT_TIMEOUT=300

# Job settings
SCHEDULER_DEFAULT_MAX_RETRIES=3
SCHEDULER_DEFAULT_RETRY_DELAY=60

# Performance settings
SCHEDULER_WORKER_TIMEOUT=300
SCHEDULER_CLEANUP_INTERVAL=3600
```

## 📊 Monitoring & Metrics

### 1. Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Job execution metrics
job_executions = Counter('scheduler_job_executions_total', 'Total job executions', ['job_name', 'status'])
job_duration = Histogram('scheduler_job_duration_seconds', 'Job execution duration', ['job_name'])
active_jobs = Gauge('scheduler_active_jobs', 'Number of currently running jobs')

# Record job metrics
async def record_job_metrics(job_name: str, duration: float, status: str):
    """Record job execution metrics."""
    
    job_executions.labels(job_name=job_name, status=status).inc()
    job_duration.labels(job_name=job_name).observe(duration)
    
    if status == "running":
        active_jobs.inc()
    elif status in ["completed", "failed"]:
        active_jobs.dec()
```

### 2. Health Dashboard
```python
async def generate_health_dashboard():
    """Generate scheduler health dashboard."""
    
    dashboard = {
        "timestamp": datetime.now().isoformat(),
        "scheduler_status": "healthy",
        "total_jobs": 0,
        "active_jobs": 0,
        "failed_jobs": 0,
        "job_summary": {},
        "system_metrics": {}
    }
    
    # Get job statistics
    jobs = await list_jobs()
    dashboard["total_jobs"] = len(jobs)
    
    for job in jobs:
        status = job.get("status", "unknown")
        dashboard["job_summary"][status] = dashboard["job_summary"].get(status, 0) + 1
        
        if status == "running":
            dashboard["active_jobs"] += 1
        elif status == "failed":
            dashboard["failed_jobs"] += 1
    
    # Determine overall status
    if dashboard["failed_jobs"] > 0:
        dashboard["scheduler_status"] = "warning"
    if dashboard["failed_jobs"] > 3:
        dashboard["scheduler_status"] = "error"
    
    return dashboard
```

---

**Next**: See [EXECUTION.md](EXECUTION.md) for trading execution, [TELEGRAM.md](TELEGRAM.md) for bot interface, or [CONFIG.md](CONFIG.md) for configuration details.
