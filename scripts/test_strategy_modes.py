"""
Strategy Modes Test Script
Tests both single_flip and scale_in strategies in PAPER mode
"""

import os
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any

from loguru import logger

from infrastructure.config_manager import config_manager
from infrastructure.bootstrap import load_env
from application.strategy_modes import strategy_manager
from application.protection_guards import protection_guards
from execution.position_level_executor import position_executor
from infrastructure.decision_logger import decision_logger
from monitoring.prometheus_exporter import get_prometheus_exporter


class StrategyTestRunner:
    """Strategy modes test runner"""
    
    def __init__(self):
        self.config = config_manager
        self.metrics = get_prometheus_exporter()
        self.start_time = None
        self.test_results = {
            'single_flip': {'entries': 0, 'flips': 0, 'skips': 0},
            'scale_in': {'entries': 0, 'scale_ins': 0, 'skips': 0}
        }
    
    async def run_single_flip_test(self, duration_minutes: int = 45) -> Dict[str, Any]:
        """Run single_flip strategy test"""
        logger.info("🧪 Starting SINGLE_FLIP strategy test")
        
        # Set environment for single_flip
        os.environ['STRATEGY_MODE'] = 'single_flip'
        os.environ['MODE'] = 'PAPER'
        os.environ['DRY_RUN'] = 'false'
        os.environ['SYMBOLS'] = 'BTC-USDT-SWAP'
        os.environ['TIMEFRAME'] = '15m'
        
        # Record strategy mode
        self.metrics.record_strategy_mode('single_flip')
        
        # Run test
        start_time = datetime.now(timezone.utc)
        from datetime import timedelta
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        logger.info(f"📅 Test duration: {duration_minutes} minutes")
        logger.info(f"🎯 Target symbols: BTC-USDT-SWAP")
        logger.info(f"⏰ Start time: {start_time.strftime('%H:%M:%S')}")
        logger.info(f"⏰ End time: {end_time.strftime('%H:%M:%S')}")
        
        # Simulate trading loop
        current_positions = {}
        entry_count = 0
        flip_count = 0
        skip_count = 0
        
        while datetime.now(timezone.utc) < end_time:
            # Simulate signal
            signal = {
                'direction': 'LONG' if entry_count % 2 == 0 else 'SHORT',
                'score': 75.0,
                'quantity': 0.001,
                'price': 50000.0
            }
            
            # Make strategy decision
            decision = strategy_manager.make_decision('BTC-USDT-SWAP', signal, current_positions)
            
            # Process decision
            if decision.action == 'enter':
                entry_count += 1
                current_positions['BTC-USDT-SWAP'] = {
                    'side': decision.direction,
                    'quantity': decision.quantity,
                    'entry_price': signal['price'],
                    'entry_time': datetime.now(timezone.utc)
                }
                
                # Record metrics
                self.metrics.record_open_transition('BTC-USDT-SWAP', decision.direction)
                
                # Log decision
                decision_logger.log_entry_decision(
                    'BTC-USDT-SWAP', decision.direction, decision.quantity, 
                    signal['price'], 'PAPER', 'single_flip'
                )
                
            elif decision.action == 'flip':
                flip_count += 1
                old_direction = current_positions['BTC-USDT-SWAP']['side']
                current_positions['BTC-USDT-SWAP'] = {
                    'side': decision.direction,
                    'quantity': decision.quantity,
                    'entry_price': signal['price'],
                    'entry_time': datetime.now(timezone.utc)
                }
                
                # Record metrics
                self.metrics.record_flip_event('BTC-USDT-SWAP', old_direction, decision.direction)
                
                # Log decision
                decision_logger.log_flip_decision(
                    'BTC-USDT-SWAP', old_direction, decision.direction,
                    decision.quantity, signal['price'], 'PAPER'
                )
                
            elif decision.action == 'skip':
                skip_count += 1
                self.metrics.record_entry_skip(decision.reason)
                decision_logger.log_skip_decision('BTC-USDT-SWAP', decision.reason, decision.details)
            
            # Wait for next iteration
            await asyncio.sleep(60)  # 1 minute intervals
        
        # Record results
        self.test_results['single_flip'] = {
            'entries': entry_count,
            'flips': flip_count,
            'skips': skip_count,
            'duration_minutes': duration_minutes
        }
        
        logger.info(f"✅ SINGLE_FLIP test completed:")
        logger.info(f"  Entries: {entry_count}")
        logger.info(f"  Flips: {flip_count}")
        logger.info(f"  Skips: {skip_count}")
        
        return self.test_results['single_flip']
    
    async def run_scale_in_test(self, duration_minutes: int = 45) -> Dict[str, Any]:
        """Run scale_in strategy test"""
        logger.info("🧪 Starting SCALE_IN strategy test")
        
        # Set environment for scale_in
        os.environ['STRATEGY_MODE'] = 'scale_in'
        os.environ['MODE'] = 'PAPER'
        os.environ['DRY_RUN'] = 'false'
        os.environ['SYMBOLS'] = 'BTC-USDT-SWAP'
        os.environ['TIMEFRAME'] = '15m'
        
        # Record strategy mode
        self.metrics.record_strategy_mode('scale_in')
        
        # Run test
        start_time = datetime.now(timezone.utc)
        from datetime import timedelta
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        logger.info(f"📅 Test duration: {duration_minutes} minutes")
        logger.info(f"🎯 Target symbols: BTC-USDT-SWAP")
        logger.info(f"⏰ Start time: {start_time.strftime('%H:%M:%S')}")
        logger.info(f"⏰ End time: {end_time.strftime('%H:%M:%S')}")
        
        # Simulate trading loop
        current_positions = {}
        entry_count = 0
        scale_in_count = 0
        skip_count = 0
        
        while datetime.now(timezone.utc) < end_time:
            # Simulate signal with price movement
            base_price = 50000.0
            price_movement = (entry_count % 3) * 0.01  # 0%, 1%, 2% movement
            signal_price = base_price * (1 + price_movement)
            
            signal = {
                'direction': 'LONG',
                'score': 75.0,
                'quantity': 0.001,
                'price': signal_price
            }
            
            # Make strategy decision
            decision = strategy_manager.make_decision('BTC-USDT-SWAP', signal, current_positions)
            
            # Process decision
            if decision.action == 'enter':
                entry_count += 1
                current_positions['BTC-USDT-SWAP'] = {
                    'side': decision.direction,
                    'quantity': decision.quantity,
                    'entry_price': signal['price'],
                    'entry_time': datetime.now(timezone.utc),
                    'ladder_count': 1
                }
                
                # Record metrics
                self.metrics.record_open_transition('BTC-USDT-SWAP', decision.direction)
                
                # Log decision
                decision_logger.log_entry_decision(
                    'BTC-USDT-SWAP', decision.direction, decision.quantity, 
                    signal['price'], 'PAPER', 'scale_in'
                )
                
            elif decision.action == 'scale_in':
                scale_in_count += 1
                current_positions['BTC-USDT-SWAP']['ladder_count'] += 1
                current_positions['BTC-USDT-SWAP']['quantity'] += decision.quantity
                
                # Record metrics
                self.metrics.record_open_transition('BTC-USDT-SWAP', decision.direction)
                
                # Log decision
                decision_logger.log_scale_in_decision(
                    'BTC-USDT-SWAP', decision.direction, decision.quantity,
                    signal['price'], current_positions['BTC-USDT-SWAP']['ladder_count'], 'PAPER'
                )
                
            elif decision.action == 'skip':
                skip_count += 1
                self.metrics.record_entry_skip(decision.reason)
                decision_logger.log_skip_decision('BTC-USDT-SWAP', decision.reason, decision.details)
            
            # Wait for next iteration
            await asyncio.sleep(60)  # 1 minute intervals
        
        # Record results
        self.test_results['scale_in'] = {
            'entries': entry_count,
            'scale_ins': scale_in_count,
            'skips': skip_count,
            'duration_minutes': duration_minutes
        }
        
        logger.info(f"✅ SCALE_IN test completed:")
        logger.info(f"  Entries: {entry_count}")
        logger.info(f"  Scale-ins: {scale_in_count}")
        logger.info(f"  Skips: {skip_count}")
        
        return self.test_results['scale_in']
    
    def generate_report(self) -> str:
        """Generate test report"""
        report_lines = [
            "=" * 80,
            "STRATEGY MODES TEST REPORT",
            "=" * 80,
            f"Test Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "SINGLE_FLIP STRATEGY RESULTS:",
            f"  Entries: {self.test_results['single_flip']['entries']}",
            f"  Flips: {self.test_results['single_flip']['flips']}",
            f"  Skips: {self.test_results['single_flip']['skips']}",
            f"  Duration: {self.test_results['single_flip']['duration_minutes']} minutes",
            "",
            "SCALE_IN STRATEGY RESULTS:",
            f"  Entries: {self.test_results['scale_in']['entries']}",
            f"  Scale-ins: {self.test_results['scale_in']['scale_ins']}",
            f"  Skips: {self.test_results['scale_in']['skips']}",
            f"  Duration: {self.test_results['scale_in']['duration_minutes']} minutes",
            "",
            "PROTECTION GUARDS STATUS:",
            f"  Once-per-bar: {protection_guards.once_per_bar_enabled}",
            f"  Same-direction block: {protection_guards.same_direction_block}",
            f"  Reversal enabled: {protection_guards.reversal_enabled}",
            f"  Entry cooldown bars: {protection_guards.entry_cooldown_bars}",
            "",
            "POSITION-LEVEL TP/SL STATUS:",
            f"  Use position TP/SL: {position_executor.use_position_tpsl}",
            f"  Reduce-only: {position_executor.reduce_only}",
            "=" * 80
        ]
        
        return "\n".join(report_lines)


async def main():
    """Main test function"""
    # Load environment
    load_env()
    
    # Initialize test runner
    test_runner = StrategyTestRunner()
    
    logger.info("🚀 Starting Strategy Modes Test")
    
    try:
        # Run single_flip test
        single_flip_results = await test_runner.run_single_flip_test(duration_minutes=5)  # Short test
        
        # Wait between tests
        await asyncio.sleep(5)
        
        # Run scale_in test
        scale_in_results = await test_runner.run_scale_in_test(duration_minutes=5)  # Short test
        
        # Generate report
        report = test_runner.generate_report()
        logger.info(report)
        
        # Save report to file
        os.makedirs('reports/strategy', exist_ok=True)
        with open('reports/strategy/TEST_RESULTS.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info("✅ Strategy modes test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Strategy modes test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
