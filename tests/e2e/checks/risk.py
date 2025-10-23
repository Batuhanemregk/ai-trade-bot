"""
Risk Management Checker
======================

Risk management kontrolleri:
- Position sizing calculations
- Exposure limits
- Tier-based risk assessment
- Circuit breaker functionality
- Risk score validation
- Portfolio risk metrics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class RiskEvent:
    """Risk event for tracking."""
    timestamp: datetime
    event_type: str  # position_size, exposure, tier, circuit_breaker, risk_score
    symbol: str
    value: float
    limit: float
    status: str  # within_limit, exceeded, warning
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class PositionSizing:
    """Position sizing calculation."""
    symbol: str
    signal_score: float
    balance: float
    max_position_pct: float
    calculated_size: float
    final_size: float
    reason: str


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_position_size_pct: float = 0.10  # 10% max per position
    max_total_risk_pct: float = 0.60     # 60% max total risk
    max_concurrent_positions: int = 20    # Max 20 positions
    min_margin_required: float = 10.0     # Min $10 margin
    circuit_breaker_loss_pct: float = 0.15  # 15% loss triggers circuit breaker


class RiskManagementChecker:
    """Checks risk management and position sizing."""
    
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.risk_events: List[RiskEvent] = []
        self.position_sizings: List[PositionSizing] = []
        self.circuit_breaker_state = "normal"  # normal, warning, emergency, paused
        
    async def check_position_sizing(self, symbol: str, signal_score: float, 
                                  balance: float, existing_positions: List[Dict]) -> Tuple[bool, str]:
        """
        Check position sizing calculation.
        
        Args:
            symbol: Trading symbol
            signal_score: Signal score (0-100)
            balance: Available balance
            existing_positions: List of existing positions
            
        Returns:
            (success, message)
        """
        try:
            # Check minimum margin
            if balance < self.limits.min_margin_required:
                event = RiskEvent(
                    timestamp=datetime.now(),
                    event_type="position_size",
                    symbol=symbol,
                    value=balance,
                    limit=self.limits.min_margin_required,
                    status="exceeded",
                    details={"reason": "insufficient_margin"}
                )
                self.risk_events.append(event)
                
                return False, f"Insufficient margin: ${balance:.2f} < ${self.limits.min_margin_required}"
            
            # Calculate total existing risk
            total_risk = sum(float(pos.get('notional', 0)) for pos in existing_positions if pos.get('size', 0) != 0)
            
            # Check max concurrent positions
            active_positions = len([pos for pos in existing_positions if pos.get('size', 0) != 0])
            if active_positions >= self.limits.max_concurrent_positions:
                event = RiskEvent(
                    timestamp=datetime.now(),
                    event_type="position_size",
                    symbol=symbol,
                    value=active_positions,
                    limit=self.limits.max_concurrent_positions,
                    status="exceeded",
                    details={"reason": "max_positions"}
                )
                self.risk_events.append(event)
                
                return False, f"Max positions reached: {active_positions}/{self.limits.max_concurrent_positions}"
            
            # Calculate available risk
            max_total_risk = balance * self.limits.max_total_risk_pct
            available_risk = max_total_risk - total_risk
            
            if available_risk <= 0:
                event = RiskEvent(
                    timestamp=datetime.now(),
                    event_type="position_size",
                    symbol=symbol,
                    value=total_risk,
                    limit=max_total_risk,
                    status="exceeded",
                    details={"reason": "no_available_risk"}
                )
                self.risk_events.append(event)
                
                return False, f"No available risk: total_risk=${total_risk:.2f} >= limit=${max_total_risk:.2f}"
            
            # Calculate position size based on signal (1% to 10% of balance)
            base_percentage = 0.01 + (signal_score / 100.0) * 0.09  # 1% to 10%
            base_percentage = max(0.01, min(0.10, base_percentage))
            
            desired_position_size = balance * base_percentage
            position_size_usdt = min(desired_position_size, available_risk)
            
            # Ensure it doesn't exceed max position size
            max_position_size = balance * self.limits.max_position_size_pct
            position_size_usdt = min(position_size_usdt, max_position_size)
            
            # Record position sizing
            sizing = PositionSizing(
                symbol=symbol,
                signal_score=signal_score,
                balance=balance,
                max_position_pct=self.limits.max_position_size_pct,
                calculated_size=desired_position_size,
                final_size=position_size_usdt,
                reason="Risk check passed"
            )
            self.position_sizings.append(sizing)
            
            # Record risk event
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type="position_size",
                symbol=symbol,
                value=position_size_usdt,
                limit=max_position_size,
                status="within_limit",
                details={
                    "signal_score": signal_score,
                    "desired_size": desired_position_size,
                    "available_risk": available_risk
                }
            )
            self.risk_events.append(event)
            
            logger.info(f"✅ Position sizing: {symbol} ${position_size_usdt:.2f} (score: {signal_score:.1f})")
            return True, f"Position size: ${position_size_usdt:.2f} (${desired_position_size:.2f} desired)"
            
        except Exception as e:
            logger.error(f"❌ Position sizing check failed: {e}")
            return False, f"Position sizing check failed: {e}"
    
    async def check_exposure_limits(self, symbol: str, balance: float, 
                                  existing_positions: List[Dict]) -> Tuple[bool, str]:
        """
        Check exposure limits.
        
        Args:
            symbol: Trading symbol
            balance: Available balance
            existing_positions: List of existing positions
            
        Returns:
            (success, message)
        """
        try:
            # Calculate total exposure
            total_exposure = sum(float(pos.get('notional', 0)) for pos in existing_positions if pos.get('size', 0) != 0)
            exposure_pct = (total_exposure / balance) * 100 if balance > 0 else 0
            
            max_exposure = balance * self.limits.max_total_risk_pct
            max_exposure_pct = self.limits.max_total_risk_pct * 100
            
            if exposure_pct <= max_exposure_pct:
                status = "within_limit"
                if exposure_pct > max_exposure_pct * 0.8:  # 80% of limit
                    status = "warning"
            else:
                status = "exceeded"
            
            # Record risk event
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type="exposure",
                symbol=symbol,
                value=exposure_pct,
                limit=max_exposure_pct,
                status=status,
                details={
                    "total_exposure": total_exposure,
                    "balance": balance,
                    "position_count": len([p for p in existing_positions if p.get('size', 0) != 0])
                }
            )
            self.risk_events.append(event)
            
            if status == "exceeded":
                logger.warning(f"⚠️ Exposure limit exceeded: {exposure_pct:.1f}% > {max_exposure_pct:.1f}%")
                return False, f"Exposure limit exceeded: {exposure_pct:.1f}% > {max_exposure_pct:.1f}%"
            elif status == "warning":
                logger.warning(f"⚠️ High exposure: {exposure_pct:.1f}% (limit: {max_exposure_pct:.1f}%)")
                return True, f"High exposure: {exposure_pct:.1f}% (limit: {max_exposure_pct:.1f}%)"
            else:
                logger.info(f"✅ Exposure within limits: {exposure_pct:.1f}% (limit: {max_exposure_pct:.1f}%)")
                return True, f"Exposure: {exposure_pct:.1f}% (limit: {max_exposure_pct:.1f}%)"
                
        except Exception as e:
            logger.error(f"❌ Exposure check failed: {e}")
            return False, f"Exposure check failed: {e}"
    
    async def check_tier_based_risk(self, symbol: str, market_cap_tier: str) -> Tuple[bool, str]:
        """
        Check tier-based risk assessment.
        
        Args:
            symbol: Trading symbol
            market_cap_tier: Market cap tier (tier_1, tier_2, tier_3, tier_4)
            
        Returns:
            (success, message)
        """
        try:
            # Define tier risk levels
            tier_risk_levels = {
                'tier_1': 25.0,  # BTC, ETH - lowest risk
                'tier_2': 35.0,  # Major altcoins
                'tier_3': 50.0,  # Mid-cap altcoins
                'tier_4': 70.0,  # Small-cap altcoins
                'unknown': 60.0  # Unknown coins
            }
            
            risk_level = tier_risk_levels.get(market_cap_tier, tier_risk_levels['unknown'])
            
            # Record risk event
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type="tier",
                symbol=symbol,
                value=risk_level,
                limit=100.0,  # Max risk level
                status="within_limit",
                details={"tier": market_cap_tier}
            )
            self.risk_events.append(event)
            
            logger.info(f"✅ Tier risk assessment: {symbol} {market_cap_tier} = {risk_level:.1f}%")
            return True, f"Tier risk: {market_cap_tier} = {risk_level:.1f}%"
            
        except Exception as e:
            logger.error(f"❌ Tier risk check failed: {e}")
            return False, f"Tier risk check failed: {e}"
    
    async def check_circuit_breaker(self, balance: float, initial_balance: float, 
                                  daily_pnl: float) -> Tuple[bool, str]:
        """
        Check circuit breaker functionality.
        
        Args:
            balance: Current balance
            initial_balance: Initial balance
            daily_pnl: Daily P&L
            
        Returns:
            (success, message)
        """
        try:
            # Calculate loss percentage
            if initial_balance > 0:
                loss_pct = abs(daily_pnl) / initial_balance
            else:
                loss_pct = 0
            
            # Check circuit breaker thresholds
            if loss_pct >= self.limits.circuit_breaker_loss_pct:
                self.circuit_breaker_state = "emergency"
                status = "exceeded"
                message = f"Circuit breaker triggered: {loss_pct:.1%} >= {self.limits.circuit_breaker_loss_pct:.1%}"
            elif loss_pct >= self.limits.circuit_breaker_loss_pct * 0.7:  # 70% of limit
                self.circuit_breaker_state = "warning"
                status = "warning"
                message = f"Circuit breaker warning: {loss_pct:.1%} >= {self.limits.circuit_breaker_loss_pct * 0.7:.1%}"
            else:
                self.circuit_breaker_state = "normal"
                status = "within_limit"
                message = f"Circuit breaker normal: {loss_pct:.1%} < {self.limits.circuit_breaker_loss_pct:.1%}"
            
            # Record risk event
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type="circuit_breaker",
                symbol="PORTFOLIO",
                value=loss_pct * 100,
                limit=self.limits.circuit_breaker_loss_pct * 100,
                status=status,
                details={
                    "daily_pnl": daily_pnl,
                    "initial_balance": initial_balance,
                    "current_balance": balance,
                    "state": self.circuit_breaker_state
                }
            )
            self.risk_events.append(event)
            
            if status == "exceeded":
                logger.error(f"🚨 {message}")
                return False, message
            elif status == "warning":
                logger.warning(f"⚠️ {message}")
                return True, message
            else:
                logger.info(f"✅ {message}")
                return True, message
                
        except Exception as e:
            logger.error(f"❌ Circuit breaker check failed: {e}")
            return False, f"Circuit breaker check failed: {e}"
    
    async def check_risk_score_validation(self, symbol: str, risk_score: float, 
                                        max_risk_score: float = 80.0) -> Tuple[bool, str]:
        """
        Check risk score validation.
        
        Args:
            symbol: Trading symbol
            risk_score: Risk score (0-100)
            max_risk_score: Maximum allowed risk score
            
        Returns:
            (success, message)
        """
        try:
            if risk_score <= max_risk_score:
                status = "within_limit"
                message = f"Risk score acceptable: {risk_score:.1f} <= {max_risk_score}"
            else:
                status = "exceeded"
                message = f"Risk score too high: {risk_score:.1f} > {max_risk_score}"
            
            # Record risk event
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type="risk_score",
                symbol=symbol,
                value=risk_score,
                limit=max_risk_score,
                status=status,
                details={"max_risk_score": max_risk_score}
            )
            self.risk_events.append(event)
            
            if status == "exceeded":
                logger.warning(f"⚠️ {message}")
                return False, message
            else:
                logger.info(f"✅ {message}")
                return True, message
                
        except Exception as e:
            logger.error(f"❌ Risk score validation failed: {e}")
            return False, f"Risk score validation failed: {e}"
    
    async def check_portfolio_risk_metrics(self, balance: float, positions: List[Dict], 
                                         daily_pnl: float) -> Tuple[bool, str]:
        """
        Check portfolio risk metrics.
        
        Args:
            balance: Current balance
            positions: List of positions
            daily_pnl: Daily P&L
            
        Returns:
            (success, message)
        """
        try:
            # Calculate portfolio metrics
            total_exposure = sum(float(pos.get('notional', 0)) for pos in positions if pos.get('size', 0) != 0)
            exposure_pct = (total_exposure / balance) * 100 if balance > 0 else 0
            
            active_positions = len([pos for pos in positions if pos.get('size', 0) != 0])
            
            # Calculate drawdown (simplified)
            drawdown_pct = abs(daily_pnl) / balance * 100 if balance > 0 else 0
            
            # Check all metrics
            metrics_ok = True
            issues = []
            
            if exposure_pct > self.limits.max_total_risk_pct * 100:
                metrics_ok = False
                issues.append(f"exposure: {exposure_pct:.1f}%")
            
            if active_positions > self.limits.max_concurrent_positions:
                metrics_ok = False
                issues.append(f"positions: {active_positions}")
            
            if drawdown_pct > self.limits.circuit_breaker_loss_pct * 100:
                metrics_ok = False
                issues.append(f"drawdown: {drawdown_pct:.1f}%")
            
            # Record risk event
            event = RiskEvent(
                timestamp=datetime.now(),
                event_type="portfolio_metrics",
                symbol="PORTFOLIO",
                value=exposure_pct,
                limit=self.limits.max_total_risk_pct * 100,
                status="within_limit" if metrics_ok else "exceeded",
                details={
                    "total_exposure": total_exposure,
                    "active_positions": active_positions,
                    "drawdown_pct": drawdown_pct,
                    "daily_pnl": daily_pnl
                }
            )
            self.risk_events.append(event)
            
            if metrics_ok:
                logger.info(f"✅ Portfolio metrics OK: exposure={exposure_pct:.1f}%, positions={active_positions}, drawdown={drawdown_pct:.1f}%")
                return True, f"Portfolio metrics OK: exposure={exposure_pct:.1f}%, positions={active_positions}, drawdown={drawdown_pct:.1f}%"
            else:
                logger.warning(f"⚠️ Portfolio metrics issues: {', '.join(issues)}")
                return False, f"Portfolio metrics issues: {', '.join(issues)}"
                
        except Exception as e:
            logger.error(f"❌ Portfolio risk metrics check failed: {e}")
            return False, f"Portfolio risk metrics check failed: {e}"
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get summary of all risk events."""
        return {
            'total_events': len(self.risk_events),
            'events_by_type': {
                event_type: len([e for e in self.risk_events if e.event_type == event_type])
                for event_type in ['position_size', 'exposure', 'tier', 'circuit_breaker', 'risk_score', 'portfolio_metrics']
            },
            'events_by_status': {
                status: len([e for e in self.risk_events if e.status == status])
                for status in ['within_limit', 'warning', 'exceeded']
            },
            'circuit_breaker_state': self.circuit_breaker_state,
            'position_sizings': len(self.position_sizings),
            'average_position_size': sum(s.final_size for s in self.position_sizings) / len(self.position_sizings) if self.position_sizings else 0
        }
    
    def get_risk_events(self) -> List[Dict]:
        """Get all risk events for analysis."""
        return [
            {
                'timestamp': e.timestamp.isoformat(),
                'event_type': e.event_type,
                'symbol': e.symbol,
                'value': e.value,
                'limit': e.limit,
                'status': e.status,
                'details': e.details
            }
            for e in self.risk_events
        ]
    
    def get_position_sizings(self) -> List[Dict]:
        """Get all position sizings for analysis."""
        return [
            {
                'symbol': s.symbol,
                'signal_score': s.signal_score,
                'balance': s.balance,
                'max_position_pct': s.max_position_pct,
                'calculated_size': s.calculated_size,
                'final_size': s.final_size,
                'reason': s.reason
            }
            for s in self.position_sizings
        ]

