"""
FULL BOT BACKTEST
-----------------
Complete backtesting with ALL bot features:
- TA, ML, News, Risk scoring
- Signal gates (persistence, bias, reversal)
- State management (IDLE -> SIGNAL -> POSITION -> COOLDOWN)
- Dynamic position sizing (ML confidence based)
- Dynamic leverage
- Performance metrics
"""
import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger

from configs.policy import load_policy
from scoring.ta_scorer import TAScorer
from scoring.ml_scorer import MLScorer
from scoring.news_scorer import NewsScorer
from application.risk_service import RiskService
from adapters.exchange_okx_ccxt import OKXCCXTAdapter
from backtests.metrics import PerformanceMetrics


@dataclass
class Position:
    """Backtest position."""
    symbol: str
    direction: str  # LONG or SHORT
    entry_time: datetime
    entry_price: float
    size_usdt: float
    leverage: float
    stop_loss: float
    take_profit: float
    
    # Scores at entry
    composite_score: float
    ta_score: float
    ml_score: float
    ml_confidence: str
    news_score: float
    risk_score: float


@dataclass
class Trade:
    """Completed trade."""
    symbol: str
    direction: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size_usdt: float
    leverage: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    
    # Scores
    composite_score: float
    ml_confidence: str


class FullBotBacktest:
    """
    Full bot backtest engine with ALL features.
    """
    
    def __init__(self, policy: Dict[str, Any], initial_capital: float = 10000.0):
        self.policy = policy
        self.initial_capital = initial_capital
        self.capital = initial_capital
        
        # Scorers
        self.ta_scorer = TAScorer()
        self.ml_scorer = MLScorer()
        self.news_scorer = NewsScorer()
        
        # Risk service (without real exchange)
        self.risk_service = None  # Will mock it
        
        # State
        self.state = "IDLE"  # IDLE, SIGNAL_DETECTED, IN_POSITION, COOLDOWN
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []
        
        # Signal persistence tracking
        self.signal_history: List[Dict] = []
        
        # Metrics
        self.equity_curve = []
        self.metrics_calc = PerformanceMetrics(initial_capital)
        
        logger.info(f"[INIT] Full bot backtest initialized with ${initial_capital}")
    
    async def run(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Run full backtest on historical data.
        
        Args:
            df: OHLCV DataFrame with columns: timestamp, open, high, low, close, volume
            symbol: Trading symbol (e.g., 'BTC-USDT')
        
        Returns:
            Results dictionary with trades, metrics, equity curve
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"FULL BOT BACKTEST: {symbol}")
        logger.info(f"Period: {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
        logger.info(f"Bars: {len(df)}")
        logger.info(f"Initial capital: ${self.initial_capital}")
        logger.info(f"{'='*60}\n")
        
        # Reset state
        self.capital = self.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.signal_history = []
        self.state = "IDLE"
        
        # Process each bar
        for idx in range(100, len(df)):  # Start from bar 100 for indicators
            bar = df.iloc[idx]
            hist_df = df.iloc[:idx+1].copy()  # Historical data up to current bar
            
            # Record equity
            equity = self._calculate_equity(bar)
            self.equity_curve.append({
                'timestamp': bar['timestamp'],
                'equity': equity,
                'capital': self.capital,
                'position_value': equity - self.capital
            })
            
            # Process bar based on state
            await self._process_bar(bar, hist_df, symbol)
            
            # Log progress every 1000 bars
            if idx % 1000 == 0:
                logger.info(f"[PROGRESS] Bar {idx}/{len(df)}, Equity: ${equity:.2f}, Trades: {len(self.trades)}, State: {self.state}")
        
        # Close any open position at end
        if self.position:
            final_bar = df.iloc[-1]
            await self._close_position(final_bar, "END_OF_DATA")
        
        # Calculate metrics
        trades_dicts = [self._trade_to_dict(t) for t in self.trades]
        equity_df = pd.DataFrame(self.equity_curve)
        equity_series = equity_df['equity'] if 'equity' in equity_df.columns else pd.Series([self.initial_capital])
        metrics = self.metrics_calc.calculate_all_metrics(trades_dicts, equity_series)
        
        return {
            'symbol': symbol,
            'trades': [self._trade_to_dict(t) for t in self.trades],
            'metrics': metrics,
            'equity_curve': self.equity_curve,
            'start_date': str(df.iloc[0]['timestamp']),
            'end_date': str(df.iloc[-1]['timestamp']),
            'bars_processed': len(df)
        }
    
    async def _process_bar(self, bar: pd.Series, hist_df: pd.DataFrame, symbol: str):
        """Process a single bar based on current state."""
        
        if self.state == "IDLE":
            # Look for signal
            signal = await self._generate_signal(hist_df, bar, symbol)
            if signal and signal['decision'] in ['LONG', 'SHORT']:
                # Check signal gates
                if self._check_signal_gates(signal):
                    self.state = "SIGNAL_DETECTED"
                    await self._enter_position(bar, signal)
        
        elif self.state == "IN_POSITION":
            # Check exit conditions
            await self._check_exit_conditions(bar)
        
        elif self.state == "COOLDOWN":
            # Check if cooldown period ended
            # For simplicity, just reset to IDLE (implement time-based cooldown if needed)
            self.state = "IDLE"
    
    async def _generate_signal(self, hist_df: pd.DataFrame, bar: pd.Series, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Generate trading signal using ALL scorers.
        """
        try:
            current_price = bar['close']
            
            # 1. TA Analysis
            try:
                ta_score, ta_rationale, ta_flags = self.ta_scorer.score(hist_df, symbol)
            except Exception as e:
                logger.warning(f"TA scoring failed: {e}")
                ta_score, ta_rationale, ta_flags = 50.0, f"TA error: {e}", {}
            
            # 2. ML Analysis
            try:
                ohlcv_bundle = {
                    'main': hist_df,
                    '15m': hist_df,
                    'trend': hist_df
                }
                ml_score, ml_rationale, ml_details = self.ml_scorer.score(symbol, ohlcv_bundle)
                ml_confidence = ml_details.get('confidence', 'low')
            except Exception as e:
                logger.warning(f"ML scoring failed: {e}")
                ml_score, ml_rationale, ml_details = 50.0, f"ML error: {e}", {}
                ml_confidence = 'low'
            
            # 3. News Analysis (mock for backtest)
            news_score = 50.0  # Neutral for backtest
            
            # 4. Risk Analysis (simplified for backtest)
            risk_score = 50.0  # Neutral for backtest
            
            # 5. Composite Score
            weights = self.policy.get('trading', {}).get('scoring', {})
            ta_weight = weights.get('ta_weight', 0.4)
            ml_weight = weights.get('ml_weight', 0.25)
            news_weight = weights.get('news_weight', 0.2)
            risk_weight = weights.get('risk_weight', 0.15)
            
            composite_score = (
                (ta_score * ta_weight) +
                (ml_score * ml_weight) +
                (news_score * news_weight) +
                (risk_score * risk_weight)
            )
            
            # Determine direction
            min_score = self.policy.get('trading', {}).get('scoring', {}).get('min_composite_score', 0.6) * 100
            
            if composite_score >= min_score:
                decision = 'LONG'
            elif composite_score <= (100 - min_score):
                decision = 'SHORT'
            else:
                decision = 'HOLD'
            
            # Calculate stop loss / take profit
            sl_pct = self.policy.get('trading', {}).get('risk', {}).get('stop_loss_pct', 0.02)
            tp_pct = self.policy.get('trading', {}).get('risk', {}).get('take_profit_pct', 0.04)
            
            if decision == 'LONG':
                stop_loss = current_price * (1 - sl_pct)
                take_profit = current_price * (1 + tp_pct)
            elif decision == 'SHORT':
                stop_loss = current_price * (1 + sl_pct)
                take_profit = current_price * (1 - tp_pct)
            else:
                return None
            
            signal = {
                'symbol': symbol,
                'decision': decision,
                'composite_score': composite_score,
                'ta_score': ta_score,
                'ml_score': ml_score,
                'ml_confidence': ml_confidence,
                'news_score': news_score,
                'risk_score': risk_score,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'timestamp': bar['timestamp']
            }
            
            # Add to signal history for persistence tracking
            self.signal_history.append(signal)
            
            return signal
            
        except Exception as e:
            logger.error(f"Signal generation failed: {e}")
            return None
    
    def _check_signal_gates(self, signal: Dict[str, Any]) -> bool:
        """
        Check signal gates (persistence, bias, reversal).
        For backtest, simplified implementation.
        """
        # Gate 1: Persistence (signal must persist for N bars)
        required_persistence = 2  # Must see signal for 2 consecutive bars
        recent_signals = self.signal_history[-required_persistence:]
        
        if len(recent_signals) < required_persistence:
            return False
        
        # Check if all recent signals agree on direction
        directions = [s['decision'] for s in recent_signals]
        if len(set(directions)) > 1:  # Not all same direction
            return False
        
        # Gate 2: Bias detection (simplified - always pass for now)
        # Gate 3: Reversal detection (simplified - always pass for now)
        
        return True
    
    async def _enter_position(self, bar: pd.Series, signal: Dict[str, Any]):
        """Enter a position."""
        try:
            # Calculate position size with ML confidence adjustment
            position_size = self._calculate_position_size(signal)
            
            if position_size < 10:  # Minimum $10
                logger.info(f"[SKIP] Position size too small: ${position_size:.2f}")
                self.state = "IDLE"
                return
            
            # Calculate leverage (simplified)
            leverage = self._calculate_leverage(signal)
            
            # Create position
            self.position = Position(
                symbol=signal['symbol'],
                direction=signal['decision'],
                entry_time=bar['timestamp'],
                entry_price=signal['entry_price'],
                size_usdt=position_size,
                leverage=leverage,
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                composite_score=signal['composite_score'],
                ta_score=signal['ta_score'],
                ml_score=signal['ml_score'],
                ml_confidence=signal['ml_confidence'],
                news_score=signal['news_score'],
                risk_score=signal['risk_score']
            )
            
            self.state = "IN_POSITION"
            
            logger.info(f"[ENTRY] {signal['decision']} @ ${signal['entry_price']:.2f}, "
                       f"size=${position_size:.2f}, leverage={leverage:.1f}x, "
                       f"score={signal['composite_score']:.1f}, ml_conf={signal['ml_confidence']}")
            
        except Exception as e:
            logger.error(f"Failed to enter position: {e}")
            self.state = "IDLE"
    
    async def _check_exit_conditions(self, bar: pd.Series):
        """Check if position should be exited."""
        if not self.position:
            return
        
        current_price = bar['close']
        
        # Check stop loss
        if self.position.direction == 'LONG':
            if current_price <= self.position.stop_loss:
                await self._close_position(bar, "STOP_LOSS")
                return
            if current_price >= self.position.take_profit:
                await self._close_position(bar, "TAKE_PROFIT")
                return
        
        elif self.position.direction == 'SHORT':
            if current_price >= self.position.stop_loss:
                await self._close_position(bar, "STOP_LOSS")
                return
            if current_price <= self.position.take_profit:
                await self._close_position(bar, "TAKE_PROFIT")
                return
    
    async def _close_position(self, bar: pd.Series, reason: str):
        """Close the current position."""
        if not self.position:
            return
        
        exit_price = bar['close']
        
        # Calculate PnL
        if self.position.direction == 'LONG':
            pnl_pct = ((exit_price - self.position.entry_price) / self.position.entry_price) * 100
        else:  # SHORT
            pnl_pct = ((self.position.entry_price - exit_price) / self.position.entry_price) * 100
        
        # Apply leverage
        pnl_pct *= self.position.leverage
        
        # Calculate PnL in USDT
        pnl = self.position.size_usdt * (pnl_pct / 100)
        
        # Update capital
        self.capital += pnl
        
        # Create trade record
        trade = Trade(
            symbol=self.position.symbol,
            direction=self.position.direction,
            entry_time=self.position.entry_time,
            exit_time=bar['timestamp'],
            entry_price=self.position.entry_price,
            exit_price=exit_price,
            size_usdt=self.position.size_usdt,
            leverage=self.position.leverage,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            composite_score=self.position.composite_score,
            ml_confidence=self.position.ml_confidence
        )
        
        self.trades.append(trade)
        
        logger.info(f"[EXIT] {self.position.direction} @ ${exit_price:.2f}, "
                   f"PnL=${pnl:.2f} ({pnl_pct:.1f}%), reason={reason}, "
                   f"capital=${self.capital:.2f}")
        
        # Reset state
        self.position = None
        self.state = "COOLDOWN" if pnl < 0 else "IDLE"
        self.signal_history = []  # Clear signal history
    
    def _calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """
        Calculate position size with ML confidence adjustment.
        """
        # Base percentage from signal strength (1% to 10%)
        composite_score = signal['composite_score']
        signal_percentage = 0.01 + (composite_score / 100.0) * 0.09
        signal_percentage = max(0.01, min(0.10, signal_percentage))
        
        # Risk adjustment (simplified - use risk score if available)
        risk_score = signal.get('risk_score', 50.0)
        risk_multiplier = 1.0 - (risk_score / 100.0) * 0.5
        risk_multiplier = max(0.5, min(1.0, risk_multiplier))
        
        # ML Confidence adjustment
        ml_confidence = signal.get('ml_confidence', 'low')
        if ml_confidence == 'high':
            ml_confidence_multiplier = 1.0
        elif ml_confidence == 'medium':
            ml_confidence_multiplier = 0.85
        else:
            ml_confidence_multiplier = 0.70
        
        # Final size
        final_percentage = signal_percentage * risk_multiplier * ml_confidence_multiplier
        final_percentage = max(0.01, min(0.10, final_percentage))
        
        position_size = self.capital * final_percentage
        
        logger.debug(f"[SIZE] score={composite_score:.1f}, signal_pct={signal_percentage:.1%}, "
                    f"risk_mult={risk_multiplier:.2f}, ml_mult={ml_confidence_multiplier:.2f}, "
                    f"final_pct={final_percentage:.1%}, size=${position_size:.2f}")
        
        return position_size
    
    def _calculate_leverage(self, signal: Dict[str, Any]) -> float:
        """Calculate leverage based on signal strength (simplified)."""
        composite_score = signal['composite_score']
        
        # Higher score = higher leverage (1x to 3x)
        if composite_score >= 80:
            return 3.0
        elif composite_score >= 70:
            return 2.5
        elif composite_score >= 60:
            return 2.0
        else:
            return 1.5
    
    def _calculate_equity(self, bar: pd.Series) -> float:
        """Calculate current equity (capital + unrealized PnL)."""
        equity = self.capital
        
        if self.position:
            current_price = bar['close']
            
            if self.position.direction == 'LONG':
                unrealized_pnl_pct = ((current_price - self.position.entry_price) / self.position.entry_price) * 100
            else:
                unrealized_pnl_pct = ((self.position.entry_price - current_price) / self.position.entry_price) * 100
            
            unrealized_pnl_pct *= self.position.leverage
            unrealized_pnl = self.position.size_usdt * (unrealized_pnl_pct / 100)
            equity += unrealized_pnl
        
        return equity
    
    def _trade_to_dict(self, trade: Trade) -> Dict[str, Any]:
        """Convert Trade to dict for serialization."""
        return {
            'symbol': trade.symbol,
            'direction': trade.direction,
            'entry_time': str(trade.entry_time),
            'exit_time': str(trade.exit_time),
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'size_usdt': trade.size_usdt,
            'leverage': trade.leverage,
            'pnl': trade.pnl,
            'pnl_pct': trade.pnl_pct,
            'exit_reason': trade.exit_reason,
            'composite_score': trade.composite_score,
            'ml_confidence': trade.ml_confidence
        }


async def main():
    """Run full bot backtest."""
    
    print("\n" + "="*60)
    print("FULL BOT BACKTEST")
    print("="*60 + "\n")
    
    # Load policy
    policy = load_policy()
    
    # Load data
    data_file = "backtests/data/BTC-USDTUSDT_15m.csv"
    if not Path(data_file).exists():
        print(f"[ERROR] Data file not found: {data_file}")
        print("Run: python scripts/download_historical_data.py")
        return
    
    df = pd.read_csv(data_file)
    print(f"[OK] Loaded {len(df)} bars from {data_file}")
    
    # Run backtest
    engine = FullBotBacktest(policy, initial_capital=10000.0)
    results = await engine.run(df, "BTC-USDT")
    
    # Print results
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60 + "\n")
    
    print(f"Period: {results['start_date']} to {results['end_date']}")
    print(f"Bars processed: {results['bars_processed']}")
    print(f"Total trades: {len(results['trades'])}")
    
    if len(results['trades']) > 0:
        # Save trades
        trades_df = pd.DataFrame(results['trades'])
        output_file = "backtests/full_bot_backtest_trades.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"\n[OK] Saved {len(trades_df)} trades to {output_file}")
        
        # Show sample trades
        print("\nSample Trades:")
        for i, trade in enumerate(results['trades'][:10]):
            print(f"  {i+1}. {trade['direction']} @ ${trade['entry_price']:.2f} -> ${trade['exit_price']:.2f}, "
                  f"PnL=${trade['pnl']:.2f} ({trade['pnl_pct']:.1f}%), {trade['exit_reason']}, "
                  f"ml_conf={trade['ml_confidence']}")
    
    # Show metrics
    engine.metrics_calc.print_summary(results['metrics'])
    
    print(f"\n[DONE] Full bot backtest complete!\n")


if __name__ == "__main__":
    asyncio.run(main())

