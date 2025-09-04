"""
Market Overview Job (15m)
Handles market health overview and symbol basket analysis
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from loguru import logger

from .base_job import BaseJob


class MarketOverviewJob(BaseJob):
    """15-minute market overview job for general market health."""
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.exchange_adapter = None
        self.market_metrics = {}
        
    async def initialize(self):
        """Initialize market overview components."""
        try:
            # Initialize exchange adapter
            from adapters.exchange_okx_ccxt import OKXCCXTAdapter
            self.exchange_adapter = OKXCCXTAdapter()
            
            logger.info("✅ MarketOverviewJob initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MarketOverviewJob: {e}")
            raise
    
    async def execute(self):
        """Execute 15-minute market overview."""
        try:
            logger.info("[JOB] market_overview starting execution")
            
            symbols = self.get_all_symbols()
            logger.info(f"[MARKET] Analyzing {len(symbols)} symbols for market overview")
            
            # Process symbols in batches
            batch_size = self.get_risk_config('batch_size')
            processed_count = 0
            
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                await self._process_symbol_batch(batch)
                processed_count += len(batch)
                
                # Small delay between batches to avoid rate limits
                if i + batch_size < len(symbols):
                    await asyncio.sleep(1)
            
            # Generate market summary
            await self._generate_market_summary()
            
            logger.info(f"[JOB] market_overview completed {processed_count}/{len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"❌ MarketOverviewJob execution failed: {e}")
            raise
    
    async def _process_symbol_batch(self, symbols: List[str]):
        """Process a batch of symbols for market overview."""
        try:
            for symbol in symbols:
                try:
                    await self._analyze_symbol_health(symbol)
                except Exception as e:
                    logger.error(f"❌ Failed to analyze {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"❌ Failed to process symbol batch: {e}")
    
    async def _analyze_symbol_health(self, symbol: str):
        """Analyze health metrics for a single symbol."""
        try:
            # Get ticker data
            ticker = await self.exchange_adapter.fetch_ticker(symbol)
            
            # Get order book for liquidity analysis
            order_book = await self.exchange_adapter.fetch_order_book(symbol, limit=20)
            
            # Calculate metrics
            metrics = {
                'symbol': symbol,
                'price': float(ticker['last']),
                'volume_24h': float(ticker.get('baseVolume', 0)),
                'price_change_24h': float(ticker.get('change', 0)),
                'bid_ask_spread': self._calculate_spread(order_book),
                'liquidity_score': self._calculate_liquidity_score(order_book),
                'volatility_score': self._calculate_volatility_score(ticker),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Store metrics
            self.market_metrics[symbol] = metrics
            
            # Log significant findings
            if metrics['bid_ask_spread'] > 0.01:  # 1% spread
                logger.warning(f"[MARKET] {symbol} high spread: {metrics['bid_ask_spread']:.3f}%")
            
            if metrics['liquidity_score'] < 0.5:
                logger.warning(f"[MARKET] {symbol} low liquidity: {metrics['liquidity_score']:.2f}")
            
            logger.debug(f"[MARKET] {symbol} health: spread={metrics['bid_ask_spread']:.3f}%, liquidity={metrics['liquidity_score']:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze symbol health for {symbol}: {e}")
    
    def _calculate_spread(self, order_book: Dict[str, Any]) -> float:
        """Calculate bid-ask spread percentage."""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            
            if best_bid == 0:
                return 0.0
            
            spread = (best_ask - best_bid) / best_bid * 100
            return spread
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate spread: {e}")
            return 0.0
    
    def _calculate_liquidity_score(self, order_book: Dict[str, Any]) -> float:
        """Calculate liquidity score (0-1, higher is better)."""
        try:
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            # Calculate total volume within 1% of mid price
            mid_price = (float(bids[0][0]) + float(asks[0][0])) / 2
            price_range = mid_price * 0.01  # 1% range
            
            bid_volume = 0.0
            ask_volume = 0.0
            
            for bid in bids:
                price = float(bid[0])
                volume = float(bid[1])
                if price >= mid_price - price_range:
                    bid_volume += volume * price
                else:
                    break
            
            for ask in asks:
                price = float(ask[0])
                volume = float(ask[1])
                if price <= mid_price + price_range:
                    ask_volume += volume * price
                else:
                    break
            
            # Normalize liquidity score (0-1)
            total_liquidity = bid_volume + ask_volume
            if total_liquidity > 100000:  # $100k+ liquidity
                return 1.0
            elif total_liquidity > 10000:  # $10k+ liquidity
                return 0.8
            elif total_liquidity > 1000:   # $1k+ liquidity
                return 0.6
            elif total_liquidity > 100:    # $100+ liquidity
                return 0.4
            else:
                return 0.2
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate liquidity score: {e}")
            return 0.0
    
    def _calculate_volatility_score(self, ticker: Dict[str, Any]) -> float:
        """Calculate volatility score (0-1, higher is more volatile)."""
        try:
            high_24h = float(ticker.get('high', 0))
            low_24h = float(ticker.get('low', 0))
            current_price = float(ticker['last'])
            
            if current_price == 0:
                return 0.0
            
            # Calculate 24h price range
            price_range = (high_24h - low_24h) / current_price
            
            # Normalize to 0-1 scale
            if price_range > 0.2:    # 20%+ range
                return 1.0
            elif price_range > 0.1:  # 10%+ range
                return 0.8
            elif price_range > 0.05: # 5%+ range
                return 0.6
            elif price_range > 0.02: # 2%+ range
                return 0.4
            else:
                return 0.2
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate volatility score: {e}")
            return 0.0
    
    async def _generate_market_summary(self):
        """Generate overall market summary."""
        try:
            if not self.market_metrics:
                logger.info("[MARKET] No market data available for summary")
                return
            
            # Calculate aggregate metrics
            total_symbols = len(self.market_metrics)
            avg_spread = sum(m['bid_ask_spread'] for m in self.market_metrics.values()) / total_symbols
            avg_liquidity = sum(m['liquidity_score'] for m in self.market_metrics.values()) / total_symbols
            avg_volatility = sum(m['volatility_score'] for m in self.market_metrics.values()) / total_symbols
            
            # Count symbols by health category
            healthy_symbols = sum(1 for m in self.market_metrics.values() 
                                if m['bid_ask_spread'] < 0.005 and m['liquidity_score'] > 0.7)
            warning_symbols = sum(1 for m in self.market_metrics.values() 
                                if m['bid_ask_spread'] > 0.01 or m['liquidity_score'] < 0.5)
            
            # Log market summary
            logger.info(f"[MARKET] Summary: {total_symbols} symbols analyzed")
            logger.info(f"[MARKET] Avg spread: {avg_spread:.3f}%, Avg liquidity: {avg_liquidity:.2f}, Avg volatility: {avg_volatility:.2f}")
            logger.info(f"[MARKET] Healthy: {healthy_symbols}, Warnings: {warning_symbols}")
            
            # Log top performers
            top_liquidity = sorted(self.market_metrics.values(), key=lambda x: x['liquidity_score'], reverse=True)[:3]
            logger.info(f"[MARKET] Top liquidity: {', '.join(f'{m['symbol']}({m['liquidity_score']:.2f})' for m in top_liquidity)}")
            
            # Log warnings
            if warning_symbols > 0:
                warning_list = [m['symbol'] for m in self.market_metrics.values() 
                              if m['bid_ask_spread'] > 0.01 or m['liquidity_score'] < 0.5]
                logger.warning(f"[MARKET] Symbols with warnings: {', '.join(warning_list)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate market summary: {e}")
    
    def get_market_metrics(self) -> Dict[str, Any]:
        """Get current market metrics."""
        return self.market_metrics
