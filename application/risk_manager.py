"""
Risk Manager - SOLID Principles Compliant
Single Responsibility: Only handles risk calculations
Open/Closed: Extensible for new risk types
Liskov Substitution: Can be replaced with different implementations
Interface Segregation: Clean, focused interface
Dependency Inversion: Depends on abstractions, not concretions
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_position_size_pct: float = 0.10  # 10% max per position
    max_total_risk_pct: float = 0.60     # 60% max total risk
    max_concurrent_positions: int = 20    # Max 20 positions
    min_margin_required: float = 10.0     # Min $10 margin


@dataclass
class PositionInfo:
    """Position information."""
    symbol: str
    notional: float
    size: float
    side: str


@dataclass
class RiskAssessment:
    """Risk assessment result."""
    can_trade: bool
    position_size_usdt: float
    reason: str
    available_margin: float
    total_risk: float


class RiskCalculator(ABC):
    """Abstract risk calculator interface."""
    
    @abstractmethod
    async def calculate_position_size(
        self, 
        symbol: str, 
        signal_score: float, 
        current_price: float,
        balance: float,
        existing_positions: list
    ) -> RiskAssessment:
        """Calculate safe position size."""
        pass


class FuturesRiskManager(RiskCalculator):
    """Futures-specific risk manager."""
    
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
    
    async def calculate_position_size(
        self, 
        symbol: str, 
        signal_score: float, 
        current_price: float,
        balance: float,
        existing_positions: list
    ) -> RiskAssessment:
        """Calculate position size for futures trading."""
        
        # Check minimum margin
        if balance < self.limits.min_margin_required:
            return RiskAssessment(
                can_trade=False,
                position_size_usdt=0.0,
                reason=f"Insufficient margin: ${balance:.2f} < ${self.limits.min_margin_required}",
                available_margin=balance,
                total_risk=0.0
            )
        
        # Calculate total existing risk
        total_risk = sum(float(pos.get('notional', 0)) for pos in existing_positions if pos.get('size', 0) != 0)
        
        # Check max concurrent positions
        active_positions = len([pos for pos in existing_positions if pos.get('size', 0) != 0])
        if active_positions >= self.limits.max_concurrent_positions:
            return RiskAssessment(
                can_trade=False,
                position_size_usdt=0.0,
                reason=f"Max positions reached: {active_positions}/{self.limits.max_concurrent_positions}",
                available_margin=balance,
                total_risk=total_risk
            )
        
        # Calculate available risk
        max_total_risk = balance * self.limits.max_total_risk_pct
        available_risk = max_total_risk - total_risk
        
        if available_risk <= 0:
            return RiskAssessment(
                can_trade=False,
                position_size_usdt=0.0,
                reason=f"No available risk: total_risk=${total_risk:.2f} >= limit=${max_total_risk:.2f}",
                available_margin=balance,
                total_risk=total_risk
            )
        
        # Calculate position size based on signal (1% to 10% of balance)
        base_percentage = 0.01 + (signal_score / 100.0) * 0.09  # 1% to 10%
        base_percentage = max(0.01, min(0.10, base_percentage))
        
        desired_position_size = balance * base_percentage
        position_size_usdt = min(desired_position_size, available_risk)
        
        # Ensure it doesn't exceed max position size
        max_position_size = balance * self.limits.max_position_size_pct
        position_size_usdt = min(position_size_usdt, max_position_size)
        
        logger.info(f"🎯 Risk calculation for {symbol}: score={signal_score:.1f}, "
                   f"balance=${balance:.2f}, desired=${desired_position_size:.2f}, "
                   f"final=${position_size_usdt:.2f}")
        
        return RiskAssessment(
            can_trade=True,
            position_size_usdt=position_size_usdt,
            reason="Risk check passed",
            available_margin=balance,
            total_risk=total_risk
        )


class RiskManager:
    """Main risk manager - uses composition for flexibility."""
    
    def __init__(self, calculator: RiskCalculator = None):
        self.calculator = calculator or FuturesRiskManager()
    
    async def assess_trade_risk(
        self,
        symbol: str,
        signal_score: float,
        current_price: float,
        balance: float,
        existing_positions: list
    ) -> RiskAssessment:
        """Assess if a trade is safe to execute."""
        return await self.calculator.calculate_position_size(
            symbol, signal_score, current_price, balance, existing_positions
        )
