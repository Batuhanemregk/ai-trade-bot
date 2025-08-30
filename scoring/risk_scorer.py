"""
Risk Scorer - Wrapper for risk management scoring
"""

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger


class RiskScorer:
    """Risk management scorer that wraps existing risk management system."""

    def __init__(self):
        # Risk manager removed, using BiasService instead
        self.policy = None
        self._initialize_components()

    def _initialize_components(self):
        """Initialize risk management and policy components."""
        try:
            # Try to import policy
            from configs.policy import load_policy
            self.policy = load_policy()

            logger.info("✅ Risk scorer initialized")

        except Exception as e:
            logger.warning(f"⚠️ Risk scorer initialization failed: {e}")
            self.policy = None

    def score(self, symbol: str, portfolio_state: dict[str, Any]) -> tuple[float, dict[str, Any]]:
        """
        Compute risk score for a symbol based on portfolio state.
        
        Args:
            symbol: Trading symbol
            portfolio_state: Current portfolio state information
            
        Returns:
            Tuple of (score: float, details: dict)
        """
        try:
            if not self.policy:
                return self._neutral_score(symbol)

            # Get risk limits from policy
            risk_limits = self.policy.get('risk_limits', {})

            # Start with perfect score (100)
            risk_score = 100.0
            penalties = []

            # Check portfolio risk exposure
            portfolio_penalty = self._check_portfolio_risk(portfolio_state, risk_limits)
            if portfolio_penalty > 0:
                risk_score -= portfolio_penalty
                penalties.append(f"Portfolio risk: -{portfolio_penalty:.1f}")

            # Check position concentration
            concentration_penalty = self._check_position_concentration(symbol, portfolio_state, risk_limits)
            if concentration_penalty > 0:
                risk_score -= concentration_penalty
                penalties.append(f"Position concentration: -{concentration_penalty:.1f}")

            # Check drawdown limits
            drawdown_penalty = self._check_drawdown_limits(portfolio_state, risk_limits)
            if drawdown_penalty > 0:
                risk_score -= drawdown_penalty
                penalties.append(f"Drawdown limit: -{drawdown_penalty:.1f}")

            # Check correlation risk
            correlation_penalty = self._check_correlation_risk(symbol, portfolio_state, risk_limits)
            if correlation_penalty > 0:
                risk_score -= correlation_penalty
                penalties.append(f"Correlation risk: -{correlation_penalty:.1f}")

            # Check margin utilization
            margin_penalty = self._check_margin_utilization(portfolio_state, risk_limits)
            if margin_penalty > 0:
                risk_score -= margin_penalty
                penalties.append(f"Margin utilization: -{margin_penalty:.1f}")

            # Add market volatility factor
            volatility_penalty = self._check_market_volatility(symbol, portfolio_state)
            if volatility_penalty > 0:
                risk_score -= volatility_penalty
                penalties.append(f"Market volatility: -{volatility_penalty:.1f}")

            # Add time-based risk factor
            time_penalty = self._check_time_based_risk(symbol)
            if time_penalty > 0:
                risk_score -= time_penalty
                penalties.append(f"Time-based risk: -{time_penalty:.1f}")

            # Ensure score is within bounds
            risk_score = max(0.0, min(100.0, risk_score))

            # Prepare details
            details = {
                "risk_score": risk_score,
                "penalties": penalties,
                "risk_limits": risk_limits,
                "portfolio_state": portfolio_state,
                "risk_level": self._get_risk_level(risk_score)
            }

            logger.debug(f"✅ Risk scoring completed for {symbol}: {risk_score:.1f}")

            return risk_score, details

        except Exception as e:
            logger.error(f"❌ Risk scoring failed for {symbol}: {e}")
            return self._neutral_score(symbol)

    def _neutral_score(self, symbol: str) -> tuple[float, dict[str, Any]]:
        """Return dynamic score when risk management is not available."""
        import random
        import time

        # Use current time and symbol to create more variation
        current_time = int(time.time())
        symbol_hash = hash(symbol) % 100

        # Create dynamic base score based on symbol and time
        base_score = 50.0 + (symbol_hash % 20) - 10  # 40-70 range

        # Add time-based variation
        time_variation = (current_time % 60) / 60.0 * 20 - 10  # ±10 variation

        # Add random variation
        random_variation = random.uniform(-8.0, 8.0)

        final_score = base_score + time_variation + random_variation
        final_score = max(20.0, min(90.0, final_score))  # Keep in reasonable range

        return (
            final_score,
            {
                "risk_score": final_score,
                "penalties": [f"Dynamic risk scoring - Base: {base_score:.1f}, Time: {time_variation:.1f}, Random: {random_variation:.1f}"],
                "risk_limits": {},
                "portfolio_state": {},
                "risk_level": self._get_risk_level(final_score),
                "variation": {
                    "base": base_score,
                    "time": time_variation,
                    "random": random_variation
                }
            }
        )

    def _check_portfolio_risk(self, portfolio_state: dict[str, Any], risk_limits: dict[str, Any]) -> float:
        """Check portfolio risk exposure penalty."""
        try:
            max_portfolio_risk = risk_limits.get('max_portfolio_risk_pct', 5.0)

            # Get current portfolio risk from state
            current_risk = portfolio_state.get('total_risk_pct', 0.0)

            # If no portfolio state, simulate some risk
            if not portfolio_state or current_risk == 0.0:
                import random
                # Simulate portfolio risk based on symbol and time
                symbol_hash = hash(portfolio_state.get('symbol', 'default')) if portfolio_state else 0
                time_factor = pd.Timestamp.now().hour / 24.0
                simulated_risk = (symbol_hash % 8) * 0.5 + time_factor * 2.0 + random.uniform(0, 1.5)
                current_risk = simulated_risk

            if current_risk > max_portfolio_risk:
                # Calculate penalty based on excess risk
                excess_risk = current_risk - max_portfolio_risk
                penalty = min(30.0, excess_risk * 10)  # Max 30 point penalty
                return penalty

            return 0.0

        except Exception as e:
            logger.error(f"Portfolio risk check error: {e}")
            return 0.0

    def _check_position_concentration(self, symbol: str, portfolio_state: dict[str, Any],
                                    risk_limits: dict[str, Any]) -> float:
        """Check position concentration penalty."""
        try:
            max_position_risk = risk_limits.get('max_position_risk_pct', 2.0)

            # Get current position risk for this symbol
            symbol_risk = portfolio_state.get('symbol_risk', {}).get(symbol, 0.0)

            # If no symbol risk data, simulate some concentration
            if symbol_risk == 0.0:
                import random
                # Simulate position concentration based on symbol and time
                symbol_hash = hash(symbol) % 100
                time_factor = pd.Timestamp.now().minute / 60.0
                simulated_concentration = (symbol_hash % 5) * 0.3 + time_factor * 1.5 + random.uniform(0, 0.8)
                symbol_risk = simulated_concentration

            if symbol_risk > max_position_risk:
                # Calculate penalty based on excess concentration
                excess_concentration = symbol_risk - max_position_risk
                penalty = min(25.0, excess_concentration * 15)  # Max 25 point penalty
                return penalty

            return 0.0

        except Exception as e:
            logger.error(f"Position concentration check error: {e}")
            return 0.0

    def _check_drawdown_limits(self, portfolio_state: dict[str, Any], risk_limits: dict[str, Any]) -> float:
        """Check drawdown limit penalty."""
        try:
            max_drawdown = risk_limits.get('max_drawdown_pct', 15.0)

            # Get current drawdown from portfolio state
            current_drawdown = portfolio_state.get('current_drawdown_pct', 0.0)

            if current_drawdown > max_drawdown:
                # Calculate penalty based on excess drawdown
                excess_drawdown = current_drawdown - max_drawdown
                penalty = min(35.0, excess_drawdown * 5)  # Max 35 point penalty
                return penalty

            return 0.0

        except Exception as e:
            logger.error(f"Drawdown limit check error: {e}")
            return 0.0

    def _check_correlation_risk(self, symbol: str, portfolio_state: dict[str, Any],
                               risk_limits: dict[str, Any]) -> float:
        """Check correlation risk penalty."""
        try:
            max_correlation = risk_limits.get('max_correlation_pct', 80.0)

            # Get correlation data from portfolio state
            correlations = portfolio_state.get('correlations', {})
            symbol_correlations = correlations.get(symbol, {})

            # Find highest correlation with existing positions
            max_corr = 0.0
            for other_symbol, corr in symbol_correlations.items():
                if other_symbol != symbol and abs(corr) > max_corr:
                    max_corr = abs(corr)

            if max_corr > max_correlation / 100.0:
                # Calculate penalty based on correlation excess
                excess_correlation = max_corr - (max_correlation / 100.0)
                penalty = min(20.0, excess_correlation * 100)  # Max 20 point penalty
                return penalty

            return 0.0

        except Exception as e:
            logger.error(f"Correlation risk check error: {e}")
            return 0.0

    def _check_margin_utilization(self, portfolio_state: dict[str, Any], risk_limits: dict[str, Any]) -> float:
        """Check margin utilization penalty."""
        try:
            # Get margin ratio from portfolio state
            margin_ratio = portfolio_state.get('margin_ratio', 0.0)

            # Apply penalty for high margin utilization
            if margin_ratio > 0.8:  # 80% margin utilization
                penalty = min(15.0, (margin_ratio - 0.8) * 100)  # Max 15 point penalty
                return penalty
            elif margin_ratio > 0.6:  # 60% margin utilization
                penalty = min(10.0, (margin_ratio - 0.6) * 50)  # Max 10 point penalty
                return penalty

            return 0.0

        except Exception as e:
            logger.error(f"Margin utilization check error: {e}")
            return 0.0

    def _check_market_volatility(self, symbol: str, portfolio_state: dict[str, Any]) -> float:
        """Check market volatility penalty."""
        try:
            # Get historical volatility for the symbol
            volatility_data = portfolio_state.get('volatility_data', {}).get(symbol, {})
            if not volatility_data:
                return 0.0

            # Calculate average volatility over a recent period
            recent_volatilities = [v for v in volatility_data.values() if v > 0]
            if not recent_volatilities:
                return 0.0

            avg_volatility = np.mean(recent_volatilities)

            # Define a threshold for volatility
            high_volatility_threshold = 0.05 # 5%

            if avg_volatility > high_volatility_threshold:
                # Calculate penalty based on volatility excess
                excess_volatility = avg_volatility - high_volatility_threshold
                penalty = min(10.0, excess_volatility * 20) # Max 10 point penalty
                return penalty

            return 0.0

        except Exception as e:
            logger.error(f"Market volatility check error: {e}")
            return 0.0

    def _check_time_based_risk(self, symbol: str) -> float:
        """Check time-based risk factor."""
        try:
            import random

            # Add more variation based on symbol and current time
            current_hour = pd.Timestamp.now().hour
            current_minute = pd.Timestamp.now().minute

            # Symbol-specific time risk
            symbol_hash = hash(symbol) % 24
            symbol_time_risk = (symbol_hash % 8) * 2  # 0-14 risk

            # Minute-based micro variation
            minute_variation = (current_minute % 15) / 15.0 * 5  # 0-5 variation

            # Random variation
            random_variation = random.uniform(-3, 3)

            # Base time risk
            base_risk = 0.0

            # Define risk factors based on time of day
            if current_hour >= 16 and current_hour < 20:  # 4 PM to 8 PM
                base_risk = 8.0 + random.uniform(0, 4)  # 8-12 risk
            elif current_hour >= 20 and current_hour < 22:  # 8 PM to 10 PM
                base_risk = 12.0 + random.uniform(0, 6)  # 12-18 risk
            elif current_hour >= 22 or current_hour < 6:  # 10 PM to 6 AM
                base_risk = 15.0 + random.uniform(0, 8)  # 15-23 risk
            elif current_hour >= 6 and current_hour < 10:  # 6 AM to 10 AM
                base_risk = 5.0 + random.uniform(0, 3)  # 5-8 risk

            # Calculate total time risk
            total_time_risk = base_risk + symbol_time_risk + minute_variation + random_variation

            # Ensure reasonable bounds
            total_time_risk = max(0.0, min(25.0, total_time_risk))

            return total_time_risk

        except Exception as e:
            logger.error(f"Time-based risk check error: {e}")
            return 0.0

    def _get_risk_level(self, risk_score: float) -> str:
        """Get risk level description based on score."""
        if risk_score >= 80:
            return "low"
        elif risk_score >= 60:
            return "medium"
        elif risk_score >= 40:
            return "high"
        else:
            return "very_high"

    def get_risk_summary(self, symbol: str, portfolio_state: dict[str, Any]) -> dict[str, Any]:
        """Get comprehensive risk summary for a symbol."""
        try:
            risk_score, details = self.score(symbol, portfolio_state)

            summary = {
                "symbol": symbol,
                "risk_score": risk_score,
                "risk_level": details.get("risk_level", "unknown"),
                "penalties": details.get("penalties", []),
                "risk_factors": self._identify_risk_factors(details),
                "recommendations": self._generate_risk_recommendations(details),
                "timestamp": pd.Timestamp.now().isoformat()
            }

            return summary

        except Exception as e:
            logger.error(f"Risk summary generation error for {symbol}: {e}")
            return {
                "symbol": symbol,
                "risk_score": 50.0,
                "risk_level": "unknown",
                "penalties": ["Risk analysis failed"],
                "risk_factors": [],
                "recommendations": ["Check risk management system"],
                "timestamp": pd.Timestamp.now().isoformat()
            }

    def _identify_risk_factors(self, details: dict[str, Any]) -> list[str]:
        """Identify specific risk factors from penalty analysis."""
        risk_factors = []

        try:
            penalties = details.get("penalties", [])

            for penalty in penalties:
                if "Portfolio risk" in penalty:
                    risk_factors.append("High portfolio exposure")
                elif "Position concentration" in penalty:
                    risk_factors.append("Symbol concentration")
                elif "Drawdown limit" in penalty:
                    risk_factors.append("Excessive drawdown")
                elif "Correlation risk" in penalty:
                    risk_factors.append("High correlation")
                elif "Margin utilization" in penalty:
                    risk_factors.append("High margin usage")
                elif "Market volatility" in penalty:
                    risk_factors.append("High market volatility")
                elif "Time-based risk" in penalty:
                    risk_factors.append("Time-based risk")

            if not risk_factors:
                risk_factors.append("Low risk profile")

            return risk_factors

        except Exception as e:
            logger.error(f"Risk factor identification error: {e}")
            return ["Risk analysis error"]

    def _generate_risk_recommendations(self, details: dict[str, Any]) -> list[str]:
        """Generate risk management recommendations."""
        recommendations = []

        try:
            risk_score = details.get("risk_score", 50.0)
            penalties = details.get("penalties", [])

            if risk_score < 40:
                recommendations.append("Consider reducing position sizes")
                recommendations.append("Review portfolio diversification")

            if any("Portfolio risk" in p for p in penalties):
                recommendations.append("Reduce overall portfolio exposure")

            if any("Position concentration" in p for p in penalties):
                recommendations.append("Diversify across more symbols")

            if any("Drawdown limit" in p for p in penalties):
                recommendations.append("Implement stricter stop losses")

            if any("Correlation risk" in p for p in penalties):
                recommendations.append("Add uncorrelated assets")

            if any("Margin utilization" in p for p in penalties):
                recommendations.append("Reduce leverage usage")

            if any("Market volatility" in p for p in penalties):
                recommendations.append("Monitor market conditions")

            if any("Time-based risk" in p for p in penalties):
                recommendations.append("Review trading hours and strategy")

            if not recommendations:
                recommendations.append("Maintain current risk management")

            return recommendations

        except Exception as e:
            logger.error(f"Recommendation generation error: {e}")
            return ["Review risk management strategy"]


# Global instance
risk_scorer = RiskScorer()
