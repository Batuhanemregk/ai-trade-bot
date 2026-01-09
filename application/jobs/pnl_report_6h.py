"""
PnL Report Job (6-hourly)
-------------------------
Generates and sends 24-hour closed position PnL reports via Telegram.

Schedule: Every 6 hours (00:00, 06:00, 12:00, 18:00)
"""
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from application.jobs.base_job import BaseJob


class PnLReport6hJob(BaseJob):
    """
    Sends 24-hour closed position PnL report to Telegram every 6 hours.
    """
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.history_file = Path("data/trade_history.jsonl")
        self.telegram_client = None
    
    async def initialize(self):
        """Initialize dependencies."""
        try:
            from infrastructure.notification_service import NotificationService
            notification_service = NotificationService()
            if notification_service.is_initialized:
                self.telegram_client = notification_service.telegram_client
                logger.info("PnL Report 6h job initialized with Telegram")
            else:
                logger.warning("Telegram not available for PnL reports")
        except Exception as e:
            logger.warning(f"Failed to initialize PnL report dependencies: {e}")
    
    async def execute(self):
        """Generate and send PnL report."""
        try:
            logger.info("Generating 6-hourly PnL report...")
            
            # Get trades from last 24 hours
            trades_24h = self._get_trades_last_24h()
            
            # Get all-time trades
            all_trades = self._get_all_trades()
            
            # Calculate PnL summaries
            summary_24h = self._calculate_pnl_summary(trades_24h)
            summary_all = self._calculate_pnl_summary(all_trades)
            
            # Generate Telegram message
            message = self._generate_telegram_message(trades_24h, summary_24h, summary_all)
            
            # Send via Telegram
            if self.telegram_client:
                # Start worker if not running
                if not self.telegram_client.is_running:
                    await self.telegram_client.start()
                success = await self.telegram_client.send_message(message)
                if success:
                    logger.info(f"PnL report sent: 24h trades={len(trades_24h)}, PnL=${summary_24h['total_pnl']:.2f}")
                else:
                    logger.error("Failed to send PnL report to Telegram")
            else:
                logger.warning("Telegram client not available, skipping PnL report")
            
        except Exception as e:
            logger.error(f"PnL report job failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_trades_last_24h(self) -> List[Dict]:
        """Get trades from last 24 hours."""
        trades = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        
        try:
            if not self.history_file.exists():
                logger.info("No trade history file found")
                return []
            
            with open(self.history_file, 'r') as f:
                for line in f:
                    try:
                        trade = json.loads(line.strip())
                        exit_time_str = trade.get('exit_time', '')
                        if exit_time_str:
                            exit_time = datetime.fromisoformat(exit_time_str.replace('Z', '+00:00'))
                            if exit_time >= cutoff:
                                trades.append(trade)
                    except Exception as e:
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to read trade history: {e}")
        
        return trades
    
    def _get_all_trades(self) -> List[Dict]:
        """Get all trades from history."""
        trades = []
        
        try:
            if not self.history_file.exists():
                return []
            
            with open(self.history_file, 'r') as f:
                for line in f:
                    try:
                        trade = json.loads(line.strip())
                        trades.append(trade)
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Failed to read trade history: {e}")
        
        return trades
    
    def _calculate_pnl_summary(self, trades: List[Dict]) -> Dict[str, Any]:
        """Calculate PnL summary from trades."""
        total_pnl = 0.0
        wins = 0
        losses = 0
        
        for trade in trades:
            pnl = float(trade.get('pnl', 0))
            total_pnl += pnl
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
        
        trade_count = len(trades)
        win_rate = (wins / trade_count * 100) if trade_count > 0 else 0
        
        return {
            'total_pnl': total_pnl,
            'trade_count': trade_count,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate
        }
    
    def _generate_telegram_message(self, trades_24h: List[Dict], 
                                   summary_24h: Dict, summary_all: Dict) -> str:
        """Generate Telegram message."""
        lines = ["📊 <b>24 SAATLİK PNL RAPORU</b>", ""]
        
        # 24-hour trades section
        if trades_24h:
            lines.append("💰 <b>Son 24 Saat:</b>")
            
            # Group by symbol
            symbol_pnl = {}
            for trade in trades_24h:
                symbol = trade.get('base_symbol', trade.get('symbol', 'UNKNOWN'))
                direction = trade.get('direction', '?').upper()
                pnl = float(trade.get('pnl', 0))
                
                if symbol not in symbol_pnl:
                    symbol_pnl[symbol] = {'pnl': 0, 'count': 0, 'direction': direction}
                symbol_pnl[symbol]['pnl'] += pnl
                symbol_pnl[symbol]['count'] += 1
            
            # Sort by PnL
            sorted_symbols = sorted(symbol_pnl.items(), key=lambda x: x[1]['pnl'], reverse=True)
            
            for i, (symbol, data) in enumerate(sorted_symbols):
                pnl = data['pnl']
                count = data['count']
                prefix = "└" if i == len(sorted_symbols) - 1 else "├"
                sign = "+" if pnl >= 0 else ""
                emoji = "🟢" if pnl >= 0 else "🔴"
                lines.append(f"{prefix} {emoji} <b>{symbol}</b>: {sign}${pnl:.2f} ({count} işlem)")
            
            lines.append("")
            
            # 24h summary
            pnl_24h = summary_24h['total_pnl']
            sign_24h = "+" if pnl_24h >= 0 else ""
            emoji_24h = "📈" if pnl_24h >= 0 else "📉"
            lines.append(f"{emoji_24h} <b>24 Saat Toplam:</b> {sign_24h}${pnl_24h:.2f} ({summary_24h['trade_count']} işlem, %{summary_24h['win_rate']:.0f} WR)")
        else:
            lines.append("💤 Son 24 saatte kapanan pozisyon yok.")
        
        lines.append("")
        
        # All-time summary
        pnl_all = summary_all['total_pnl']
        sign_all = "+" if pnl_all >= 0 else ""
        emoji_all = "💎" if pnl_all >= 0 else "💸"
        lines.append(f"{emoji_all} <b>Genel Toplam:</b> {sign_all}${pnl_all:.2f} ({summary_all['trade_count']} işlem)")
        
        # Timestamp
        now = datetime.now(timezone.utc).strftime("%H:%M UTC")
        lines.append("")
        lines.append(f"⏰ <i>Son güncelleme: {now}</i>")
        
        return "\n".join(lines)


def create_job(policy: Dict, semaphore: asyncio.Semaphore, runtime_state: Dict) -> PnLReport6hJob:
    """Factory function for job creation."""
    return PnLReport6hJob(policy, semaphore, runtime_state)
