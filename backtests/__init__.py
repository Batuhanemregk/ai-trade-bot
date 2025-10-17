"""
Backtest framework for AiBotBS trading strategies.

This module provides tools for backtesting trading strategies using historical data.
"""

from backtests.engine import BacktestEngine
from backtests.data_loader import OHLCVDataLoader
from backtests.metrics import PerformanceMetrics
from backtests.visualizer import EquityCurveVisualizer

__all__ = [
    'BacktestEngine',
    'OHLCVDataLoader',
    'PerformanceMetrics',
    'EquityCurveVisualizer',
]

