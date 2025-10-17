"""
Visualization tools for backtest results.
Creates equity curves, drawdown charts, and trade analysis plots.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
from loguru import logger


class EquityCurveVisualizer:
    """
    Creates visualizations for backtest results.
    """
    
    def __init__(self, output_dir: str = "backtests/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Visualizer initialized: {self.output_dir}")
    
    def plot_equity_curve(
        self,
        equity_curve: List[Tuple[datetime, float]],
        trades: List[Dict[str, Any]],
        initial_capital: float,
        symbol: str = "Portfolio",
        save_path: Optional[str] = None
    ) -> str:
        """
        Plot equity curve with trade markers.
        
        Args:
            equity_curve: List of (timestamp, equity) tuples
            trades: List of trade dictionaries
            initial_capital: Starting capital
            symbol: Symbol or portfolio name
            save_path: Custom save path (optional)
            
        Returns:
            Path to saved plot
        """
        if len(equity_curve) == 0:
            logger.warning("No equity curve data to plot")
            return ""
        
        # Prepare data
        timestamps = [ec[0] for ec in equity_curve]
        equity_values = [ec[1] for ec in equity_curve]
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
        fig.suptitle(f'Backtest Results: {symbol}', fontsize=16, fontweight='bold')
        
        # Plot equity curve
        ax1.plot(timestamps, equity_values, linewidth=2, color='#2E86DE', label='Equity')
        ax1.axhline(y=initial_capital, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
        
        # Mark winning and losing trades
        for trade in trades:
            color = 'green' if trade['pnl'] > 0 else 'red'
            marker = '^' if trade['direction'] == 'LONG' else 'v'
            
            # Entry marker
            entry_idx = self._find_closest_index(timestamps, trade['entry_time'])
            if entry_idx is not None:
                ax1.scatter(
                    timestamps[entry_idx], 
                    equity_values[entry_idx],
                    color=color, 
                    marker=marker, 
                    s=100,
                    alpha=0.6,
                    edgecolors='black',
                    linewidths=0.5
                )
        
        ax1.set_ylabel('Portfolio Value ($)', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left', fontsize=10)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Calculate and plot drawdown
        equity_series = pd.Series(equity_values)
        running_max = equity_series.expanding().max()
        drawdown = ((equity_series - running_max) / running_max) * 100
        
        ax2.fill_between(timestamps, drawdown, 0, color='red', alpha=0.3, label='Drawdown')
        ax2.plot(timestamps, drawdown, color='darkred', linewidth=1.5)
        ax2.set_ylabel('Drawdown (%)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='lower left', fontsize=10)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add statistics text box
        final_equity = equity_values[-1]
        total_return = ((final_equity - initial_capital) / initial_capital) * 100
        max_dd = drawdown.min()
        
        stats_text = f'Initial: ${initial_capital:,.0f}\n'
        stats_text += f'Final: ${final_equity:,.0f}\n'
        stats_text += f'Return: {total_return:.2f}%\n'
        stats_text += f'Max DD: {max_dd:.2f}%\n'
        stats_text += f'Trades: {len(trades)}'
        
        ax1.text(
            0.02, 0.98, stats_text,
            transform=ax1.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        )
        
        plt.tight_layout()
        
        # Save plot
        if save_path is None:
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = self.output_dir / f"equity_curve_{symbol}_{timestamp_str}.png"
        else:
            save_path = Path(save_path)
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Equity curve saved to {save_path}")
        return str(save_path)
    
    def plot_trade_analysis(
        self,
        trades: List[Dict[str, Any]],
        symbol: str = "Portfolio",
        save_path: Optional[str] = None
    ) -> str:
        """
        Plot trade analysis charts.
        
        Args:
            trades: List of trade dictionaries
            symbol: Symbol or portfolio name
            save_path: Custom save path (optional)
            
        Returns:
            Path to saved plot
        """
        if len(trades) == 0:
            logger.warning("No trades to analyze")
            return ""
        
        # Prepare data
        pnls = [t['pnl'] for t in trades]
        pnl_pcts = [t['pnl_pct'] for t in trades]
        cumulative_pnl = np.cumsum(pnls)
        
        # Create figure with subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'Trade Analysis: {symbol}', fontsize=16, fontweight='bold')
        
        # 1. PnL per trade
        colors = ['green' if pnl > 0 else 'red' for pnl in pnls]
        ax1.bar(range(len(pnls)), pnls, color=colors, alpha=0.7)
        ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax1.set_xlabel('Trade Number', fontweight='bold')
        ax1.set_ylabel('PnL ($)', fontweight='bold')
        ax1.set_title('PnL per Trade')
        ax1.grid(True, alpha=0.3)
        
        # 2. Cumulative PnL
        ax2.plot(range(len(cumulative_pnl)), cumulative_pnl, linewidth=2, color='#2E86DE')
        ax2.fill_between(range(len(cumulative_pnl)), cumulative_pnl, 0, alpha=0.3, color='#2E86DE')
        ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        ax2.set_xlabel('Trade Number', fontweight='bold')
        ax2.set_ylabel('Cumulative PnL ($)', fontweight='bold')
        ax2.set_title('Cumulative PnL')
        ax2.grid(True, alpha=0.3)
        
        # 3. PnL distribution
        ax3.hist(pnl_pcts, bins=20, color='steelblue', alpha=0.7, edgecolor='black')
        ax3.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Break-even')
        ax3.set_xlabel('PnL (%)', fontweight='bold')
        ax3.set_ylabel('Frequency', fontweight='bold')
        ax3.set_title('PnL Distribution')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Trade duration vs PnL
        durations = [t['duration_hours'] for t in trades if 'duration_hours' in t]
        if durations:
            scatter_colors = ['green' if pnl > 0 else 'red' for pnl in pnls]
            ax4.scatter(durations, pnls, c=scatter_colors, alpha=0.6, s=50, edgecolors='black', linewidths=0.5)
            ax4.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
            ax4.set_xlabel('Duration (hours)', fontweight='bold')
            ax4.set_ylabel('PnL ($)', fontweight='bold')
            ax4.set_title('Trade Duration vs PnL')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        if save_path is None:
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = self.output_dir / f"trade_analysis_{symbol}_{timestamp_str}.png"
        else:
            save_path = Path(save_path)
        
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Trade analysis saved to {save_path}")
        return str(save_path)
    
    def export_trades_csv(
        self,
        trades: List[Dict[str, Any]],
        symbol: str = "Portfolio",
        save_path: Optional[str] = None
    ) -> str:
        """
        Export trades to CSV file.
        
        Args:
            trades: List of trade dictionaries
            symbol: Symbol or portfolio name
            save_path: Custom save path (optional)
            
        Returns:
            Path to saved CSV
        """
        if len(trades) == 0:
            logger.warning("No trades to export")
            return ""
        
        # Convert to DataFrame
        df = pd.DataFrame(trades)
        
        # Reorder columns for readability
        column_order = [
            'symbol', 'direction', 'entry_time', 'exit_time',
            'entry_price', 'exit_price', 'quantity',
            'pnl', 'pnl_pct', 'duration_hours',
            'exit_reason', 'signal_score', 'commission_total'
        ]
        
        # Only include columns that exist
        column_order = [col for col in column_order if col in df.columns]
        df = df[column_order]
        
        # Format datetime columns
        for col in ['entry_time', 'exit_time']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Save to CSV
        if save_path is None:
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = self.output_dir / f"trades_{symbol}_{timestamp_str}.csv"
        else:
            save_path = Path(save_path)
        
        df.to_csv(save_path, index=False)
        
        logger.info(f"Trades exported to {save_path} ({len(trades)} trades)")
        return str(save_path)
    
    def _find_closest_index(self, timestamps: List[datetime], target: datetime) -> Optional[int]:
        """Find index of closest timestamp."""
        if len(timestamps) == 0:
            return None
        
        timestamps_array = np.array(timestamps, dtype='datetime64')
        target_array = np.datetime64(target)
        idx = np.abs(timestamps_array - target_array).argmin()
        return int(idx)


# Example usage
if __name__ == "__main__":
    # Sample data
    import random
    from datetime import timedelta
    
    # Generate sample equity curve
    start_time = datetime.now()
    equity_curve = []
    equity = 10000.0
    
    for i in range(100):
        equity += random.uniform(-100, 150)  # Random walk with positive drift
        timestamp = start_time + timedelta(hours=i)
        equity_curve.append((timestamp, equity))
    
    # Generate sample trades
    trades = []
    for i in range(20):
        pnl = random.uniform(-100, 200)
        trade = {
            'symbol': 'BTC-USDT',
            'direction': random.choice(['LONG', 'SHORT']),
            'entry_time': start_time + timedelta(hours=i*5),
            'exit_time': start_time + timedelta(hours=i*5+2),
            'entry_price': 40000 + random.uniform(-1000, 1000),
            'exit_price': 40000 + random.uniform(-1000, 1000),
            'quantity': 0.1,
            'pnl': pnl,
            'pnl_pct': (pnl / 1000) * 100,
            'duration_hours': 2.0,
            'exit_reason': random.choice(['take_profit', 'stop_loss']),
            'signal_score': random.uniform(60, 90),
            'commission_total': 1.2
        }
        trades.append(trade)
    
    # Create visualizer
    viz = EquityCurveVisualizer()
    
    # Plot equity curve
    equity_plot = viz.plot_equity_curve(equity_curve, trades, 10000.0, "BTC-USDT")
    print(f"Equity curve saved: {equity_plot}")
    
    # Plot trade analysis
    trade_plot = viz.plot_trade_analysis(trades, "BTC-USDT")
    print(f"Trade analysis saved: {trade_plot}")
    
    # Export trades to CSV
    trades_csv = viz.export_trades_csv(trades, "BTC-USDT")
    print(f"Trades CSV saved: {trades_csv}")

