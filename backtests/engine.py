"""
Core Backtest Engine for AiBotBS.
Simulates trading strategy on historical data.
"""

import pandas as pd
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from loguru import logger

from backtests.data_loader import OHLCVDataLoader
from backtests.metrics import PerformanceMetrics
from configs.policy import load_policy


class BacktestEngine:
    """
    Backtests trading strategies on historical data.
    
    Simulates the complete trading flow:
    1. Load historical OHLCV data
    2. For each bar, generate trading signals
    3. Execute trades based on signals
    4. Track portfolio equity
    5. Calculate performance metrics
    """
    
    def __init__(self, policy_path: str = "configs/policy.yaml", initial_capital: float = 10000.0):
        """
        Args:
            policy_path: Path to policy configuration
            initial_capital: Starting capital for backtest
        """
        self.policy = load_policy(policy_path)
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # State
        self.positions = {}  # symbol -> position dict
        self.trades = []  # List of completed trades
        self.equity_curve = []  # List of (timestamp, equity) tuples
        self.orders = []  # List of all orders
        
        # Components
        self.data_loader = OHLCVDataLoader()
        self.metrics_calc = PerformanceMetrics(initial_capital=initial_capital)
        self.analysis_engine = None  # Will be initialized with policy
        
        # Backtest settings
        self.commission = self.policy.get('trading', {}).get('execution', {}).get('commission', 0.0006)  # 0.06% default
        self.slippage = self.policy.get('trading', {}).get('execution', {}).get('slippage_tolerance', 0.001)  # 0.1% default
        
        logger.info(f"BacktestEngine initialized: ${initial_capital:,.2f} capital, "
                   f"{self.commission*100:.2f}% commission, {self.slippage*100:.2f}% slippage")
    
    async def run(
        self, 
        data_file: str, 
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Run backtest on historical data.
        
        Args:
            data_file: Path to CSV file with OHLCV data
            symbol: Trading symbol (e.g., "BTC-USDT")
            start_date: Start date for backtest (optional)
            end_date: End date for backtest (optional)
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest for {symbol}")
        logger.info(f"  Data file: {data_file}")
        logger.info(f"  Initial capital: ${self.initial_capital:,.2f}")
        
        # Load data
        df = self.data_loader.load_csv(data_file, symbol=symbol)
        
        # Filter by date range
        if start_date:
            df = df[df['timestamp'] >= start_date]
        if end_date:
            df = df[df['timestamp'] <= end_date]
        
        if len(df) == 0:
            raise ValueError("No data available for backtest period")
        
        logger.info(f"  Backtest period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        logger.info(f"  Total bars: {len(df)}")
        
        # Initialize analysis engine (mock mode for backtest)
        await self._initialize_analysis_engine()
        
        # Simulate trading bar by bar
        for idx, row in df.iterrows():
            await self._process_bar(row, df, idx)
        
        # Close any remaining positions
        await self._close_all_positions(df.iloc[-1])
        
        # Calculate metrics
        equity_series = pd.Series([e[1] for e in self.equity_curve])
        metrics = self.metrics_calc.calculate_all_metrics(self.trades, equity_series)
        
        # Prepare results
        results = {
            'metrics': metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve,
            'final_capital': self.current_capital,
            'symbol': symbol,
            'start_date': df['timestamp'].min(),
            'end_date': df['timestamp'].max(),
            'bars_processed': len(df)
        }
        
        logger.info(f"Backtest completed: {len(self.trades)} trades, "
                   f"{metrics['win_rate']:.1f}% win rate, "
                   f"{metrics['total_return']:.2f}% return")
        
        return results
    
    async def _initialize_analysis_engine(self):
        """Initialize analysis engine in backtest mode."""
        # Create minimal policy for backtest
        backtest_policy = self.policy.copy()
        backtest_policy['exchange']['mode'] = 'dry-run'
        backtest_policy['backtest_mode'] = True
        
        # We'll use simplified scoring for backtest MVP
        # In future, can integrate full AnalysisEngine
        logger.info("Analysis engine initialized in backtest mode")
    
    async def _process_bar(self, bar: pd.Series, full_df: pd.DataFrame, idx: int):
        """
        Process a single OHLCV bar.
        
        Args:
            bar: Current bar data
            full_df: Full dataframe (for historical context)
            idx: Current bar index
        """
        timestamp = bar['timestamp']
        symbol = bar['symbol']
        close_price = bar['close']
        
        # Update equity
        self._update_equity(timestamp, close_price)
        
        # Check for exit signals on existing positions
        await self._check_exit_signals(bar)
        
        # Generate entry signal if no position
        if symbol not in self.positions:
            # Need at least 100 bars of history for indicators
            if idx < 100:
                return
            
            # Get historical data for analysis
            hist_df = full_df.iloc[max(0, idx-200):idx+1].copy()
            
            # Generate signal (simplified for MVP)
            signal = await self._generate_signal(hist_df, bar)
            
            # Execute entry if signal is strong enough
            if signal and self._should_enter(signal):
                await self._enter_position(bar, signal)
    
    async def _generate_signal(self, hist_df: pd.DataFrame, current_bar: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal for current bar.
        
        For MVP, uses simplified TA-based signals.
        Future: Integrate full AnalysisEngine with ML, News, etc.
        
        Args:
            hist_df: Historical data
            current_bar: Current bar
            
        Returns:
            Signal dictionary or None
        """
        # Simplified signal generation for MVP
        # Calculate basic indicators
        close_prices = hist_df['close'].values
        
        # Simple moving averages
        sma_20 = close_prices[-20:].mean() if len(close_prices) >= 20 else None
        sma_50 = close_prices[-50:].mean() if len(close_prices) >= 50 else None
        
        if sma_20 is None or sma_50 is None:
            return None
        
        current_price = current_bar['close']
        
        # Trend detection (golden cross / death cross)
        direction = None
        score = 50.0  # Neutral
        
        if sma_20 > sma_50:
            # Bullish trend
            distance_from_sma = ((current_price - sma_20) / sma_20) * 100
            if -2 < distance_from_sma < 0:  # Price near SMA20 (pullback)
                direction = 'LONG'
                score = 70.0
        elif sma_20 < sma_50:
            # Bearish trend
            distance_from_sma = ((current_price - sma_20) / sma_20) * 100
            if 0 < distance_from_sma < 2:  # Price near SMA20 (pullback)
                direction = 'SHORT'
                score = 70.0
        
        if direction is None:
            return None
        
        # Calculate ATR for stop loss/take profit
        if len(hist_df) >= 14:
            high_low = hist_df['high'] - hist_df['low']
            atr = high_low[-14:].mean()
        else:
            atr = current_price * 0.02  # 2% default
        
        return {
            'symbol': current_bar['symbol'],
            'direction': direction,
            'score': score,
            'entry_price': current_price,
            'stop_loss': current_price - (2 * atr) if direction == 'LONG' else current_price + (2 * atr),
            'take_profit': current_price + (3 * atr) if direction == 'LONG' else current_price - (3 * atr),
            'timestamp': current_bar['timestamp']
        }
    
    def _should_enter(self, signal: Dict[str, Any]) -> bool:
        """Determine if signal is strong enough to enter."""
        min_score = self.policy.get('trading', {}).get('scoring', {}).get('min_composite_score', 0.6) * 100
        return signal['score'] >= min_score
    
    async def _enter_position(self, bar: pd.Series, signal: Dict[str, Any]):
        """
        Enter a new position based on signal.
        
        Args:
            bar: Current bar data
            signal: Trading signal
        """
        symbol = bar['symbol']
        entry_price = signal['entry_price']
        direction = signal['direction']
        
        # Calculate position size
        position_size_usd = self._calculate_position_size(signal)
        
        if position_size_usd < 10:  # Minimum position size
            return
        
        # Apply slippage
        if direction == 'LONG':
            actual_entry = entry_price * (1 + self.slippage)
        else:
            actual_entry = entry_price * (1 - self.slippage)
        
        # Calculate quantity
        quantity = position_size_usd / actual_entry
        
        # Apply commission
        commission_cost = position_size_usd * self.commission
        
        # Update capital
        self.current_capital -= (position_size_usd + commission_cost)
        
        # Create position
        position = {
            'symbol': symbol,
            'direction': direction,
            'entry_price': actual_entry,
            'entry_time': bar['timestamp'],
            'quantity': quantity,
            'position_size_usd': position_size_usd,
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'commission_paid': commission_cost,
            'signal_score': signal['score']
        }
        
        self.positions[symbol] = position
        
        logger.debug(f"[ENTRY] {symbol} {direction} @ ${actual_entry:.2f}, size=${position_size_usd:.2f}, qty={quantity:.6f}")
    
    async def _check_exit_signals(self, bar: pd.Series):
        """Check for exit conditions on open positions."""
        symbol = bar['symbol']
        
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        current_price = bar['close']
        
        # Check stop loss / take profit
        should_exit = False
        exit_reason = None
        
        if position['direction'] == 'LONG':
            if current_price <= position['stop_loss']:
                should_exit = True
                exit_reason = 'stop_loss'
            elif current_price >= position['take_profit']:
                should_exit = True
                exit_reason = 'take_profit'
        else:  # SHORT
            if current_price >= position['stop_loss']:
                should_exit = True
                exit_reason = 'stop_loss'
            elif current_price <= position['take_profit']:
                should_exit = True
                exit_reason = 'take_profit'
        
        if should_exit:
            await self._exit_position(bar, position, exit_reason)
    
    async def _exit_position(self, bar: pd.Series, position: Dict[str, Any], reason: str):
        """
        Exit an open position.
        
        Args:
            bar: Current bar data
            position: Position to exit
            reason: Exit reason
        """
        symbol = position['symbol']
        exit_price = bar['close']
        
        # Apply slippage
        if position['direction'] == 'LONG':
            actual_exit = exit_price * (1 - self.slippage)
        else:
            actual_exit = exit_price * (1 + self.slippage)
        
        # Calculate PnL
        if position['direction'] == 'LONG':
            pnl = (actual_exit - position['entry_price']) * position['quantity']
        else:  # SHORT
            pnl = (position['entry_price'] - actual_exit) * position['quantity']
        
        # Apply commission
        exit_value = position['quantity'] * actual_exit
        commission_cost = exit_value * self.commission
        pnl -= commission_cost
        
        # Update capital
        self.current_capital += (exit_value - commission_cost)
        
        # Calculate trade duration
        duration = (bar['timestamp'] - position['entry_time']).total_seconds() / 3600  # hours
        
        # Record trade
        trade = {
            'symbol': symbol,
            'direction': position['direction'],
            'entry_price': position['entry_price'],
            'exit_price': actual_exit,
            'entry_time': position['entry_time'],
            'exit_time': bar['timestamp'],
            'quantity': position['quantity'],
            'pnl': pnl,
            'pnl_pct': (pnl / position['position_size_usd']) * 100,
            'duration_hours': duration,
            'exit_reason': reason,
            'signal_score': position['signal_score'],
            'commission_total': position['commission_paid'] + commission_cost
        }
        
        self.trades.append(trade)
        
        # Remove position
        del self.positions[symbol]
        
        logger.debug(f"[EXIT] {symbol} {reason} @ ${actual_exit:.2f}, PnL=${pnl:.2f} ({trade['pnl_pct']:.1f}%)")
    
    async def _close_all_positions(self, last_bar: pd.Series):
        """Close all remaining positions at end of backtest."""
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            await self._exit_position(last_bar, position, reason='backtest_end')
    
    def _calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """Calculate position size based on risk parameters."""
        # Base position size from policy
        max_position_pct = self.policy.get('trading', {}).get('risk', {}).get('max_position_size', 0.1)
        base_size = self.current_capital * max_position_pct
        
        # Adjust by signal strength
        signal_multiplier = signal['score'] / 100.0
        position_size = base_size * signal_multiplier
        
        # Ensure we have enough capital
        position_size = min(position_size, self.current_capital * 0.95)  # Keep 5% cash buffer
        
        return position_size
    
    def _update_equity(self, timestamp: datetime, current_price: float):
        """Update equity curve with current portfolio value."""
        # Calculate unrealized PnL from open positions
        unrealized_pnl = 0.0
        for symbol, position in self.positions.items():
            if position['direction'] == 'LONG':
                unrealized_pnl += (current_price - position['entry_price']) * position['quantity']
            else:  # SHORT
                unrealized_pnl += (position['entry_price'] - current_price) * position['quantity']
        
        total_equity = self.current_capital + unrealized_pnl
        self.equity_curve.append((timestamp, total_equity))


# Example usage
if __name__ == "__main__":
    async def main():
        # Create sample data
        loader = OHLCVDataLoader()
        loader.create_sample_data(
            symbol="BTC-USDT",
            start_price=40000.0,
            num_bars=1000,
            timeframe="15m"
        )
        
        # Run backtest
        engine = BacktestEngine(initial_capital=10000.0)
        results = await engine.run(
            data_file="BTC-USDT_15m_sample.csv",
            symbol="BTC-USDT"
        )
        
        # Print results
        engine.metrics_calc.print_summary(results['metrics'])
        
        print(f"\n📊 Sample Trades:")
        for i, trade in enumerate(results['trades'][:5], 1):
            print(f"  {i}. {trade['direction']} @ ${trade['entry_price']:.2f} → ${trade['exit_price']:.2f} "
                  f"PnL=${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%)")
    
    asyncio.run(main())

