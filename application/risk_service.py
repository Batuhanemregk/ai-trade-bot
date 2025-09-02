"""
Risk Service for AiBotBS.
Provides risk assessment, limit enforcement, and risk scoring for trading decisions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from domain.models import RiskLevel, SignalType


@dataclass
class RiskAssessment:
    """Risk assessment for a trading decision."""
    id: str
    symbol: str
    timestamp: datetime
    risk_score: float  # 0.0 to 1.0 (0 = no risk, 1 = maximum risk)
    risk_level: RiskLevel
    risk_factors: list[str]
    risk_limits: dict[str, Any]
    position_size: float
    notional_value: float
    margin_required: float
    max_position_size: float
    leverage_used: float
    max_leverage: float
    portfolio_exposure: float
    max_portfolio_exposure: float
    market_volatility: float
    correlation: float
    risk_adjusted_score: float  # Original score adjusted for risk
    risk_rationale: str
    blocked: bool = False  # Whether the trade is blocked by bias
    block_reason: str = ""  # Reason for blocking if applicable
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_position_size: float
    max_leverage: float
    max_drawdown: float
    max_margin_ratio: float
    max_risk_per_trade: float
    max_portfolio_risk: float
    max_portfolio_exposure: float
    stop_loss_threshold: float
    take_profit_threshold: float
    max_correlation: float
    max_concentration: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskPenalty:
    """Risk penalty information."""
    factor: str  # "exposure", "correlation", "drawdown", "leverage", "concentration"
    severity: str  # "low", "medium", "high", "critical"
    penalty_amount: float  # Score reduction amount
    description: str
    recommendation: str


class RiskService:
    """Service for risk assessment and limit enforcement."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("risk_service")

        # Risk limits configuration
        self.risk_limits = RiskLimits(
            max_position_size=config.get("max_position_size", 100000.0),
            max_leverage=config.get("max_leverage", 10.0),
            max_drawdown=config.get("max_drawdown", 0.20),  # 20%
            max_margin_ratio=config.get("max_margin_ratio", 0.80),  # 80%
            max_risk_per_trade=config.get("max_risk_per_trade", 0.02),  # 2%
            max_portfolio_risk=config.get("max_portfolio_risk", 0.10),  # 10%
            max_portfolio_exposure=config.get("max_portfolio_exposure", 0.10),  # 10%
            stop_loss_threshold=config.get("stop_loss_threshold", 0.05),  # 5%
            take_profit_threshold=config.get("take_profit_threshold", 0.10),  # 10%
            max_correlation=config.get("max_correlation", 0.8),  # 80%
            max_concentration=config.get("max_concentration", 0.3),  # 30%
            metadata=config.get("risk_metadata", {})
        )

        # Risk scoring configuration
        self.risk_weights = config.get("risk_weights", {
            "position_size": 0.25,
            "leverage": 0.25,
            "portfolio_exposure": 0.20,
            "market_volatility": 0.15,
            "correlation": 0.15
        })

        # Performance tracking
        self._assessments_performed = 0
        self._risk_violations = 0
        self._score_downgrades = 0
        self._last_assessment = None

        self.logger.info(f"Risk service initialized with limits: {self.risk_limits}")

    def assess_risk(self, symbol: str, score: float, signal: SignalType,
                    position_size: float, leverage: float = 1.0,
                    portfolio_exposure: float = 0.0,
                    market_volatility: float = 0.0,
                    correlation: float = 0.0,
                    bias_action: str = "allow",
                    bias_reason: str = "") -> RiskAssessment:
        """Assess risk for a trading decision."""
        try:
            # Check bias service for blocks
            blocked = False
            block_reason = ""
            
            if bias_action == "block":
                blocked = True
                block_reason = f"BLOCKED_BY_BIAS: {bias_reason}"
                self.logger.warning(f"Trade blocked by bias for {symbol}: {bias_reason}")
                
                # Return blocked assessment immediately
                return RiskAssessment(
                    id=str(uuid4()),
                    symbol=symbol,
                    timestamp=datetime.now(),
                    risk_score=1.0,  # Maximum risk for blocked trades
                    risk_level=RiskLevel.EXTREME,
                    risk_factors=[block_reason],
                    risk_limits=self.risk_limits.__dict__,
                    position_size=position_size,
                    notional_value=position_size * leverage,
                    margin_required=position_size / leverage,
                    max_position_size=self.risk_limits.max_position_size,
                    leverage_used=leverage,
                    max_leverage=self.risk_limits.max_leverage,
                    portfolio_exposure=portfolio_exposure,
                    max_portfolio_exposure=self.risk_limits.max_portfolio_exposure,
                    market_volatility=market_volatility,
                    correlation=correlation,
                    risk_adjusted_score=0.0,  # Zero score for blocked trades
                    risk_rationale=f"Trade blocked by bias: {bias_reason}",
                    blocked=blocked,
                    block_reason=block_reason,
                    metadata={
                        "bias_action": bias_action,
                        "bias_reason": bias_reason,
                        "blocked_by_bias": True
                    }
                )
            
            # Calculate risk factors
            risk_factors = []
            risk_score = 0.0

            # Position size risk (80% threshold)
            position_risk = min(position_size / self.risk_limits.max_position_size, 1.0)
            if position_risk > 0.8:
                risk_factors.append(f"Large position size ({position_risk:.1%} of max)")
                risk_score += position_risk * self.risk_weights["position_size"]

            # Leverage risk (80% threshold)
            leverage_risk = min(leverage / self.risk_limits.max_leverage, 1.0)
            if leverage_risk > 0.8:
                risk_factors.append(f"High leverage ({leverage_risk:.1%} of max)")
                risk_score += leverage_risk * self.risk_weights["leverage"]

            # Portfolio exposure risk (80% threshold)
            exposure_risk = min(portfolio_exposure / self.risk_limits.max_portfolio_exposure, 1.0)
            if exposure_risk > 0.8:
                risk_factors.append(f"High portfolio exposure ({exposure_risk:.1%} of max)")
                risk_score += exposure_risk * self.risk_weights["portfolio_exposure"]

            # Correlation risk (exceeds max)
            if correlation > self.risk_limits.max_correlation:
                risk_factors.append(f"High correlation ({correlation:.1%})")
                risk_score += (correlation / self.risk_limits.max_correlation) * self.risk_weights["correlation"]

            # Market volatility risk (50% threshold)
            if market_volatility > 0.5:
                risk_factors.append(f"High market volatility ({market_volatility:.1%})")
                risk_score += market_volatility * self.risk_weights["market_volatility"]

            # Determine risk level
            if risk_score >= 0.8:
                risk_level = RiskLevel.EXTREME
            elif risk_score >= 0.6:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 0.4:
                risk_level = RiskLevel.MEDIUM
            elif risk_score >= 0.2:
                risk_level = RiskLevel.LOW
            else:
                risk_level = RiskLevel.LOW

            # Calculate risk-adjusted score
            risk_adjusted_score = max(0, score - (risk_score * 20))  # Reduce score by risk penalty

            # Generate risk rationale
            risk_rationale = self._generate_risk_rationale(risk_factors, risk_score, risk_level)

            # Create risk assessment
            assessment = RiskAssessment(
                id=str(uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors=risk_factors,
                risk_limits=self.risk_limits.__dict__,
                position_size=position_size,
                notional_value=position_size * leverage,
                margin_required=position_size / leverage,
                max_position_size=self.risk_limits.max_position_size,
                leverage_used=leverage,
                max_leverage=self.risk_limits.max_leverage,
                portfolio_exposure=portfolio_exposure,
                max_portfolio_exposure=self.risk_limits.max_portfolio_exposure,
                market_volatility=market_volatility,
                correlation=correlation,
                risk_adjusted_score=risk_adjusted_score,
                risk_rationale=risk_rationale,
                blocked=blocked,
                block_reason=block_reason,
                metadata={
                    "market_volatility": market_volatility,
                    "correlation": correlation,
                    "risk_weights_used": self.risk_weights,
                    "bias_action": bias_action,
                    "bias_reason": bias_reason
                }
            )

            self._assessments_performed += 1
            if risk_score > 0.6:
                self._risk_violations += 1
            if risk_adjusted_score < score:
                self._score_downgrades += 1
            self._last_assessment = assessment

            self.logger.info(f"Risk assessment for {symbol}: {risk_level.value} (score: {risk_score:.2f})")
            return assessment

        except Exception as e:
            self.logger.error(f"Error in risk assessment for {symbol}: {e}")
            raise

    def annotate_composite_score(self, composite_score: Any,
                                position_size: float = 0.0,
                                leverage: float = 1.0,
                                portfolio_exposure: float = 0.0,
                                market_volatility: float = 0.0,
                                correlation: float = 0.0) -> list[str]:
        """Annotate a CompositeScore with risk notes (read-only, no execution changes)."""
        try:
            risk_notes = []
            risk_penalties = {}

            # Check position size risk
            if position_size > 0:
                position_risk = min(position_size / self.risk_limits.max_position_size, 1.0)
                if position_risk > 0.8:
                    risk_notes.append(f"⚠️ Large position: {position_risk:.1%} of max size")
                    risk_penalties["position_size"] = position_risk * 5  # 5 point penalty

            # Check leverage risk
            if leverage > 1.0:
                leverage_risk = min(leverage / self.risk_limits.max_leverage, 1.0)
                if leverage_risk > 0.8:
                    risk_notes.append(f"⚡ High leverage: {leverage_risk:.1%} of max")
                    risk_penalties["leverage"] = leverage_risk * 5

            # Check portfolio exposure risk
            if portfolio_exposure > 0:
                exposure_risk = min(portfolio_exposure / self.risk_limits.max_portfolio_exposure, 1.0)
                if exposure_risk > 0.8:
                    risk_notes.append(f"📊 High exposure: {exposure_risk:.1%} of portfolio")
                    risk_penalties["exposure"] = exposure_risk * 3

            # Check correlation risk
            if correlation > self.risk_limits.max_correlation:
                risk_notes.append(f"🔗 High correlation: {correlation:.1%} (max: {self.risk_limits.max_correlation:.1%})")
                risk_penalties["correlation"] = (correlation / self.risk_limits.max_correlation) * 4

            # Check drawdown risk (if available)
            if hasattr(composite_score, 'metadata') and 'drawdown' in composite_score.metadata:
                drawdown = composite_score.metadata['drawdown']
                if drawdown > self.risk_limits.max_drawdown:
                    risk_notes.append(f"📉 High drawdown: {drawdown:.1%} (max: {self.risk_limits.max_drawdown:.1%})")
                    risk_penalties["drawdown"] = (drawdown / self.risk_limits.max_drawdown) * 6

            # Add risk summary if any risks found
            if risk_notes:
                total_penalty = sum(risk_penalties.values())
                risk_notes.append(f"🎯 Total risk penalty: -{total_penalty:.1f} points")

                # Update the composite score with risk information
                if hasattr(composite_score, 'risk_notes'):
                    composite_score.risk_notes = risk_notes
                if hasattr(composite_score, 'risk_penalties'):
                    composite_score.risk_penalties = risk_penalties

            self.logger.info(f"Annotated {composite_score.symbol} with {len(risk_notes)} risk notes")
            return risk_notes

        except Exception as e:
            self.logger.error(f"Error annotating composite score: {e}")
            return ["❌ Error analyzing risk factors"]

    def get_risk_summary(self, symbol: str) -> dict[str, Any]:
        """Get risk summary for a symbol."""
        if not self._last_assessment or self._last_assessment.symbol != symbol:
            return {"error": "No risk assessment available for symbol"}

        assessment = self._last_assessment
        return {
            "symbol": assessment.symbol,
            "risk_score": assessment.risk_score,
            "risk_level": assessment.risk_level.value,
            "risk_factors": assessment.risk_factors,
            "risk_adjusted_score": assessment.risk_adjusted_score,
            "rationale": assessment.risk_rationale,
            "limits": {
                "max_position_size": assessment.max_position_size,
                "max_leverage": assessment.max_leverage,
                "max_portfolio_exposure": assessment.max_portfolio_exposure
            },
            "current": {
                "position_size": assessment.position_size,
                "leverage": assessment.leverage_used,
                "portfolio_exposure": assessment.portfolio_exposure
            }
        }

    async def get_status(self) -> dict[str, Any]:
        """Get current risk status."""
        return {
            "risk_level": "LOW",  # Mock risk level
            "portfolio_exposure": 0.15,  # 15% exposure
            "active_positions": 2,
            "max_drawdown": 0.05,  # 5% max drawdown
            "correlation_risk": "LOW",
            "volatility_risk": "MEDIUM",
            "timestamp": "2025-09-02T03:19:00Z"
        }

    def get_service_status(self) -> dict[str, Any]:
        """Get service status and performance metrics."""
        return {
            "risk_limits": {
                "max_position_size": self.risk_limits.max_position_size,
                "max_leverage": self.risk_limits.max_leverage,
                "max_drawdown": self.risk_limits.max_drawdown,
                "max_portfolio_exposure": self.risk_limits.max_portfolio_exposure,
                "max_correlation": self.risk_limits.max_correlation
            },
            "risk_weights": self.risk_weights,
            "performance": {
                "assessments_performed": self._assessments_performed,
                "risk_violations": self._risk_violations,
                "score_downgrades": self._score_downgrades,
                "last_assessment": self._last_assessment.symbol if self._last_assessment else None
            }
        }

    def _generate_risk_rationale(self, risk_factors: list[str], risk_score: float, risk_level: RiskLevel) -> str:
        """Generate human-readable risk rationale."""
        if not risk_factors:
            return "No significant risk factors identified."

        rationale_parts = [f"Risk Level: {risk_level.value.upper()} (Score: {risk_score:.2f})"]
        rationale_parts.append("Risk Factors:")

        for factor in risk_factors:
            rationale_parts.append(f"• {factor}")

        if risk_level in [RiskLevel.HIGH, RiskLevel.EXTREME]:
            rationale_parts.append("Recommendation: Consider reducing position size or leverage.")
        elif risk_level == RiskLevel.MEDIUM:
            rationale_parts.append("Recommendation: Monitor closely and set tight stop-losses.")
        else:
            rationale_parts.append("Recommendation: Standard risk management applies.")

        return " ".join(rationale_parts)
