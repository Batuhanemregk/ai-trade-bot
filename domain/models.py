"""
Domain models for AiBotBS trading system.
Core business entities and value objects.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    TRIGGER = "trigger"


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionSide(str, Enum):
    """Position side enumeration."""
    LONG = "long"
    SHORT = "short"


class SignalType(str, Enum):
    """Signal type enumeration."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class RiskLevel(str, Enum):
    """Risk level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class Money:
    """Money value object with currency."""
    amount: Decimal
    currency: str = "USDT"

    def __post_init__(self):
        if isinstance(self.amount, (int, float)):
            self.amount = Decimal(str(self.amount))

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, scalar: int | float | Decimal) -> 'Money':
        return Money(self.amount * Decimal(str(scalar)), self.currency)

    def __truediv__(self, scalar: int | float | Decimal) -> 'Money':
        return Money(self.amount / Decimal(str(scalar)), self.currency)


@dataclass
class Price:
    """Price value object with precision."""
    value: Decimal
    currency: str = "USDT"
    precision: int = 8

    def __post_init__(self):
        if isinstance(self.value, (int, float)):
            self.value = Decimal(str(self.value))
        self.value = self.value.quantize(Decimal('0.00000001'))

    def __add__(self, other: 'Price') -> 'Price':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Price(self.value + other.value, self.currency, self.precision)

    def __sub__(self, other: 'Price') -> 'Price':
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Price(self.value - other.value, self.currency, self.precision)

    def __mul__(self, scalar: int | float | Decimal) -> 'Price':
        return Price(self.value * Decimal(str(scalar)), self.currency, self.precision)


@dataclass
class Quantity:
    """Quantity value object with precision."""
    value: Decimal
    precision: int = 8

    def __post_init__(self):
        if isinstance(self.value, (int, float)):
            self.value = Decimal(str(self.value))
        self.value = self.value.quantize(Decimal('0.00000001'))

    def __add__(self, other: 'Quantity') -> 'Quantity':
        return Quantity(self.value + other.value, self.precision)

    def __sub__(self, other: 'Quantity') -> 'Quantity':
        return Quantity(self.value - other.value, self.precision)

    def __mul__(self, scalar: int | float | Decimal) -> 'Quantity':
        return Quantity(self.value * Decimal(str(scalar)), self.precision)

    def __truediv__(self, scalar: int | float | Decimal) -> 'Quantity':
        return Quantity(self.value / Decimal(str(scalar)), self.precision)


@dataclass
class Signal:
    """Trading signal entity."""
    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    signal_type: SignalType = SignalType.HOLD
    confidence: float = 0.0  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = ""  # "ta", "ml", "news", "composite"
    metadata: dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class Score:
    """Scoring result entity."""
    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    ta_score: float = 0.0
    ml_score: float = 0.0
    news_score: float = 0.0
    risk_score: float = 0.0
    composite_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    weights: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        for score_name in ['ta_score', 'ml_score', 'news_score', 'risk_score', 'composite_score']:
            score_value = getattr(self, score_name)
            if not 0.0 <= score_value <= 1.0:
                raise ValueError(f"{score_name} must be between 0.0 and 1.0")


@dataclass
class Order:
    """Order entity."""
    id: str = ""
    client_order_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: Quantity = field(default_factory=lambda: Quantity(Decimal('0')))
    price: Price | None = None
    stop_price: Price | None = None
    trigger_price: Price | None = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: Quantity = field(default_factory=lambda: Quantity(Decimal('0')))
    average_price: Price | None = None
    commission: Money = field(default_factory=lambda: Money(Decimal('0')))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, any] = field(default_factory=dict)

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    @property
    def is_partially_filled(self) -> bool:
        return self.status == OrderStatus.PARTIALLY_FILLED

    @property
    def is_active(self) -> bool:
        return self.status in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]

    @property
    def remaining_quantity(self) -> Quantity:
        return self.quantity - self.filled_quantity


@dataclass
class Position:
    """Position entity."""
    id: UUID = field(default_factory=uuid4)
    symbol: str = ""
    side: PositionSide = PositionSide.LONG
    quantity: Quantity = field(default_factory=lambda: Quantity(Decimal('0')))
    entry_price: Price = field(default_factory=lambda: Price(Decimal('0')))
    current_price: Price = field(default_factory=lambda: Price(Decimal('0')))
    unrealized_pnl: Money = field(default_factory=lambda: Money(Decimal('0')))
    realized_pnl: Money = field(default_factory=lambda: Money(Decimal('0')))
    leverage: float = 1.0
    margin: Money = field(default_factory=lambda: Money(Decimal('0')))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, any] = field(default_factory=dict)

    @property
    def market_value(self) -> Money:
        return Money(self.quantity.value * self.current_price.value, self.current_price.currency)

    @property
    def total_pnl(self) -> Money:
        return self.unrealized_pnl + self.realized_pnl

    @property
    def pnl_percentage(self) -> float:
        if self.entry_price.value == 0:
            return 0.0
        return float((self.current_price.value - self.entry_price.value) / self.entry_price.value)


@dataclass
class RiskMetrics:
    """Risk metrics entity."""
    id: UUID = field(default_factory=uuid4)
    portfolio_value: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_exposure: Money = field(default_factory=lambda: Money(Decimal('0')))
    max_drawdown: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not 0.0 <= self.max_drawdown <= 1.0:
            raise ValueError("Max drawdown must be between 0.0 and 1.0")
        if not 0.0 <= self.win_rate <= 1.0:
            raise ValueError("Win rate must be between 0.0 and 1.0")


@dataclass
class Trade:
    """Trade entity."""
    id: UUID = field(default_factory=uuid4)
    order_id: str = ""
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    quantity: Quantity = field(default_factory=lambda: Quantity(Decimal('0')))
    price: Price = field(default_factory=lambda: Price(Decimal('0')))
    commission: Money = field(default_factory=lambda: Money(Decimal('0')))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, any] = field(default_factory=dict)


@dataclass
class Portfolio:
    """Portfolio entity."""
    id: UUID = field(default_factory=uuid4)
    total_value: Money = field(default_factory=lambda: Money(Decimal('0')))
    available_balance: Money = field(default_factory=lambda: Money(Decimal('0')))
    positions: list[Position] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_positions_value(self) -> Money:
        return sum(pos.market_value for pos in self.positions)

    @property
    def total_pnl(self) -> Money:
        return sum(pos.total_pnl for pos in self.positions)

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def active_position_count(self) -> int:
        return len([pos for pos in self.positions if pos.quantity.value > 0])


@dataclass
class TradingConfig:
    """Trading configuration entity."""
    symbols: list[str] = field(default_factory=list)
    default_timeframe: str = "1h"
    analysis_interval: int = 300  # 5 minutes
    position_update_interval: int = 60  # 1 minute
    dry_run: bool = True
    paper_trading: bool = True
    risk: dict[str, Any] = field(default_factory=dict)
    notifications: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradingState:
    """Trading state entity."""
    running: bool = False
    last_analysis: datetime | None = None
    last_signal: datetime | None = None
    last_execution: datetime | None = None
    total_signals: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    current_positions: int = 0
    total_pnl: Money = field(default_factory=lambda: Money(Decimal('0')))
    daily_pnl: Money = field(default_factory=lambda: Money(Decimal('0')))
    start_time: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def should_reset_daily(self) -> bool:
        """Check if daily reset is needed based on start time."""
        if not self.start_time:
            return True
        
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Reset if start time is before today
        return self.start_time < start_of_day
