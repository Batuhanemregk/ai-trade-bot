"""
Backtest Engine.

Main loop that processes bars and simulates trading using:
- TA Scorer (production code)
- ML Scorer (production code, if model exists)
- Composite Signal (production code)
- Signal Gate (production code)
- Virtual Exchange (backtest-only)
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path

import pandas as pd
from loguru import logger

from backtest.virtual_exchange import VirtualExchangeAdapter, IntrabarMode
from backtest.data import BacktestDataLoader
from backtest.reporter import BacktestReporter

# Import production scoring components
from scoring.ta_scorer import TAScorer
from scoring.composite_signal import CompositeSignal
from application.signal_gate import SignalGate
from application.position_state_manager import PositionStateManager
from configs.policy import load_policy


class BacktestEngine:
    """
    Event-driven backtest engine.
    
    Processes historical bars and simulates trading using production scoring logic.
    """
    
    def __init__(
        self,
        symbol: str,
        initial_balance: float = 10000.0,
        fee_bps: float = 6.0,
        slippage_bps: float = 3.0,
        intrabar_mode: str = "conservative",
        output_dir: str = "data/backtest_results/default"
    ):
        self.symbol = symbol
        self.initial_balance = initial_balance
        
        # Load policy
        self.policy = load_policy()
        
        # Virtual exchange
        mode = IntrabarMode.CONSERVATIVE if intrabar_mode == "conservative" else IntrabarMode.OPTIMISTIC
        leverage = self.policy.get('trading', {}).get('risk', {}).get('leverage', {}).get('default', 5)
        
        self.exchange = VirtualExchangeAdapter(
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            intrabar_mode=mode,
            leverage=leverage
        )
        self.exchange.set_initial_balance(initial_balance)
        
        # Data loader
        self.data_loader = BacktestDataLoader()
        
        # Reporter
        self.reporter = BacktestReporter(output_dir)
        
        # Scoring components (production code)
        self.ta_scorer = TAScorer()
        self.ml_scorer = None  # Initialized later if model exists
        self.signal_gate = SignalGate(self.policy)
        self.state_manager = PositionStateManager(self.policy)
        
        # Config
        self.scoring_config = self.policy.get('trading', {}).get('scoring', {})
        self.thresholds = self.scoring_config.get('decision_thresholds', {})
        self.enter_long = self.thresholds.get('enter_long', 54)
        self.exit_long = self.thresholds.get('exit_long', 47)
        self.enter_short = self.thresholds.get('enter_short', 43)
        self.exit_short = self.thresholds.get('exit_short', 53)
        
        # Weights
        self.ta_weight = self.scoring_config.get('ta_weight', 0.6)
        self.ml_weight = self.scoring_config.get('ml_weight', 0.3)
        
        # TP/SL config
        self.tp_sl_config = self.policy.get('trading', {}).get('risk', {}).get('tp_sl_atr', {})
        self.sl_atr_mult = self.tp_sl_config.get('sl_atr_mult', 2.0)
        self.tp_atr_mult = self.tp_sl_config.get('tp_atr_mult', 3.0)
        
        # Position sizing
        self.position_pct = 0.02  # Default 2% per trade
        
        # Data
        self.df_15m: Optional[pd.DataFrame] = None
        self.df_1h: Optional[pd.DataFrame] = None
        
        logger.info(f"[ENGINE] Initialized for {symbol}")
        logger.info(f"[ENGINE] Thresholds: enter_long={self.enter_long}, enter_short={self.enter_short}")
        logger.info(f"[ENGINE] TP/SL ATR: sl_mult={self.sl_atr_mult}, tp_mult={self.tp_atr_mult}")
    
    def _initialize_ml_scorer(self):
        """Try to initialize ML scorer if model exists."""
        try:
            from scoring.ml_scorer import MLScorer
            self.ml_scorer = MLScorer()
            
            # Check if model exists for symbol
            base_symbol = self.symbol.split('-')[0]
            model_dir = Path("models/lgbm")
            model_files = list(model_dir.glob(f"{base_symbol}*.pkl"))
            
            if not model_files:
                logger.info(f"[ENGINE] No ML model found for {base_symbol}, running TA-only mode")
                self.ml_scorer = None
            else:
                logger.info(f"[ENGINE] ML scorer initialized for {base_symbol}")
                
        except Exception as e:
            logger.warning(f"[ENGINE] ML scorer init failed: {e}, running TA-only mode")
            self.ml_scorer = None
    
    def load_data(
        self,
        start_date: datetime,
        end_date: datetime
    ):
        """Load OHLCV data for backtesting."""
        self.df_15m = self.data_loader.load_ohlcv(self.symbol, "15m", start_date, end_date)
        
        # Try to load 1h, aggregate if missing
        try:
            self.df_1h = self.data_loader.load_ohlcv(self.symbol, "1h", start_date, end_date)
        except FileNotFoundError:
            logger.info("[ENGINE] 1h data not found, aggregating from 15m")
            self.df_1h = self.data_loader._aggregate_to_1h(self.df_15m)
        
        logger.info(f"[ENGINE] Loaded {len(self.df_15m)} 15m bars, {len(self.df_1h)} 1h bars")
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR for TP/SL."""
        import numpy as np
        
        if len(df) < period + 1:
            return df['close'].iloc[-1] * 0.02  # Fallback 2%
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        
        return float(np.mean(tr[-period:]))
    
    def _compute_ta_score(self, ohlcv_slice: pd.DataFrame) -> tuple:
        """Compute TA score using production scorer."""
        try:
            score, rationale, flags = self.ta_scorer.score(ohlcv_slice, self.symbol)
            return score, rationale, flags
        except Exception as e:
            logger.warning(f"[ENGINE] TA scoring error: {e}")
            return 50.0, "ta_error", {}
    
    def _compute_ml_score(self, ohlcv_bundle: Dict[str, pd.DataFrame]) -> tuple:
        """Compute ML score using production scorer."""
        if self.ml_scorer is None:
            return None, "ml_disabled", {}
        
        try:
            score, rationale, details = self.ml_scorer.score(self.symbol, ohlcv_bundle)
            return score, rationale, details
        except Exception as e:
            logger.debug(f"[ENGINE] ML scoring error: {e}")
            return None, f"ml_error: {e}", {}
    
    def _compute_composite_score(self, ta_score: float, ml_score: Optional[float]) -> float:
        """Compute composite score with weight redistribution."""
        news_score = 50.0  # Neutral in backtest
        risk_score = 50.0  # Neutral in backtest
        
        if ml_score is None:
            # Redistribute ML weight to TA
            effective_ta_weight = self.ta_weight + self.ml_weight
            composite = (
                effective_ta_weight * ta_score +
                0.05 * news_score +  # news_weight
                0.05 * risk_score    # risk_weight
            )
        else:
            composite = (
                self.ta_weight * ta_score +
                self.ml_weight * ml_score +
                0.05 * news_score +
                0.05 * risk_score
            )
        
        return composite
    
    def _get_decision(self, composite: float, has_position: bool, position_side: str) -> str:
        """Get trading decision from composite score."""
        if not has_position:
            if composite >= self.enter_long:
                return "OPEN_LONG"
            elif composite <= self.enter_short:
                return "OPEN_SHORT"
            else:
                return "SKIP"
        else:
            if position_side == 'long':
                if composite <= self.exit_long:
                    return "CLOSE"
                elif composite <= self.enter_short:
                    return "REVERSE_TO_SHORT"
                else:
                    return "HOLD"
            else:  # short
                if composite >= self.exit_short:
                    return "CLOSE"
                elif composite >= self.enter_long:
                    return "REVERSE_TO_LONG"
                else:
                    return "HOLD"
    
    def _calculate_position_size(self, composite: float) -> float:
        """Calculate position size based on signal strength."""
        strength = abs(composite - 50) / 50
        
        # Tier-based sizing
        if strength < 0.3:
            pct = 0.02  # weak
        elif strength < 0.5:
            pct = 0.04  # medium
        elif strength < 0.7:
            pct = 0.06  # strong
        else:
            pct = 0.08  # extreme
        
        return self.exchange.balance * pct
    
    def _calculate_tp_sl(self, entry_price: float, side: str, atr: float) -> tuple:
        """Calculate TP/SL prices."""
        if side == 'long':
            sl_price = entry_price - (self.sl_atr_mult * atr)
            tp_price = entry_price + (self.tp_atr_mult * atr)
        else:
            sl_price = entry_price + (self.sl_atr_mult * atr)
            tp_price = entry_price - (self.tp_atr_mult * atr)
        
        return tp_price, sl_price
    
    async def run(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Run backtest on historical data.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Summary dict
        """
        logger.info(f"[ENGINE] Starting backtest for {self.symbol}")
        logger.info(f"[ENGINE] Period: {start_date} to {end_date}")
        
        # Initialize ML scorer
        self._initialize_ml_scorer()
        
        # Load data
        self.load_data(start_date, end_date)
        
        if self.df_15m.empty:
            logger.error("[ENGINE] No data loaded")
            return {}
        
        # Minimum lookback for indicators
        min_lookback = 50
        total_bars = len(self.df_15m)
        
        logger.info(f"[ENGINE] Processing {total_bars - min_lookback} bars...")
        
        # Main loop
        for i in range(min_lookback, total_bars):
            bar = self.df_15m.iloc[i]
            bar_time = self.df_15m.index[i]
            
            # Set bar context
            self.exchange.set_bar_context(i, bar_time)
            
            # Get OHLCV slices
            ohlcv_bundle = self.data_loader.get_multi_timeframe_slice(
                self.symbol, i, self.df_15m, self.df_1h
            )
            
            main_df = ohlcv_bundle.get('main')
            if main_df is None or main_df.empty:
                continue
            
            current_price = bar['close']
            
            # Check TP/SL first
            position = self.exchange.get_position(self.symbol)
            if position:
                exit_reason = self.exchange.check_tpsl_hit(
                    self.symbol, bar['high'], bar['low'], bar['close']
                )
                if exit_reason:
                    # Use TP or SL price
                    if exit_reason == 'TP_HIT':
                        exit_price = position.tp_price
                    else:
                        exit_price = position.sl_price
                    
                    self.exchange.close_position(self.symbol, exit_price, exit_reason)
                    
                    self.reporter.record_decision(
                        timestamp=bar_time,
                        symbol=self.symbol,
                        ta_score=0, ml_score=0, news_score=50, risk_score=50, final_score=0,
                        decision=exit_reason,
                        skip_reason="",
                        has_position=False,
                        position_side=None
                    )
                    
                    # Record equity after close
                    self.exchange.record_equity({self.symbol: current_price})
                    continue
            
            # Compute scores
            ta_score, ta_rationale, ta_flags = self._compute_ta_score(main_df)
            ml_score, ml_rationale, ml_details = self._compute_ml_score(ohlcv_bundle)
            composite = self._compute_composite_score(ta_score, ml_score)
            
            # Get position state
            has_position = self.exchange.has_position(self.symbol)
            position_side = position.side if position else None
            
            # Get decision
            decision = self._get_decision(composite, has_position, position_side)
            
            skip_reason = ""
            
            # Execute decision
            if decision == "OPEN_LONG":
                atr = self._calculate_atr(main_df)
                size = self._calculate_position_size(composite)
                tp, sl = self._calculate_tp_sl(current_price, 'long', atr)
                
                self.exchange.open_position(
                    self.symbol, 'long', size, current_price, tp, sl
                )
                
            elif decision == "OPEN_SHORT":
                atr = self._calculate_atr(main_df)
                size = self._calculate_position_size(composite)
                tp, sl = self._calculate_tp_sl(current_price, 'short', atr)
                
                self.exchange.open_position(
                    self.symbol, 'short', size, current_price, tp, sl
                )
                
            elif decision == "CLOSE":
                self.exchange.close_position(self.symbol, current_price, "SIGNAL_EXIT")
                
            elif decision in ["REVERSE_TO_LONG", "REVERSE_TO_SHORT"]:
                self.exchange.close_position(self.symbol, current_price, "REVERSAL")
                
                new_side = 'long' if decision == "REVERSE_TO_LONG" else 'short'
                atr = self._calculate_atr(main_df)
                size = self._calculate_position_size(composite)
                tp, sl = self._calculate_tp_sl(current_price, new_side, atr)
                
                self.exchange.open_position(
                    self.symbol, new_side, size, current_price, tp, sl
                )
                
            elif decision == "SKIP":
                # Determine skip reason
                if composite > self.enter_short and composite < self.enter_long:
                    skip_reason = "neutral_zone"
                else:
                    skip_reason = "threshold_not_met"
            
            elif decision == "HOLD":
                skip_reason = "holding_position"
            
            # Record decision
            self.reporter.record_decision(
                timestamp=bar_time,
                symbol=self.symbol,
                ta_score=ta_score,
                ml_score=ml_score if ml_score else 0,
                news_score=50,
                risk_score=50,
                final_score=composite,
                decision=decision,
                skip_reason=skip_reason,
                has_position=has_position,
                position_side=position_side
            )
            
            # Record equity
            self.exchange.record_equity({self.symbol: current_price})
            
            # Progress log
            if i % 500 == 0:
                logger.info(f"[ENGINE] Progress: {i}/{total_bars} bars | "
                           f"Trades: {len(self.exchange.trades)} | "
                           f"Balance: ${self.exchange.balance:.2f}")
        
        # Close any remaining position
        if self.exchange.has_position(self.symbol):
            final_price = self.df_15m['close'].iloc[-1]
            self.exchange.close_position(self.symbol, final_price, "END_OF_DATA")
        
        # Generate reports
        trades = self.exchange.get_trades()
        equity_curve = self.exchange.get_equity_curve()
        
        summary = self.reporter.save_all(
            trades=trades,
            initial_balance=self.initial_balance,
            final_balance=self.exchange.balance,
            symbol=self.symbol,
            start_date=start_date,
            end_date=end_date,
            equity_curve=equity_curve
        )
        
        logger.info(f"[ENGINE] Backtest complete: {len(trades)} trades")
        
        return summary


# Synchronous wrapper for CLI
def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    initial_balance: float = 10000.0,
    fee_bps: float = 6.0,
    slippage_bps: float = 3.0,
    intrabar_mode: str = "conservative",
    output_dir: str = "data/backtest_results/default"
) -> Dict[str, Any]:
    """Run backtest synchronously."""
    engine = BacktestEngine(
        symbol=symbol,
        initial_balance=initial_balance,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        intrabar_mode=intrabar_mode,
        output_dir=output_dir
    )
    
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)
    
    return asyncio.run(engine.run(start_dt, end_dt))
