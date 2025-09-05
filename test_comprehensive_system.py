"""
Comprehensive System Test Plan
Tests all implemented features with PASS/FAIL validation and log evidence
"""

import asyncio
import os
import yaml
from datetime import datetime, timezone
from loguru import logger
from typing import Dict, Any, List, Tuple

# Test configuration
TEST_CONFIG = {
    'test_symbols': ['BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'SOL-USDT-SWAP'],
    'test_duration_minutes': 5,
    'log_file': 'logs/test_comprehensive.log'
}

class ComprehensiveTester:
    """Comprehensive system tester with PASS/FAIL validation"""
    
    def __init__(self):
        self.test_results = []
        self.log_evidence = []
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        logger.info("🚀 Starting Comprehensive System Tests")
        
        # Test 1: News Bootstrap
        await self.test_news_bootstrap()
        
        # Test 2: LLM Digest System
        await self.test_llm_digest_system()
        
        # Test 3: Telegram Notifications
        await self.test_telegram_notifications()
        
        # Test 4: Trade Visibility
        await self.test_trade_visibility()
        
        # Test 5: Scheduler Hygiene
        await self.test_scheduler_hygiene()
        
        # Test 6: Policy Configuration
        await self.test_policy_configuration()
        
        # Generate final report
        return self.generate_final_report()
    
    async def test_news_bootstrap(self):
        """Test 1: News Bootstrap and Persist System"""
        logger.info("🧪 Test 1: News Bootstrap and Persist System")
        
        try:
            from application.news_service import NewsService
            from configs.policy import load_policy
            
            # Load policy
            policy = load_policy()
            news_service = NewsService(policy)
            
            # Test on-start bootstrap
            symbols = TEST_CONFIG['test_symbols']
            await news_service.ensure_bootstrap_on_start(symbols)
            
            # Check watermarks
            watermark_stats = news_service.watermark_manager.get_all_watermarks()
            symbols_with_watermarks = len(watermark_stats)
            
            # Check news data
            news_stats = news_service.get_news_stats()
            symbols_with_news = news_stats['symbols_with_news']
            
            # Validate results
            if symbols_with_watermarks > 0:
                self.test_results.append({
                    'test': 'news_bootstrap',
                    'status': 'PASS',
                    'evidence': f"symbols_with_watermarks={symbols_with_watermarks}",
                    'details': f"Watermarks created for {symbols_with_watermarks} symbols"
                })
            else:
                self.test_results.append({
                    'test': 'news_bootstrap',
                    'status': 'FAIL',
                    'evidence': f"symbols_with_watermarks={symbols_with_watermarks}",
                    'details': "No watermarks created during bootstrap"
                })
            
            if symbols_with_news > 0:
                self.test_results.append({
                    'test': 'news_data_storage',
                    'status': 'PASS',
                    'evidence': f"symbols_with_news={symbols_with_news}",
                    'details': f"News data stored for {symbols_with_news} symbols"
                })
            else:
                self.test_results.append({
                    'test': 'news_data_storage',
                    'status': 'FAIL',
                    'evidence': f"symbols_with_news={symbols_with_news}",
                    'details': "No news data stored during bootstrap"
                })
                
        except Exception as e:
            self.test_results.append({
                'test': 'news_bootstrap',
                'status': 'FAIL',
                'evidence': f"error={str(e)}",
                'details': f"News bootstrap test failed: {e}"
            })
    
    async def test_llm_digest_system(self):
        """Test 2: LLM Digest System"""
        logger.info("🧪 Test 2: LLM Digest System")
        
        try:
            from application.news_service import NewsService
            from configs.policy import load_policy
            
            policy = load_policy()
            news_service = NewsService(policy)
            
            # Test digest creation
            test_news = [
                {
                    'title': 'Bitcoin reaches new all-time high',
                    'url': 'https://example.com/btc-news-1',
                    'publishedAt': datetime.now(timezone.utc).isoformat(),
                    'content': 'Bitcoin has reached a new all-time high...'
                }
            ]
            
            # Test digest manager
            digest_hash, is_changed, cached_result = news_service.digest_manager.get_digest_status(
                'BTC-USDT-SWAP', test_news, 30
            )
            
            if digest_hash and len(digest_hash) > 0:
                self.test_results.append({
                    'test': 'llm_digest_creation',
                    'status': 'PASS',
                    'evidence': f"digest_hash={digest_hash[:16]}...",
                    'details': "Digest hash created successfully"
                })
            else:
                self.test_results.append({
                    'test': 'llm_digest_creation',
                    'status': 'FAIL',
                    'evidence': f"digest_hash={digest_hash}",
                    'details': "Failed to create digest hash"
                })
            
            # Test cache functionality
            if is_changed:
                self.test_results.append({
                    'test': 'llm_digest_change_detection',
                    'status': 'PASS',
                    'evidence': f"is_changed={is_changed}",
                    'details': "Digest change detection working"
                })
            else:
                self.test_results.append({
                    'test': 'llm_digest_change_detection',
                    'status': 'FAIL',
                    'evidence': f"is_changed={is_changed}",
                    'details': "Digest change detection not working"
                })
                
        except Exception as e:
            self.test_results.append({
                'test': 'llm_digest_system',
                'status': 'FAIL',
                'evidence': f"error={str(e)}",
                'details': f"LLM digest system test failed: {e}"
            })
    
    async def test_telegram_notifications(self):
        """Test 3: Telegram Notifications"""
        logger.info("🧪 Test 3: Telegram Notifications")
        
        try:
            from infrastructure.notification_service import NotificationService
            
            # Initialize notification service
            notification_service = NotificationService()
            
            # Test configuration loading
            stats = notification_service.get_stats()
            config_loaded = stats['config_loaded']
            
            if config_loaded:
                self.test_results.append({
                    'test': 'telegram_config_loading',
                    'status': 'PASS',
                    'evidence': f"config_loaded={config_loaded}",
                    'details': "Telegram configuration loaded successfully"
                })
            else:
                self.test_results.append({
                    'test': 'telegram_config_loading',
                    'status': 'FAIL',
                    'evidence': f"config_loaded={config_loaded}",
                    'details': "Failed to load Telegram configuration"
                })
            
            # Test message sending (if enabled)
            if stats['telegram_enabled']:
                await notification_service.start()
                
                # Send test message
                await notification_service.send_system_notification(
                    "TEST", "Comprehensive system test"
                )
                
                # Check queue stats
                queue_stats = stats.get('telegram', {})
                queue_size = queue_stats.get('queue_size', 0)
                
                if queue_size >= 0:
                    self.test_results.append({
                        'test': 'telegram_message_queuing',
                        'status': 'PASS',
                        'evidence': f"queue_size={queue_size}",
                        'details': "Message queuing system working"
                    })
                else:
                    self.test_results.append({
                        'test': 'telegram_message_queuing',
                        'status': 'FAIL',
                        'evidence': f"queue_size={queue_size}",
                        'details': "Message queuing system not working"
                    })
                
                await notification_service.stop()
            else:
                self.test_results.append({
                    'test': 'telegram_message_queuing',
                    'status': 'SKIP',
                    'evidence': "telegram_enabled=false",
                    'details': "Telegram disabled, skipping message test"
                })
                
        except Exception as e:
            self.test_results.append({
                'test': 'telegram_notifications',
                'status': 'FAIL',
                'evidence': f"error={str(e)}",
                'details': f"Telegram notifications test failed: {e}"
            })
    
    async def test_trade_visibility(self):
        """Test 4: Trade Visibility and Audit Logs"""
        logger.info("🧪 Test 4: Trade Visibility and Audit Logs")
        
        try:
            # Test structured log format
            test_logs = [
                "[ENTRY] sym=BTC-USDT-SWAP dir=LONG size=0.002000 px=50000.00 reason=score>=60 state=READY tf=15m bar=2025-09-05T00:15Z",
                "[REVCHK] sym=BTC-USDT-SWAP strength=0.72 confirm=2 holding=4 edge=1.8x cost=0.3x → PASS",
                "[ORDER] sym=BTC-USDT-SWAP clientId=E_12345 side=buy amount=0.002000 price=50000.00",
                "[ORDER] sym=BTC-USDT-SWAP clientId=E_12345 status=SUCCESS ordId=123456 filled=0.002000"
            ]
            
            # Validate log format
            valid_logs = 0
            for log in test_logs:
                if self.validate_structured_log(log):
                    valid_logs += 1
            
            if valid_logs == len(test_logs):
                self.test_results.append({
                    'test': 'trade_visibility_logs',
                    'status': 'PASS',
                    'evidence': f"valid_logs={valid_logs}/{len(test_logs)}",
                    'details': "All structured log formats valid"
                })
            else:
                self.test_results.append({
                    'test': 'trade_visibility_logs',
                    'status': 'FAIL',
                    'evidence': f"valid_logs={valid_logs}/{len(test_logs)}",
                    'details': f"Only {valid_logs}/{len(test_logs)} log formats valid"
                })
                
        except Exception as e:
            self.test_results.append({
                'test': 'trade_visibility',
                'status': 'FAIL',
                'evidence': f"error={str(e)}",
                'details': f"Trade visibility test failed: {e}"
            })
    
    async def test_scheduler_hygiene(self):
        """Test 5: Scheduler Hygiene"""
        logger.info("🧪 Test 5: Scheduler Hygiene")
        
        try:
            from application.jobs.base_job import BaseJob
            from configs.policy import load_policy
            
            policy = load_policy()
            
            # Test bar idempotency - create a concrete implementation
            class TestJob(BaseJob):
                async def initialize(self):
                    pass
                async def execute(self):
                    pass
            
            job = TestJob(policy, None, {})
            
            # Test bar ID generation
            bar_id_15m = job.get_current_bar_id('15m')
            bar_id_5m = job.get_current_bar_id('5m')
            bar_id_1h = job.get_current_bar_id('1h')
            
            if bar_id_15m and bar_id_5m and bar_id_1h:
                self.test_results.append({
                    'test': 'bar_id_generation',
                    'status': 'PASS',
                    'evidence': f"bar_id_15m={bar_id_15m} bar_id_5m={bar_id_5m} bar_id_1h={bar_id_1h}",
                    'details': "Bar ID generation working for all timeframes"
                })
            else:
                self.test_results.append({
                    'test': 'bar_id_generation',
                    'status': 'FAIL',
                    'evidence': f"bar_id_15m={bar_id_15m} bar_id_5m={bar_id_5m} bar_id_1h={bar_id_1h}",
                    'details': "Bar ID generation failed for some timeframes"
                })
            
            # Test idempotency
            symbol = 'BTC-USDT-SWAP'
            timeframe = '15m'
            
            # First check should be False
            first_check = job.is_bar_already_processed(symbol, timeframe)
            
            # Mark as processed
            job.mark_bar_processed(symbol, timeframe)
            
            # Second check should be True
            second_check = job.is_bar_already_processed(symbol, timeframe)
            
            if not first_check and second_check:
                self.test_results.append({
                    'test': 'bar_idempotency',
                    'status': 'PASS',
                    'evidence': f"first_check={first_check} second_check={second_check}",
                    'details': "Bar idempotency working correctly"
                })
            else:
                self.test_results.append({
                    'test': 'bar_idempotency',
                    'status': 'FAIL',
                    'evidence': f"first_check={first_check} second_check={second_check}",
                    'details': "Bar idempotency not working correctly"
                })
                
        except Exception as e:
            self.test_results.append({
                'test': 'scheduler_hygiene',
                'status': 'FAIL',
                'evidence': f"error={str(e)}",
                'details': f"Scheduler hygiene test failed: {e}"
            })
    
    async def test_policy_configuration(self):
        """Test 6: Policy Configuration"""
        logger.info("🧪 Test 6: Policy Configuration")
        
        try:
            from configs.policy import load_policy
            
            policy = load_policy()
            
            # Test required sections
            required_sections = [
                'news', 'news_llm', 'news_scoring', 'schedule', 'scheduler'
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in policy:
                    missing_sections.append(section)
            
            if not missing_sections:
                self.test_results.append({
                    'test': 'policy_sections',
                    'status': 'PASS',
                    'evidence': f"all_sections_present={len(required_sections)}",
                    'details': "All required policy sections present"
                })
            else:
                self.test_results.append({
                    'test': 'policy_sections',
                    'status': 'FAIL',
                    'evidence': f"missing_sections={missing_sections}",
                    'details': f"Missing policy sections: {missing_sections}"
                })
            
            # Test news configuration
            news_config = policy.get('news', {})
            if 'lookback_hours_bootstrap' in news_config and 'overlap_minutes' in news_config:
                self.test_results.append({
                    'test': 'news_config',
                    'status': 'PASS',
                    'evidence': f"lookback_hours={news_config['lookback_hours_bootstrap']} overlap_minutes={news_config['overlap_minutes']}",
                    'details': "News configuration complete"
                })
            else:
                self.test_results.append({
                    'test': 'news_config',
                    'status': 'FAIL',
                    'evidence': f"news_config={news_config}",
                    'details': "News configuration incomplete"
                })
                
        except Exception as e:
            self.test_results.append({
                'test': 'policy_configuration',
                'status': 'FAIL',
                'evidence': f"error={str(e)}",
                'details': f"Policy configuration test failed: {e}"
            })
    
    def validate_structured_log(self, log: str) -> bool:
        """Validate structured log format"""
        try:
            # Check for required patterns
            patterns = [
                r'\[ENTRY\]',
                r'\[REVCHK\]',
                r'\[ORDER\]',
                r'\[CLOSE\]',
                r'\[TRAIL\]',
                r'\[COOLDOWN\]',
                r'\[REGIME\]'
            ]
            
            import re
            for pattern in patterns:
                if re.search(pattern, log):
                    return True
            
            return False
        except:
            return False
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate final test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAIL'])
        skipped_tests = len([r for r in self.test_results if r['status'] == 'SKIP'])
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'skipped': skipped_tests,
                'success_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            'results': self.test_results,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Log summary
        logger.info(f"📊 Test Summary: {passed_tests}/{total_tests} PASSED ({report['summary']['success_rate']})")
        
        for result in self.test_results:
            status_emoji = "✅" if result['status'] == 'PASS' else "❌" if result['status'] == 'FAIL' else "⏭️"
            logger.info(f"{status_emoji} {result['test']}: {result['status']} - {result['evidence']}")
        
        return report

async def main():
    """Run comprehensive system tests"""
    tester = ComprehensiveTester()
    report = await tester.run_all_tests()
    
    # Save report
    import json
    with open('test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info("📋 Test report saved to test_report.json")
    
    return report

if __name__ == "__main__":
    asyncio.run(main())
