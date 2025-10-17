#!/usr/bin/env python3
"""
Decision Replay Utility
Reconstruct trades from decision logs
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_decisions(date: Optional[str] = None, symbol: Optional[str] = None) -> List[dict]:
    """
    Load decisions from JSONL files.
    
    Args:
        date: Date in YYYY-MM-DD format (default: today)
        symbol: Filter by symbol (optional)
        
    Returns:
        List of decision entries
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    log_file = Path(f"logs/decisions/decisions_{date}.jsonl")
    
    if not log_file.exists():
        print(f"[ERROR] No decision log found for {date}")
        print(f"  Expected: {log_file}")
        return []
    
    decisions = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                
                # Filter by symbol
                if symbol and entry.get('sym') != symbol:
                    continue
                
                decisions.append(entry)
            except json.JSONDecodeError:
                continue
    
    return decisions


def replay_decision(entry: dict):
    """Reconstruct a single trading decision."""
    print("\n" + "=" * 60)
    print(f"DECISION REPLAY: {entry['sym']}")
    print("=" * 60)
    
    # Timestamp
    print(f"\n⏰ Time: {entry['t']}")
    
    # Composite signal
    print(f"\n📊 Composite Signal:")
    print(f"  Score: {entry['comp']}/100 (Grade: {entry['grade']})")
    print(f"  Decision: {entry['dir']}")
    print(f"  Confidence: {entry['conf']}%")
    
    # Component scores
    print(f"\n🎯 Component Scores:")
    print(f"  TA:   {entry['ta']}/100 - Trend: {entry.get('ta_trend', 'n/a')}")
    print(f"  ML:   {entry['ml']}/100")
    print(f"  News: {entry['news']}/100")
    print(f"  Risk: {entry['risk']}/100")
    
    # Technical flags
    print(f"\n📈 Technical Flags:")
    print(f"  Trend: {entry.get('ta_trend', 'n/a')}")
    print(f"  Mean Reversion: {entry.get('ta_meanrev', 'n/a')}")
    print(f"  Breakout: {entry.get('ta_breakout', 'n/a')}")
    
    # Gate status
    print(f"\n🚦 Gate Status: {entry['gate']}")
    
    # Action
    print(f"\n🎬 Action: {entry['action']}")
    
    if entry['action'] in ['OPEN', 'ENTRY']:
        print(f"\n💰 Execution Details:")
        print(f"  Size: {entry['size']} contracts")
        if entry.get('tp'):
            print(f"  Take Profit: ${entry['tp']:.2f}")
        if entry.get('sl'):
            print(f"  Stop Loss: ${entry['sl']:.2f}")
    
    # Reason
    if entry.get('reason'):
        print(f"\n📝 Reason: {entry['reason']}")
    
    # Metadata
    if entry.get('meta'):
        print(f"\n🔧 Metadata:")
        for key, value in entry['meta'].items():
            print(f"  {key}: {value}")


def summary_statistics(decisions: List[dict]):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    
    if not decisions:
        print("\nNo decisions found")
        return
    
    # Count by action
    actions = {}
    for d in decisions:
        action = d.get('action', 'UNKNOWN')
        actions[action] = actions.get(action, 0) + 1
    
    print(f"\n📊 Total Decisions: {len(decisions)}")
    print(f"\nActions:")
    for action, count in sorted(actions.items()):
        print(f"  {action}: {count}")
    
    # Average scores
    avg_comp = sum(d['comp'] for d in decisions) / len(decisions)
    avg_ta = sum(d['ta'] for d in decisions) / len(decisions)
    avg_ml = sum(d['ml'] for d in decisions) / len(decisions)
    avg_news = sum(d['news'] for d in decisions) / len(decisions)
    avg_risk = sum(d['risk'] for d in decisions) / len(decisions)
    
    print(f"\n📈 Average Scores:")
    print(f"  Composite: {avg_comp:.1f}/100")
    print(f"  TA: {avg_ta:.1f}/100")
    print(f"  ML: {avg_ml:.1f}/100")
    print(f"  News: {avg_news:.1f}/100")
    print(f"  Risk: {avg_risk:.1f}/100")
    
    # Decision distribution
    directions = {}
    for d in decisions:
        direction = d.get('dir', 'FLAT')
        directions[direction] = directions.get(direction, 0) + 1
    
    print(f"\n🧭 Decision Distribution:")
    for direction, count in sorted(directions.items()):
        pct = count / len(decisions) * 100
        print(f"  {direction}: {count} ({pct:.1f}%)")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Replay trading decisions from logs')
    parser.add_argument('--date', help='Date (YYYY-MM-DD)', default=None)
    parser.add_argument('--symbol', help='Filter by symbol', default=None)
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    parser.add_argument('--last', type=int, help='Show last N decisions', default=None)
    
    args = parser.parse_args()
    
    # Load decisions
    decisions = load_decisions(args.date, args.symbol)
    
    if not decisions:
        return 1
    
    # Limit if requested
    if args.last:
        decisions = decisions[-args.last:]
    
    # Show summary or replay
    if args.summary:
        summary_statistics(decisions)
    else:
        # Replay each decision
        for entry in decisions:
            replay_decision(entry)
        
        # Also show summary
        summary_statistics(decisions)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

