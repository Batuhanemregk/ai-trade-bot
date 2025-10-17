"""
Portfolio Reporter
------------------
Generates comprehensive portfolio performance reports.

Features:
- Daily/weekly performance summaries
- Trade-level analytics
- Risk metrics and exposure analysis
- Export to JSON and CSV
- Telegram integration
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
import pandas as pd


class PortfolioReporter:
    """
    Generates and exports portfolio performance reports.
    
    Usage:
        reporter = PortfolioReporter()
        report = await reporter.generate_daily_report(portfolio, trades)
        await reporter.send_telegram_report(report)
    """
    
    def __init__(self, reports_dir: str = "reports"):
        """
        Initialize portfolio reporter.
        
        Args:
            reports_dir: Directory to save reports
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Portfolio reporter initialized (dir={reports_dir})")
    
    async def generate_daily_report(self, portfolio: Dict[str, Any], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate daily performance report.
        
        Args:
            portfolio: Portfolio state dictionary
            trades: List of trade dictionaries for the day
        
        Returns:
            Report dictionary with summary and details
        """
        try:
            date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # Calculate statistics
            summary = self._calculate_summary(portfolio, trades)
            
            # Analyze trades
            trade_analysis = self._analyze_trades(trades)
            
            # Risk metrics
            risk_metrics = self._calculate_risk_metrics(portfolio, trades)
            
            # Build report
            report = {
                'date': date_str,
                'type': 'daily',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'summary': summary,
                'trade_analysis': trade_analysis,
                'risk_metrics': risk_metrics,
                'positions': portfolio.get('positions', []),
                'trades': trades
            }
            
            # Save report
            report_file = self.reports_dir / f"daily_{date_str}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Daily report generated: {report_file}")
            
            # Save trades as CSV
            if trades:
                self._save_trades_csv(trades, date_str, 'daily')
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            raise
    
    async def generate_weekly_report(self, portfolio: Dict[str, Any], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate weekly performance report.
        
        Args:
            portfolio: Portfolio state dictionary
            trades: List of trade dictionaries for the week
        
        Returns:
            Report dictionary with weekly summary
        """
        try:
            # Get week number
            now = datetime.now(timezone.utc)
            week_str = now.strftime('%Y-W%W')
            
            # Calculate statistics
            summary = self._calculate_summary(portfolio, trades)
            
            # Weekly trends
            weekly_trends = self._calculate_weekly_trends(trades)
            
            # Best/worst performers
            symbol_performance = self._analyze_symbol_performance(trades)
            
            # Build report
            report = {
                'week': week_str,
                'type': 'weekly',
                'start_date': (now - timedelta(days=7)).strftime('%Y-%m-%d'),
                'end_date': now.strftime('%Y-%m-%d'),
                'timestamp': now.isoformat(),
                'summary': summary,
                'weekly_trends': weekly_trends,
                'symbol_performance': symbol_performance,
                'trades': trades
            }
            
            # Save report
            report_file = self.reports_dir / f"weekly_{week_str}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Weekly report generated: {report_file}")
            
            # Save trades as CSV
            if trades:
                self._save_trades_csv(trades, week_str, 'weekly')
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate weekly report: {e}")
            raise
    
    def _calculate_summary(self, portfolio: Dict[str, Any], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics."""
        
        total_trades = len(trades)
        if total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_r': 0.0,
                'avg_trade_pnl': 0.0,
                'max_win': 0.0,
                'max_loss': 0.0,
                'profit_factor': 0.0,
                'expectancy': 0.0
            }
        
        # Win rate
        wins = [t for t in trades if t.get('pnl', 0) > 0]
        losses = [t for t in trades if t.get('pnl', 0) < 0]
        win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
        
        # PnL statistics
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
        
        max_win = max((t.get('pnl', 0) for t in trades), default=0.0)
        max_loss = min((t.get('pnl', 0) for t in trades), default=0.0)
        
        # Profit factor
        gross_profit = sum(t.get('pnl', 0) for t in wins)
        gross_loss = abs(sum(t.get('pnl', 0) for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Expectancy
        expectancy = avg_trade_pnl
        
        # Average R (risk-reward ratio)
        avg_r = self._calculate_avg_r(trades)
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': round(win_rate * 100, 1),
            'total_pnl': round(total_pnl, 2),
            'avg_trade_pnl': round(avg_trade_pnl, 2),
            'max_win': round(max_win, 2),
            'max_loss': round(max_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'expectancy': round(expectancy, 2),
            'avg_r': round(avg_r, 2)
        }
    
    def _analyze_trades(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trade patterns and distributions."""
        
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        
        analysis = {
            'by_direction': {},
            'by_symbol': {},
            'by_exit_reason': {},
            'duration_stats': {}
        }
        
        # By direction
        if 'direction' in df.columns:
            direction_stats = df.groupby('direction').agg({
                'pnl': ['count', 'sum', 'mean']
            }).to_dict()
            analysis['by_direction'] = self._flatten_dict(direction_stats)
        
        # By symbol
        if 'symbol' in df.columns:
            symbol_stats = df.groupby('symbol').agg({
                'pnl': ['count', 'sum', 'mean']
            }).to_dict()
            analysis['by_symbol'] = self._flatten_dict(symbol_stats)
        
        # By exit reason
        if 'exit_reason' in df.columns:
            exit_stats = df.groupby('exit_reason').agg({
                'pnl': ['count', 'sum']
            }).to_dict()
            analysis['by_exit_reason'] = self._flatten_dict(exit_stats)
        
        # Duration statistics
        if 'entry_time' in df.columns and 'exit_time' in df.columns:
            try:
                df['duration'] = pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])
                df['duration_minutes'] = df['duration'].dt.total_seconds() / 60
                
                analysis['duration_stats'] = {
                    'avg_minutes': round(df['duration_minutes'].mean(), 1),
                    'median_minutes': round(df['duration_minutes'].median(), 1),
                    'min_minutes': round(df['duration_minutes'].min(), 1),
                    'max_minutes': round(df['duration_minutes'].max(), 1)
                }
            except Exception as e:
                logger.warning(f"Failed to calculate duration stats: {e}")
        
        return analysis
    
    def _calculate_risk_metrics(self, portfolio: Dict[str, Any], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate risk-related metrics."""
        
        return {
            'max_drawdown': round(portfolio.get('max_drawdown', 0) * 100, 2),
            'current_drawdown': round(portfolio.get('current_drawdown', 0) * 100, 2),
            'exposure_pct': round(portfolio.get('exposure_pct', 0) * 100, 2),
            'exposure_usd': round(portfolio.get('exposure_usd', 0), 2),
            'positions_open': len(portfolio.get('positions', [])),
            'leverage_avg': self._calculate_avg_leverage(portfolio),
            'risk_per_trade_avg': self._calculate_avg_risk(trades)
        }
    
    def _calculate_weekly_trends(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate weekly trends and patterns."""
        
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        
        # Group by day
        try:
            df['date'] = pd.to_datetime(df['exit_time']).dt.date
            daily_pnl = df.groupby('date')['pnl'].sum().to_dict()
            
            # Convert dates to strings for JSON serialization
            daily_pnl_str = {str(k): round(v, 2) for k, v in daily_pnl.items()}
            
            return {
                'daily_pnl': daily_pnl_str,
                'best_day': max(daily_pnl.items(), key=lambda x: x[1], default=(None, 0)),
                'worst_day': min(daily_pnl.items(), key=lambda x: x[1], default=(None, 0))
            }
        except Exception as e:
            logger.warning(f"Failed to calculate weekly trends: {e}")
            return {}
    
    def _analyze_symbol_performance(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance by symbol."""
        
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        
        if 'symbol' not in df.columns or 'pnl' not in df.columns:
            return {}
        
        symbol_stats = df.groupby('symbol').agg({
            'pnl': ['count', 'sum', 'mean']
        })
        
        # Find best and worst
        symbol_pnl = df.groupby('symbol')['pnl'].sum()
        best_symbol = symbol_pnl.idxmax() if len(symbol_pnl) > 0 else None
        worst_symbol = symbol_pnl.idxmin() if len(symbol_pnl) > 0 else None
        
        return {
            'best_performer': {
                'symbol': best_symbol,
                'pnl': round(symbol_pnl[best_symbol], 2) if best_symbol else 0
            },
            'worst_performer': {
                'symbol': worst_symbol,
                'pnl': round(symbol_pnl[worst_symbol], 2) if worst_symbol else 0
            },
            'all_symbols': self._flatten_dict(symbol_stats.to_dict())
        }
    
    def _save_trades_csv(self, trades: List[Dict[str, Any]], date_or_week: str, report_type: str):
        """Save trades to CSV file."""
        try:
            df = pd.DataFrame(trades)
            csv_file = self.reports_dir / f"trades_{report_type}_{date_or_week}.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"Trades CSV saved: {csv_file}")
        except Exception as e:
            logger.warning(f"Failed to save trades CSV: {e}")
    
    def _calculate_avg_r(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate average R-multiple."""
        if not trades:
            return 0.0
        
        r_multiples = []
        for trade in trades:
            pnl = trade.get('pnl', 0)
            size = trade.get('size_usdt', 0)
            if size > 0:
                r_multiples.append(pnl / (size * 0.02))  # Assuming 2% risk per trade
        
        return sum(r_multiples) / len(r_multiples) if r_multiples else 0.0
    
    def _calculate_avg_leverage(self, portfolio: Dict[str, Any]) -> float:
        """Calculate average leverage across positions."""
        positions = portfolio.get('positions', [])
        if not positions:
            return 0.0
        
        leverages = [p.get('leverage', 1.0) for p in positions]
        return sum(leverages) / len(leverages) if leverages else 0.0
    
    def _calculate_avg_risk(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate average risk per trade."""
        if not trades:
            return 0.0
        
        risks = []
        for trade in trades:
            size = trade.get('size_usdt', 0)
            entry_price = trade.get('entry_price', 0)
            stop_loss = trade.get('stop_loss', 0)
            
            if size > 0 and entry_price > 0 and stop_loss > 0:
                risk_pct = abs((entry_price - stop_loss) / entry_price)
                risks.append(risk_pct * 100)
        
        return sum(risks) / len(risks) if risks else 0.0
    
    def _flatten_dict(self, nested_dict: Dict) -> Dict:
        """Flatten nested dictionary for JSON serialization."""
        flat = {}
        for key, value in nested_dict.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat_key = f"{key}_{sub_key}"
                    flat[flat_key] = round(float(sub_value), 2) if isinstance(sub_value, (int, float)) else sub_value
            else:
                flat[key] = round(float(value), 2) if isinstance(value, (int, float)) else value
        return flat
    
    async def format_telegram_message(self, report: Dict[str, Any]) -> str:
        """
        Format report as Telegram message.
        
        Args:
            report: Report dictionary
        
        Returns:
            Formatted message string
        """
        summary = report.get('summary', {})
        risk_metrics = report.get('risk_metrics', {})
        report_type = report.get('type', 'daily').upper()
        date_or_week = report.get('date') or report.get('week', '')
        
        message = f"""
📊 **{report_type} REPORT - {date_or_week}**

**Performance:**
• Total Trades: {summary.get('total_trades', 0)}
• Win Rate: {summary.get('win_rate', 0)}%
• Total PnL: ${summary.get('total_pnl', 0):.2f}
• Avg PnL/Trade: ${summary.get('avg_trade_pnl', 0):.2f}
• Avg R: {summary.get('avg_r', 0):.2f}R

**Trade Stats:**
• Winning: {summary.get('winning_trades', 0)}
• Losing: {summary.get('losing_trades', 0)}
• Max Win: ${summary.get('max_win', 0):.2f}
• Max Loss: ${summary.get('max_loss', 0):.2f}
• Profit Factor: {summary.get('profit_factor', 0):.2f}

**Risk Metrics:**
• Current Drawdown: {risk_metrics.get('current_drawdown', 0)}%
• Max Drawdown: {risk_metrics.get('max_drawdown', 0)}%
• Exposure: {risk_metrics.get('exposure_pct', 0)}%
• Open Positions: {risk_metrics.get('positions_open', 0)}

**Expectancy:** ${summary.get('expectancy', 0):.2f}
"""
        
        # Add symbol performance for weekly reports
        if report_type == 'WEEKLY' and 'symbol_performance' in report:
            perf = report['symbol_performance']
            best = perf.get('best_performer', {})
            worst = perf.get('worst_performer', {})
            
            if best.get('symbol'):
                message += f"\n🏆 Best: {best['symbol']} (${best.get('pnl', 0):.2f})"
            if worst.get('symbol'):
                message += f"\n📉 Worst: {worst['symbol']} (${worst.get('pnl', 0):.2f})"
        
        return message.strip()





