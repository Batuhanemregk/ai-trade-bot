"""
Event System - Domain layer event interfaces and base classes.
Follows SOLID principles and Clean Architecture patterns.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4


class EventType(Enum):
    """Event types enumeration."""
    TRADE_SIGNAL = "trade_signal"
    POSITION_UPDATE = "position_update"
    RISK_ALERT = "risk_alert"
    PORTFOLIO_UPDATE = "portfolio_update"
    SYSTEM_STATUS = "system_status"
    MARKET_DATA = "market_data"
    ANALYSIS_COMPLETE = "analysis_complete"
    ORDER_EXECUTED = "order_executed"
    ERROR_OCCURRED = "error_occurred"


class EventPriority(Enum):
    """Event priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


@dataclass
class Event:
    """Base event class."""
    id: str = field(default_factory=lambda: str(uuid4()))
    type: EventType = EventType.SYSTEM_STATUS
    priority: EventPriority = EventPriority.INFO
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate event after initialization."""
        if not self.id:
            self.id = str(uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now()


@dataclass
class TradeSignalEvent(Event):
    """Trade signal event."""
    type: EventType = EventType.TRADE_SIGNAL
    symbol: str = ""
    side: str = ""
    score: float = 0.0
    confidence: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            "symbol": self.symbol,
            "side": self.side,
            "score": self.score,
            "confidence": self.confidence
        })


@dataclass
class PositionUpdateEvent(Event):
    """Position update event."""
    type: EventType = EventType.POSITION_UPDATE
    symbol: str = ""
    side: str = ""
    size: float = 0.0
    price: float = 0.0
    pnl: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            "symbol": self.symbol,
            "side": self.side,
            "size": self.size,
            "price": self.price,
            "pnl": self.pnl
        })


@dataclass
class RiskAlertEvent(Event):
    """Risk alert event."""
    type: EventType = EventType.RISK_ALERT
    risk_level: str = "low"
    risk_factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "recommendations": self.recommendations
        })


@dataclass
class PortfolioUpdateEvent(Event):
    """Portfolio update event."""
    type: EventType = EventType.PORTFOLIO_UPDATE
    total_balance: float = 0.0
    total_pnl: float = 0.0
    position_count: int = 0
    exposure_ratio: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            "total_balance": self.total_balance,
            "total_pnl": self.total_pnl,
            "position_count": self.position_count,
            "exposure_ratio": self.exposure_ratio
        })


class EventHandler(ABC):
    """Abstract event handler interface."""
    
    @abstractmethod
    async def handle(self, event: Event) -> bool:
        """Handle an event."""
        pass
    
    @abstractmethod
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can handle the event."""
        pass


class EventBus(ABC):
    """Abstract event bus interface."""
    
    @abstractmethod
    async def publish(self, event: Event) -> bool:
        """Publish an event to all subscribers."""
        pass
    
    @abstractmethod
    def subscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """Subscribe a handler to an event type."""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """Unsubscribe a handler from an event type."""
        pass
    
    @abstractmethod
    async def process_events(self) -> int:
        """Process all pending events."""
        pass


class EventSubscriber(ABC):
    """Abstract event subscriber interface."""
    
    @abstractmethod
    async def on_event(self, event: Event) -> None:
        """Handle received event."""
        pass
    
    @abstractmethod
    def get_subscribed_events(self) -> List[EventType]:
        """Get list of event types this subscriber is interested in."""
        pass


class EventPublisher(ABC):
    """Abstract event publisher interface."""
    
    @abstractmethod
    async def publish_event(self, event: Event) -> bool:
        """Publish an event."""
        pass
    
    @abstractmethod
    async def publish_events(self, events: List[Event]) -> int:
        """Publish multiple events."""
        pass


# Concrete implementations for domain layer
class SimpleEventHandler(EventHandler):
    """Simple event handler implementation."""
    
    def __init__(self, handler_func: Callable[[Event], bool], event_types: List[EventType]):
        self.handler_func = handler_func
        self.event_types = event_types
    
    async def handle(self, event: Event) -> bool:
        """Handle event using the provided function."""
        try:
            return self.handler_func(event)
        except Exception as e:
            # Log error but don't fail
            return False
    
    def can_handle(self, event: Event) -> bool:
        """Check if this handler can handle the event type."""
        return event.type in self.event_types


class EventFilter:
    """Event filtering utility."""
    
    def __init__(self, event_types: Optional[List[EventType]] = None, 
                 min_priority: Optional[EventPriority] = None,
                 source_filter: Optional[str] = None):
        self.event_types = event_types
        self.min_priority = min_priority
        self.source_filter = source_filter
    
    def matches(self, event: Event) -> bool:
        """Check if event matches the filter criteria."""
        if self.event_types and event.type not in self.event_types:
            return False
        
        if self.min_priority and event.priority.value > self.min_priority.value:
            return False
        
        if self.source_filter and event.source != self.source_filter:
            return False
        
        return True


class EventMetrics:
    """Event system metrics."""
    
    def __init__(self):
        self.total_events = 0
        self.events_by_type = {}
        self.events_by_priority = {}
        self.events_by_source = {}
        self.handlers_by_type = {}
        self.last_event_time = None
    
    def record_event(self, event: Event):
        """Record event metrics."""
        self.total_events += 1
        self.last_event_time = event.timestamp
        
        # Count by type
        event_type = event.type.value
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1
        
        # Count by priority
        priority = event.priority.value
        self.events_by_priority[priority] = self.events_by_priority.get(priority, 0) + 1
        
        # Count by source
        source = event.source
        self.events_by_source[source] = self.events_by_source.get(source, 0) + 1
    
    def record_handler(self, event_type: EventType, handler_count: int):
        """Record handler metrics."""
        self.handlers_by_type[event_type.value] = handler_count
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_events": self.total_events,
            "events_by_type": self.events_by_type,
            "events_by_priority": self.events_by_priority,
            "events_by_source": self.events_by_source,
            "handlers_by_type": self.handlers_by_type,
            "last_event_time": self.last_event_time
        }
