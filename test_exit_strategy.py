"""
Test Exit Strategy Features Implementation
"""
import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv
load_dotenv()

async def test_exchange_methods():
    """Test new exchange adapter methods exist and are callable."""
    print("\n=== Testing Exchange Adapter Methods ===")
    
    from adapters.exchange_okx_ccxt import OKXCCXTAdapter
    
    adapter = OKXCCXTAdapter()
    adapter.load_markets()
    
    # Check methods exist
    methods = ['fetch_algo_orders', 'cancel_algo_order', 'create_algo_stop_loss', 
               'update_stop_loss', 'close_position_market', 'get_position_sl_order']
    
    for method in methods:
        if hasattr(adapter, method):
            print(f"  ✅ {method} exists")
        else:
            print(f"  ❌ {method} MISSING")
    
    # Test fetch_algo_orders (safe read-only)
    print("\n  Testing fetch_algo_orders...")
    try:
        orders = await adapter.fetch_algo_orders()
        print(f"    ✅ Fetched {len(orders)} algo orders")
    except Exception as e:
        print(f"    ⚠️ fetch_algo_orders error: {e}")
    
    await adapter.close()
    print("  ✅ Adapter closed")

async def test_policy_toggle():
    """Test policy toggle function."""
    print("\n=== Testing Policy Toggle ===")
    
    import yaml
    
    policy_path = 'configs/policy.yaml'
    
    # Read current value
    with open(policy_path, 'r', encoding='utf-8') as f:
        policy = yaml.safe_load(f)
    
    trailing_enabled = policy.get('trading', {}).get('scoring', {}).get('trailing', {}).get('enabled')
    print(f"  Current trailing.enabled: {trailing_enabled}")
    
    # Read all feature states
    scoring = policy.get('trading', {}).get('scoring', {})
    features = ['trailing', 'partial_tp', 'time_exit', 'dynamic_tpsl']
    
    for feature in features:
        enabled = scoring.get(feature, {}).get('enabled', 'N/A')
        print(f"  {feature}.enabled: {enabled}")

async def test_trailing_job_config():
    """Test trailing job reads config correctly."""
    print("\n=== Testing Trailing Job Config ===")
    
    from infrastructure.bootstrap import load_policy
    
    policy = load_policy()
    scoring = policy.get('trading', {}).get('scoring', {})
    
    trailing = scoring.get('trailing', {})
    partial_tp = scoring.get('partial_tp', {})
    time_exit = scoring.get('time_exit', {})
    dynamic_tpsl = scoring.get('dynamic_tpsl', {})
    
    print(f"  Trailing: enabled={trailing.get('enabled')}")
    print(f"    activation_r_multiple: {trailing.get('activation_r_multiple')}")
    print(f"    breakeven_r_multiple: {trailing.get('breakeven_r_multiple')}")
    print(f"    tight_r_multiple: {trailing.get('tight_r_multiple')}")
    
    print(f"\n  Partial TP: enabled={partial_tp.get('enabled')}")
    levels = partial_tp.get('levels', [])
    for i, level in enumerate(levels):
        print(f"    Level {i+1}: R={level.get('r_multiple')}, close={level.get('close_pct')*100}%")
    
    print(f"\n  Time Exit: enabled={time_exit.get('enabled')}")
    print(f"    max_position_age_hours: {time_exit.get('max_position_age_hours')}")
    print(f"    warning_hours: {time_exit.get('warning_hours')}")
    
    print(f"\n  Dynamic TP/SL: enabled={dynamic_tpsl.get('enabled')}")

async def test_context_resolver():
    """Test context resolver returns trading features."""
    print("\n=== Testing Context Resolver ===")
    
    from adapters.telegram.context_resolver import ContextResolver
    
    resolver = ContextResolver()
    context = await resolver.resolve_settings_context()
    
    features = ['trailing_enabled', 'partial_tp_enabled', 'time_exit_enabled', 'dynamic_tpsl_enabled']
    
    for feature in features:
        value = context.get(feature, 'N/A')
        print(f"  {feature}: {value}")

async def main():
    print("=" * 60)
    print("EXIT STRATEGY IMPLEMENTATION TEST")
    print("=" * 60)
    
    try:
        await test_exchange_methods()
    except Exception as e:
        print(f"  ❌ Exchange test failed: {e}")
    
    try:
        await test_policy_toggle()
    except Exception as e:
        print(f"  ❌ Policy toggle test failed: {e}")
    
    try:
        await test_trailing_job_config()
    except Exception as e:
        print(f"  ❌ Trailing job config test failed: {e}")
    
    try:
        await test_context_resolver()
    except Exception as e:
        print(f"  ❌ Context resolver test failed: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
