"""
Health check endpoint for AI Trading Bot.
Provides system status, connectivity checks, and quick diagnostics.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any
from loguru import logger


class HealthChecker:
    """Centralized health checking system."""
    
    def __init__(self):
        self.checks = {}
        self.last_check_time = None
        
    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return aggregated status."""
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'checks': {}
        }
        
        # Run all checks
        checks_to_run = [
            ('okx_api', self._check_okx_api),
            ('telegram', self._check_telegram),
            ('scheduler', self._check_scheduler),
            ('metrics', self._check_metrics),
            ('logs', self._check_logs),
        ]
        
        for check_name, check_func in checks_to_run:
            try:
                check_result = await check_func()
                results['checks'][check_name] = check_result
                
                # Update overall status
                if check_result['status'] == 'fail':
                    results['status'] = 'unhealthy'
                elif check_result['status'] == 'warn' and results['status'] == 'healthy':
                    results['status'] = 'degraded'
                    
            except Exception as e:
                logger.error(f"Health check failed for {check_name}: {e}")
                results['checks'][check_name] = {
                    'status': 'fail',
                    'emoji': '❌',
                    'message': f'Check failed: {str(e)}'
                }
                results['status'] = 'unhealthy'
        
        self.last_check_time = datetime.utcnow()
        return results
    
    async def _check_okx_api(self) -> Dict[str, Any]:
        """Check OKX API connectivity and whitelist status."""
        try:
            from adapters.okx_client_facade import OKXClient
            
            # Try to create client
            client = OKXClient()
            
            # Try a simple API call
            try:
                # This will fail if IP not whitelisted
                ticker = await client.fetch_ticker('BTC-USDT-SWAP')
                
                return {
                    'status': 'ok',
                    'emoji': '✅',
                    'message': 'OKX API: Connected and whitelisted',
                    'details': {
                        'last_price': ticker.get('last') if ticker else None,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            except Exception as api_error:
                error_msg = str(api_error)
                
                # Check for IP whitelist error
                if 'IP' in error_msg and 'whitelist' in error_msg.lower():
                    return {
                        'status': 'fail',
                        'emoji': '❌',
                        'message': 'OKX API: IP not whitelisted',
                        'details': {'error': error_msg}
                    }
                else:
                    return {
                        'status': 'warn',
                        'emoji': '⚠️',
                        'message': f'OKX API: Error - {error_msg[:100]}',
                        'details': {'error': error_msg}
                    }
                    
        except ImportError:
            return {
                'status': 'warn',
                'emoji': '⚠️',
                'message': 'OKX API: Client not configured',
                'details': {}
            }
    
    async def _check_telegram(self) -> Dict[str, Any]:
        """Check Telegram bot connectivity."""
        try:
            from adapters.telegram_client import TelegramClient
            import os
            
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not telegram_token:
                return {
                    'status': 'warn',
                    'emoji': '⚠️',
                    'message': 'Telegram: Token not configured',
                    'details': {}
                }
            
            # Try to create client
            try:
                client = TelegramClient()
                return {
                    'status': 'ok',
                    'emoji': '✅',
                    'message': 'Telegram: Client initialized',
                    'details': {}
                }
            except Exception as e:
                return {
                    'status': 'warn',
                    'emoji': '⚠️',
                    'message': f'Telegram: {str(e)[:100]}',
                    'details': {'error': str(e)}
                }
                
        except ImportError:
            return {
                'status': 'warn',
                'emoji': '⚠️',
                'message': 'Telegram: Client not available',
                'details': {}
            }
    
    async def _check_scheduler(self) -> Dict[str, Any]:
        """Check scheduler status and job information."""
        try:
            # Check if scheduler module is available
            import infrastructure.scheduler as scheduler_module
            
            # Try to get scheduler instance
            if hasattr(scheduler_module, 'get_scheduler'):
                sched = scheduler_module.get_scheduler()
                
                if sched:
                    jobs = sched.get_jobs()
                    
                    return {
                        'status': 'ok',
                        'emoji': '✅',
                        'message': f'Scheduler: {len(jobs)} jobs registered',
                        'details': {
                            'job_count': len(jobs),
                            'jobs': [
                                {
                                    'id': job.id,
                                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None
                                }
                                for job in jobs[:5]  # First 5 jobs
                            ]
                        }
                    }
                else:
                    return {
                        'status': 'warn',
                        'emoji': '⚠️',
                        'message': 'Scheduler: Not running',
                        'details': {}
                    }
            else:
                return {
                    'status': 'warn',
                    'emoji': '⚠️',
                    'message': 'Scheduler: Instance not available',
                    'details': {}
                }
                
        except Exception as e:
            return {
                'status': 'warn',
                'emoji': '⚠️',
                'message': f'Scheduler: {str(e)[:100]}',
                'details': {'error': str(e)}
            }
    
    async def _check_metrics(self) -> Dict[str, Any]:
        """Check Prometheus metrics availability."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/metrics', timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        metric_count = len([l for l in text.split('\n') if l.startswith('aibot_')])
                        
                        return {
                            'status': 'ok',
                            'emoji': '✅',
                            'message': f'Metrics: {metric_count} bot metrics exposed',
                            'details': {
                                'endpoint': 'http://localhost:8000/metrics',
                                'metric_count': metric_count
                            }
                        }
                    else:
                        return {
                            'status': 'warn',
                            'emoji': '⚠️',
                            'message': f'Metrics: HTTP {resp.status}',
                            'details': {}
                        }
                        
        except Exception as e:
            return {
                'status': 'warn',
                'emoji': '⚠️',
                'message': 'Metrics: Endpoint not responding',
                'details': {'error': str(e)[:100]}
            }
    
    async def _check_logs(self) -> Dict[str, Any]:
        """Check log file status."""
        try:
            from pathlib import Path
            
            logs_dir = Path('logs')
            if not logs_dir.exists():
                return {
                    'status': 'warn',
                    'emoji': '⚠️',
                    'message': 'Logs: Directory not found',
                    'details': {}
                }
            
            log_files = list(logs_dir.glob('*.log'))
            total_size = sum(f.stat().st_size for f in log_files)
            total_size_mb = total_size / (1024 * 1024)
            
            return {
                'status': 'ok',
                'emoji': '✅',
                'message': f'Logs: {len(log_files)} files ({total_size_mb:.1f} MB)',
                'details': {
                    'file_count': len(log_files),
                    'total_size_mb': round(total_size_mb, 2),
                    'newest_file': log_files[-1].name if log_files else None
                }
            }
            
        except Exception as e:
            return {
                'status': 'warn',
                'emoji': '⚠️',
                'message': f'Logs: {str(e)[:100]}',
                'details': {}
            }
    
    def format_console_output(self, results: Dict[str, Any]) -> str:
        """Format health check results for console output."""
        lines = []
        lines.append("=" * 50)
        lines.append(f"  HEALTH CHECK - {results['timestamp']}")
        lines.append(f"  Overall Status: {results['status'].upper()}")
        lines.append("=" * 50)
        lines.append("")
        
        for check_name, check_result in results['checks'].items():
            emoji = check_result.get('emoji', '❓')
            message = check_result.get('message', 'No message')
            lines.append(f"{emoji} {check_name.upper()}: {message}")
            
            # Add details if available
            details = check_result.get('details', {})
            if details and isinstance(details, dict):
                for key, value in details.items():
                    if key != 'error':  # Skip errors in summary
                        lines.append(f"   └─ {key}: {value}")
        
        lines.append("")
        lines.append("=" * 50)
        
        return "\n".join(lines)


# Singleton instance
_health_checker = None


def get_health_checker() -> HealthChecker:
    """Get or create the global health checker instance."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


async def run_health_check_cli():
    """Run health check from CLI and print results."""
    checker = get_health_checker()
    results = await checker.check_all()
    print(checker.format_console_output(results))
    
    # Return exit code based on status
    if results['status'] == 'healthy':
        return 0
    elif results['status'] == 'degraded':
        return 1
    else:
        return 2


if __name__ == '__main__':
    import sys
    exit_code = asyncio.run(run_health_check_cli())
    sys.exit(exit_code)

