#!/usr/bin/env python3
"""
Scheduler Health Check - Quick health check for running scheduler
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


def check_runtime_state():
    """Check runtime state file."""
    print("\n[CHECK] Runtime State")
    print("=" * 60)
    
    state_file = Path("data/runtime_state.json")
    
    if not state_file.exists():
        print("   [WARNING] No runtime state file found")
        print("   Scheduler may not have started yet")
        return False
    
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        last_save = state.get('last_save')
        if last_save:
            last_save_dt = datetime.fromisoformat(last_save.replace('Z', '+00:00'))
            time_since = (datetime.now(timezone.utc) - last_save_dt).total_seconds()
            
            print(f"   [OK] State file exists")
            print(f"   Last save: {last_save_dt.strftime('%Y-%m-%d %H:%M:%S')} ({time_since:.0f}s ago)")
            
            if time_since > 300:  # 5 minutes
                print(f"   [WARNING] State file is stale (>5 min)")
            
            # Check bar tracking
            bars = state.get('last_processed_bars', {})
            print(f"   Tracked bars: {len(bars)}")
            
            return True
        else:
            print("   [OK] State file exists (no timestamp)")
            return True
            
    except Exception as e:
        print(f"   [ERROR] Failed to read state: {e}")
        return False


def check_job_history():
    """Check job execution history."""
    print("\n[CHECK] Job History")
    print("=" * 60)
    
    history_file = Path("data/run_history.jsonl")
    
    if not history_file.exists():
        print("   [WARNING] No job history found")
        print("   Scheduler may not have started yet")
        return False
    
    try:
        recent_jobs = []
        with open(history_file, 'r') as f:
            lines = f.readlines()
            for line in lines[-20:]:  # Last 20 jobs
                try:
                    entry = json.loads(line.strip())
                    recent_jobs.append(entry)
                except:
                    continue
        
        if not recent_jobs:
            print("   [WARNING] No recent job executions found")
            return False
        
        # Analyze recent jobs
        success_count = sum(1 for j in recent_jobs if j.get('status') == 'SUCCESS')
        failed_count = sum(1 for j in recent_jobs if j.get('status') == 'FAILED')
        
        print(f"   [OK] Recent jobs: {len(recent_jobs)}")
        print(f"   Success: {success_count}, Failed: {failed_count}")
        
        # Check last execution
        last_job = recent_jobs[-1]
        job_name = last_job.get('name', 'unknown')
        job_status = last_job.get('status', 'unknown')
        job_time = last_job.get('started_at', 'unknown')
        job_duration = last_job.get('duration_ms', 0)
        
        print(f"\n   Last job:")
        print(f"   - Name: {job_name}")
        print(f"   - Status: {job_status}")
        print(f"   - Time: {job_time}")
        print(f"   - Duration: {job_duration}ms")
        
        # Check if scheduler is active (last job within 15 min)
        if job_time != 'unknown':
            try:
                job_dt = datetime.fromisoformat(job_time.replace('Z', '+00:00'))
                time_since = (datetime.now(timezone.utc) - job_dt).total_seconds()
                
                print(f"   - Time since: {time_since:.0f}s ago")
                
                if time_since > 900:  # 15 minutes
                    print(f"\n   [WARNING] Scheduler may not be running (last job >15min ago)")
                    return False
                else:
                    print(f"\n   [OK] Scheduler appears to be active")
                    return True
            except:
                pass
        
        return True
        
    except Exception as e:
        print(f"   [ERROR] Failed to read history: {e}")
        return False


def check_log_file():
    """Check main log file."""
    print("\n[CHECK] Log File")
    print("=" * 60)
    
    log_file = Path("logs/main.log")
    
    if not log_file.exists():
        print("   [WARNING] No log file found")
        return False
    
    try:
        # Get file size
        size_bytes = log_file.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        
        print(f"   [OK] Log file exists")
        print(f"   Size: {size_mb:.2f} MB")
        
        # Check recent errors
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            error_count = sum(1 for line in recent_lines if 'ERROR' in line)
            warning_count = sum(1 for line in recent_lines if 'WARNING' in line)
            
            print(f"   Recent errors (last 100 lines): {error_count}")
            print(f"   Recent warnings: {warning_count}")
            
            if error_count > 10:
                print(f"   [WARNING] High error count")
                return False
            
        return True
        
    except Exception as e:
        print(f"   [ERROR] Failed to read log: {e}")
        return False


def check_data_freshness():
    """Check if data files are being updated."""
    print("\n[CHECK] Data Freshness")
    print("=" * 60)
    
    files_to_check = [
        ("data/runtime_state.json", 300),      # Should update every 5 min
        ("data/run_history.jsonl", 900),       # Should update every 15 min
        ("data/news_llm_digest.json", 3600),   # Should update every hour
    ]
    
    all_fresh = True
    
    for file_path, max_age_seconds in files_to_check:
        path = Path(file_path)
        
        if not path.exists():
            print(f"   [WARNING] {file_path} - Not found")
            continue
        
        try:
            mod_time = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - mod_time).total_seconds()
            
            status = "[OK]" if age_seconds < max_age_seconds else "[STALE]"
            print(f"   {status} {file_path}")
            print(f"        Age: {age_seconds:.0f}s (max: {max_age_seconds}s)")
            
            if age_seconds >= max_age_seconds:
                all_fresh = False
                
        except Exception as e:
            print(f"   [ERROR] {file_path} - {e}")
            all_fresh = False
    
    return all_fresh


def main():
    """Run all health checks."""
    print("\n" + "=" * 60)
    print("SCHEDULER HEALTH CHECK")
    print("=" * 60)
    
    checks = [
        ("Runtime State", check_runtime_state),
        ("Job History", check_job_history),
        ("Log File", check_log_file),
        ("Data Freshness", check_data_freshness),
    ]
    
    results = []
    for check_name, check_func in checks:
        result = check_func()
        results.append((check_name, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("HEALTH SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "[HEALTHY]" if result else "[ISSUE]"
        print(f"   {status}: {check_name}")
    
    print(f"\n   Health score: {passed}/{total}")
    
    if passed == total:
        print("\n[OK] Scheduler is healthy and running normally")
        return 0
    elif passed >= total * 0.75:
        print("\n[WARNING] Scheduler has some issues but is mostly operational")
        return 1
    else:
        print("\n[ERROR] Scheduler has major issues or is not running")
        return 2


if __name__ == "__main__":
    sys.exit(main())

