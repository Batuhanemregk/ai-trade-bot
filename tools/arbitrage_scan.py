#!/usr/bin/env python
"""
OKX SPOT Triangular Arbitrage Scanner
=====================================
ANALYSIS ONLY - Does NOT place any orders.

Scans top 100 SPOT instruments for triangular arbitrage opportunities.
Uses real OKX API data: instruments, fees, and orderbooks.

Usage:
    python tools/arbitrage_scan.py
    python tools/arbitrage_scan.py --trade-size 500 --slippage 0.05
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import json
import ccxt.async_support as ccxt
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# ==================== CONFIGURATION ====================

TRADE_SIZE_USDT = 1000.0  # Base trade size
SLIPPAGE_BUFFER_PCT = 0.03  # 0.03% per leg conservative buffer
TOP_INSTRUMENTS = 100  # Number of top instruments by volume
MIN_BOOK_DEPTH = 50  # Order book depth to fetch
RATE_LIMIT_DELAY = 0.1  # Delay between API calls

# ==================== DATA STRUCTURES ====================

@dataclass
class Instrument:
    inst_id: str
    base: str
    quote: str
    volume_24h: float  # In quote currency
    
@dataclass
class OrderBookLevel:
    price: float
    size: float
    
@dataclass
class OrderBook:
    inst_id: str
    bids: List[OrderBookLevel]  # Sorted high to low
    asks: List[OrderBookLevel]  # Sorted low to high
    timestamp: datetime
    
@dataclass
class LegExecution:
    inst_id: str
    side: str  # 'buy' or 'sell'
    vwap_price: float
    total_size: float
    levels_consumed: int
    fee_amount: float
    slippage_cost: float
    
@dataclass
class TriangleCycle:
    path: List[str]  # e.g., ['USDT', 'BTC', 'ETH', 'USDT']
    legs: List[Tuple[str, str]]  # [(inst_id, side), ...]
    gross_return_pct: float
    total_fees_usdt: float
    slippage_buffer_usdt: float
    net_profit_usdt: float
    net_profit_pct: float
    leg_details: List[LegExecution]
    
# ==================== OKX API CLIENT ====================

class OKXArbitrageScanner:
    def __init__(self, trade_size: float = TRADE_SIZE_USDT, slippage_pct: float = SLIPPAGE_BUFFER_PCT):
        self.trade_size = trade_size
        self.slippage_pct = slippage_pct
        self.exchange: Optional[ccxt.okx] = None
        self.instruments: Dict[str, Instrument] = {}
        self.orderbooks: Dict[str, OrderBook] = {}
        self.maker_fee: float = 0.0
        self.taker_fee: float = 0.0
        self.fee_response: dict = {}
        
        # Graph for cycle detection
        self.graph: Dict[str, List[Tuple[str, str, str]]] = defaultdict(list)  # currency -> [(target, inst_id, side), ...]
        
    async def initialize(self):
        """Initialize OKX connection with API credentials."""
        api_key = os.getenv('OKX_API_KEY')
        secret = os.getenv('OKX_API_SECRET')  # Note: matches .env file
        passphrase = os.getenv('OKX_API_PASSPHRASE')  # Note: matches .env file
        
        if not all([api_key, secret, passphrase]):
            raise ValueError(f"OKX API credentials not found. KEY={bool(api_key)}, SECRET={bool(secret)}, PASS={bool(passphrase)}")
        
        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret,
            'password': passphrase,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        print("✅ OKX connection initialized")
        
    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            
    # ==================== STEP 1: FETCH INSTRUMENTS ====================
    
    async def fetch_top_instruments(self) -> List[Instrument]:
        """Fetch ALL SPOT instruments that could form triangular cycles."""
        print("\n📊 Step 1: Fetching ALL SPOT instruments...")
        
        # Fetch all spot tickers
        tickers = await self.exchange.fetch_tickers(params={'instType': 'SPOT'})
        
        instruments = []
        quote_currencies = set()
        
        for symbol, ticker in tickers.items():
            try:
                parts = symbol.split('/')
                if len(parts) != 2:
                    continue
                base, quote = parts
                
                # Get 24h quote volume
                volume_24h = ticker.get('quoteVolume', 0) or 0
                
                inst = Instrument(
                    inst_id=f"{base}-{quote}",
                    base=base,
                    quote=quote,
                    volume_24h=float(volume_24h)
                )
                instruments.append(inst)
                quote_currencies.add(quote)
            except Exception:
                continue
        
        # Store ALL instruments (not just top N)
        for inst in instruments:
            self.instruments[inst.inst_id] = inst
            
        # Sort for reporting
        instruments.sort(key=lambda x: x.volume_24h, reverse=True)
        
        print(f"  Found {len(tickers)} total tickers")
        print(f"  Stored {len(instruments)} tradable SPOT instruments")
        print(f"  Quote currencies: {sorted(quote_currencies)}")
        print(f"  Top 5 by volume: {[i.inst_id for i in instruments[:5]]}")
        
        return instruments
    
    # ==================== STEP 2: FETCH REAL FEES ====================
    
    async def fetch_my_fees(self) -> Tuple[float, float]:
        """Fetch real maker/taker fees from OKX private API."""
        print("\n💰 Step 2: Fetching MY real fee rates...")
        
        try:
            # OKX trade-fee endpoint for SPOT
            response = await self.exchange.private_get_account_trade_fee({'instType': 'SPOT'})
            self.fee_response = response
            
            if response.get('code') == '0' and response.get('data'):
                fee_data = response['data'][0]
                
                # OKX returns fees as negative decimals (e.g., -0.001 = 0.1%)
                maker_fee_raw = float(fee_data.get('maker', '-0.001'))
                taker_fee_raw = float(fee_data.get('taker', '-0.0015'))
                
                # Convert to positive percentage
                self.maker_fee = abs(maker_fee_raw)
                self.taker_fee = abs(taker_fee_raw)
                
                print(f"  API Response fields: maker={fee_data.get('maker')}, taker={fee_data.get('taker')}")
                print(f"  ✅ Maker fee: {self.maker_fee * 100:.4f}%")
                print(f"  ✅ Taker fee: {self.taker_fee * 100:.4f}%")
                
                return self.maker_fee, self.taker_fee
            else:
                raise ValueError(f"Failed to fetch fees: {response}")
                
        except Exception as e:
            print(f"  ⚠️ Failed to fetch fees: {e}")
            print("  Using default OKX spot fees (0.10% maker, 0.15% taker)")
            self.maker_fee = 0.001
            self.taker_fee = 0.0015
            return self.maker_fee, self.taker_fee
    
    # ==================== STEP 3: BUILD GRAPH & FIND CYCLES ====================
    
    def build_tradable_graph(self):
        """Build directed graph from instruments for cycle detection."""
        print("\n🔗 Step 3: Building tradable graph...")
        
        self.graph.clear()
        
        for inst_id, inst in self.instruments.items():
            # Selling base gets quote: base -> quote
            self.graph[inst.base].append((inst.quote, inst_id, 'sell'))
            
            # Buying base costs quote: quote -> base
            self.graph[inst.quote].append((inst.base, inst_id, 'buy'))
        
        # Count unique currencies
        all_currencies = set(self.graph.keys())
        total_edges = sum(len(v) for v in self.graph.values())
        
        print(f"  Currencies in graph: {len(all_currencies)}")
        print(f"  Total directed edges: {total_edges}")
        print(f"  USDT connections: {len(self.graph.get('USDT', []))}")
        
    def find_triangular_cycles(self) -> List[List[Tuple[str, str, str]]]:
        """Find all 3-edge cycles starting and ending in USDT."""
        print("\n🔄 Finding triangular cycles (USDT -> A -> B -> USDT)...")
        
        cycles = []
        visited_cycles: Set[frozenset] = set()
        
        # Start from USDT
        if 'USDT' not in self.graph:
            print("  ⚠️ No USDT pairs found!")
            return []
        
        # USDT -> A
        for (currency_a, inst_1, side_1) in self.graph['USDT']:
            if currency_a == 'USDT':
                continue
                
            # A -> B
            for (currency_b, inst_2, side_2) in self.graph.get(currency_a, []):
                if currency_b == 'USDT' or currency_b == currency_a:
                    continue
                    
                # B -> USDT
                for (currency_c, inst_3, side_3) in self.graph.get(currency_b, []):
                    if currency_c == 'USDT':
                        # Found a cycle!
                        cycle_key = frozenset([inst_1, inst_2, inst_3])
                        
                        if cycle_key not in visited_cycles:
                            visited_cycles.add(cycle_key)
                            cycles.append([
                                ('USDT', currency_a, inst_1, side_1),
                                (currency_a, currency_b, inst_2, side_2),
                                (currency_b, 'USDT', inst_3, side_3)
                            ])
        
        print(f"  Found {len(cycles)} unique triangular cycles")
        
        return cycles
    
    # ==================== STEP 4: FETCH ORDERBOOKS & SIMULATE ====================
    
    async def fetch_orderbook(self, inst_id: str) -> Optional[OrderBook]:
        """Fetch order book for an instrument."""
        try:
            # Convert inst_id format for CCXT
            symbol = inst_id.replace('-', '/')
            
            book = await self.exchange.fetch_order_book(symbol, limit=MIN_BOOK_DEPTH)
            
            bids = [OrderBookLevel(price=float(b[0]), size=float(b[1])) for b in book.get('bids', [])]
            asks = [OrderBookLevel(price=float(a[0]), size=float(a[1])) for a in book.get('asks', [])]
            
            return OrderBook(
                inst_id=inst_id,
                bids=bids,
                asks=asks,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            return None
    
    def simulate_leg_execution(self, orderbook: OrderBook, side: str, 
                               amount_in: float, fee_rate: float) -> Optional[LegExecution]:
        """
        Simulate executing a leg with order book depth.
        
        Args:
            orderbook: Order book data
            side: 'buy' or 'sell'
            amount_in: Amount of input currency
            fee_rate: Fee rate (e.g., 0.001 for 0.1%)
        
        Returns:
            LegExecution with VWAP and output amount
        """
        if side == 'sell':
            # Selling base, consuming bids
            levels = orderbook.bids
            if not levels:
                return None
            
            # We have amount_in of base, want to get quote
            remaining_base = amount_in
            total_quote = 0
            levels_used = 0
            
            for level in levels:
                if remaining_base <= 0:
                    break
                    
                fill_base = min(remaining_base, level.size)
                fill_quote = fill_base * level.price
                
                total_quote += fill_quote
                remaining_base -= fill_base
                levels_used += 1
            
            if remaining_base > amount_in * 0.01:  # More than 1% unfilled
                return None
                
            vwap = total_quote / (amount_in - remaining_base) if (amount_in - remaining_base) > 0 else 0
            output_amount = total_quote
            
        else:  # buy
            # Buying base, consuming asks
            levels = orderbook.asks
            if not levels:
                return None
            
            # We have amount_in of quote, want to get base
            remaining_quote = amount_in
            total_base = 0
            levels_used = 0
            
            for level in levels:
                if remaining_quote <= 0:
                    break
                    
                max_base_at_level = remaining_quote / level.price
                fill_base = min(max_base_at_level, level.size)
                fill_quote = fill_base * level.price
                
                total_base += fill_base
                remaining_quote -= fill_quote
                levels_used += 1
            
            if remaining_quote > amount_in * 0.01:  # More than 1% unfilled
                return None
                
            vwap = amount_in / total_base if total_base > 0 else 0
            output_amount = total_base
        
        # Apply fee
        fee_amount = output_amount * fee_rate
        after_fee = output_amount - fee_amount
        
        # Apply slippage buffer
        slippage_cost = after_fee * self.slippage_pct / 100
        after_slippage = after_fee - slippage_cost
        
        return LegExecution(
            inst_id=orderbook.inst_id,
            side=side,
            vwap_price=vwap,
            total_size=after_slippage,
            levels_consumed=levels_used,
            fee_amount=fee_amount,
            slippage_cost=slippage_cost
        )
    
    async def simulate_cycle(self, cycle: List[Tuple], use_maker: bool = False) -> Optional[TriangleCycle]:
        """Simulate executing a full triangular cycle."""
        fee_rate = self.maker_fee if use_maker else self.taker_fee
        
        path = ['USDT']
        legs = []
        leg_details = []
        
        current_amount = self.trade_size
        total_fees = 0
        total_slippage = 0
        
        for (from_curr, to_curr, inst_id, side) in cycle:
            path.append(to_curr)
            legs.append((inst_id, side))
            
            # Fetch orderbook if not cached
            if inst_id not in self.orderbooks:
                ob = await self.fetch_orderbook(inst_id)
                if ob:
                    self.orderbooks[inst_id] = ob
                await asyncio.sleep(RATE_LIMIT_DELAY)
            
            orderbook = self.orderbooks.get(inst_id)
            if not orderbook:
                return None
            
            # Simulate execution
            leg = self.simulate_leg_execution(orderbook, side, current_amount, fee_rate)
            if not leg:
                return None
            
            leg_details.append(leg)
            current_amount = leg.total_size
            total_fees += leg.fee_amount
            total_slippage += leg.slippage_cost
        
        # Calculate returns
        final_usdt = current_amount
        net_profit = final_usdt - self.trade_size
        net_profit_pct = (net_profit / self.trade_size) * 100
        gross_return = ((final_usdt + total_fees + total_slippage) / self.trade_size - 1) * 100
        
        return TriangleCycle(
            path=path,
            legs=legs,
            gross_return_pct=gross_return,
            total_fees_usdt=total_fees,
            slippage_buffer_usdt=total_slippage,
            net_profit_usdt=net_profit,
            net_profit_pct=net_profit_pct,
            leg_details=leg_details
        )
    
    # ==================== STEP 5 & 6: ANALYSIS & REPORT ====================
    
    async def run_full_scan(self) -> Dict:
        """Run the complete arbitrage scan and return results."""
        scan_start = datetime.now(timezone.utc)
        results = {
            'scan_timestamp': scan_start.isoformat(),
            'trade_size_usdt': self.trade_size,
            'slippage_buffer_pct': self.slippage_pct,
        }
        
        try:
            await self.initialize()
            
            # Step 1: Fetch instruments
            instruments = await self.fetch_top_instruments()
            results['instruments_scanned'] = len(instruments)
            results['top_instruments'] = [
                {'inst_id': i.inst_id, 'volume_24h': i.volume_24h, 'quote': i.quote}
                for i in instruments[:20]
            ]
            
            # Step 2: Fetch fees
            await self.fetch_my_fees()
            results['fees'] = {
                'maker_fee_pct': self.maker_fee * 100,
                'taker_fee_pct': self.taker_fee * 100,
                'api_response': str(self.fee_response.get('data', [{}])[0]) if self.fee_response.get('data') else 'N/A'
            }
            
            # Step 3: Build graph and find cycles
            self.build_tradable_graph()
            cycles = self.find_triangular_cycles()
            results['total_triangles_found'] = len(cycles)
            
            # Step 4: Simulate all cycles
            print(f"\n⚡ Step 4: Simulating {len(cycles)} cycles with {self.trade_size} USDT...")
            
            profitable_taker = []
            profitable_maker = []
            all_net_profits = []
            positive_before_slippage = 0
            positive_after_slippage = 0
            
            for i, cycle in enumerate(cycles):
                if i % 20 == 0:
                    print(f"  Processing cycle {i+1}/{len(cycles)}...")
                
                # Taker simulation
                result_taker = await self.simulate_cycle(cycle, use_maker=False)
                if result_taker:
                    all_net_profits.append(result_taker.net_profit_pct)
                    
                    # Check profitability before/after slippage
                    profit_before_slip = result_taker.net_profit_usdt + result_taker.slippage_buffer_usdt
                    if profit_before_slip > 0:
                        positive_before_slippage += 1
                    if result_taker.net_profit_usdt > 0:
                        positive_after_slippage += 1
                        profitable_taker.append(result_taker)
                
                # Maker simulation (hypothetical)
                result_maker = await self.simulate_cycle(cycle, use_maker=True)
                if result_maker and result_maker.net_profit_usdt > 0:
                    profitable_maker.append(result_maker)
            
            # Sort by profit
            profitable_taker.sort(key=lambda x: x.net_profit_usdt, reverse=True)
            profitable_maker.sort(key=lambda x: x.net_profit_usdt, reverse=True)
            
            # Step 5: Statistics
            results['statistics'] = {
                'cycles_simulated': len(cycles),
                'positive_before_slippage': positive_before_slippage,
                'positive_after_slippage_taker': positive_after_slippage,
                'positive_maker_scenario': len(profitable_maker),
                'net_profit_distribution': {
                    'min': min(all_net_profits) if all_net_profits else 0,
                    'max': max(all_net_profits) if all_net_profits else 0,
                    'mean': sum(all_net_profits) / len(all_net_profits) if all_net_profits else 0,
                }
            }
            
            # Top 20 opportunities (taker)
            results['top_opportunities_taker'] = []
            for cycle in profitable_taker[:20]:
                opp = {
                    'path': ' -> '.join(cycle.path),
                    'legs': [f"{l[0]} ({l[1]})" for l in cycle.legs],
                    'vwap_prices': [f"{ld.vwap_price:.8f}" for ld in cycle.leg_details],
                    'gross_return_pct': round(cycle.gross_return_pct, 4),
                    'total_fees_usdt': round(cycle.total_fees_usdt, 4),
                    'slippage_buffer_usdt': round(cycle.slippage_buffer_usdt, 4),
                    'net_profit_usdt': round(cycle.net_profit_usdt, 4),
                    'net_profit_pct': round(cycle.net_profit_pct, 4),
                    'levels_used': [ld.levels_consumed for ld in cycle.leg_details]
                }
                results['top_opportunities_taker'].append(opp)
            
            # Top 20 opportunities (maker - hypothetical)
            results['top_opportunities_maker'] = []
            for cycle in profitable_maker[:20]:
                opp = {
                    'path': ' -> '.join(cycle.path),
                    'net_profit_usdt': round(cycle.net_profit_usdt, 4),
                    'net_profit_pct': round(cycle.net_profit_pct, 4),
                }
                results['top_opportunities_maker'].append(opp)
            
            results['scan_duration_seconds'] = (datetime.now(timezone.utc) - scan_start).total_seconds()
            
        finally:
            await self.close()
        
        return results
    
    def print_report(self, results: Dict):
        """Print formatted report."""
        print("\n" + "="*80)
        print("📊 OKX SPOT TRIANGULAR ARBITRAGE ANALYSIS REPORT")
        print("="*80)
        
        # A) Summary
        print("\n🅰️ SUMMARY")
        print("-"*40)
        print(f"  Scan timestamp:         {results['scan_timestamp']}")
        print(f"  Trade size:             {results['trade_size_usdt']} USDT")
        print(f"  Slippage buffer:        {results['slippage_buffer_pct']}% per leg")
        print(f"  Instruments scanned:    {results['instruments_scanned']}")
        print(f"  Triangles found:        {results['total_triangles_found']}")
        
        stats = results.get('statistics', {})
        print(f"  Profitable (taker):     {stats.get('positive_after_slippage_taker', 0)}")
        print(f"  Profitable (maker):     {stats.get('positive_maker_scenario', 0)}")
        print(f"  Scan duration:          {results.get('scan_duration_seconds', 0):.1f}s")
        
        # B) Fee Report
        print("\n🅱️ FEE REPORT (from OKX API)")
        print("-"*40)
        fees = results.get('fees', {})
        print(f"  Maker fee:              {fees.get('maker_fee_pct', 0):.4f}%")
        print(f"  Taker fee:              {fees.get('taker_fee_pct', 0):.4f}%")
        print(f"  API response:           {fees.get('api_response', 'N/A')[:100]}")
        
        # C) Top Opportunities (Taker)
        print("\n🅲️ TOP OPPORTUNITIES (Taker Execution)")
        print("-"*40)
        
        opportunities = results.get('top_opportunities_taker', [])
        if not opportunities:
            print("  ❌ No profitable opportunities found with taker fees + slippage")
        else:
            for i, opp in enumerate(opportunities[:10], 1):
                print(f"\n  #{i}: {opp['path']}")
                print(f"      Legs: {', '.join(opp['legs'])}")
                print(f"      Gross return: {opp['gross_return_pct']:.4f}%")
                print(f"      Fees: ${opp['total_fees_usdt']:.4f} | Slippage buffer: ${opp['slippage_buffer_usdt']:.4f}")
                print(f"      💰 Net profit: ${opp['net_profit_usdt']:.4f} ({opp['net_profit_pct']:.4f}%)")
                print(f"      Book levels used: {opp['levels_used']}")
        
        # D) "If you had traded" simulation
        print("\n🅳️ 'IF YOU HAD TRADED' SIMULATION")
        print("-"*40)
        
        if opportunities:
            for i, opp in enumerate(opportunities[:3], 1):
                print(f"\n  Opportunity #{i}: {opp['path']}")
                print(f"  → If you executed this cycle at scan moment with {results['trade_size_usdt']} USDT (taker),")
                print(f"    expected net would be ${opp['net_profit_usdt']:.4f} after fees + {results['slippage_buffer_pct']}% slippage buffer.")
                if opp['net_profit_pct'] > 0.1:
                    print(f"    ⚠️ This edge ({opp['net_profit_pct']:.4f}%) may disappear in <1 second due to competition.")
        else:
            print("  No profitable opportunities to simulate.")
        
        # E) Conclusion
        print("\n🅴️ CONCLUSION")
        print("-"*40)
        
        profitable_count = stats.get('positive_after_slippage_taker', 0)
        before_slip = stats.get('positive_before_slippage', 0)
        
        if profitable_count == 0:
            print("  ❌ VERDICT: OKX spot triangular arbitrage is NOT viable at this moment.")
            print("\n  Dominant blockers:")
            print(f"    • Fees consume most edge (3 legs × {fees.get('taker_fee_pct', 0.15):.2f}% = ~{3 * fees.get('taker_fee_pct', 0.15):.2f}% total)")
            print("    • Bid-ask spreads are typically 0.02-0.10% per leg")
            print("    • Combined friction: ~0.5-1.0% minimum just to break even")
            print(f"    • Cycles profitable before slippage: {before_slip}")
            print(f"    • Cycles profitable after slippage: {profitable_count}")
            if before_slip > 0 and profitable_count == 0:
                print("    → Some marginal opportunities exist but slippage buffer eliminates them")
        else:
            best_edge = opportunities[0]['net_profit_pct'] if opportunities else 0
            print(f"  ✅ VERDICT: Some opportunities exist!")
            print(f"\n  • {profitable_count} profitable cycles found")
            print(f"  • Best net edge: {best_edge:.4f}%")
            print(f"\n  Recommendations:")
            print(f"    • Minimum edge threshold: >0.20% recommended")
            print(f"    • Speed is critical - edges disappear in milliseconds")
            print(f"    • Consider maker orders to reduce fees from {fees.get('taker_fee_pct', 0.15):.2f}% to {fees.get('maker_fee_pct', 0.10):.2f}%")
            print(f"    • Watch for larger size requirements (check book depth)")
        
        # Distribution histogram (text)
        print("\n📈 Net Profit Distribution (all simulated cycles)")
        print("-"*40)
        dist = stats.get('net_profit_distribution', {})
        print(f"  Min: {dist.get('min', 0):.4f}%")
        print(f"  Max: {dist.get('max', 0):.4f}%")
        print(f"  Mean: {dist.get('mean', 0):.4f}%")
        
        print("\n" + "="*80)
        print("🔒 REMINDER: This was ANALYSIS ONLY. No orders were placed.")
        print("="*80)


# ==================== MAIN ====================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='OKX SPOT Triangular Arbitrage Scanner')
    parser.add_argument('--trade-size', type=float, default=TRADE_SIZE_USDT, 
                        help='Trade size in USDT (default: 1000)')
    parser.add_argument('--slippage', type=float, default=SLIPPAGE_BUFFER_PCT,
                        help='Slippage buffer per leg in %% (default: 0.03)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON file path (optional)')
    
    args = parser.parse_args()
    
    scanner = OKXArbitrageScanner(trade_size=args.trade_size, slippage_pct=args.slippage)
    
    print("🚀 Starting OKX SPOT Triangular Arbitrage Scan...")
    print(f"   Trade size: {args.trade_size} USDT")
    print(f"   Slippage buffer: {args.slippage}% per leg")
    
    results = await scanner.run_full_scan()
    
    # Print report
    scanner.print_report(results)
    
    # Optionally save to JSON
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 Results saved to: {args.output}")
    
    return results


if __name__ == '__main__':
    asyncio.run(main())
