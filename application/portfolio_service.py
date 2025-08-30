"""
Portfolio service for position management.
Contains positions, exposure, PnL, and correlation lookup.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class PortfolioService:
    """Service for managing portfolio positions and analysis."""
    
    def __init__(self, exchange, cache=None, logger=None):
        self.exchange = exchange
        self.cache = cache
        self.logger = logger or logging.getLogger(__name__)
        
        # Portfolio state
        self._positions_cache = {}
        self._last_positions_update = 0
        self._cache_ttl = 30  # 30 seconds cache TTL
    
    async def get_positions(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get current positions with caching."""
        try:
            current_time = asyncio.get_event_loop().time()
            
            # Check cache validity
            if (current_time - self._last_positions_update < self._cache_ttl and 
                self._positions_cache):
                if symbols:
                    return [pos for pos in self._positions_cache if pos.get("symbol") in symbols]
                return self._positions_cache.copy()
            
            # Fetch fresh positions
            try:
                positions = await self.exchange.fetch_positions()
            except Exception as e:
                self.logger.warning(f"Failed to fetch positions from exchange: {e}")
                return []
            
            # Filter and normalize positions
            normalized_positions = []
            for pos in positions:
                if pos.get("size", 0) != 0:  # Only non-zero positions
                    normalized_pos = {
                        "symbol": pos.get("symbol"),
                        "side": pos.get("side", "unknown"),
                        "size": abs(float(pos.get("size", 0))),
                        "notional": float(pos.get("notional", 0)),
                        "unrealized_pnl": float(pos.get("unrealizedPnl", 0)),
                        "entry_price": float(pos.get("entryPrice", 0)),
                        "mark_price": float(pos.get("markPrice", 0)),
                        "leverage": float(pos.get("leverage", 1)),
                        "margin_type": pos.get("marginType", "cross"),
                        "timestamp": pos.get("timestamp", current_time)
                    }
                    normalized_positions.append(normalized_pos)
            
            # Update cache
            self._positions_cache = normalized_positions
            self._last_positions_update = current_time
            
            # Filter by symbols if requested
            if symbols:
                return [pos for pos in normalized_positions if pos.get("symbol") in symbols]
            
            return normalized_positions
            
        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            return []
    
    async def get_exposure(self) -> Dict[str, Any]:
        """Get portfolio exposure summary."""
        try:
            positions = await self.get_positions()
            
            if not positions:
                return {
                    "total_positions": 0,
                    "total_notional": 0.0,
                    "total_unrealized_pnl": 0.0,
                    "long_exposure": 0.0,
                    "short_exposure": 0.0,
                    "net_exposure": 0.0,
                    "max_leverage": 0.0
                }
            
            # Calculate exposure metrics
            total_notional = sum(pos.get("notional", 0) for pos in positions)
            total_unrealized_pnl = sum(pos.get("unrealized_pnl", 0) for pos in positions)
            
            long_positions = [pos for pos in positions if pos.get("side") == "long"]
            short_positions = [pos for pos in positions if pos.get("side") == "short"]
            
            long_exposure = sum(pos.get("notional", 0) for pos in long_positions)
            short_exposure = sum(pos.get("notional", 0) for pos in short_positions)
            net_exposure = long_exposure - short_exposure
            
            max_leverage = max((pos.get("leverage", 1) for pos in positions), default=1)
            
            return {
                "total_positions": len(positions),
                "total_notional": total_notional,
                "total_unrealized_pnl": total_unrealized_pnl,
                "long_exposure": long_exposure,
                "short_exposure": short_exposure,
                "net_exposure": net_exposure,
                "max_leverage": max_leverage,
                "long_count": len(long_positions),
                "short_count": len(short_positions)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get exposure: {e}")
            return {}
    
    async def correlation(self, symbols: List[str]) -> float:
        """Calculate correlation between symbols based on price movements."""
        try:
            if len(symbols) < 2:
                return 0.0
            
            # Get historical price data for correlation calculation
            correlations = []
            
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    symbol1, symbol2 = symbols[i], symbols[j]
                    
                    try:
                        # Get OHLCV data for both symbols
                        ohlcv1 = await self.exchange.fetch_ohlcv(symbol1, "1h", limit=100)
                        ohlcv2 = await self.exchange.fetch_ohlcv(symbol2, "1h", limit=100)
                        
                        if len(ohlcv1) < 50 or len(ohlcv2) < 50:
                            continue
                        
                        # Convert to pandas DataFrames
                        df1 = pd.DataFrame(ohlcv1, columns=["timestamp", "open", "high", "low", "close", "volume"])
                        df2 = pd.DataFrame(ohlcv2, columns=["timestamp", "open", "high", "low", "close", "volume"])
                        
                        # Calculate returns
                        returns1 = df1["close"].pct_change().dropna()
                        returns2 = df2["close"].pct_change().dropna()
                        
                        # Align series
                        min_length = min(len(returns1), len(returns2))
                        returns1 = returns1.tail(min_length)
                        returns2 = returns2.tail(min_length)
                        
                        # Calculate correlation
                        if len(returns1) > 10:  # Minimum data points
                            corr = returns1.corr(returns2)
                            if not pd.isna(corr):
                                correlations.append(corr)
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to calculate correlation for {symbol1}-{symbol2}: {e}")
                        continue
            
            if not correlations:
                return 0.0
            
            # Return average correlation
            return float(np.mean(correlations))
            
        except Exception as e:
            self.logger.error(f"Failed to calculate correlation: {e}")
            return 0.0
    
    async def get_portfolio_state(self) -> Dict[str, Any]:
        """Get complete portfolio state including positions, exposure, and risk metrics."""
        try:
            positions = await self.get_positions()
            exposure = await self.get_exposure()
            
            # Get account balance if available
            try:
                balance = await self.exchange.fetch_balance()
                total_balance = float(balance.get("total", {}).get("USDT", 0))
                free_balance = float(balance.get("free", {}).get("USDT", 0))
            except Exception:
                total_balance = 0.0
                free_balance = 0.0
            
            return {
                "positions": positions,
                "exposure": exposure,
                "balance": {
                    "total_usdt": total_balance,
                    "free_usdt": free_balance,
                    "used_margin": total_balance - free_balance
                },
                "summary": {
                    "total_positions": len(positions),
                    "total_notional": exposure.get("total_notional", 0),
                    "total_pnl": exposure.get("total_unrealized_pnl", 0),
                    "net_exposure": exposure.get("net_exposure", 0)
                },
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get portfolio state: {e}")
            return {
                "positions": [],
                "exposure": {},
                "balance": {"total_usdt": 0, "free_usdt": 0, "used_margin": 0},
                "summary": {"total_positions": 0, "total_notional": 0, "total_pnl": 0, "net_exposure": 0},
                "timestamp": asyncio.get_event_loop().time()
            }

    async def get_position_risk(self, symbol: str) -> Dict[str, Any]:
        """Get risk metrics for a specific position."""
        try:
            positions = await self.get_positions([symbol])
            if not positions:
                return {}
            
            position = positions[0]
            
            # Calculate risk metrics
            notional = position.get("notional", 0)
            unrealized_pnl = position.get("unrealized_pnl", 0)
            entry_price = position.get("entry_price", 0)
            mark_price = position.get("mark_price", 0)
            leverage = position.get("leverage", 1)
            
            # Calculate price change percentage
            if entry_price > 0:
                price_change_pct = ((mark_price - entry_price) / entry_price) * 100
            else:
                price_change_pct = 0.0
            
            # Calculate margin usage
            margin_used = notional / leverage if leverage > 0 else 0
            
            return {
                "symbol": symbol,
                "notional": notional,
                "unrealized_pnl": unrealized_pnl,
                "price_change_pct": price_change_pct,
                "margin_used": margin_used,
                "leverage": leverage,
                "side": position.get("side"),
                "size": position.get("size")
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get position risk for {symbol}: {e}")
            return {}


__all__ = ["PortfolioService"]
