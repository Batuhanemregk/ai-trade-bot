#!/usr/bin/env python3
"""
Analyze trading logs for 2025-11-10 to understand why no trades were executed.
"""
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Optional

def parse_decision_log(line: str) -> Optional[Dict]:
    """Parse a decision log line and extract key information."""
    # Pattern: timestamp | level | logger:function:line - message
    # Example: 2025-11-10 00:00:08.946 | INFO | infrastructure.decision_logger:log_decision_summary:108 - ℹ️ 21:00:08 | BTC-USDT-SWAP | tf=15m | bar=2025-11-09T21:00:00Z | run=... | TA=59.2 ML=51.0 News=50.0 Risk=57.4 | Final=54.6 (FAIL) | Dir=flat | Gate=FAIL (persist , conf , age , hyst=) | ...
    
    if 'decision_logger' not in line or 'log_decision_summary' not in line:
        return None
    
    try:
        # Extract timestamp
        timestamp_match = re.search(r'2025-11-10 (\d{2}:\d{2}:\d{2})', line)
        if not timestamp_match:
            return None
        
        # Extract symbol
        symbol_match = re.search(r'(\w+-\w+-\w+)\s+\|', line)
        symbol = symbol_match.group(1) if symbol_match else 'UNKNOWN'
        
        # Extract bar
        bar_match = re.search(r'bar=([^|\s]+)', line)
        bar = bar_match.group(1) if bar_match else 'UNKNOWN'
        
        # Extract scores
        ta_match = re.search(r'TA=([\d.]+)', line)
        ml_match = re.search(r'ML=([\d.]+)', line)
        news_match = re.search(r'News=([\d.]+)', line)
        risk_match = re.search(r'Risk=([\d.]+)', line)
        final_match = re.search(r'Final=([\d.]+)', line)
        
        ta = float(ta_match.group(1)) if ta_match else None
        ml = float(ml_match.group(1)) if ml_match else None
        news = float(news_match.group(1)) if news_match else None
        risk = float(risk_match.group(1)) if risk_match else None
        final = float(final_match.group(1)) if final_match else None
        
        # Extract direction and gate status
        dir_match = re.search(r'Dir=(\w+)', line)
        direction = dir_match.group(1) if dir_match else 'UNKNOWN'
        
        gate_match = re.search(r'Gate=(\w+)', line)
        gate = gate_match.group(1) if gate_match else 'UNKNOWN'
        
        # Extract gate details
        persist_match = re.search(r'persist\s+(\d+)/(\d+)', line)
        conf_match = re.search(r'conf\s+([\d.]+)/([\d.]+)', line)
        age_match = re.search(r'age\s+(\d+)/(\d+)', line)
        
        persist = (int(persist_match.group(1)), int(persist_match.group(2))) if persist_match else (0, 5)
        conf = (float(conf_match.group(1)), float(conf_match.group(2))) if conf_match else (0.0, 0.0)
        age = (int(age_match.group(1)), int(age_match.group(2))) if age_match else (0, 6)
        
        # Extract state (handle both → and ->)
        state_match = re.search(r'state:\s+(\w+)[→-](\w+)', line)
        state_from = state_match.group(1) if state_match else 'UNKNOWN'
        state_to = state_match.group(2) if state_match else 'UNKNOWN'
        
        return {
            'timestamp': timestamp_match.group(1),
            'symbol': symbol,
            'bar': bar,
            'ta': ta,
            'ml': ml,
            'news': news,
            'risk': risk,
            'final': final,
            'direction': direction,
            'gate': gate,
            'persist': persist,
            'conf': conf,
            'age': age,
            'state_from': state_from,
            'state_to': state_to,
            'raw_line': line.strip()
        }
    except Exception as e:
        print(f"Error parsing line: {e}")
        return None

def parse_error_log(line: str) -> Optional[Dict]:
    """Parse an error log line."""
    if 'ERROR' not in line or '2025-11-10' not in line:
        return None
    
    try:
        timestamp_match = re.search(r'2025-11-10 (\d{2}:\d{2}:\d{2})', line)
        if not timestamp_match:
            return None
        
        # Extract error message
        error_match = re.search(r'ERROR.*?-\s+(.+?)(?:\n|$)', line)
        error_msg = error_match.group(1).strip() if error_match else line.strip()
        
        # Extract logger
        logger_match = re.search(r'(\w+(?:\.\w+)*):\w+:\d+', line)
        logger = logger_match.group(1) if logger_match else 'UNKNOWN'
        
        return {
            'timestamp': timestamp_match.group(1),
            'logger': logger,
            'message': error_msg,
            'raw_line': line.strip()
        }
    except Exception as e:
        return None

