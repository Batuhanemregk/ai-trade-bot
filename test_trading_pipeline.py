"""
Trading Analysis Full Pipeline Test
Runs TradingAnalysisJob with real market data in paper mode.
Does NOT execute real trades - only simulates the full flow.

Run: python test_trading_pipeline.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# Ensure paper mode
os.environ['TRADING_MODE'] = 'paper'


async def run_single_analysis(symbol: str = "BTC-USDT-SWAP"):
    """Run a single trading analysis for a symbol."""
    print(f"\n{'='*60}")
    print(f"🔄 Running analysis for {symbol}")
    print(f"{'='*60}")
    
    # Load policy
    import yaml
    with open('configs/policy.yaml', 'r') as f:
        policy = yaml.safe_load(f)
    
    # Initialize components
    from application.jobs.trading_analysis import TradingAnalysisJob
    
    # Create minimal runtime state
    runtime_state = {
        'positions': {},
        'orders': {},
        'balance': {'USDT': 1000.0}
    }
    
    # Create job
    semaphore = asyncio.Semaphore(3)
    job = TradingAnalysisJob(policy, semaphore, runtime_state)
    
    # Initialize
    job.initialize()
    
    try:
        # Process single symbol
        result = await job._process_symbol(symbol)
        
        if result:
            print(f"\n📊 Analysis Result:")
            print(f"   Symbol: {result.get('symbol')}")
            print(f"   TA Score: {result.get('ta_score', 0):.1f}")
            print(f"   ML Score: {result.get('ml_score', 0):.1f}")
            print(f"   News Score: {result.get('news_score', 0):.1f}")
            print(f"   Risk Score: {result.get('risk_score', 0):.1f}")
            print(f"   Final Score: {result.get('final_score', 0):.1f}")
            print(f"   Direction: {result.get('decision')}")
            print(f"   Action: {result.get('action')}")
            
            return result
        else:
            print("❌ No result returned")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        job.cleanup()


async def run_multiple_cycles(symbol: str = "BTC-USDT-SWAP", cycles: int = 3):
    """
    Run multiple analysis cycles to test persistence.
    Simulates what would happen over multiple bars.
    """
    print(f"\n{'='*60}")
    print(f"🔄 Running {cycles} cycles for {symbol}")
    print(f"   (Simulating {cycles} x 15min bars)")
    print(f"{'='*60}")
    
    import yaml
    with open('configs/policy.yaml', 'r') as f:
        policy = yaml.safe_load(f)
    
    from application.jobs.trading_analysis import TradingAnalysisJob
    from application.signal_gate import SignalGate
    
    # Create shared signal gate (persists across cycles)
    signal_gate = SignalGate(policy)
    
    runtime_state = {
        'positions': {},
        'orders': {},
        'balance': {'USDT': 1000.0}
    }
    
    semaphore = asyncio.Semaphore(3)
    
    results = []
    
    for cycle in range(1, cycles + 1):
        print(f"\n--- Cycle {cycle}/{cycles} ---")
        
        job = TradingAnalysisJob(policy, semaphore, runtime_state)
        # Inject shared signal gate for persistence testing
        job.signal_gate = signal_gate
        job.initialize()
        
        try:
            result = await job._process_symbol(symbol)
            
            if result:
                # Get gate status
                history = signal_gate.get_signal_history(symbol)
                persist_count = len(history) if history else 0
                
                print(f"   Score: {result.get('final_score', 0):.1f}")
                print(f"   Direction: {result.get('decision')}")
                print(f"   History Length: {persist_count}")
                print(f"   Action: {result.get('action')}")
                
                results.append(result)
        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            job.cleanup()
        
        # Small delay between cycles
        if cycle < cycles:
            await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    
    if results:
        actions = [r.get('action', 'UNKNOWN') for r in results]
        print(f"   Actions: {actions}")
        
        final_history = signal_gate.get_signal_history(symbol)
        print(f"   Final History Length: {len(final_history) if final_history else 0}")
        
        # Check if any trade would have been executed
        trade_actions = ['OPEN_LONG', 'OPEN_SHORT', 'CLOSE_REVERSE']
        trades = [a for a in actions if a in trade_actions]
        
        if trades:
            print(f"   ✅ Trade signals: {trades}")
        else:
            print(f"   ⏳ No trade signals (all MAINTAIN)")
    
    return results


async def test_gate_with_mock_scores():
    """
    Test gate logic with controlled mock scores.
    Forces high scores to verify gate passes correctly.
    """
    print(f"\n{'='*60}")
    print(f"🧪 Testing Gate with Mock Scores (forced high)")
    print(f"{'='*60}")
    
    import yaml
    with open('configs/policy.yaml', 'r') as f:
        policy = yaml.safe_load(f)
    
    from application.signal_gate import SignalGate
    from datetime import timedelta
    
    gate = SignalGate(policy)
    symbol = "TEST-USDT"
    
    persist_required = policy['trading']['scoring']['signal']['persistence_bars']
    enter_long = policy['trading']['scoring']['decision_thresholds']['enter_long']
    
    print(f"   enter_long threshold: {enter_long}")
    print(f"   persistence required: {persist_required}")
    print()
    
    # Simulate consecutive high-score bars
    ohlcv = [[1, 100, 101, 99, 100, 1000] for _ in range(20)]
    
    for i in range(persist_required + 2):
        bar_time = datetime.now(timezone.utc) + timedelta(minutes=15*i)
        signal = {
            'final_score': 70,  # High score, definitely long
            'bar_timestamp': bar_time
        }
        
        result = gate.process_signal(symbol, signal, ohlcv)
        
        status = "✅ PASS" if result.is_valid else "⏳ PENDING"
        print(f"   Bar {i+1}: persist={result.persistence_bars}/{persist_required} | {status}")
        
        if result.is_valid:
            print(f"\n   🎉 Gate PASSED at bar {i+1}!")
            break
    
    return result.is_valid


async def main():
    """Main test runner."""
    print("\n" + "="*60)
    print("🧪 TRADING PIPELINE TEST")
    print("="*60)
    print(f"Mode: PAPER (no real trades)")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Mock score gate test
    print("\n" + "-"*60)
    gate_ok = await test_gate_with_mock_scores()
    
    # Test 2: Single real analysis
    print("\n" + "-"*60)
    print("Running real analysis with live market data...")
    result = await run_single_analysis("BTC-USDT-SWAP")
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    print(f"   Gate Logic: {'✅ PASS' if gate_ok else '❌ FAIL'}")
    print(f"   Real Analysis: {'✅ OK' if result else '❌ FAIL'}")
    
    if gate_ok and result:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️ Some tests failed - check output above")


if __name__ == "__main__":
    asyncio.run(main())
