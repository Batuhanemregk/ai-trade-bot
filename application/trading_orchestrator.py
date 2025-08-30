"""
Trading Orchestrator - Main coordinator for the trading system.
Follows Single Responsibility Principle by only handling coordination.
"""

import asyncio
import signal
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from domain.models import TradingConfig, TradingState
from domain.events import EventType, EventPriority, TradeSignalEvent, PositionUpdateEvent, RiskAlertEvent, PortfolioUpdateEvent
from domain.strategies import StrategyRegistry, CompositeStrategy
from infrastructure.scheduler import Scheduler
from infrastructure.event_bus import AsyncEventBus, EventPublisherImpl
from application.risk_service import RiskService
from application.trade_service import TradeService
from application.portfolio_service import PortfolioService
from adapters.exchange_okx_ccxt import OKXExchangeAdapter
from adapters.exchange_okx_rest import OKXRESTAdapter
from telegram_bot.bot import TelegramBot


class TradingOrchestrator:
    """
    Main trading orchestrator that coordinates all trading components.
    
    Responsibilities:
    - Initialize and coordinate all trading components
    - Manage the main trading loop
    - Handle graceful shutdown
    - Coordinate between different services
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Initialize services
        self.scheduler = Scheduler()
        
        # Initialize exchange adapters with environment variables
        import os
        exchange_config = {
            'api_key': os.getenv('OKX_API_KEY'),
            'secret': os.getenv('OKX_API_SECRET'),
            'passphrase': os.getenv('OKX_API_PASSPHRASE'),
            'sandbox': os.getenv('OKX_SANDBOX', 'false').lower() == 'true',
            'testnet': os.getenv('OKX_TESTNET', 'false').lower() == 'true',
            'mode': os.getenv('OKX_MODE', 'live')
        }
        self.okx_ccxt = OKXExchangeAdapter(exchange_config)
        self.okx_rest = OKXRESTAdapter(exchange_config)
        
        # Initialize telegram bot with config
        telegram_config = getattr(config, 'telegram', {}) if hasattr(config, 'telegram') else config.get('telegram', {})
        if telegram_config.get('enabled', False):
            self.telegram_bot = TelegramBot(telegram_config.get('token', 'mock_token'))
        else:
            self.telegram_bot = None
        
        # Initialize services with config
        trading_config = getattr(config, 'trading', {}) if hasattr(config, 'trading') else config.get('trading', {})
        risk_config = trading_config.get('risk', {}) if isinstance(trading_config, dict) else {}
        self.risk_service = RiskService(risk_config)
        self.portfolio_service = PortfolioService(self.okx_ccxt)
        self.trade_service = TradeService(self.okx_ccxt, config, self.risk_service)
        
        # Initialize event system
        self.event_bus = AsyncEventBus()
        self.event_publisher = EventPublisherImpl(self.event_bus)
        
        # Initialize strategy registry
        self.strategy_registry = StrategyRegistry()
        self._setup_strategies()
        
        # Trading state
        self.trading_state = TradingState()
        self.start_time = datetime.now()
        
        # Performance tracking
        self.total_signals = 0
        self.successful_trades = 0
        
        logger.info("Trading Orchestrator initialized with Clean Architecture components")
    
    def _setup_strategies(self):
        """Setup and register trading strategies."""
        try:
            # Real trading strategies will be loaded from config
            # For now, just log that we're ready for real trading
            logger.info("Trading strategies ready - will load from config during runtime")
            
        except Exception as e:
            logger.error(f"Failed to setup strategies: {e}")
    
    async def start(self) -> bool:
        """Start the trading orchestrator."""
        try:
            logger.info("Starting Trading Orchestrator...")
            
            # Test connections
            if not await self._test_connections():
                logger.error("Failed to establish connections")
                return False
            
            # Initialize components
            await self._initialize_components()
            
            # Set up signal handlers
            self._setup_signal_handlers()
            
            # Start main loop
            self.running = True
            logger.info("Trading Orchestrator started successfully")
            
            # Send startup notification
            await self._send_startup_notification()
            
            # Publish system started event
            await self._publish_system_event("started")
            
            # Start event bus
            await self.event_bus.start()
            
            # Start scheduler
            await self.scheduler.start()
            
            # Start main trading loop
            await self._main_loop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start trading orchestrator: {e}")
            await self._send_error_notification("Startup Failed", str(e))
            return False
    
    async def stop(self):
        """Stop the trading orchestrator gracefully."""
        logger.info("Stopping trading orchestrator...")
        self.running = False
        self.shutdown_event.set()
        
        # Close all positions if in live mode
        dry_run = getattr(self.config, 'dry_run', True) if hasattr(self.config, 'dry_run') else self.config.get('dry_run', True)
        if not dry_run:
            await self.risk_service.close_all_positions("orchestrator_shutdown")
            await self._send_notification(
                "Orchestrator Shutdown",
                "All positions closed due to orchestrator shutdown",
                "warning"
            )
        
                    # Stop event bus
            await self.event_bus.stop()
            
            # Close connections
            await self._cleanup()
        
        logger.info("Trading orchestrator stopped")
        
        # Publish system stopped event
        await self._publish_system_event("stopped")
    
    async def _test_connections(self) -> bool:
        """Test all external connections."""
        try:
            # Test OKX connection
            if not await self.okx_ccxt.test_connection():
                logger.error("OKX connection test failed")
                return False
            
            # Test Telegram connection
            if self.telegram_bot:
                await self.telegram_bot.send_message("🔄 Testing Telegram connection...")
            else:
                logger.info("Telegram bot disabled, skipping connection test")
            
            logger.info("All connections tested successfully")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def _initialize_components(self):
        """Initialize all trading components."""
        try:
            # Initialize Telegram client
            if self.telegram_bot:
                try:
                    # Start Telegram bot first
                    await self.telegram_bot.start()
                    # Then initialize
                    await self.telegram_bot.initialize()
                    logger.info("Telegram client started and initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize Telegram client: {e}")
            else:
                logger.info("Telegram bot disabled, skipping initialization")
            
            # Load existing state
            await self._load_trading_state()
            
            # Reset daily metrics if it's a new day
            await self._check_daily_reset()
            
            logger.info("All components initialized")
            
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise
    
    async def _load_trading_state(self):
        """Load trading state from persistent storage."""
        try:
            # Load portfolio state
            portfolio = await self.portfolio_service.get_portfolio_state()
            if portfolio:
                self.trading_state.portfolio = portfolio
                logger.info("Portfolio state loaded successfully")
            
            # Load positions
            positions = await self.portfolio_service.get_positions()
            if positions:
                self.trading_state.positions = positions
                logger.info(f"Loaded {len(positions)} existing positions")
            
        except Exception as e:
            logger.error(f"Failed to load trading state: {e}")
    
    async def _check_daily_reset(self):
        """Check if daily metrics should be reset."""
        try:
            if self.trading_state.should_reset_daily():
                logger.info("New day detected, resetting daily metrics")
                await self.risk_service.reset_daily_metrics()
                
                await self._send_notification(
                    "Daily Reset",
                    "Daily trading metrics have been reset",
                    "info"
                )
                
        except Exception as e:
            logger.error(f"Daily reset check failed: {e}")
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.stop())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _main_loop(self):
        """Main trading loop."""
        logger.info("Entering main trading loop")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._analysis_loop()),
            asyncio.create_task(self._position_monitoring_loop()),
            asyncio.create_task(self._portfolio_update_loop()),
            asyncio.create_task(self._risk_monitoring_loop())
        ]
        
        try:
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            await self._send_error_notification("Main Loop Error", str(e))
            
        finally:
            # Cancel all background tasks
            for task in tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _analysis_loop(self):
        """Main analysis loop for generating trading signals."""
        while self.running and not self.shutdown_event.is_set():
            try:
                # Get symbols from config
                symbols = getattr(self.config, 'symbols', []) or self.config.get('symbols', [])
                if not symbols:
                    symbols = self.config.get('exchange', {}).get('symbols', {}).get('trading_pairs', [])
                
                # Analyze each symbol
                for symbol in symbols:
                    try:
                        # Get market data
                        ohlcv = await self.okx_ccxt.fetch_ohlcv(symbol, '1h', limit=100)
                        if not ohlcv or len(ohlcv) < 50:
                            continue
                        
                        # Simple technical analysis (RSI, MACD)
                        signal = await self._analyze_symbol(symbol, ohlcv)
                        
                        if signal and signal['score'] > 0.6:  # Minimum score threshold
                            await self._execute_trade_signal(symbol, signal)
                            
                    except Exception as e:
                        logger.warning(f"Failed to analyze {symbol}: {e}")
                        continue
                
                # Wait for next analysis cycle
                analysis_interval = getattr(self.config, 'analysis_interval', 300) or self.config.get('analysis_interval', 300)
                await asyncio.sleep(analysis_interval)
                
            except Exception as e:
                logger.error(f"Analysis loop error: {e}")
                await asyncio.sleep(10)
    
    async def _position_monitoring_loop(self):
        """Monitor active positions and update PnL."""
        while self.running and not self.shutdown_event.is_set():
            try:
                # Position monitoring logic will be moved to PositionMonitor
                position_interval = getattr(self.config, 'position_update_interval', 60) or self.config.get('position_update_interval', 60)
                await asyncio.sleep(position_interval)
                
            except Exception as e:
                logger.error(f"Position monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _portfolio_update_loop(self):
        """Update portfolio information."""
        while self.running and not self.shutdown_event.is_set():
            try:
                # Portfolio update logic will be moved to PortfolioManager
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Portfolio update error: {e}")
                await asyncio.sleep(60)
    
    async def _risk_monitoring_loop(self):
        """Monitor risk metrics and send alerts."""
        while self.running and not self.shutdown_event.is_set():
            try:
                # Risk monitoring logic will be moved to RiskMonitor
                await asyncio.sleep(120)
                
            except Exception as e:
                logger.error(f"Risk monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _send_startup_notification(self):
        """Send startup notification."""
        dry_run = getattr(self.config, 'dry_run', True) if hasattr(self.config, 'dry_run') else self.config.get('dry_run', True)
        paper_trading = getattr(self.config, 'paper_trading', True) if hasattr(self.config, 'paper_trading') else self.config.get('paper_trading', True)
        symbols = getattr(self.config, 'symbols', []) if hasattr(self.config, 'symbols') else self.config.get('symbols', [])
        
        await self._send_notification(
            "Orchestrator Started",
            f"Trading Orchestrator is now running\n"
            f"Mode: {'🟢 LIVE' if not dry_run else '🟡 DRY RUN'}\n"
            f"Paper Trading: {'Yes' if paper_trading else 'No'}\n"
            f"Symbols: {len(symbols)} coins\n"
            f"Monitoring: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}",
            "success"
        )
    
    async def _analyze_symbol(self, symbol: str, ohlcv: list) -> dict:
        """Analyze symbol and generate trading signal."""
        try:
            if len(ohlcv) < 50:
                return None
            
            # Extract close prices
            closes = [float(candle[4]) for candle in ohlcv]
            
            # Calculate RSI
            rsi = self._calculate_rsi(closes, 14)
            
            # Calculate MACD
            macd, signal = self._calculate_macd(closes)
            
            # Generate signal
            signal_strength = 0.0
            side = "flat"
            
            if rsi < 30 and macd > signal:  # Oversold + bullish MACD
                signal_strength = 0.8
                side = "long"
            elif rsi > 70 and macd < signal:  # Overbought + bearish MACD
                signal_strength = 0.8
                side = "short"
            elif rsi < 40 and macd > signal:  # Slightly oversold
                signal_strength = 0.6
                side = "long"
            elif rsi > 60 and macd < signal:  # Slightly overbought
                signal_strength = 0.6
                side = "short"
            
            if signal_strength > 0:
                return {
                    "symbol": symbol,
                    "side": side,
                    "score": signal_strength,
                    "rsi": rsi,
                    "macd": macd,
                    "signal": signal,
                    "timestamp": asyncio.get_event_loop().time()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to analyze {symbol}: {e}")
            return None
    
    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """Calculate RSI indicator."""
        try:
            if len(prices) < period + 1:
                return 50.0
            
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            gains = [d if d > 0 else 0 for d in deltas]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception:
            return 50.0
    
    def _calculate_macd(self, prices: list, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD indicator."""
        try:
            if len(prices) < slow:
                return 0.0, 0.0
            
            # Calculate EMAs
            ema_fast = self._calculate_ema(prices, fast)
            ema_slow = self._calculate_ema(prices, slow)
            
            macd_line = ema_fast - ema_slow
            signal_line = self._calculate_ema([macd_line], signal)
            
            return macd_line, signal_line
            
        except Exception:
            return 0.0, 0.0
    
    def _calculate_ema(self, prices: list, period: int) -> float:
        """Calculate Exponential Moving Average."""
        try:
            if len(prices) < period:
                return prices[-1] if prices else 0.0
            
            multiplier = 2 / (period + 1)
            ema = prices[0]
            
            for price in prices[1:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return ema
            
        except Exception:
            return prices[-1] if prices else 0.0
    
    async def _execute_trade_signal(self, symbol: str, signal: dict):
        """Execute trading signal."""
        try:
            # Check if we already have a position
            positions = await self.portfolio_service.get_positions([symbol])
            if positions:
                logger.info(f"Already have position in {symbol}, skipping signal")
                return
            
            # Get account balance
            balance = await self.okx_ccxt.fetch_balance()
            usdt_balance = float(balance.get('free', {}).get('USDT', 0))
            
            if usdt_balance < 10:  # Minimum $10
                logger.warning(f"Insufficient USDT balance: {usdt_balance}")
                return
            
            # Calculate position size (1% of balance)
            position_size = usdt_balance * 0.01
            
            # Execute trade
            if signal['side'] == 'long':
                order = await self.okx_ccxt.create_market_buy_order(symbol, position_size)
                logger.info(f"LONG signal executed for {symbol}: {order}")
                
                # Send Telegram notification
                await self._send_notification(
                    "🟢 LONG Signal Executed",
                    f"Symbol: {symbol}\n"
                    f"Score: {signal['score']:.2f}\n"
                    f"RSI: {signal['rsi']:.1f}\n"
                    f"MACD: {signal['macd']:.4f}\n"
                    f"Amount: ${position_size:.2f}",
                    "success"
                )
                
            elif signal['side'] == 'short':
                order = await self.okx_ccxt.create_market_sell_order(symbol, position_size)
                logger.info(f"SHORT signal executed for {symbol}: {order}")
                
                # Send Telegram notification
                await self._send_notification(
                    "🔴 SHORT Signal Executed",
                    f"Symbol: {symbol}\n"
                    f"Score: {signal['score']:.2f}\n"
                    f"RSI: {signal['rsi']:.1f}\n"
                    f"MACD: {signal['macd']:.4f}\n"
                    f"Amount: ${position_size:.2f}",
                    "success"
                )
            
            self.total_signals += 1
            
        except Exception as e:
            logger.error(f"Failed to execute trade signal for {symbol}: {e}")
            await self._send_error_notification("Trade Execution Failed", f"{symbol}: {e}")
    
    async def _send_notification(self, title: str, message: str, level: str = "info"):
        """Send notification through Telegram."""
        if not self.telegram_bot:
            logger.info(f"Telegram notification (skipped): {title} - {message}")
            return
        
        try:
            await self.telegram_bot.send_notification(title, message, level)
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    async def _send_error_notification(self, title: str, message: str):
        """Send error notification."""
        await self._send_notification(title, message, "error")
    
    async def _cleanup(self):
        """Clean up resources."""
        try:
            await self.scheduler.stop()
            await self.event_bus.stop()
            await self.okx_ccxt.close()
            await self.telegram_bot.close()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        symbols = getattr(self.config, 'symbols', []) if hasattr(self.config, 'symbols') else self.config.get('symbols', [])
        dry_run = getattr(self.config, 'dry_run', True) if hasattr(self.config, 'dry_run') else self.config.get('dry_run', True)
        paper_trading = getattr(self.config, 'paper_trading', True) if hasattr(self.config, 'paper_trading') else self.config.get('paper_trading', True)
        default_timeframe = getattr(self.config, 'default_timeframe', '1h') if hasattr(self.config, 'default_timeframe') else self.config.get('default_timeframe', '1h')
        
        return {
            "running": self.running,
            "uptime": (datetime.now() - self.start_time).total_seconds(),
            "total_signals": self.total_signals,
            "successful_trades": self.successful_trades,
            "symbols_count": len(symbols),
            "symbols": symbols,
            "config": {
                "dry_run": dry_run,
                "paper_trading": paper_trading,
                "timeframe": default_timeframe
            },
            "event_bus_status": self.event_bus.get_queue_status(),
            "strategy_registry": self.strategy_registry.get_registry_summary()
        }
    
    async def _publish_system_event(self, event_type: str):
        """Publish system event."""
        try:
            from domain.events import Event, EventType, EventPriority
            
            event = Event(
                type=EventType.SYSTEM_STATUS,
                priority=EventPriority.INFO,
                source="trading_orchestrator",
                data={"event_type": event_type, "timestamp": datetime.now().isoformat()},
                metadata={"orchestrator_status": self.get_status()}
            )
            
            await self.event_publisher.publish_event(event)
            logger.debug(f"Published system event: {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish system event: {e}")
    
    async def _publish_trading_signal(self, symbol: str, side: str, score: float, confidence: float):
        """Publish trading signal event."""
        try:
            event = TradeSignalEvent(
                symbol=symbol,
                side=side,
                score=score,
                confidence=confidence,
                priority=EventPriority.MEDIUM,
                source="trading_orchestrator",
                metadata={"strategy": "composite_trading"}
            )
            
            await self.event_publisher.publish_event(event)
            logger.debug(f"Published trading signal: {symbol} {side}")
            
        except Exception as e:
            logger.error(f"Failed to publish trading signal: {e}")
    
    async def _publish_position_update(self, symbol: str, side: str, size: float, price: float, pnl: float):
        """Publish position update event."""
        try:
            event = PositionUpdateEvent(
                symbol=symbol,
                side=side,
                size=size,
                price=price,
                pnl=pnl,
                priority=EventPriority.LOW,
                source="trading_orchestrator"
            )
            
            await self.event_publisher.publish_event(event)
            logger.debug(f"Published position update: {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to publish position update: {e}")
    
    async def _publish_risk_alert(self, risk_level: str, risk_factors: List[str], recommendations: List[str]):
        """Publish risk alert event."""
        try:
            event = RiskAlertEvent(
                risk_level=risk_level,
                risk_factors=risk_factors,
                recommendations=recommendations,
                priority=EventPriority.HIGH if risk_level == "high" else EventPriority.MEDIUM,
                source="trading_orchestrator"
            )
            
            await self.event_publisher.publish_event(event)
            logger.debug(f"Published risk alert: {risk_level}")
            
        except Exception as e:
            logger.error(f"Failed to publish risk alert: {e}")
    
    async def _publish_portfolio_update(self, portfolio_data: Dict[str, Any]):
        """Publish portfolio update event."""
        try:
            event = PortfolioUpdateEvent(
                total_balance=portfolio_data.get("total_balance", 0),
                total_pnl=portfolio_data.get("total_pnl", 0),
                position_count=portfolio_data.get("position_count", 0),
                exposure_ratio=portfolio_data.get("exposure_ratio", 0),
                priority=EventPriority.LOW,
                source="trading_orchestrator"
            )
            
            await self.event_publisher.publish_event(event)
            logger.debug("Published portfolio update")
            
        except Exception as e:
            logger.error(f"Failed to publish portfolio update: {e}")
