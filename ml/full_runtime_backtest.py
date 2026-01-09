"""
Full Runtime Backtest - Gerçek trading pipeline'ı geçmiş veri üzerinde simüle eder.

Bu script şunları simüle eder:
1. TA Score hesaplama (ta_scorer)
2. ML Score hesaplama (ml_scorer) 
3. Composite signal hesaplama (TA + ML + News + Risk ağırlıkları)
4. Decision thresholds (enter_long, enter_short, exit)
5. Position sizing (tier-based)
6. TP/SL hesaplama (ATR-based)
7. Protection guards (streak, cooldown, once-per-bar)
8. PnL hesaplama

Kullanım:
    python ml/full_runtime_backtest.py --symbol BTC --start 2024-01-01 --end 2024-12-01
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np
from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class PositionSide(Enum):
    FLAT = "FLAT"
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class Position:
    """Simulated position."""
    symbol: str
    side: PositionSide
    entry_price: float
    size: float
    entry_time: datetime
    tp_price: float
    sl_price: float
    entry_bar: int
    trailing_stop: Optional[float] = None
    trailing_activated: bool = False
    partial_tp_levels: List[float] = field(default_factory=list)
    
    def unrealized_pnl(self, current_price: float) -> float:
        if self.side == PositionSide.LONG:
            return (current_price - self.entry_price) / self.entry_price * 100
        elif self.side == PositionSide.SHORT:
            return (self.entry_price - current_price) / self.entry_price * 100
        return 0.0


@dataclass
class Trade:
    """Completed trade record."""
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    pnl_pct: float
    pnl_usdt: float
    exit_reason: str
    holding_bars: int
    size: float


@dataclass 
class BacktestResult:
    """Backtest results summary."""
    symbol: str
    start_date: datetime
    end_date: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl_pct: float
    total_pnl_usdt: float
    max_drawdown_pct: float
    avg_trade_pnl: float
    avg_holding_bars: float
    profit_factor: float
    sharpe_ratio: float
    trades: List[Trade]
    equity_curve: List[float]


class FullRuntimeBacktest:
    """
    Full runtime backtest engine.
    Uses actual TA scorer, ML scorer, and composite signal logic.
    """
    
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        self.scoring_config = policy.get('trading', {}).get('scoring', {})
        self.thresholds = self.scoring_config.get('decision_thresholds', {})
        
        # Weights
        self.ta_weight = self.scoring_config.get('ta_weight', 0.6)
        self.ml_weight = self.scoring_config.get('ml_weight', 0.3)
        self.news_weight = self.scoring_config.get('news_weight', 0.05)
        self.risk_weight = self.scoring_config.get('risk_weight', 0.05)
        
        # Thresholds
        self.enter_long = self.thresholds.get('enter_long', 54)
        self.exit_long = self.thresholds.get('exit_long', 47)
        self.enter_short = self.thresholds.get('enter_short', 43)
        self.exit_short = self.thresholds.get('exit_short', 53)
        
        # Position sizing tiers
        self.tiers = self.scoring_config.get('position_sizing', {}).get('tiers', {
            'weak': {'position_pct': 0.02, 'min_strength': 0.0, 'max_strength': 0.3},
            'medium': {'position_pct': 0.04, 'min_strength': 0.3, 'max_strength': 0.5},
            'strong': {'position_pct': 0.06, 'min_strength': 0.5, 'max_strength': 0.7},
            'extreme': {'position_pct': 0.08, 'min_strength': 0.7, 'max_strength': 1.0}
        })
        
        # Risk parameters
        self.atr_sl_mult = policy.get('trading', {}).get('risk', {}).get('sl_atr_mult', 2.0)
        self.atr_tp_mult = policy.get('trading', {}).get('risk', {}).get('tp_atr_mult', 4.0)
        
        # Protection guards
        self.streak_threshold = 2  # Reduce size after 2 losses
        self.cooldown_bars = 2
        
        # Scorers (will be initialized)
        self.ta_scorer = None
        self.ml_scorer = None
        
        # State
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []
        self.equity = 10000.0  # Starting equity
        self.equity_curve: List[float] = []
        self.consecutive_losses = 0
        self.last_trade_bar = -999
        
        logger.info(f"[BACKTEST] Initialized with thresholds: "
                   f"enter_long={self.enter_long}, exit_long={self.exit_long}, "
                   f"enter_short={self.enter_short}, exit_short={self.exit_short}")
    
    def initialize_scorers(self):
        """Initialize TA and ML scorers."""
        try:
            from scoring.ta_scorer import TAScorer
            self.ta_scorer = TAScorer()
            logger.info("✅ TA Scorer initialized")
        except Exception as e:
            logger.warning(f"⚠️ TA Scorer init failed: {e}")
            self.ta_scorer = None
        
        try:
            from scoring.ml_scorer import MLScorer
            self.ml_scorer = MLScorer()
            logger.info("✅ ML Scorer initialized")
        except Exception as e:
            logger.warning(f"⚠️ ML Scorer init failed: {e}")
            self.ml_scorer = None
    
    def compute_ta_score(self, df: pd.DataFrame, symbol: str) -> Tuple[float, str, dict]:
        """Compute TA score using actual scorer."""
        if self.ta_scorer is None:
            return 50.0, "ta_scorer_unavailable", {}
        
        try:
            score, rationale, flags = self.ta_scorer.score(df, symbol)
            return score, rationale, flags
        except Exception as e:
            logger.warning(f"TA scoring error: {e}")
            return 50.0, f"ta_error: {e}", {}
    
    def compute_ml_score(self, symbol: str, ohlcv_bundle: Dict[str, pd.DataFrame]) -> Tuple[Optional[float], str, dict]:
        """Compute ML score using actual scorer."""
        if self.ml_scorer is None:
            return None, "ml_scorer_unavailable", {}
        
        try:
            score, rationale, details = self.ml_scorer.score(symbol, ohlcv_bundle)
            return score, rationale, details
        except Exception as e:
            logger.warning(f"ML scoring error: {e}")
            return None, f"ml_error: {e}", {}
    
    def compute_composite_score(self, ta_score: float, ml_score: Optional[float]) -> float:
        """Compute composite score with weight redistribution for None ML."""
        if ml_score is None:
            # Redistribute ML weight to TA
            effective_ta_weight = self.ta_weight + self.ml_weight
            composite = effective_ta_weight * ta_score + self.news_weight * 50 + self.risk_weight * 50
        else:
            composite = (
                self.ta_weight * ta_score +
                self.ml_weight * ml_score +
                self.news_weight * 50 +  # Neutral news
                self.risk_weight * 50     # Neutral risk
            )
        return composite
    
    def get_decision(self, composite_score: float, current_position: PositionSide) -> str:
        """Get trading decision based on composite score and current position."""
        if current_position == PositionSide.FLAT:
            if composite_score >= self.enter_long:
                return "OPEN_LONG"
            elif composite_score <= self.enter_short:
                return "OPEN_SHORT"
            else:
                return "HOLD"
        elif current_position == PositionSide.LONG:
            if composite_score <= self.exit_long:
                return "CLOSE_LONG"
            elif composite_score <= self.enter_short:
                return "REVERSE_TO_SHORT"
            else:
                return "HOLD"
        elif current_position == PositionSide.SHORT:
            if composite_score >= self.exit_short:
                return "CLOSE_SHORT"
            elif composite_score >= self.enter_long:
                return "REVERSE_TO_LONG"
            else:
                return "HOLD"
        return "HOLD"
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR for TP/SL calculation."""
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1])
            )
        )
        atr = np.mean(tr[-period:])
        return atr
    
    def calculate_tp_sl(self, entry_price: float, side: PositionSide, atr: float) -> Tuple[float, float]:
        """Calculate TP/SL based on ATR."""
        if side == PositionSide.LONG:
            sl_price = entry_price - (atr * self.atr_sl_mult)
            tp_price = entry_price + (atr * self.atr_tp_mult)
        else:  # SHORT
            sl_price = entry_price + (atr * self.atr_sl_mult)
            tp_price = entry_price - (atr * self.atr_tp_mult)
        return tp_price, sl_price
    
    def get_position_size(self, strength: float) -> float:
        """Get position size based on signal strength tier."""
        # Apply streak reduction
        reduction = 1.0
        if self.consecutive_losses >= self.streak_threshold:
            reduction = 0.5
            logger.debug(f"[STREAK] {self.consecutive_losses} losses, reducing size by 50%")
        
        # Find tier
        for tier_name, tier_config in self.tiers.items():
            min_s = tier_config.get('min_strength', 0)
            max_s = tier_config.get('max_strength', 1)
            if min_s <= strength < max_s:
                base_pct = tier_config.get('position_pct', 0.02)
                return base_pct * reduction
        
        return 0.02 * reduction  # Default weak tier
    
    def check_tp_sl(self, current_price: float, current_bar: int) -> Optional[str]:
        """Check if TP or SL is hit."""
        if self.position is None:
            return None
        
        if self.position.side == PositionSide.LONG:
            if current_price >= self.position.tp_price:
                return "TP_HIT"
            elif current_price <= self.position.sl_price:
                return "SL_HIT"
        elif self.position.side == PositionSide.SHORT:
            if current_price <= self.position.tp_price:
                return "TP_HIT"
            elif current_price >= self.position.sl_price:
                return "SL_HIT"
        
        return None
    
    def check_trailing_stop(self, current_price: float, r_multiple: float) -> bool:
        """Check and update trailing stop."""
        if self.position is None:
            return False
        
        trailing_config = self.policy.get('trading', {}).get('scoring', {}).get('trailing', {})
        if not trailing_config.get('enabled', False):
            return False
        
        activation_r = trailing_config.get('activation_r', 1.5)
        trail_pct = trailing_config.get('trail_pct', 0.5)
        
        if r_multiple >= activation_r and not self.position.trailing_activated:
            self.position.trailing_activated = True
            if self.position.side == PositionSide.LONG:
                self.position.trailing_stop = current_price * (1 - trail_pct / 100)
            else:
                self.position.trailing_stop = current_price * (1 + trail_pct / 100)
            logger.debug(f"[TRAIL] Activated at R={r_multiple:.2f}")
        
        if self.position.trailing_activated and self.position.trailing_stop:
            # Update trailing stop
            if self.position.side == PositionSide.LONG:
                new_stop = current_price * (1 - trail_pct / 100)
                if new_stop > self.position.trailing_stop:
                    self.position.trailing_stop = new_stop
                if current_price <= self.position.trailing_stop:
                    return True
            else:
                new_stop = current_price * (1 + trail_pct / 100)
                if new_stop < self.position.trailing_stop:
                    self.position.trailing_stop = new_stop
                if current_price >= self.position.trailing_stop:
                    return True
        
        return False
    
    def open_position(self, symbol: str, side: PositionSide, entry_price: float, 
                     atr: float, strength: float, bar_index: int, timestamp: datetime):
        """Open a new position."""
        position_pct = self.get_position_size(strength)
        size = self.equity * position_pct
        
        tp_price, sl_price = self.calculate_tp_sl(entry_price, side, atr)
        
        self.position = Position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            size=size,
            entry_time=timestamp,
            tp_price=tp_price,
            sl_price=sl_price,
            entry_bar=bar_index
        )
        
        self.last_trade_bar = bar_index
        
        logger.info(f"[OPEN] {side.value} {symbol} @ {entry_price:.2f} | "
                   f"Size: ${size:.2f} | TP: {tp_price:.2f} | SL: {sl_price:.2f}")
    
    def close_position(self, exit_price: float, exit_reason: str, 
                      bar_index: int, timestamp: datetime):
        """Close current position."""
        if self.position is None:
            return
        
        pnl_pct = self.position.unrealized_pnl(exit_price)
        pnl_usdt = self.position.size * (pnl_pct / 100)
        
        trade = Trade(
            symbol=self.position.symbol,
            side=self.position.side.value,
            entry_price=self.position.entry_price,
            exit_price=exit_price,
            entry_time=self.position.entry_time,
            exit_time=timestamp,
            pnl_pct=pnl_pct,
            pnl_usdt=pnl_usdt,
            exit_reason=exit_reason,
            holding_bars=bar_index - self.position.entry_bar,
            size=self.position.size
        )
        
        self.trades.append(trade)
        self.equity += pnl_usdt
        
        # Update streak
        if pnl_usdt < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        logger.info(f"[CLOSE] {exit_reason} @ {exit_price:.2f} | "
                   f"PnL: {pnl_pct:+.2f}% (${pnl_usdt:+.2f}) | "
                   f"Equity: ${self.equity:.2f}")
        
        self.position = None
        self.last_trade_bar = bar_index
    
    def run(self, symbol: str, df: pd.DataFrame) -> BacktestResult:
        """Run full backtest on historical data."""
        logger.info(f"[BACKTEST] Starting for {symbol} with {len(df)} bars")
        
        self.initialize_scorers()
        
        # Reset state
        self.position = None
        self.trades = []
        self.equity = 10000.0
        self.equity_curve = [self.equity]
        self.consecutive_losses = 0
        self.last_trade_bar = -999
        
        # Minimum lookback for indicators
        min_lookback = 50
        
        for i in range(min_lookback, len(df)):
            current_bar = df.iloc[:i+1].copy()
            current_price = current_bar['close'].iloc[-1]
            current_time = current_bar.index[-1] if isinstance(current_bar.index[-1], datetime) else datetime.now()
            
            # Check cooldown
            bars_since_trade = i - self.last_trade_bar
            if bars_since_trade < self.cooldown_bars and self.position is None:
                self.equity_curve.append(self.equity)
                continue
            
            # Check TP/SL first
            if self.position is not None:
                exit_reason = self.check_tp_sl(current_price, i)
                if exit_reason:
                    self.close_position(current_price, exit_reason, i, current_time)
                    self.equity_curve.append(self.equity)
                    continue
                
                # Check trailing stop
                r_mult = (current_price - self.position.entry_price) / self.position.entry_price
                if self.position.side == PositionSide.SHORT:
                    r_mult = -r_mult
                
                if self.check_trailing_stop(current_price, r_mult):
                    self.close_position(current_price, "TRAILING_STOP", i, current_time)
                    self.equity_curve.append(self.equity)
                    continue
            
            # Compute scores
            ta_score, ta_rationale, ta_flags = self.compute_ta_score(current_bar, symbol)
            
            ohlcv_bundle = {'main': current_bar}
            ml_score, ml_rationale, ml_details = self.compute_ml_score(symbol, ohlcv_bundle)
            
            composite = self.compute_composite_score(ta_score, ml_score)
            
            # Get current position side
            current_side = self.position.side if self.position else PositionSide.FLAT
            
            # Get decision
            decision = self.get_decision(composite, current_side)
            
            # Calculate ATR for position sizing
            atr = self.calculate_atr(current_bar)
            
            # Calculate signal strength (normalized composite)
            strength = abs(composite - 50) / 50
            
            # Execute decision
            if decision == "OPEN_LONG":
                self.open_position(symbol, PositionSide.LONG, current_price, atr, strength, i, current_time)
            elif decision == "OPEN_SHORT":
                self.open_position(symbol, PositionSide.SHORT, current_price, atr, strength, i, current_time)
            elif decision == "CLOSE_LONG" or decision == "CLOSE_SHORT":
                self.close_position(current_price, "SIGNAL_EXIT", i, current_time)
            elif decision == "REVERSE_TO_SHORT":
                self.close_position(current_price, "REVERSAL", i, current_time)
                self.open_position(symbol, PositionSide.SHORT, current_price, atr, strength, i, current_time)
            elif decision == "REVERSE_TO_LONG":
                self.close_position(current_price, "REVERSAL", i, current_time)
                self.open_position(symbol, PositionSide.LONG, current_price, atr, strength, i, current_time)
            
            self.equity_curve.append(self.equity)
            
            # Log every 100 bars
            if i % 100 == 0:
                logger.info(f"[PROGRESS] Bar {i}/{len(df)} | Equity: ${self.equity:.2f} | Trades: {len(self.trades)}")
        
        # Close any open position at end
        if self.position is not None:
            final_price = df['close'].iloc[-1]
            final_time = df.index[-1] if isinstance(df.index[-1], datetime) else datetime.now()
            self.close_position(final_price, "END_OF_DATA", len(df)-1, final_time)
        
        # Calculate results
        result = self._calculate_results(symbol, df)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"[BACKTEST COMPLETE] {symbol}")
        logger.info(f"{'='*60}")
        logger.info(f"Total Trades: {result.total_trades}")
        logger.info(f"Win Rate: {result.win_rate:.1%}")
        logger.info(f"Total PnL: {result.total_pnl_pct:+.2f}% (${result.total_pnl_usdt:+.2f})")
        logger.info(f"Max Drawdown: {result.max_drawdown_pct:.2f}%")
        logger.info(f"Profit Factor: {result.profit_factor:.2f}")
        logger.info(f"Avg Holding: {result.avg_holding_bars:.1f} bars")
        
        return result
    
    def _calculate_results(self, symbol: str, df: pd.DataFrame) -> BacktestResult:
        """Calculate backtest statistics."""
        if not self.trades:
            return BacktestResult(
                symbol=symbol,
                start_date=df.index[0],
                end_date=df.index[-1],
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl_pct=0.0,
                total_pnl_usdt=0.0,
                max_drawdown_pct=0.0,
                avg_trade_pnl=0.0,
                avg_holding_bars=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                trades=self.trades,
                equity_curve=self.equity_curve
            )
        
        winning = [t for t in self.trades if t.pnl_usdt > 0]
        losing = [t for t in self.trades if t.pnl_usdt <= 0]
        
        total_pnl = sum(t.pnl_usdt for t in self.trades)
        total_pnl_pct = (self.equity - 10000) / 10000 * 100
        
        # Max drawdown
        peak = self.equity_curve[0]
        max_dd = 0
        for eq in self.equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # Profit factor
        gross_profit = sum(t.pnl_usdt for t in winning) if winning else 0
        gross_loss = abs(sum(t.pnl_usdt for t in losing)) if losing else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio (simplified)
        returns = [t.pnl_pct for t in self.trades]
        if len(returns) > 1:
            sharpe = np.mean(returns) / (np.std(returns) + 0.001) * np.sqrt(252)
        else:
            sharpe = 0
        
        return BacktestResult(
            symbol=symbol,
            start_date=df.index[0],
            end_date=df.index[-1],
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(self.trades),
            total_pnl_pct=total_pnl_pct,
            total_pnl_usdt=total_pnl,
            max_drawdown_pct=max_dd,
            avg_trade_pnl=np.mean([t.pnl_pct for t in self.trades]),
            avg_holding_bars=np.mean([t.holding_bars for t in self.trades]),
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            trades=self.trades,
            equity_curve=self.equity_curve
        )


