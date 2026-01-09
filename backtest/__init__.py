"""
Backtest Module - Event-driven backtesting for ai-trade-bot.

This module provides offline backtesting capabilities using cached OHLCV data.
It reuses the production scoring pipeline (TA, ML, composite) with virtual execution.

Usage:
    python -m backtest.run --symbol BTC-USDT-SWAP --tf 15m --start 2024-07-01 --end 2025-12-26
"""

from backtest.backtest_engine import BacktestEngine
from backtest.virtual_exchange import VirtualExchangeAdapter, VirtualPosition
from backtest.data import BacktestDataLoader
from backtest.reporter import BacktestReporter

__all__ = [
    'BacktestEngine',
    'VirtualExchangeAdapter', 
    'VirtualPosition',
    'BacktestDataLoader',
    'BacktestReporter'
]
