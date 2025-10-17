"""
Performance Metrics Calculator for Backtesting.
Calculates Sharpe, Sortino, Drawdown, Win Rate, and other metrics.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional
from loguru import logger


class PerformanceMetrics:
    """
    Calculates comprehensive performance metrics for backtest results.
    """
    
    def __init__(self, initial_capital: float = 10000.0, risk_free_rate: float = 0.0):
        """
        Args:
            initial_capital: Starting portfolio value
            risk_free_rate: Annual risk-free rate (default: 0%)
        """
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
    
    def calculate_all_metrics(
        self, 
        trades: List[Dict[str, Any]], 
        equity_curve: pd.Series
    ) -> Dict[str, Any]:
        """
        Calculate all performance metrics.
        
        Args:
            trades: List of trade dictionaries
            equity_curve: Timeseries of portfolio equity
            
        Returns:
            Dictionary containing all metrics
        """
        if len(trades) == 0:
            logger.warning("No trades to calculate metrics")
            return self._empty_metrics()
        
        metrics = {}
        
        # Basic metrics
        metrics['total_trades'] = len(trades)
        metrics['initial_capital'] = self.initial_capital
        metrics['final_capital'] = equity_curve.iloc[-1] if len(equity_curve) > 0 else self.initial_capital
        metrics['total_return'] = ((metrics['final_capital'] - self.initial_capital) / self.initial_capital) * 100
        
        # Trade statistics
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]
        
        metrics['winning_trades'] = len(winning_trades)
        metrics['losing_trades'] = len(losing_trades)
        metrics['win_rate'] = (len(winning_trades) / len(trades)) * 100 if trades else 0
        
        # PnL statistics
        pnls = [t['pnl'] for t in trades]
        metrics['total_pnl'] = sum(pnls)
        metrics['avg_pnl_per_trade'] = np.mean(pnls) if pnls else 0
        metrics['max_win'] = max(pnls) if pnls else 0
        metrics['max_loss'] = min(pnls) if pnls else 0
        
        # Win/Loss ratios
        if winning_trades and losing_trades:
            avg_win = np.mean([t['pnl'] for t in winning_trades])
            avg_loss = abs(np.mean([t['pnl'] for t in losing_trades]))
            metrics['avg_win'] = avg_win
            metrics['avg_loss'] = avg_loss
            metrics['win_loss_ratio'] = avg_win / avg_loss if avg_loss > 0 else 0
        else:
            metrics['avg_win'] = 0
            metrics['avg_loss'] = 0
            metrics['win_loss_ratio'] = 0
        
        # Expectancy
        win_prob = metrics['win_rate'] / 100
        loss_prob = 1 - win_prob
        metrics['expectancy'] = (win_prob * metrics['avg_win']) - (loss_prob * abs(metrics['avg_loss']))
        
        # Risk metrics
        metrics['sharpe_ratio'] = self._calculate_sharpe_ratio(equity_curve)
        metrics['sortino_ratio'] = self._calculate_sortino_ratio(equity_curve)
        metrics['calmar_ratio'] = self._calculate_calmar_ratio(equity_curve)
        
        # Drawdown metrics
        drawdown_metrics = self._calculate_drawdown(equity_curve)
        metrics.update(drawdown_metrics)
        
        # Trade duration
        durations = [t.get('duration_hours', 0) for t in trades if 'duration_hours' in t]
        if durations:
            metrics['avg_trade_duration_hours'] = np.mean(durations)
            metrics['max_trade_duration_hours'] = max(durations)
            metrics['min_trade_duration_hours'] = min(durations)
        else:
            metrics['avg_trade_duration_hours'] = 0
            metrics['max_trade_duration_hours'] = 0
            metrics['min_trade_duration_hours'] = 0
        
        # Profit factor
        gross_profit = sum([t['pnl'] for t in winning_trades]) if winning_trades else 0
        gross_loss = abs(sum([t['pnl'] for t in losing_trades])) if losing_trades else 0
        metrics['profit_factor'] = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Recovery factor
        metrics['recovery_factor'] = abs(metrics['total_pnl'] / metrics['max_drawdown']) if metrics['max_drawdown'] != 0 else 0
        
        logger.info(f"Calculated metrics: {metrics['total_trades']} trades, "
                   f"{metrics['win_rate']:.1f}% win rate, "
                   f"{metrics['total_return']:.2f}% return")
        
        return metrics
    
    def _calculate_sharpe_ratio(self, equity_curve: pd.Series, periods_per_year: int = 35040) -> float:
        """
        Calculate Sharpe Ratio.
        
        Args:
            equity_curve: Timeseries of portfolio equity
            periods_per_year: Number of periods per year (35040 for 15min bars)
            
        Returns:
            Sharpe ratio
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate returns
        returns = equity_curve.pct_change().dropna()
        
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        # Annualized metrics
        excess_returns = returns - (self.risk_free_rate / periods_per_year)
        sharpe = np.sqrt(periods_per_year) * (excess_returns.mean() / returns.std())
        
        return float(sharpe)
    
    def _calculate_sortino_ratio(self, equity_curve: pd.Series, periods_per_year: int = 35040) -> float:
        """
        Calculate Sortino Ratio (only considers downside volatility).
        
        Args:
            equity_curve: Timeseries of portfolio equity
            periods_per_year: Number of periods per year
            
        Returns:
            Sortino ratio
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate returns
        returns = equity_curve.pct_change().dropna()
        
        if len(returns) == 0:
            return 0.0
        
        # Downside deviation (only negative returns)
        downside_returns = returns[returns < 0]
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        downside_std = downside_returns.std()
        excess_returns = returns.mean() - (self.risk_free_rate / periods_per_year)
        sortino = np.sqrt(periods_per_year) * (excess_returns / downside_std)
        
        return float(sortino)
    
    def _calculate_calmar_ratio(self, equity_curve: pd.Series) -> float:
        """
        Calculate Calmar Ratio (return / max drawdown).
        
        Args:
            equity_curve: Timeseries of portfolio equity
            
        Returns:
            Calmar ratio
        """
        if len(equity_curve) < 2:
            return 0.0
        
        total_return = (equity_curve.iloc[-1] - equity_curve.iloc[0]) / equity_curve.iloc[0]
        drawdown_metrics = self._calculate_drawdown(equity_curve)
        max_drawdown = abs(drawdown_metrics['max_drawdown'])
        
        if max_drawdown == 0:
            return 0.0
        
        calmar = total_return / max_drawdown
        return float(calmar)
    
    def _calculate_drawdown(self, equity_curve: pd.Series) -> Dict[str, float]:
        """
        Calculate drawdown metrics.
        
        Args:
            equity_curve: Timeseries of portfolio equity
            
        Returns:
            Dictionary with drawdown metrics
        """
        if len(equity_curve) == 0:
            return {
                'max_drawdown': 0.0,
                'max_drawdown_pct': 0.0,
                'avg_drawdown': 0.0,
                'max_drawdown_duration': 0
            }
        
        # Calculate running maximum
        running_max = equity_curve.expanding().max()
        
        # Calculate drawdown
        drawdown = equity_curve - running_max
        drawdown_pct = (drawdown / running_max) * 100
        
        # Max drawdown
        max_dd = drawdown.min()
        max_dd_pct = drawdown_pct.min()
        
        # Average drawdown (only negative values)
        negative_dd = drawdown[drawdown < 0]
        avg_dd = negative_dd.mean() if len(negative_dd) > 0 else 0.0
        
        # Max drawdown duration
        is_drawdown = drawdown < 0
        drawdown_periods = []
        current_period = 0
        
        for in_dd in is_drawdown:
            if in_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                current_period = 0
        
        if current_period > 0:  # If still in drawdown at end
            drawdown_periods.append(current_period)
        
        max_dd_duration = max(drawdown_periods) if drawdown_periods else 0
        
        return {
            'max_drawdown': float(max_dd),
            'max_drawdown_pct': float(max_dd_pct),
            'avg_drawdown': float(avg_dd),
            'max_drawdown_duration': int(max_dd_duration)
        }
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics when no trades."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_return': 0.0,
            'total_pnl': 0.0,
            'avg_pnl_per_trade': 0.0,
            'max_win': 0.0,
            'max_loss': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0,
            'initial_capital': self.initial_capital,
            'final_capital': self.initial_capital,
            'win_loss_ratio': 0.0,
            'max_drawdown_duration': 0
        }
    
    def print_summary(self, metrics: Dict[str, Any]):
        """Print a formatted summary of metrics."""
        print("\n" + "=" * 60)
        print("BACKTEST PERFORMANCE SUMMARY")
        print("=" * 60)
        
        print(f"\nOverall Performance:")
        print(f"  Initial Capital:    ${metrics['initial_capital']:,.2f}")
        print(f"  Final Capital:      ${metrics.get('final_capital', 0):,.2f}")
        print(f"  Total Return:       {metrics['total_return']:.2f}%")
        print(f"  Total PnL:          ${metrics['total_pnl']:,.2f}")
        
        print(f"\nTrade Statistics:")
        print(f"  Total Trades:       {metrics['total_trades']}")
        print(f"  Winning Trades:     {metrics['winning_trades']} ({metrics['win_rate']:.1f}%)")
        print(f"  Losing Trades:      {metrics['losing_trades']}")
        print(f"  Win/Loss Ratio:     {metrics.get('win_loss_ratio', 0):.2f}")
        
        print(f"\nPnL Analysis:")
        print(f"  Avg PnL/Trade:      ${metrics['avg_pnl_per_trade']:.2f}")
        print(f"  Max Win:            ${metrics['max_win']:.2f}")
        print(f"  Max Loss:           ${metrics['max_loss']:.2f}")
        print(f"  Profit Factor:      {metrics.get('profit_factor', 0):.2f}")
        print(f"  Expectancy:         ${metrics.get('expectancy', 0):.2f}")
        
        print(f"\nRisk Metrics:")
        print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:.2f}")
        print(f"  Sortino Ratio:      {metrics['sortino_ratio']:.2f}")
        print(f"  Calmar Ratio:       {metrics.get('calmar_ratio', 0):.2f}")
        print(f"  Max Drawdown:       ${metrics['max_drawdown']:.2f} ({metrics['max_drawdown_pct']:.2f}%)")
        print(f"  Max DD Duration:    {metrics.get('max_drawdown_duration', 0)} periods")
        
        if 'avg_trade_duration_hours' in metrics:
            print(f"\nTrade Duration:")
            print(f"  Average:            {metrics['avg_trade_duration_hours']:.1f} hours")
            print(f"  Max:                {metrics.get('max_trade_duration_hours', 0):.1f} hours")
        
        print("\n" + "=" * 60 + "\n")


# Example usage
if __name__ == "__main__":
    # Sample trades
    sample_trades = [
        {'symbol': 'BTC-USDT', 'pnl': 100, 'duration_hours': 2},
        {'symbol': 'BTC-USDT', 'pnl': -50, 'duration_hours': 1},
        {'symbol': 'ETH-USDT', 'pnl': 75, 'duration_hours': 3},
        {'symbol': 'ETH-USDT', 'pnl': 150, 'duration_hours': 4},
        {'symbol': 'BTC-USDT', 'pnl': -25, 'duration_hours': 1.5},
    ]
    
    # Sample equity curve
    equity_values = [10000, 10100, 10050, 10125, 10275, 10250]
    equity_curve = pd.Series(equity_values)
    
    # Calculate metrics
    metrics_calc = PerformanceMetrics(initial_capital=10000)
    metrics = metrics_calc.calculate_all_metrics(sample_trades, equity_curve)
    
    # Print summary
    metrics_calc.print_summary(metrics)

