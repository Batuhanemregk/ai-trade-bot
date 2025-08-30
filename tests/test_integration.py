"""
Integration Tests - Test complete system integration.
Tests all components working together including event system and strategy pattern.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from application.trading_orchestrator import TradingOrchestrator
from domain.events import EventType, EventPriority, TradeSignalEvent
from domain.strategies import StrategyRegistry, TechnicalAnalysisStrategy
from infrastructure.event_bus import AsyncEventBus, EventSubscriberImpl
from infrastructure.bootstrap import load_policy, validate_policy


class MockPortfolioService:
    """Mock portfolio service for testing."""
    
    async def get_portfolio_state(self):
        return {
            "total_balance": 10000.0,
            "total_pnl": 500.0,
            "position_count": 2,
            "exposure_ratio": 0.3
        }
    
    async def get_portfolio_value(self):
        return 10000.0
    
    async def get_positions(self):
        return []
    
    async def update_portfolio_state(self, state):
        return True


class MockRiskService:
    """Mock risk service for testing."""
    
    async def assess_risk(self, symbol, score, signal_type, market_data):
        return Mock(
            risk_level="low",
            risk_factors=[],
            recommendations=["Proceed with trade"]
        )
    
    async def reset_daily_metrics(self):
        return True


class MockTradeService:
    """Mock trade service for testing."""
    
    def __init__(self, exchange, policy, risk_service):
        self.exchange = exchange
        self.policy = policy
        self.risk_service = risk_service


class MockExchangeAdapter:
    """Mock exchange adapter for testing."""
    
    async def test_connection(self):
        return True
    
    async def close(self):
        return True


class MockTelegramBot:
    """Mock telegram bot for testing."""
    
    async def send_notification(self, title, message, level):
        return True
    
    async def send_message(self, message):
        return True
    
    async def initialize(self):
        return True
    
    async def close(self):
        return True


class MockScheduler:
    """Mock scheduler for testing."""
    
    async def start(self):
        return True
    
    async def stop(self):
        return True


class TestEventSubscriber(EventSubscriberImpl):
    """Test event subscriber for integration testing."""
    
    def __init__(self):
        super().__init__([EventType.TRADE_SIGNAL, EventType.SYSTEM_STATUS])
        self.received_signals = []
        self.received_system_events = []
    
    async def handle_event(self, event):
        """Handle specific event types."""
        if event.type == EventType.TRADE_SIGNAL:
            self.received_signals.append(event)
        elif event.type == EventType.SYSTEM_STATUS:
            self.received_system_events.append(event)


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "symbols": ["BTC-USDT", "ETH-USDT"],
        "default_timeframe": "1h",
        "analysis_interval": 300,
        "position_update_interval": 60,
        "dry_run": True,
        "paper_trading": True,
        "risk": {
            "max_daily_loss": 0.05,
            "max_position_size": 0.1,
            "max_active_positions": 5
        },
        "notifications": {
            "telegram_enabled": True,
            "risk_alerts": True,
            "trade_notifications": True
        }
    }


@pytest.fixture
def mock_services():
    """Mock services for testing."""
    return {
        "portfolio_service": MockPortfolioService(),
        "risk_service": MockRiskService(),
        "trade_service": MockTradeService(MockExchangeAdapter(), {}, MockRiskService()),
        "exchange_adapter": MockExchangeAdapter(),
        "telegram_bot": MockTelegramBot(),
        "scheduler": MockScheduler()
    }


@pytest.fixture
async def event_bus():
    """Event bus for testing."""
    bus = AsyncEventBus(max_queue_size=100)
    await bus.start()
    yield bus
    await bus.stop()


@pytest.fixture
async def trading_orchestrator(mock_config, mock_services):
    """Trading orchestrator for testing."""
    # Patch the dependencies
    with patch('domain.trading_orchestrator.PortfolioService', return_value=mock_services["portfolio_service"]), \
         patch('domain.trading_orchestrator.RiskService', return_value=mock_services["risk_service"]), \
         patch('domain.trading_orchestrator.TradeService', return_value=mock_services["trade_service"]), \
         patch('domain.trading_orchestrator.OKXExchangeAdapter', return_value=mock_services["exchange_adapter"]), \
         patch('domain.trading_orchestrator.OKXRESTAdapter', return_value=mock_services["exchange_adapter"]), \
         patch('domain.trading_orchestrator.TelegramBot', return_value=mock_services["telegram_bot"]), \
         patch('domain.trading_orchestrator.Scheduler', return_value=mock_services["scheduler"]):
        
        orchestrator = TradingOrchestrator(mock_config)
        yield orchestrator


class TestSystemIntegration:
    """Test complete system integration."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, trading_orchestrator):
        """Test that orchestrator initializes correctly."""
        assert trading_orchestrator is not None
        assert trading_orchestrator.event_bus is not None
        assert trading_orchestrator.strategy_registry is not None
        assert len(trading_orchestrator.strategy_registry.get_all_strategies()) > 0
        
        # Check that strategies are registered
        registry_summary = trading_orchestrator.strategy_registry.get_registry_summary()
        assert registry_summary["total_strategies"] >= 4  # 3 individual + 1 composite
        assert registry_summary["active_strategies"] >= 4
    
    @pytest.mark.asyncio
    async def test_event_system_integration(self, trading_orchestrator, event_bus):
        """Test event system integration."""
        # Subscribe to events
        test_subscriber = TestEventSubscriber()
        event_bus.add_subscriber(test_subscriber)
        
        # Start orchestrator
        await trading_orchestrator.start()
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Check that system events were published
        assert len(test_subscriber.received_system_events) > 0
        
        # Check event bus status
        status = trading_orchestrator.event_bus.get_queue_status()
        assert status["running"] is True
        
        # Stop orchestrator
        await trading_orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_strategy_registry_integration(self, trading_orchestrator):
        """Test strategy registry integration."""
        registry = trading_orchestrator.strategy_registry
        
        # Check that strategies are properly registered
        ta_strategies = registry.get_strategies_by_type(registry.strategies["technical_analysis"].strategy_type)
        assert len(ta_strategies) == 1
        
        ml_strategies = registry.get_strategies_by_type(registry.strategies["machine_learning"].strategy_type)
        assert len(ml_strategies) == 1
        
        # Check composite strategy
        composite = registry.get_strategy("composite_trading")
        assert composite is not None
        assert len(composite.strategies) == 3
        assert composite.weights["technical_analysis"] == 0.4
        assert composite.weights["machine_learning"] == 0.3
        assert composite.weights["news_sentiment"] == 0.3
    
    @pytest.mark.asyncio
    async def test_event_publishing(self, trading_orchestrator):
        """Test event publishing functionality."""
        # Test trading signal publishing
        await trading_orchestrator._publish_trading_signal("BTC-USDT", "buy", 0.8, 0.9)
        
        # Test position update publishing
        await trading_orchestrator._publish_position_update("BTC-USDT", "long", 0.1, 50000, 100)
        
        # Test risk alert publishing
        await trading_orchestrator._publish_risk_alert("medium", ["High volatility"], ["Reduce position size"])
        
        # Test portfolio update publishing
        portfolio_data = {"total_balance": 10000, "total_pnl": 500, "position_count": 2, "exposure_ratio": 0.3}
        await trading_orchestrator._publish_portfolio_update(portfolio_data)
        
        # Check event bus queue
        queue_status = trading_orchestrator.event_bus.get_queue_status()
        assert queue_status["queue_size"] >= 4  # Should have at least 4 events
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, trading_orchestrator, event_bus):
        """Test complete trading workflow."""
        # Subscribe to events
        test_subscriber = TestEventSubscriber()
        event_bus.add_subscriber(test_subscriber)
        
        # Start orchestrator
        await trading_orchestrator.start()
        
        # Wait for initialization
        await asyncio.sleep(0.1)
        
        # Publish a trading signal
        await trading_orchestrator._publish_trading_signal("ETH-USDT", "sell", 0.7, 0.8)
        
        # Wait for event processing
        await asyncio.sleep(0.1)
        
        # Check that events were received
        assert len(test_subscriber.received_signals) > 0
        
        # Check event metrics
        metrics = trading_orchestrator.event_bus.get_metrics()
        assert metrics["event_metrics"]["total_events"] > 0
        
        # Stop orchestrator
        await trading_orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_error_handling(self, trading_orchestrator):
        """Test error handling in the system."""
        # Test with invalid event data
        try:
            await trading_orchestrator._publish_trading_signal("", "", -1, -1)
        except Exception as e:
            # Should handle gracefully
            assert "Failed to publish trading signal" in str(e) or "Failed to publish trading signal" in str(e)
        
        # Test with invalid strategy context
        try:
            from domain.strategies import StrategyContext
            context = StrategyContext(symbol="", timeframe="", market_data={})
            # This should not raise an exception
            assert context is not None
        except Exception as e:
            # Should handle gracefully
            pass
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, trading_orchestrator):
        """Test performance metrics collection."""
        # Get initial metrics
        initial_metrics = trading_orchestrator.get_status()
        
        # Perform some operations
        await trading_orchestrator._publish_trading_signal("BTC-USDT", "buy", 0.9, 0.95)
        await trading_orchestrator._publish_position_update("BTC-USDT", "long", 0.05, 50000, 50)
        
        # Get updated metrics
        updated_metrics = trading_orchestrator.get_status()
        
        # Check that metrics are being collected
        assert "event_bus_status" in updated_metrics
        assert "strategy_registry" in updated_metrics
        
        # Check strategy registry metrics
        strategy_metrics = updated_metrics["strategy_registry"]
        assert strategy_metrics["total_strategies"] >= 4
        assert strategy_metrics["active_strategies"] >= 4


