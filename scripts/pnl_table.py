"""Get last 24 hours PnL from OKX API."""
import asyncio
from datetime import datetime, timedelta
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from infrastructure.bootstrap import load_env

async def main():
    load_env()
    adapter = OKXCCXTAdapter()
    
    # Calculate 24 hours ago timestamp
    now = datetime.now()
    yesterday = now - timedelta(hours=24)
    yesterday_ts = int(yesterday.timestamp() * 1000)
    
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append(f"SON 24 SAAT PNL ({yesterday.strftime('%m-%d %H:%M')} - {now.strftime('%m-%d %H:%M')})")
    output_lines.append("=" * 80)
    
    try:
        # Fetch all bills from last 24h
        result = adapter.exchange.private_get_account_bills_archive({
            'instType': 'SWAP',
            'type': '2',
            'limit': '100',
            'begin': str(yesterday_ts)
        })
        
        bills = result.get('data', [])
        
        # Filter for realized PnL entries in last 24h
        pnl_entries = []
        for bill in bills:
            ts = int(bill.get('ts', 0))
            if ts >= yesterday_ts:
                pnl = float(bill.get('pnl', 0))
                if pnl != 0:
                    pnl_entries.append({
                        'symbol': bill.get('instId', ''),
                        'pnl': pnl,
                        'fee': float(bill.get('fee', 0)),
                        'time': bill.get('ts', '')
                    })
        
        total_pnl = 0
        total_fee = 0
        wins = 0
        losses = 0
        
        # Group by symbol for summary
        symbol_pnl = {}
        
        output_lines.append(f"{'#':<3} {'Sembol':<12} {'PnL':>12} {'Fee':>10} {'Zaman':<12}")
        output_lines.append("-" * 80)
        
        for i, entry in enumerate(pnl_entries, 1):
            symbol = entry['symbol'].replace('-USDT-SWAP', '')
            pnl = entry['pnl']
            fee = entry['fee']
            ts = int(entry['time']) if entry['time'] else 0
            time_str = datetime.fromtimestamp(ts/1000).strftime('%H:%M') if ts else 'N/A'
            
            total_pnl += pnl
            total_fee += fee
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
            
            # Accumulate by symbol
            if symbol not in symbol_pnl:
                symbol_pnl[symbol] = 0
            symbol_pnl[symbol] += pnl
            
            pnl_sign = '+' if pnl >= 0 else ''
            icon = '[+]' if pnl > 0 else '[-]' if pnl < 0 else '[=]'
            
            output_lines.append(f"{i:<3} {symbol:<12} {icon} {pnl_sign}${pnl:>8.2f} ${fee:>8.2f} {time_str}")
        
        output_lines.append("-" * 80)
        
        # Symbol summary
        output_lines.append("\nSEMBOL BAZLI OZET:")
        for sym, pnl in sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True):
            icon = '[+]' if pnl > 0 else '[-]' if pnl < 0 else '[=]'
            pnl_sign = '+' if pnl >= 0 else ''
            output_lines.append(f"  {sym:<10} {icon} {pnl_sign}${pnl:.2f}")
        
        output_lines.append("-" * 80)
        total_sign = '+' if total_pnl >= 0 else ''
        output_lines.append(f"TOPLAM PnL: {total_sign}${total_pnl:.2f}")
        output_lines.append(f"TOPLAM Fee: ${total_fee:.2f}")
        output_lines.append(f"NET KAR: {total_sign}${total_pnl + total_fee:.2f}")
        output_lines.append(f"Islem: {len(pnl_entries)} | Kazanc: {wins} | Kayip: {losses}")
        if wins + losses > 0:
            output_lines.append(f"Win Rate: {wins/(wins+losses)*100:.1f}%")
        
    except Exception as e:
        output_lines.append(f"Error: {e}")
        import traceback
        output_lines.append(traceback.format_exc())
    
    await adapter.close()
    
    with open('data/pnl_table_output.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    for line in output_lines:
        print(line)

asyncio.run(main())
