"""
PnL Tracker - OKX API'den trade history çekerek gerçek PnL takibi.

Features:
- OKX API'den son 3 aylık trade history
- Günlük/Haftalık/Aylık/Genel PnL
- Per-coin analiz ve top gainers
- Restart bağımsız (OKX'ten her zaman güncel veri)
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
from loguru import logger
from dataclasses import dataclass, asdict


@dataclass
class TradeRecord:
    """Single trade record from OKX."""
    symbol: str
    base: str
    side: str  # buy/sell
    pnl: float
    fill_price: float
    fill_qty: float
    fee: float
    timestamp: datetime
    trade_id: str


@dataclass
class PnLSummary:
    """PnL summary for a time period."""
    total_pnl: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    fees_paid: float


class PnLTracker:
    """Tracks PnL by fetching trade history from OKX API."""
    
    def __init__(self):
        self.exchange = None
        self._cache: Dict[str, Any] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 60  # 1 minute cache
        
    async def _get_exchange(self):
        """Lazy load exchange adapter."""
        if self.exchange is None:
            try:
                import ccxt.async_support as ccxt
                import os
                from dotenv import load_dotenv
                load_dotenv()
                
                self.exchange = ccxt.okx({
                    'apiKey': os.getenv('OKX_API_KEY'),
                    'secret': os.getenv('OKX_API_SECRET'),
                    'password': os.getenv('OKX_API_PASSPHRASE'),
                    'options': {'defaultType': 'swap'}
                })
            except Exception as e:
                logger.error(f"Failed to initialize exchange: {e}")
                raise
        return self.exchange
    
    async def fetch_trade_history(self, days: int = 90) -> List[TradeRecord]:
        """Fetch CLOSED positions from OKX position history endpoint."""
        try:
            exchange = await self._get_exchange()
            
            all_trades = []
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Use positions-history endpoint - gives closed positions directly
            after_id = None
            max_pages = 10  # Max ~1000 positions
            
            for page in range(max_pages):
                try:
                    params = {
                        'instType': 'SWAP',
                        'limit': '100'
                    }
                    if after_id:
                        params['after'] = after_id
                    
                    response = await exchange.private_get_account_positions_history(params)
                    positions = response.get('data', [])
                    
                    if not positions:
                        break
                    
                    for pos in positions:
                        try:
                            inst_id = pos.get('instId', '')
                            if not inst_id:
                                continue
                            
                            # Parse close timestamp
                            close_ts = int(pos.get('uTime', 0))
                            close_time = datetime.fromtimestamp(close_ts / 1000, tz=timezone.utc)
                            
                            # Check if within date range
                            if close_time < cutoff:
                                continue
                            
                            base = inst_id.split('-')[0] if '-' in inst_id else inst_id
                            
                            # Get PnL values
                            pnl = float(pos.get('pnl', 0) or 0)
                            realized_pnl = float(pos.get('realizedPnl', 0) or 0)
                            fee = float(pos.get('fee', 0) or 0)
                            funding_fee = float(pos.get('fundingFee', 0) or 0)
                            
                            # Use realizedPnl which includes fees
                            total_pnl = realized_pnl
                            total_fee = abs(fee) + abs(funding_fee)
                            
                            record = TradeRecord(
                                symbol=inst_id,
                                base=base,
                                side=pos.get('direction', 'unknown'),
                                pnl=total_pnl,
                                fill_price=float(pos.get('closeAvgPx', 0) or 0),
                                fill_qty=float(pos.get('closeTotalPos', 0) or 0),
                                fee=total_fee,
                                timestamp=close_time,
                                trade_id=pos.get('posId', '')
                            )
                            all_trades.append(record)
                            
                        except Exception as e:
                            logger.debug(f"Failed to parse position: {e}")
                            continue
                    
                    # Get after ID for pagination
                    if positions:
                        after_id = positions[-1].get('posId')
                    else:
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch positions page {page}: {e}")
                    break
            
            logger.info(f"Fetched {len(all_trades)} closed positions from OKX (last {days} days)")
            return all_trades
            
        except Exception as e:
            logger.error(f"Failed to fetch trade history: {e}")
            return []
    
    def calculate_summary(self, trades: List[TradeRecord]) -> PnLSummary:
        """Calculate PnL summary from trade records."""
        if not trades:
            return PnLSummary(
                total_pnl=0, total_trades=0, wins=0, losses=0, 
                win_rate=0, avg_win=0, avg_loss=0, 
                best_trade=0, worst_trade=0, fees_paid=0
            )
        
        pnls = [t.pnl for t in trades]
        fees = sum(abs(t.fee) for t in trades)
        
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        return PnLSummary(
            total_pnl=sum(pnls),
            total_trades=len(trades),
            wins=len(wins),
            losses=len(losses),
            win_rate=(len(wins) / len(trades) * 100) if trades else 0,
            avg_win=(sum(wins) / len(wins)) if wins else 0,
            avg_loss=(sum(losses) / len(losses)) if losses else 0,
            best_trade=max(pnls) if pnls else 0,
            worst_trade=min(pnls) if pnls else 0,
            fees_paid=fees
        )
    
    def get_per_coin_pnl(self, trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
        """Get PnL breakdown per coin."""
        coin_data = {}
        
        for trade in trades:
            base = trade.base
            if base not in coin_data:
                coin_data[base] = {
                    'pnl': 0,
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'fees': 0
                }
            
            coin_data[base]['pnl'] += trade.pnl
            coin_data[base]['trades'] += 1
            coin_data[base]['fees'] += abs(trade.fee)
            
            if trade.pnl > 0:
                coin_data[base]['wins'] += 1
            elif trade.pnl < 0:
                coin_data[base]['losses'] += 1
        
        # Calculate win rate
        for coin in coin_data:
            total = coin_data[coin]['trades']
            wins = coin_data[coin]['wins']
            coin_data[coin]['win_rate'] = (wins / total * 100) if total > 0 else 0
        
        return coin_data
    
    def get_top_gainers(self, coin_data: Dict[str, Dict], limit: int = 5) -> List[Tuple[str, float]]:
        """Get top gaining coins."""
        sorted_coins = sorted(coin_data.items(), key=lambda x: x[1]['pnl'], reverse=True)
        return [(coin, data['pnl']) for coin, data in sorted_coins[:limit]]
    
    def get_top_losers(self, coin_data: Dict[str, Dict], limit: int = 5) -> List[Tuple[str, float]]:
        """Get top losing coins."""
        sorted_coins = sorted(coin_data.items(), key=lambda x: x[1]['pnl'])
        return [(coin, data['pnl']) for coin, data in sorted_coins[:limit]]
    
    async def get_full_report(self) -> Dict[str, Any]:
        """Get full PnL report with all time periods."""
        try:
            # Check cache
            if self._cache_time and (datetime.now() - self._cache_time).seconds < self._cache_ttl:
                return self._cache
            
            # Fetch last 90 days of trades
            all_trades = await self.fetch_trade_history(days=90)
            
            now = datetime.now(timezone.utc)
            
            # Filter by time periods
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=today_start.weekday())
            month_start = today_start.replace(day=1)
            
            trades_today = [t for t in all_trades if t.timestamp >= today_start]
            trades_week = [t for t in all_trades if t.timestamp >= week_start]
            trades_month = [t for t in all_trades if t.timestamp >= month_start]
            
            # Calculate summaries
            summary_today = self.calculate_summary(trades_today)
            summary_week = self.calculate_summary(trades_week)
            summary_month = self.calculate_summary(trades_month)
            summary_all = self.calculate_summary(all_trades)
            
            # Per-coin analysis for each period
            coin_pnl_today = self.get_per_coin_pnl(trades_today)
            coin_pnl_week = self.get_per_coin_pnl(trades_week)
            coin_pnl_month = self.get_per_coin_pnl(trades_month)
            coin_pnl_all = self.get_per_coin_pnl(all_trades)
            
            report = {
                'updated_at': now.isoformat(),
                'today': asdict(summary_today),
                'week': asdict(summary_week),
                'month': asdict(summary_month),
                'all_time': asdict(summary_all),
                'top_gainers': self.get_top_gainers(coin_pnl_all),
                'top_losers': self.get_top_losers(coin_pnl_all),
                'per_coin': coin_pnl_all,
                # Per-period coin data
                'per_coin_today': coin_pnl_today,
                'per_coin_week': coin_pnl_week,
                'per_coin_month': coin_pnl_month,
                # Per-period top gainers/losers
                'top_gainers_today': self.get_top_gainers(coin_pnl_today, 3),
                'top_losers_today': self.get_top_losers(coin_pnl_today, 3),
                'top_gainers_week': self.get_top_gainers(coin_pnl_week, 3),
                'top_losers_week': self.get_top_losers(coin_pnl_week, 3),
                'top_gainers_month': self.get_top_gainers(coin_pnl_month, 3),
                'top_losers_month': self.get_top_losers(coin_pnl_month, 3),
                'total_trades': len(all_trades)
            }
            
            # Cache result
            self._cache = report
            self._cache_time = datetime.now()
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate PnL report: {e}")
            return {
                'error': str(e),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
    
    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            self.exchange = None


# Global instance
_pnl_tracker: Optional[PnLTracker] = None


def get_pnl_tracker() -> PnLTracker:
    """Get global PnL tracker instance."""
    global _pnl_tracker
    if _pnl_tracker is None:
        _pnl_tracker = PnLTracker()
    return _pnl_tracker