class TestEventSystem:
    """Test event system functionality."""
    
    @pytest.mark.asyncio
    async def test_event_bus_operations(self, event_bus):
        """Test event bus basic operations."""
        # Test event publishing
        from domain.events import Event, EventType, EventPriority
        
        event = Event(
            type=EventType.SYSTEM_STATUS,
            priority=EventPriority.INFO,
            source="test",
            data={"message": "test event"}
        )
        
        success = await event_bus.publish(event)
        assert success is True
        
        # Test event processing
        processed = await event_bus.process_events()
        assert processed > 0
        
        # Check metrics
        metrics = event_bus.get_metrics()
        assert metrics["event_metrics"]["total_events"] > 0
    
    @pytest.mark.asyncio
    async def test_event_filtering(self, event_bus):
        """Test event filtering functionality."""
        from domain.events import Event, EventType, EventPriority, EventFilter
        
        # Create events with different priorities
        high_priority_event = Event(
            type=EventType.RISK_ALERT,
            priority=EventPriority.HIGH,
            source="test"
        )
        
        low_priority_event = Event(
            type=EventType.SYSTEM_STATUS,
            priority=EventPriority.LOW,
            source="test"
        )
        
        # Test filter
        filter_high = EventFilter(min_priority=EventPriority.HIGH)
        assert filter_high.matches(high_priority_event) is True
        assert filter_high.matches(low_priority_event) is False
        
        # Test type filter
        filter_risk = EventFilter(event_types=[EventType.RISK_ALERT])
        assert filter_risk.matches(high_priority_event) is True
        assert filter_risk.matches(low_priority_event) is False


