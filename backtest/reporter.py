"""
Backtest Reporter.

Generates output files:
- trades.csv: Individual trade records
- summary.json: Performance metrics
- gate_stats.csv: Signal gate skip reasons
- equity_curve.csv: Equity over time (optional)
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import Counter
from loguru import logger


class BacktestReporter:
    """
    Generates backtest reports and output files.
    """
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Collected data
        self.gate_reasons: List[str] = []
        self.decision_log: List[Dict[str, Any]] = []
    
    def record_decision(
        self,
        timestamp: datetime,
        symbol: str,
        ta_score: float,
        ml_score: float,
        news_score: float,
        risk_score: float,
        final_score: float,
        decision: str,
        skip_reason: str,
        has_position: bool,
        position_side: str = None
    ):
        """Record a per-bar decision for logging."""
        self.decision_log.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'ta_score': ta_score,
            'ml_score': ml_score,
            'news_score': news_score,
            'risk_score': risk_score,
            'final_score': final_score,
            'decision': decision,
            'skip_reason': skip_reason,
            'has_position': has_position,
            'position_side': position_side
        })
        
        if skip_reason:
            self.gate_reasons.append(skip_reason)
    
    def save_trades(self, trades: List[Any]):
        """Save trades to CSV."""
        file_path = self.output_dir / "trades.csv"
        
        if not trades:
            logger.warning("[REPORT] No trades to save")
            return
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'trade_id', 'symbol', 'side', 'entry_time', 'entry_price',
                'entry_bar', 'exit_time', 'exit_price', 'exit_bar',
                'exit_reason', 'size', 'pnl_pct', 'pnl_usdt', 'fees_usdt',
                'holding_bars', 'max_adverse_excursion'
            ])
            
            # Data
            for t in trades:
                writer.writerow([
                    t.trade_id,
                    t.symbol,
                    t.side,
                    t.entry_time.isoformat() if t.entry_time else '',
                    f"{t.entry_price:.6f}",
                    t.entry_bar,
                    t.exit_time.isoformat() if t.exit_time else '',
                    f"{t.exit_price:.6f}",
                    t.exit_bar,
                    t.exit_reason,
                    f"{t.size:.2f}",
                    f"{t.pnl_pct:.4f}",
                    f"{t.pnl_usdt:.4f}",
                    f"{t.fees_usdt:.4f}",
                    t.holding_bars,
                    f"{t.max_adverse_excursion:.4f}"
                ])
        
        logger.info(f"[REPORT] Saved {len(trades)} trades to {file_path}")
    
    def save_summary(
        self,
        trades: List[Any],
        initial_balance: float,
        final_balance: float,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        equity_curve: List[Dict[str, Any]] = None
    ):
        """Calculate and save performance summary."""
        if not trades:
            summary = {
                'symbol': symbol,
                'period': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                },
                'initial_balance': initial_balance,
                'final_balance': final_balance,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl_pct': 0.0,
                'total_pnl_usdt': 0.0,
                'profit_factor': 0.0,
                'max_drawdown_pct': 0.0,
                'sharpe_ratio': 0.0,
                'avg_trade_pnl': 0.0,
                'avg_holding_bars': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'fees_total': 0.0
            }
        else:
            winning = [t for t in trades if t.pnl_usdt > 0]
            losing = [t for t in trades if t.pnl_usdt <= 0]
            
            total_pnl = sum(t.pnl_usdt for t in trades)
            total_pnl_pct = (final_balance - initial_balance) / initial_balance * 100
            
            # Gross profit/loss
            gross_profit = sum(t.pnl_usdt for t in winning) if winning else 0
            gross_loss = abs(sum(t.pnl_usdt for t in losing)) if losing else 0
            
            # Profit factor
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Max drawdown from equity curve
            max_dd = 0.0
            if equity_curve:
                peak = equity_curve[0].get('equity', initial_balance)
                for point in equity_curve:
                    equity = point.get('equity', initial_balance)
                    if equity > peak:
                        peak = equity
                    dd = (peak - equity) / peak * 100 if peak > 0 else 0
                    if dd > max_dd:
                        max_dd = dd
            
            # Sharpe ratio (simplified)
            import numpy as np
            returns = [t.pnl_pct for t in trades]
            if len(returns) > 1:
                sharpe = np.mean(returns) / (np.std(returns) + 0.001) * np.sqrt(252)
            else:
                sharpe = 0.0
            
            summary = {
                'symbol': symbol,
                'period': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None
                },
                'initial_balance': initial_balance,
                'final_balance': round(final_balance, 2),
                'total_trades': len(trades),
                'winning_trades': len(winning),
                'losing_trades': len(losing),
                'win_rate': round(len(winning) / len(trades), 4) if trades else 0,
                'total_pnl_pct': round(total_pnl_pct, 4),
                'total_pnl_usdt': round(total_pnl, 2),
                'profit_factor': round(profit_factor, 4) if profit_factor != float('inf') else 999.0,
                'max_drawdown_pct': round(max_dd, 4),
                'sharpe_ratio': round(sharpe, 4),
                'avg_trade_pnl': round(np.mean([t.pnl_pct for t in trades]), 4) if trades else 0,
                'avg_holding_bars': round(np.mean([t.holding_bars for t in trades]), 2) if trades else 0,
                'avg_win': round(np.mean([t.pnl_pct for t in winning]), 4) if winning else 0,
                'avg_loss': round(np.mean([t.pnl_pct for t in losing]), 4) if losing else 0,
                'fees_total': round(sum(t.fees_usdt for t in trades), 2)
            }
        
        file_path = self.output_dir / "summary.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"[REPORT] Saved summary to {file_path}")
        
        # Print summary to console
        print("\n" + "="*60)
        print("BACKTEST SUMMARY")
        print("="*60)
        print(f"Symbol: {summary['symbol']}")
        print(f"Period: {summary['period']['start']} to {summary['period']['end']}")
        print(f"Initial Balance: ${summary['initial_balance']:,.2f}")
        print(f"Final Balance: ${summary['final_balance']:,.2f}")
        print("-"*60)
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['win_rate']*100:.1f}% ({summary['winning_trades']}W / {summary['losing_trades']}L)")
        print(f"Total PnL: {summary['total_pnl_pct']:+.2f}% (${summary['total_pnl_usdt']:+,.2f})")
        print(f"Profit Factor: {summary['profit_factor']:.2f}")
        print(f"Max Drawdown: {summary['max_drawdown_pct']:.2f}%")
        print(f"Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
        print(f"Avg Trade PnL: {summary['avg_trade_pnl']:.2f}%")
        print(f"Avg Holding: {summary['avg_holding_bars']:.1f} bars")
        print(f"Total Fees: ${summary['fees_total']:.2f}")
        print("="*60 + "\n")
        
        return summary
    
    def save_gate_stats(self):
        """Save signal gate skip statistics."""
        file_path = self.output_dir / "gate_stats.csv"
        
        counter = Counter(self.gate_reasons)
        total = len(self.gate_reasons)
        
        # Add PASS count
        pass_count = len([d for d in self.decision_log if d['decision'] in ['OPEN_LONG', 'OPEN_SHORT', 'REVERSE']])
        counter['PASS'] = pass_count
        total_decisions = total + pass_count
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['reason', 'count', 'pct'])
            
            for reason, count in counter.most_common():
                pct = count / total_decisions * 100 if total_decisions > 0 else 0
                writer.writerow([reason, count, f"{pct:.1f}"])
        
        logger.info(f"[REPORT] Saved gate stats to {file_path}")
    
    def save_equity_curve(self, equity_curve: List[Dict[str, Any]]):
        """Save equity curve to CSV."""
        if not equity_curve:
            return
        
        file_path = self.output_dir / "equity_curve.csv"
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['bar', 'timestamp', 'equity', 'balance', 'unrealized', 'position_count'])
            
            for point in equity_curve:
                ts = point.get('timestamp')
                writer.writerow([
                    point.get('bar', 0),
                    ts.isoformat() if ts else '',
                    f"{point.get('equity', 0):.2f}",
                    f"{point.get('balance', 0):.2f}",
                    f"{point.get('unrealized', 0):.2f}",
                    point.get('position_count', 0)
                ])
        
        logger.info(f"[REPORT] Saved equity curve to {file_path}")
    
    def save_all(
        self,
        trades: List[Any],
        initial_balance: float,
        final_balance: float,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        equity_curve: List[Dict[str, Any]] = None
    ):
        """Save all reports."""
        self.save_trades(trades)
        summary = self.save_summary(trades, initial_balance, final_balance, symbol, start_date, end_date, equity_curve)
        self.save_gate_stats()
        if equity_curve:
            self.save_equity_curve(equity_curve)
        
        return summary