async def load_historical_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Load historical OHLCV data."""
    # Try to load from existing training data
    data_dir = Path("data/ml_training")
    csv_file = data_dir / f"{symbol}_15m_multiclass.csv"
    
    if csv_file.exists():
        logger.info(f"Loading data from {csv_file}")
        df = pd.read_csv(csv_file, parse_dates=['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    
    # Alternative: fetch from exchange
    logger.info(f"Fetching historical data for {symbol} from exchange...")
    try:
        from adapters.exchange_okx_ccxt import OKXCCXTAdapter
        adapter = OKXCCXTAdapter()
        
        # Fetch 15m data
        ohlcv = await adapter.fetch_ohlcv(f"{symbol}-USDT-SWAP", '15m', limit=2000)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        await adapter.close()
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return pd.DataFrame()


async def main():
    parser = argparse.ArgumentParser(description='Full Runtime Backtest')
    parser.add_argument('--symbol', type=str, default='BTC', help='Symbol to backtest')
    parser.add_argument('--start', type=str, default='2024-01-01', help='Start date')
    parser.add_argument('--end', type=str, default='2024-12-01', help='End date')
    
    args = parser.parse_args()
    
    # Load policy
    from configs.policy import load_policy
    policy = load_policy()
    
    # Load historical data
    df = await load_historical_data(args.symbol, args.start, args.end)
    
    if df.empty:
        logger.error("No data available for backtest")
        return
    
    logger.info(f"Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    # Run backtest
    backtest = FullRuntimeBacktest(policy)
    result = backtest.run(args.symbol, df)
    
    # Save results
    output_dir = Path("data/backtest_results")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save trades
    trades_df = pd.DataFrame([{
        'symbol': t.symbol,
        'side': t.side,
        'entry_price': t.entry_price,
        'exit_price': t.exit_price,
        'entry_time': t.entry_time,
        'exit_time': t.exit_time,
        'pnl_pct': t.pnl_pct,
        'pnl_usdt': t.pnl_usdt,
        'exit_reason': t.exit_reason,
        'holding_bars': t.holding_bars
    } for t in result.trades])
    
    trades_file = output_dir / f"{args.symbol}_backtest_trades.csv"
    trades_df.to_csv(trades_file, index=False)
    logger.info(f"✅ Trades saved to {trades_file}")
    
    # Save summary
    summary = {
        'symbol': result.symbol,
        'total_trades': result.total_trades,
        'win_rate': result.win_rate,
        'total_pnl_pct': result.total_pnl_pct,
        'total_pnl_usdt': result.total_pnl_usdt,
        'max_drawdown_pct': result.max_drawdown_pct,
        'profit_factor': result.profit_factor,
        'sharpe_ratio': result.sharpe_ratio,
        'avg_holding_bars': result.avg_holding_bars
    }
    
    summary_file = output_dir / f"{args.symbol}_backtest_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"✅ Summary saved to {summary_file}")


if __name__ == '__main__':
    asyncio.run(main())