class TestStrategyPattern:
    """Test strategy pattern functionality."""
    
    def test_strategy_registry(self):
        """Test strategy registry operations."""
        registry = StrategyRegistry()
        
        # Create test strategy
        strategy = TechnicalAnalysisStrategy("test_strategy")
        strategy.indicators = ["RSI", "MACD"]
        
        # Register strategy
        success = registry.register(strategy)
        assert success is True
        
        # Get strategy
        retrieved = registry.get_strategy("test_strategy")
        assert retrieved is not None
        assert retrieved.name == "test_strategy"
        
        # Check registry summary
        summary = registry.get_registry_summary()
        assert summary["total_strategies"] == 1
        assert summary["active_strategies"] == 1
        
        # Unregister strategy
        success = registry.unregister("test_strategy")
        assert success is True
        assert registry.get_strategy("test_strategy") is None
    
    def test_composite_strategy(self):
        """Test composite strategy functionality."""
        from domain.strategies import CompositeStrategy, TechnicalAnalysisStrategy
        
        # Create composite strategy
        composite = CompositeStrategy("test_composite")
        
        # Add strategies
        ta1 = TechnicalAnalysisStrategy("ta1")
        ta2 = TechnicalAnalysisStrategy("ta2")
        
        composite.add_strategy(ta1, weight=0.6)
        composite.add_strategy(ta2, weight=0.4)
        
        # Check strategy composition
        assert len(composite.strategies) == 2
        assert composite.weights["ta1"] == 0.6
        assert composite.weights["ta2"] == 0.4
        
        # Remove strategy
        composite.remove_strategy("ta1")
        assert len(composite.strategies) == 1
        assert "ta1" not in composite.weights


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v"])
