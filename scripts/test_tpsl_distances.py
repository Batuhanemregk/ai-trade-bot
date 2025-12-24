#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TP/SL Distance Test Script
Fetches current positions from OKX and calculates TP/SL distances as percentages.
"""
import asyncio
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


async def main():
    from adapters.exchange_okx_ccxt import OKXCCXTAdapter
    
    print("=" * 60)
    print("OKX TP/SL Distance Analysis")
    print("=" * 60)
    
    adapter = OKXCCXTAdapter()
    
    try:
        # 1. Fetch positions
        print("\nFetching positions...")
        positions = await adapter.fetch_positions()
        
        if not positions:
            print("No open positions found")
            return
        
        open_positions = [p for p in positions if float(p.get('contracts', 0) or 0) > 0]
        print(f"Found {len(open_positions)} open positions")
        
        # 2. Fetch all algo orders at once
        print("\nFetching TP/SL orders...")
        exchange = adapter.ccxt_client
        
        # Get algo orders from OKX
        all_algo_orders = {}
        try:
            params = {
                'instType': 'SWAP',
                'ordType': 'conditional',
            }
            raw_orders = exchange.private_get_trade_orders_algo_pending(params)
            if raw_orders and 'data' in raw_orders:
                for o in raw_orders['data']:
                    inst_id = o.get('instId', '')
                    if inst_id not in all_algo_orders:
                        all_algo_orders[inst_id] = {'tp': None, 'sl': None}
                    tp = float(o.get('tpTriggerPx', 0) or 0)
                    sl = float(o.get('slTriggerPx', 0) or 0)
                    if tp > 0:
                        all_algo_orders[inst_id]['tp'] = tp
                    if sl > 0:
                        all_algo_orders[inst_id]['sl'] = sl
        except Exception as e:
            print(f"Error fetching algo orders: {e}")
        
        # 3. Analyze each position
        for pos in open_positions:
            size = float(pos.get('contracts', 0) or 0)
            if size == 0:
                continue
                
            symbol = pos.get('symbol', '')
            side = pos.get('side', '')
            entry = float(pos.get('entryPrice', 0) or 0)
            mark_price = float(pos.get('markPrice', 0) or 0)
            upnl = float(pos.get('unrealizedPnl', 0) or 0)
            
            # Convert symbol to OKX format
            okx_symbol = symbol.replace('/', '-').replace(':USDT', '-SWAP')
            
            print(f"\n{'─' * 50}")
            print(f"Position: {symbol}")
            print(f"  Side: {side.upper()}")
            print(f"  Size: {size}")
            print(f"  Entry: ${entry:.6f}")
            print(f"  Mark:  ${mark_price:.6f}")
            print(f"  uPnL:  ${upnl:.2f}")
            
            # Get TP/SL for this symbol
            algo = all_algo_orders.get(okx_symbol, {})
            tp_price = algo.get('tp')
            sl_price = algo.get('sl')
            
            print(f"\n  TP/SL Analysis:")
            
            if tp_price and entry > 0:
                tp_dist = abs(tp_price - entry) / entry * 100
                print(f"  TP: ${tp_price:.6f} ({tp_dist:.2f}% from entry)")
            else:
                print(f"  TP: Not found")
                
            if sl_price and entry > 0:
                sl_dist = abs(sl_price - entry) / entry * 100
                print(f"  SL: ${sl_price:.6f} ({sl_dist:.2f}% from entry)")
            else:
                print(f"  SL: Not found")
            
            if tp_price and sl_price and entry > 0:
                rr_ratio = abs(tp_price - entry) / abs(sl_price - entry) if abs(sl_price - entry) > 0 else 0
                print(f"  R:R = 1:{rr_ratio:.2f}")
                
                # Calculate what ATR would be to produce these levels
                # TP = entry + tp_mult * ATR, SL = entry - sl_mult * ATR (for LONG)
                # Using policy defaults: tp_mult=4, sl_mult=2
                tp_mult = 4.0
                sl_mult = 2.0
                
                if side.upper() == 'LONG':
                    estimated_atr_from_tp = abs(tp_price - entry) / tp_mult
                    estimated_atr_from_sl = abs(entry - sl_price) / sl_mult
                else:  # SHORT
                    estimated_atr_from_tp = abs(entry - tp_price) / tp_mult
                    estimated_atr_from_sl = abs(sl_price - entry) / sl_mult
                
                avg_atr = (estimated_atr_from_tp + estimated_atr_from_sl) / 2
                print(f"\n  Estimated ATR:")
                print(f"    From TP (4x): ${estimated_atr_from_tp:.6f} ({estimated_atr_from_tp/entry*100:.3f}%)")
                print(f"    From SL (2x): ${estimated_atr_from_sl:.6f} ({estimated_atr_from_sl/entry*100:.3f}%)")
        
        print(f"\n{'=' * 60}")
        print("Analysis complete")
        
    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