def parse_warning_log(line: str) -> Optional[Dict]:
    """Parse a warning log line."""
    if 'WARNING' not in line or '2025-11-10' not in line:
        return None
    
    try:
        timestamp_match = re.search(r'2025-11-10 (\d{2}:\d{2}:\d{2})', line)
        if not timestamp_match:
            return None
        
        warning_match = re.search(r'WARNING.*?-\s+(.+?)(?:\n|$)', line)
        warning_msg = warning_match.group(1).strip() if warning_match else line.strip()
        
        logger_match = re.search(r'(\w+(?:\.\w+)*):\w+:\d+', line)
        logger = logger_match.group(1) if logger_match else 'UNKNOWN'
        
        return {
            'timestamp': timestamp_match.group(1),
            'logger': logger,
            'message': warning_msg,
            'raw_line': line.strip()
        }
    except Exception as e:
        return None

def analyze_logs(log_file: str):
    """Analyze logs for 2025-11-10."""
    print(f"Analyzing logs from {log_file}...")
    
    decisions = []
    errors = []
    warnings = []
    
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '2025-11-10' not in line:
                continue
            
            # Parse decision logs
            decision = parse_decision_log(line)
            if decision:
                decisions.append(decision)
            
            # Parse errors
            error = parse_error_log(line)
            if error:
                errors.append(error)
            
            # Parse warnings
            warning = parse_warning_log(line)
            if warning:
                warnings.append(warning)
    
    print(f"\n=== SUMMARY ===")
    print(f"Total decisions: {len(decisions)}")
    print(f"Total errors: {len(errors)}")
    print(f"Total warnings: {len(warnings)}")
    
    # Analyze decisions
    if decisions:
        print(f"\n=== DECISION ANALYSIS ===")
        
        # Group by bar
        bars = defaultdict(list)
        for d in decisions:
            bars[d['bar']].append(d)
        
        print(f"Unique bars analyzed: {len(bars)}")
        
        # Count gate statuses
        gate_counts = defaultdict(int)
        direction_counts = defaultdict(int)
        state_transitions = defaultdict(int)
        
        for d in decisions:
            gate_counts[d['gate']] += 1
            direction_counts[d['direction']] += 1
            state_transitions[f"{d['state_from']}→{d['state_to']}"] += 1
        
        print(f"\nGate statuses:")
        for gate, count in sorted(gate_counts.items(), key=lambda x: -x[1]):
            print(f"  {gate}: {count}")
        
        print(f"\nDirections:")
        for direction, count in sorted(direction_counts.items(), key=lambda x: -x[1]):
            print(f"  {direction}: {count}")
        
        print(f"\nState transitions:")
        for transition, count in sorted(state_transitions.items(), key=lambda x: -x[1])[:10]:
            # Replace any arrow-like characters with ->
            trans_str = transition.replace('\u2192', '->').replace('\u2013', '->').replace('-', '->')
            print(f"  {trans_str}: {count}")
        
        # Analyze final scores
        final_scores = [d['final'] for d in decisions if d['final'] is not None]
        if final_scores:
            print(f"\nFinal score statistics:")
            print(f"  Min: {min(final_scores):.2f}")
            print(f"  Max: {max(final_scores):.2f}")
            print(f"  Avg: {sum(final_scores)/len(final_scores):.2f}")
            print(f"  Scores >= 60 (LONG threshold): {sum(1 for s in final_scores if s >= 60)}")
            print(f"  Scores <= 40 (SHORT threshold): {sum(1 for s in final_scores if s <= 40)}")
            print(f"  Scores in 40-60 range (FLAT): {sum(1 for s in final_scores if 40 < s < 60)}")
        
        # Find closest to thresholds
        print(f"\nClosest to LONG threshold (>=60):")
        long_candidates = [(d['symbol'], d['bar'], d['final'], d['gate'], d['persist'], d['conf'], d['age']) 
                          for d in decisions if d['final'] is not None and d['final'] >= 55]
        long_candidates.sort(key=lambda x: -x[2])
        for symbol, bar, final, gate, persist, conf, age in long_candidates[:10]:
            print(f"  {symbol} | {bar} | Final={final:.2f} | Gate={gate} | persist={persist[0]}/{persist[1]} | conf={conf[0]:.2f}/{conf[1]:.2f} | age={age[0]}/{age[1]}")
        
        print(f"\nClosest to SHORT threshold (<=40):")
        short_candidates = [(d['symbol'], d['bar'], d['final'], d['gate'], d['persist'], d['conf'], d['age']) 
                           for d in decisions if d['final'] is not None and d['final'] <= 45]
        short_candidates.sort(key=lambda x: x[2])
        for symbol, bar, final, gate, persist, conf, age in short_candidates[:10]:
            print(f"  {symbol} | {bar} | Final={final:.2f} | Gate={gate} | persist={persist[0]}/{persist[1]} | conf={conf[0]:.2f}/{conf[1]:.2f} | age={age[0]}/{age[1]}")
        
        # Analyze gate failures
        print(f"\n=== GATE FAILURE ANALYSIS ===")
        gate_failures = [d for d in decisions if d['gate'] == 'FAIL']
        print(f"Total gate failures: {len(gate_failures)}")
        
        # Group by failure reason (persist, conf, age)
        persist_failures = [d for d in gate_failures if d['persist'][0] < d['persist'][1]]
        conf_failures = [d for d in gate_failures if d['conf'][0] < d['conf'][1] and d['conf'][1] > 0]
        age_failures = [d for d in gate_failures if d['age'][0] < d['age'][1]]
        
        print(f"  Persist failures (persist < required): {len(persist_failures)}")
        print(f"  Confirmation failures (conf < required): {len(conf_failures)}")
        print(f"  Age failures (age < required): {len(age_failures)}")
    
    # Analyze errors
    if errors:
        print(f"\n=== ERROR ANALYSIS ===")
        
        # Group by logger
        error_by_logger = defaultdict(list)
        for e in errors:
            error_by_logger[e['logger']].append(e)
        
        print(f"Errors by logger:")
        for logger, errs in sorted(error_by_logger.items(), key=lambda x: -len(x[1])):
            print(f"  {logger}: {len(errs)}")
        
        # Most common errors
        error_messages = defaultdict(int)
        for e in errors:
            # Extract key part of error message
            msg = e['message'][:100] if len(e['message']) > 100 else e['message']
            error_messages[msg] += 1
        
        print(f"\nMost common errors:")
        for msg, count in sorted(error_messages.items(), key=lambda x: -x[1])[:10]:
            print(f"  [{count}x] {msg}")
    
    # Analyze warnings
    if warnings:
        print(f"\n=== WARNING ANALYSIS ===")
        
        # Group by logger
        warning_by_logger = defaultdict(list)
        for w in warnings:
            warning_by_logger[w['logger']].append(w)
        
        print(f"Warnings by logger:")
        for logger, warns in sorted(warning_by_logger.items(), key=lambda x: -len(x[1])):
            print(f"  {logger}: {len(warns)}")
        
        # Most common warnings
        warning_messages = defaultdict(int)
        for w in warnings:
            msg = w['message'][:100] if len(w['message']) > 100 else w['message']
            warning_messages[msg] += 1
        
        print(f"\nMost common warnings:")
        for msg, count in sorted(warning_messages.items(), key=lambda x: -x[1])[:10]:
            print(f"  [{count}x] {msg}")
    
    # Time-based analysis
    if decisions:
        print(f"\n=== TIME-BASED ANALYSIS ===")
        
        # Group by hour
        hours = defaultdict(int)
        for d in decisions:
            hour = d['timestamp'][:2]
            hours[hour] += 1
        
        print(f"Decisions per hour:")
        for hour in sorted(hours.keys()):
            print(f"  {hour}:00 - {hours[hour]} decisions")
    
    return decisions, errors, warnings

