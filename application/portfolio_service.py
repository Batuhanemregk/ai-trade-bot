"""
Portfolio Service - Real portfolio management with exchange integration
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from loguru import logger


class PortfolioService:
    """Real portfolio service with exchange integration."""
    
    def __init__(self, exchange_adapter=None):
        self.exchange_adapter = exchange_adapter
        self._cached_balance = None
        self._cache_timestamp = None
        self._cache_duration = 30  # Cache for 30 seconds
    
    async def get_portfolio_value(self) -> float:
        """Get total portfolio value in USDT."""
        try:
            balance = await self._get_balance()
            
            # Calculate total portfolio value
            total_value = 0.0
            
            # USDT balance
            if 'USDT' in balance:
                usdt_balance = balance['USDT']
                if isinstance(usdt_balance, dict):
                    total_value += float(usdt_balance.get('total', 0))
                else:
                    total_value += float(usdt_balance)
            
            # Convert other currencies to USDT value
            for currency, amounts in balance.items():
                if currency == 'USDT':
                    continue
                
                # Skip non-dict entries (like 'info', 'timestamp', 'free', 'used', 'total' summary keys)
                if not isinstance(amounts, dict):
                    continue
                
                total = float(amounts.get('total', 0))
                if total > 0:
                    # Get current price for this currency
                    try:
                        ticker = await self.exchange_adapter.fetch_ticker(f"{currency}/USDT")
                        price = float(ticker['last'])
                        total_value += total * price
                    except Exception as e:
                        logger.warning(f"Could not get price for {currency}: {e}")
                        # Use a conservative estimate or skip
                        continue
            
            logger.debug(f"Portfolio value: {total_value:.2f} USDT")
            return total_value
            
        except Exception as e:
            logger.error(f"Failed to get portfolio value: {e}")
            return 0.0
    
    async def get_available_balance(self) -> float:
        """Get available USDT balance for trading."""
        try:
            balance = await self._get_balance()
            
            if 'USDT' in balance:
                usdt_balance = balance['USDT']
                if isinstance(usdt_balance, dict):
                    free_balance = float(usdt_balance.get('free', 0))
                else:
                    free_balance = float(usdt_balance)
                logger.debug(f"Available USDT balance: {free_balance:.2f}")
                return free_balance
            else:
                logger.warning("No USDT balance found")
                return 0.0
                
        except Exception as e:
            logger.error(f"Failed to get available balance: {e}")
            return 0.0
    
    async def get_balance_breakdown(self) -> Dict[str, Any]:
        """Get detailed balance breakdown."""
        try:
            balance = await self._get_balance()
            
            breakdown = {
                'total_value_usdt': await self.get_portfolio_value(),
                'available_usdt': await self.get_available_balance(),
                'currencies': {}
            }
            
            # Add currency details
            for currency, amounts in balance.items():
                if isinstance(amounts, dict):
                    total = float(amounts.get('total', 0))
                    if total > 0:
                        breakdown['currencies'][currency] = {
                            'total': total,
                            'free': float(amounts.get('free', 0)),
                            'used': float(amounts.get('used', 0))
                        }
                else:
                    # Handle case where amounts is just a number
                    total = float(amounts)
                    if total > 0:
                        breakdown['currencies'][currency] = {
                            'total': total,
                            'free': total,
                            'used': 0.0
                        }
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Failed to get balance breakdown: {e}")
            return {
                'total_value_usdt': 0.0,
                'available_usdt': 0.0,
                'currencies': {}
            }
    
    async def _get_balance(self) -> Dict[str, Any]:
        """Get balance from exchange with caching."""
        import time
        
        current_time = time.time()
        
        # Check if we have valid cached data
        if (self._cached_balance and 
            self._cache_timestamp and 
            current_time - self._cache_timestamp < self._cache_duration):
            return self._cached_balance
        
        try:
            if not self.exchange_adapter:
                logger.error("No exchange adapter available")
                return {}
            
            # Fetch fresh balance from exchange
            balance = await self.exchange_adapter.fetch_balance()
            
            # Cache the result
            self._cached_balance = balance
            self._cache_timestamp = current_time
            
            logger.debug(f"Fetched fresh balance from exchange")
            return balance
            
        except Exception as e:
            logger.error(f"Failed to fetch balance from exchange: {e}")
            # Return cached data if available, otherwise empty
            return self._cached_balance or {}
    
    async def get_position_value(self, symbol: str) -> float:
        """Get current value of a specific position."""
        try:
            if not self.exchange_adapter:
                return 0.0
            
            # Get position info
            positions = await self.exchange_adapter.fetch_positions([symbol])
            
            if not positions:
                return 0.0
            
            position = positions[0]
            if float(position.get('contracts', 0)) == 0:
                return 0.0
            
            # Calculate position value
            contracts = float(position['contracts'])
            mark_price = float(position.get('markPrice', 0))
            position_value = abs(contracts * mark_price)
            
            logger.debug(f"Position value for {symbol}: {position_value:.2f} USDT")
            return position_value
            
        except Exception as e:
            logger.error(f"Failed to get position value for {symbol}: {e}")
            return 0.0
    
    async def get_total_position_value(self) -> float:
        """Get total value of all open positions."""
        try:
            if not self.exchange_adapter:
                return 0.0
            
            # Get all positions
            positions = await self.exchange_adapter.fetch_positions()
            
            total_value = 0.0
            for position in positions:
                contracts = float(position.get('contracts', 0))
                if contracts != 0:  # Only count open positions
                    mark_price = float(position.get('markPrice', 0))
                    position_value = abs(contracts * mark_price)
                    total_value += position_value
            
            logger.debug(f"Total position value: {total_value:.2f} USDT")
            return total_value
            
        except Exception as e:
            logger.error(f"Failed to get total position value: {e}")
            return 0.0
    
    def clear_cache(self):
        """Clear cached balance data."""
        self._cached_balance = None
        self._cache_timestamp = None
        logger.debug("Portfolio cache cleared")