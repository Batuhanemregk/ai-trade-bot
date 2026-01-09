"""
Virtual Exchange Adapter for Backtesting.

Simulates order execution with:
- Market fills at bar close + slippage
- Taker fee application
- TP/SL evaluation using bar high/low
- Position bookkeeping
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from loguru import logger


class IntrabarMode(Enum):
    """Tie-break mode when both TP and SL hit in same bar."""
    CONSERVATIVE = "conservative"  # SL wins (worst case)
    OPTIMISTIC = "optimistic"      # TP wins (best case)


@dataclass
class VirtualPosition:
    """Virtual position for backtesting."""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    size: float  # Position size in quote currency (USDT)
    entry_time: datetime
    entry_bar: int
    tp_price: float
    sl_price: float
    trailing_stop: Optional[float] = None
    trailing_activated: bool = False
    max_favorable_excursion: float = 0.0  # Best unrealized PnL
    max_adverse_excursion: float = 0.0    # Worst unrealized PnL


@dataclass
class VirtualTrade:
    """Completed trade record."""
    trade_id: int
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    entry_bar: int
    exit_bar: int
    exit_reason: str  # TP_HIT, SL_HIT, SIGNAL_EXIT, REVERSAL, END_OF_DATA
    size: float
    pnl_pct: float
    pnl_usdt: float
    fees_usdt: float
    holding_bars: int
    max_adverse_excursion: float = 0.0


class VirtualExchangeAdapter:
    """
    Virtual exchange adapter for backtesting.
    
    Simulates exchange behavior with deterministic execution.
    """
    
    def __init__(
        self,
        fee_bps: float = 6.0,
        slippage_bps: float = 3.0,
        intrabar_mode: IntrabarMode = IntrabarMode.CONSERVATIVE,
        leverage: int = 5
    ):
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.intrabar_mode = intrabar_mode
        self.leverage = leverage
        
        # State
        self.positions: Dict[str, VirtualPosition] = {}
        self.trades: List[VirtualTrade] = []
        self.trade_counter = 0
        self.current_bar_index = 0
        self.current_bar_time: Optional[datetime] = None
        
        # Balance tracking
        self.initial_balance: float = 10000.0
        self.balance: float = 10000.0
        self.equity_curve: List[Dict[str, Any]] = []
        
        logger.info(f"[VEXCH] Initialized: fee={fee_bps}bps, slip={slippage_bps}bps, "
                   f"mode={intrabar_mode.value}, leverage={leverage}x")
    
    def set_initial_balance(self, balance: float):
        """Set initial balance."""
        self.initial_balance = balance
        self.balance = balance
    
    def set_bar_context(self, bar_index: int, bar_time: datetime):
        """Set current bar context for order execution."""
        self.current_bar_index = bar_index
        self.current_bar_time = bar_time
    
    def _apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to price (worse for trader)."""
        slip_mult = self.slippage_bps / 10000
        if side == 'buy':
            return price * (1 + slip_mult)  # Pay more
        else:
            return price * (1 - slip_mult)  # Receive less
    
    def _calculate_fee(self, notional: float) -> float:
        """Calculate fee for a trade."""
        return notional * (self.fee_bps / 10000)
    
    def open_position(
        self,
        symbol: str,
        side: str,
        size_usdt: float,
        price: float,
        tp_price: float,
        sl_price: float
    ) -> Optional[VirtualPosition]:
        """
        Open a new position.
        
        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            size_usdt: Position size in USDT (margin)
            price: Entry price (bar close)
            tp_price: Take profit price
            sl_price: Stop loss price
            
        Returns:
            VirtualPosition or None if failed
        """
        if symbol in self.positions:
            logger.warning(f"[VEXCH] Position already exists for {symbol}")
            return None
        
        # Apply slippage to entry
        fill_side = 'buy' if side == 'long' else 'sell'
        fill_price = self._apply_slippage(price, fill_side)
        
        # Calculate fee (on notional = margin * leverage)
        notional = size_usdt * self.leverage
        entry_fee = self._calculate_fee(notional)
        self.balance -= entry_fee
        
        # Create position
        position = VirtualPosition(
            symbol=symbol,
            side=side,
            entry_price=fill_price,
            size=size_usdt,
            entry_time=self.current_bar_time,
            entry_bar=self.current_bar_index,
            tp_price=tp_price,
            sl_price=sl_price
        )
        
        self.positions[symbol] = position
        
        logger.debug(f"[VEXCH] OPEN {side.upper()} {symbol} @ {fill_price:.2f} | "
                    f"Size: ${size_usdt:.2f} | TP: {tp_price:.2f} | SL: {sl_price:.2f} | "
                    f"Fee: ${entry_fee:.4f}")
        
        return position
    
    def close_position(
        self,
        symbol: str,
        price: float,
        reason: str
    ) -> Optional[VirtualTrade]:
        """
        Close an existing position.
        
        Args:
            symbol: Trading symbol
            price: Exit price
            reason: Exit reason (TP_HIT, SL_HIT, SIGNAL_EXIT, etc.)
            
        Returns:
            VirtualTrade record or None
        """
        if symbol not in self.positions:
            logger.warning(f"[VEXCH] No position to close for {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Apply slippage to exit
        exit_side = 'sell' if position.side == 'long' else 'buy'
        fill_price = self._apply_slippage(price, exit_side)
        
        # Calculate PnL
        if position.side == 'long':
            pnl_pct = (fill_price - position.entry_price) / position.entry_price * 100
        else:
            pnl_pct = (position.entry_price - fill_price) / position.entry_price * 100
        
        # PnL in USDT (leveraged)
        notional = position.size * self.leverage
        pnl_usdt = notional * (pnl_pct / 100)
        
        # Exit fee
        exit_fee = self._calculate_fee(notional)
        total_fees = exit_fee  # Entry fee already deducted
        
        # Update balance
        self.balance += pnl_usdt - exit_fee
        
        # Create trade record
        self.trade_counter += 1
        trade = VirtualTrade(
            trade_id=self.trade_counter,
            symbol=symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=fill_price,
            entry_time=position.entry_time,
            exit_time=self.current_bar_time,
            entry_bar=position.entry_bar,
            exit_bar=self.current_bar_index,
            exit_reason=reason,
            size=position.size,
            pnl_pct=pnl_pct,
            pnl_usdt=pnl_usdt,
            fees_usdt=total_fees,
            holding_bars=self.current_bar_index - position.entry_bar,
            max_adverse_excursion=position.max_adverse_excursion
        )
        
        self.trades.append(trade)
        del self.positions[symbol]
        
        logger.debug(f"[VEXCH] CLOSE {position.side.upper()} {symbol} @ {fill_price:.2f} | "
                    f"Reason: {reason} | PnL: {pnl_pct:+.2f}% (${pnl_usdt:+.2f}) | "
                    f"Fee: ${exit_fee:.4f}")
        
        return trade
    
    def check_tpsl_hit(
        self,
        symbol: str,
        bar_high: float,
        bar_low: float,
        bar_close: float
    ) -> Optional[str]:
        """
        Check if TP or SL is hit within a bar.
        
        Uses bar high/low to check intrabar hits.
        Tie-break behavior controlled by intrabar_mode.
        
        Returns:
            'TP_HIT', 'SL_HIT', or None
        """
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        
        # Update max adverse/favorable excursion
        if position.side == 'long':
            current_pnl = (bar_close - position.entry_price) / position.entry_price * 100
            worst_pnl = (bar_low - position.entry_price) / position.entry_price * 100
            best_pnl = (bar_high - position.entry_price) / position.entry_price * 100
        else:
            current_pnl = (position.entry_price - bar_close) / position.entry_price * 100
            worst_pnl = (position.entry_price - bar_high) / position.entry_price * 100
            best_pnl = (position.entry_price - bar_low) / position.entry_price * 100
        
        position.max_adverse_excursion = min(position.max_adverse_excursion, worst_pnl)
        position.max_favorable_excursion = max(position.max_favorable_excursion, best_pnl)
        
        # Check hits
        tp_hit = False
        sl_hit = False
        
        if position.side == 'long':
            tp_hit = bar_high >= position.tp_price
            sl_hit = bar_low <= position.sl_price
        else:  # short
            tp_hit = bar_low <= position.tp_price
            sl_hit = bar_high >= position.sl_price
        
        # Handle tie-break
        if tp_hit and sl_hit:
            if self.intrabar_mode == IntrabarMode.CONSERVATIVE:
                return 'SL_HIT'  # Worst case
            else:
                return 'TP_HIT'  # Best case
        elif sl_hit:
            return 'SL_HIT'
        elif tp_hit:
            return 'TP_HIT'
        
        return None
    
    def update_trailing_stop(self, symbol: str, current_price: float, activation_r: float = 1.5, trail_pct: float = 0.5):
        """Update trailing stop if conditions met."""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Calculate R-multiple
        if position.side == 'long':
            r_mult = (current_price - position.entry_price) / position.entry_price
        else:
            r_mult = (position.entry_price - current_price) / position.entry_price
        
        # Activate trailing
        if r_mult >= activation_r and not position.trailing_activated:
            position.trailing_activated = True
            if position.side == 'long':
                position.trailing_stop = current_price * (1 - trail_pct / 100)
            else:
                position.trailing_stop = current_price * (1 + trail_pct / 100)
        
        # Update trailing stop
        if position.trailing_activated and position.trailing_stop:
            if position.side == 'long':
                new_stop = current_price * (1 - trail_pct / 100)
                if new_stop > position.trailing_stop:
                    position.trailing_stop = new_stop
                    position.sl_price = new_stop  # Update SL
            else:
                new_stop = current_price * (1 + trail_pct / 100)
                if new_stop < position.trailing_stop:
                    position.trailing_stop = new_stop
                    position.sl_price = new_stop  # Update SL
    
    def record_equity(self, current_prices: Dict[str, float] = None):
        """Record equity at current bar."""
        # Calculate unrealized PnL
        unrealized = 0.0
        if current_prices:
            for symbol, position in self.positions.items():
                if symbol in current_prices:
                    price = current_prices[symbol]
                    if position.side == 'long':
                        pnl_pct = (price - position.entry_price) / position.entry_price
                    else:
                        pnl_pct = (position.entry_price - price) / position.entry_price
                    unrealized += position.size * self.leverage * pnl_pct
        
        equity = self.balance + unrealized
        
        self.equity_curve.append({
            'bar': self.current_bar_index,
            'timestamp': self.current_bar_time,
            'equity': equity,
            'balance': self.balance,
            'unrealized': unrealized,
            'position_count': len(self.positions)
        })
    
    def get_position(self, symbol: str) -> Optional[VirtualPosition]:
        """Get position for symbol."""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if position exists."""
        return symbol in self.positions
    
    def get_balance(self) -> float:
        """Get current balance."""
        return self.balance
    
    def get_trades(self) -> List[VirtualTrade]:
        """Get all completed trades."""
        return self.trades
    
    def get_equity_curve(self) -> List[Dict[str, Any]]:
        """Get equity curve data."""
        return self.equity_curve
    
    # === Mock methods for compatibility with production code ===
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200):
        """Mock - data is injected from BacktestEngine."""
        raise NotImplementedError("Use BacktestEngine.get_ohlcv_slice() instead")
    
    async def fetch_positions(self, symbols: list = None):
        """Return virtual positions in CCXT-like format."""
        positions = []
        for symbol, pos in self.positions.items():
            positions.append({
                'symbol': symbol,
                'side': pos.side,
                'contracts': pos.size,
                'entryPrice': pos.entry_price,
                'info': {'instId': symbol}
            })
        return positions
    
    async def fetch_balance(self):
        """Return virtual balance."""
        return {
            'USDT': {
                'total': self.balance,
                'free': self.balance - sum(p.size for p in self.positions.values())
            }
        }
    
    async def create_market_order(self, symbol: str, side: str, amount: float, **kwargs):
        """Mock for compatibility - use open_position/close_position directly."""
        logger.warning("[VEXCH] create_market_order called - use open_position() instead")
        return {'id': f'VIRT_{self.trade_counter}', 'status': 'filled'}
    
    async def close(self):
        """No-op for virtual adapter."""
        pass