if __name__ == '__main__':
    import sys
    import io
    # Force UTF-8 encoding for stdout
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    decisions, errors, warnings = analyze_logs('logs/fallback.log')
    
    # Write detailed report
    with open('docs/TRADING_ANALYSIS_2025-11-10.md', 'w', encoding='utf-8') as f:
        f.write("# Trading Analysis Report - 2025-11-10\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total decisions: {len(decisions)}\n")
        f.write(f"- Total errors: {len(errors)}\n")
        f.write(f"- Total warnings: {len(warnings)}\n")
        f.write(f"- Trades executed: 0\n\n")
        
        if decisions:
            final_scores = [d['final'] for d in decisions if d['final'] is not None]
            if final_scores:
                f.write(f"## Score Statistics\n\n")
                f.write(f"- Min score: {min(final_scores):.2f}\n")
                f.write(f"- Max score: {max(final_scores):.2f}\n")
                f.write(f"- Avg score: {sum(final_scores)/len(final_scores):.2f}\n")
                f.write(f"- Scores >= 60: {sum(1 for s in final_scores if s >= 60)}\n")
                f.write(f"- Scores <= 40: {sum(1 for s in final_scores if s <= 40)}\n")
                f.write(f"- Scores in 40-60 range: {sum(1 for s in final_scores if 40 < s < 60)}\n\n")
            
            gate_failures = [d for d in decisions if d['gate'] == 'FAIL']
            f.write(f"## Gate Failures\n\n")
            f.write(f"- Total gate failures: {len(gate_failures)}\n")
            f.write(f"- Persist failures: {len([d for d in gate_failures if d['persist'][0] < d['persist'][1]])}\n")
            f.write(f"- Confirmation failures: {len([d for d in gate_failures if d['conf'][0] < d['conf'][1] and d['conf'][1] > 0])}\n")
            f.write(f"- Age failures: {len([d for d in gate_failures if d['age'][0] < d['age'][1]])}\n\n")
    
    print(f"\n=== Report written to docs/TRADING_ANALYSIS_2025-11-10.md ===")

