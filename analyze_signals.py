import re
from collections import defaultdict
from datetime import datetime

# Read log file
with open('logs/aibotbs.log', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Parse ALL signals after 19:34
signals = []
transitions = []
entries = []
exits = []
oco_brackets = []

for line in lines:
    # Match time pattern HH:MM:SS
    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', line)
    if not time_match:
        continue
    time_str = time_match.group(1)
    
    # Skip if before 19:34
    if time_str < '19:34:00':
        continue
    
    # Match GATE signal pattern
    gate_match = re.search(r'(\S+-USDT-SWAP)\s+\|\s+tf=15m\s+\|\s+TA=(\d+\.?\d*)\s+ML=(\d+\.?\d*)\s+News=(\d+\.?\d*)\s+Risk=(\d+\.?\d*)\s+\|\s+Final=(\d+\.?\d*)\s+\((\w)\)\s+\|\s+Dir=(\w+)\s+age=(\d+)/(\d+)\s+\|\s+Gate=(\w+)', line)
    if gate_match:
        signals.append({
            'time': time_str,
            'symbol': gate_match.group(1),
            'ta': float(gate_match.group(2)),
            'ml': float(gate_match.group(3)),
            'news': float(gate_match.group(4)),
            'risk': float(gate_match.group(5)),
            'final': float(gate_match.group(6)),
            'grade': gate_match.group(7),
            'dir': gate_match.group(8),
            'age': int(gate_match.group(9)),
            'max_age': int(gate_match.group(10)),
            'gate': gate_match.group(11)
        })
    
    # Match transition pattern
    trans_match = re.search(r'\[ACTION\]\s+(\S+-USDT-SWAP):\s+transition=(\w+)\s+from=(\w+)\s+to=(\w+)', line)
    if trans_match:
        transitions.append({
            'time': time_str,
            'symbol': trans_match.group(1),
            'action': trans_match.group(2),
            'from': trans_match.group(3),
            'to': trans_match.group(4)
        })
    
    # Match entry signals
    if 'ENTRY' in line or 'Opening' in line or 'transition=ENTER' in line:
        entries.append({'time': time_str, 'line': line.strip()})
    
    # Match exit signals
    if 'EXIT' in line or 'Closing' in line or 'transition=EXIT' in line:
        exits.append({'time': time_str, 'line': line.strip()})
    
    # Match OCO bracket creation
    oco_match = re.search(r'\[OCO-BRACKET\]\s+sym=(\S+)\s+oco_link=(\S+)\s+tp_id=(\S+)\s+sl_id=(\S+)', line)
    if oco_match:
        oco_brackets.append({
            'time': time_str,
            'symbol': oco_match.group(1),
            'oco_link': oco_match.group(2),
            'tp_id': oco_match.group(3),
            'sl_id': oco_match.group(4)
        })

# Aggregate by symbol
symbol_data = defaultdict(lambda: {
    'signals': [], 
    'long_signals': 0, 
    'short_signals': 0, 
    'flat_signals': 0, 
    'transitions': [],
    'gate_pass': 0,
    'gate_pending': 0,
    'gate_reject': 0
})

for s in signals:
    sym = s['symbol']
    symbol_data[sym]['signals'].append(s)
    if s['dir'] == 'long':
        symbol_data[sym]['long_signals'] += 1
    elif s['dir'] == 'short':
        symbol_data[sym]['short_signals'] += 1
    else:
        symbol_data[sym]['flat_signals'] += 1
    
    if s['gate'] == 'PASS':
        symbol_data[sym]['gate_pass'] += 1
    elif s['gate'] == 'PENDING':
        symbol_data[sym]['gate_pending'] += 1
    else:
        symbol_data[sym]['gate_reject'] += 1

for t in transitions:
    symbol_data[t['symbol']]['transitions'].append(t)

# Generate markdown report
report = []
report.append("# 📊 Trading Signal Analysis Report")
report.append(f"\n**Analiz Periyodu:** 19:34 - {signals[-1]['time'] if signals else 'N/A'}")
report.append(f"\n**Toplam Sinyal Sayısı:** {len(signals)}")
report.append(f"\n**Toplam Transition Sayısı:** {len(transitions)}")
report.append(f"\n**OCO Bracket Oluşturuldu:** {len(oco_brackets)}")
report.append("\n---\n")

# Summary table
report.append("## 📈 Özet Tablo\n")
report.append("| Coin | Toplam | Long | Short | Flat | Gate PASS | Gate PENDING | Avg TA | Avg ML | Avg Final | Son Dir |")
report.append("|------|--------|------|-------|------|-----------|--------------|--------|--------|-----------|---------|")

for sym in sorted(symbol_data.keys()):
    data = symbol_data[sym]
    total = len(data['signals'])
    if total == 0:
        continue
    avg_ta = sum(s['ta'] for s in data['signals']) / total
    avg_ml = sum(s['ml'] for s in data['signals']) / total
    avg_final = sum(s['final'] for s in data['signals']) / total
    last_dir = data['signals'][-1]['dir'] if data['signals'] else 'N/A'
    
    coin = sym.replace('-USDT-SWAP', '')
    report.append(f"| {coin} | {total} | {data['long_signals']} | {data['short_signals']} | {data['flat_signals']} | {data['gate_pass']} | {data['gate_pending']} | {avg_ta:.1f} | {avg_ml:.1f} | {avg_final:.1f} | {last_dir} |")

report.append("\n---\n")

# Detailed per-coin analysis
report.append("## 📋 Coin Bazlı Detaylı Analiz\n")

for sym in sorted(symbol_data.keys()):
    data = symbol_data[sym]
    if not data['signals']:
        continue
    
    coin = sym.replace('-USDT-SWAP', '')
    report.append(f"### {coin}\n")
    
    # Stats
    total = len(data['signals'])
    report.append(f"**Toplam Sinyal:** {total}\n")
    
    # Current position state
    if data['transitions']:
        last_trans = data['transitions'][-1]
        report.append(f"**Mevcut Durum:** {last_trans['to']}\n")
    
    # All signals table
    report.append("\n| Zaman | TA | ML | News | Risk | Final | Dir | Age | Gate |")
    report.append("|-------|-----|-----|------|------|-------|-----|-----|------|")
    
    for s in data['signals']:
        report.append(f"| {s['time']} | {s['ta']:.1f} | {s['ml']:.1f} | {s['news']:.1f} | {s['risk']:.1f} | {s['final']:.1f} | {s['dir']} | {s['age']}/{s['max_age']} | {s['gate']} |")
    
    # Transitions
    if data['transitions']:
        report.append("\n**State Transitions:**\n")
        report.append("| Zaman | Action | From → To |")
        report.append("|-------|--------|-----------|")
        for t in data['transitions']:
            report.append(f"| {t['time']} | {t['action']} | {t['from']} → {t['to']} |")
    
    report.append("\n---\n")

# Reversal analysis
report.append("## 🔄 Ters Sinyal Analizi\n")
report.append("Short pozisyondayken Long sinyal veya Long pozisyondayken Short sinyal geldi mi?\n")

reversal_found = False
for sym in sorted(symbol_data.keys()):
    data = symbol_data[sym]
    coin = sym.replace('-USDT-SWAP', '')
    
    current_position = None
    for t in data['transitions']:
        current_position = t['to']
    
    reversals = []
    for s in data['signals']:
        if current_position == 'SHORT_OPEN' and s['dir'] == 'long':
            reversals.append(f"- {s['time']} | **LONG sinyal** geldi ama pozisyon SHORT_OPEN | Final={s['final']}")
            reversal_found = True
        elif current_position == 'LONG_OPEN' and s['dir'] == 'short':
            reversals.append(f"- {s['time']} | **SHORT sinyal** geldi ama pozisyon LONG_OPEN | Final={s['final']}")
            reversal_found = True
    
    if reversals:
        report.append(f"### {coin}\n")
        for r in reversals:
            report.append(r)
        report.append("")

if not reversal_found:
    report.append("❌ **Hiçbir ters sinyal tespit edilmedi.** Tüm pozisyonlar kendi yönündeki sinyalleri almaya devam etti.\n")

# OCO Brackets
if oco_brackets:
    report.append("## 🔗 OCO Bracket Emirleri\n")
    report.append("| Zaman | Symbol | OCO Link | TP ID | SL ID |")
    report.append("|-------|--------|----------|-------|-------|")
    for oco in oco_brackets:
        report.append(f"| {oco['time']} | {oco['symbol']} | {oco['oco_link']} | {oco['tp_id'][:10]}... | {oco['sl_id'][:10]}... |")

# Entry/Exit events
if entries:
    report.append("\n## 📥 Entry Sinyalleri\n")
    for e in entries[:20]:
        report.append(f"- `{e['time']}` {e['line'][:100]}...")

if exits:
    report.append("\n## 📤 Exit Sinyalleri\n")
    for e in exits[:20]:
        report.append(f"- `{e['time']}` {e['line'][:100]}...")

# Write report
with open('signal_report.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(report))

print(f"✅ Report generated: signal_report.md")
print(f"Total signals: {len(signals)}")
print(f"Total transitions: {len(transitions)}")
print(f"OCO brackets: {len(oco_brackets)}")
