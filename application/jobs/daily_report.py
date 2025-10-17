"""
Daily Report Job
----------------
Generates and sends daily performance reports.

Schedule: Every day at 23:55 (5 minutes before midnight)
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from loguru import logger

from application.jobs.base import BaseJob
from application.portfolio_reporter import PortfolioReporter


class DailyReportJob(BaseJob):
    """
    Generates daily performance report and sends via Telegram.
    """
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.reporter = PortfolioReporter()
        self.exchange_adapter = None
        self.telegram_bot = None
    
    async def initialize(self):
        """Initialize dependencies."""
        try:
            # Initialize exchange adapter
            from adapters.exchange_okx_ccxt import OKXCCXTAdapter
            self.exchange_adapter = OKXCCXTAdapter(self.policy)
            
            # Initialize Telegram bot
            from telegram_bot.bot import TelegramBot
            self.telegram_bot = TelegramBot(self.policy)
            
            logger.info("Daily report job initialized")
            
        except Exception as e:
            logger.warning(f"Failed to initialize daily report dependencies: {e}")
    
    async def execute(self):
        """Generate and send daily report."""
        try:
            logger.info("Generating daily report...")
            
            # Get portfolio state
            portfolio = await self._get_portfolio_state()
            
            # Get today's trades
            trades = await self._get_today_trades()
            
            # Generate report
            report = await self.reporter.generate_daily_report(portfolio, trades)
            
            logger.info(f"Daily report generated: {len(trades)} trades, "
                       f"PnL=${report['summary']['total_pnl']:.2f}")
            
            # Send via Telegram
            if self.telegram_bot:
                await self._send_telegram_report(report)
            
            # Update Prometheus metrics (if available)
            await self._update_prometheus_metrics(report)
            
        except Exception as e:
            logger.error(f"Daily report job failed: {e}")
            raise
    
    async def _get_portfolio_state(self) -> Dict[str, Any]:
        """
        Get current portfolio state.
        
        Returns:
            Portfolio state dictionary
        """
        try:
            if not self.exchange_adapter:
                return self._get_mock_portfolio()
            
            # Fetch real portfolio data
            balance = await self.exchange_adapter.fetch_balance()
            positions = await self.exchange_adapter.fetch_positions()
            
            # Calculate metrics
            total_value = balance.get('USDT', {}).get('total', 0)
            exposure = sum(abs(float(p.get('notional', 0))) for p in positions if p.get('size', 0) != 0)
            exposure_pct = exposure / total_value if total_value > 0 else 0
            
            # Get drawdown from runtime state
            max_equity = self.runtime_state.get('max_equity', total_value)
            current_drawdown = (max_equity - total_value) / max_equity if max_equity > 0 else 0
            max_drawdown = self.runtime_state.get('max_drawdown', 0)
            
            return {
                'total_value': total_value,
                'exposure_usd': exposure,
                'exposure_pct': exposure_pct,
                'current_drawdown': current_drawdown,
                'max_drawdown': max_drawdown,
                'positions': [
                    {
                        'symbol': p.get('symbol'),
                        'size': p.get('size', 0),
                        'notional': p.get('notional', 0),
                        'leverage': p.get('leverage', 1),
                        'unrealized_pnl': p.get('unrealizedPnl', 0)
                    }
                    for p in positions if p.get('size', 0) != 0
                ]
            }
            
        except Exception as e:
            logger.warning(f"Failed to fetch portfolio state: {e}")
            return self._get_mock_portfolio()
    
    async def _get_today_trades(self) -> list:
        """
        Get today's completed trades.
        
        Returns:
            List of trade dictionaries
        """
        try:
            # Try to load from trade history file
            from pathlib import Path
            import json
            
            history_file = Path("data/trade_history.jsonl")
            if not history_file.exists():
                logger.info("No trade history file found")
                return []
            
            # Read trades from today
            today = datetime.now(timezone.utc).date()
            trades = []
            
            with open(history_file, 'r') as f:
                for line in f:
                    try:
                        trade = json.loads(line.strip())
                        
                        # Check if trade is from today
                        exit_time = datetime.fromisoformat(trade.get('exit_time', ''))
                        if exit_time.date() == today:
                            trades.append(trade)
                    except Exception as e:
                        logger.warning(f"Failed to parse trade line: {e}")
                        continue
            
            logger.info(f"Found {len(trades)} trades from today")
            return trades
            
        except Exception as e:
            logger.warning(f"Failed to load today's trades: {e}")
            return []
    
    async def _send_telegram_report(self, report: Dict[str, Any]):
        """Send report via Telegram."""
        try:
            # Format message
            message = await self.reporter.format_telegram_message(report)
            
            # Send message
            await self.telegram_bot.send_message(message, parse_mode='Markdown')
            
            # Send CSV file
            import csv
            from io import StringIO
            from pathlib import Path
            
            date_str = report['date']
            csv_file = Path(f"reports/trades_daily_{date_str}.csv")
            
            if csv_file.exists():
                # Send as document
                await self.telegram_bot.send_document(
                    str(csv_file),
                    caption=f"Daily trades - {date_str}"
                )
            
            logger.info("Daily report sent via Telegram")
            
        except Exception as e:
            logger.warning(f"Failed to send Telegram report: {e}")
    
    async def _update_prometheus_metrics(self, report: Dict[str, Any]):
        """Update Prometheus metrics from report."""
        try:
            from monitoring.prometheus_exporter import get_prometheus_exporter
            
            prometheus = get_prometheus_exporter()
            summary = report['summary']
            
            # Update portfolio-level metrics
            prometheus.update_portfolio_metrics({
                'pnl': summary.get('total_pnl', 0),
                'drawdown': report['risk_metrics'].get('current_drawdown', 0) / 100,
                'max_drawdown': report['risk_metrics'].get('max_drawdown', 0) / 100,
                'exposure_pct': report['risk_metrics'].get('exposure_pct', 0) / 100,
                'exposure_usd': report['risk_metrics'].get('exposure_usd', 0),
                'positions_open': report['risk_metrics'].get('positions_open', 0)
            })
            
            logger.debug("Prometheus metrics updated from report")
            
        except Exception as e:
            logger.debug(f"Prometheus update skipped: {e}")
    
    def _get_mock_portfolio(self) -> Dict[str, Any]:
        """Get mock portfolio for testing."""
        return {
            'total_value': 10000.0,
            'exposure_usd': 0.0,
            'exposure_pct': 0.0,
            'current_drawdown': 0.0,
            'max_drawdown': 0.0,
            'positions': []
        }





