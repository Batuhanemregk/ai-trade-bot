"""
Add TP/SL to existing positions that don't have them.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def add_tpsl_to_positions():
    """Add TP/SL to positions that don't have them."""
    print("\n" + "="*60)
    print("FIX MISSING TP/SL FOR POSITIONS")
    print("="*60)
    
    from infrastructure.bootstrap import create_exchange_adapter
    import numpy as np
    
    adapter = await create_exchange_adapter()
    
    try:
        # Get all open positions
        positions = await adapter.fetch_positions()
        
        open_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
        
        print(f"\nFound {len(open_positions)} open positions")
        
        for pos in open_positions:
            symbol = pos.get('symbol', '')
            side = pos.get('side', '')
            size = float(pos.get('contracts', 0))
            entry_price = float(pos.get('entryPrice', 0))
            
            print(f"\n📊 {symbol}: {side} {size} @ {entry_price}")
            
            # Check if TP/SL exists
            try:
                existing_sl = await adapter.get_position_sl_order(symbol)
                existing_tp = await adapter.get_position_tp_order(symbol)
                
                has_sl = existing_sl is not None
                has_tp = existing_tp is not None
                
                print(f"   SL: {'✅ Exists' if has_sl else '❌ Missing'}")
                print(f"   TP: {'✅ Exists' if has_tp else '❌ Missing'}")
                
                if has_sl and has_tp:
                    print(f"   → Already has TP/SL, skipping")
                    continue
                
            except Exception as e:
                print(f"   ⚠️ Error checking existing orders: {e}")
                has_sl = False
                has_tp = False
            
            # Calculate TP/SL based on ATR (2% SL, 4% TP as fallback)
            sl_pct = 0.02
            tp_pct = 0.04
            
            if side == 'long':
                sl_price = entry_price * (1 - sl_pct)
                tp_price = entry_price * (1 + tp_pct)
            else:  # short
                sl_price = entry_price * (1 + sl_pct)
                tp_price = entry_price * (1 - tp_pct)
            
            print(f"   Calculated: TP={tp_price:.6f}, SL={sl_price:.6f}")
            
            # Determine close side
            close_side = 'sell' if side == 'long' else 'buy'
            
            # Create SL if missing
            if not has_sl:
                try:
                    sl_result = await adapter.create_algo_stop_loss(
                        symbol=symbol,
                        side=close_side,
                        size=abs(size),
                        trigger_price=sl_price
                    )
                    if sl_result.get('success'):
                        print(f"   ✅ Created SL: {sl_result.get('algoId', 'OK')}")
                    else:
                        print(f"   ❌ SL creation failed: {sl_result.get('error')}")
                except Exception as e:
                    print(f"   ❌ Failed to create SL: {e}")
            
            # Create TP if missing
            if not has_tp:
                try:
                    tp_result = await adapter.create_algo_take_profit(
                        symbol=symbol,
                        side=close_side,
                        size=abs(size),
                        trigger_price=tp_price
                    )
                    if tp_result.get('success'):
                        print(f"   ✅ Created TP: {tp_result.get('algoId', 'OK')}")
                    else:
                        print(f"   ❌ TP creation failed: {tp_result.get('error')}")
                except Exception as e:
                    print(f"   ❌ Failed to create TP: {e}")
        
        print("\n" + "="*60)
        print("DONE")
        print("="*60)
        
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(add_tpsl_to_positions())
