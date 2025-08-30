"""
Risk Monitor - Handles risk management and validation.
Follows Single Responsibility Principle by only handling risk monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from domain.models import RiskAssessment, RiskAlert, Position, PortfolioState
from application.portfolio_service import PortfolioService
from telegram_bot.bot import TelegramBot


class RiskMonitor:
    """
    Risk monitor that validates trading decisions and monitors portfolio risk.
    
    Responsibilities:
    - Validate trading signals against risk parameters
    - Monitor portfolio risk metrics
    - Generate risk alerts
    - Enforce risk limits
    """
    
    def __init__(
        self,
        portfolio_service: PortfolioService,
        telegram_bot: TelegramBot,
        config: Dict[str, Any]
    ):
        self.portfolio_service = portfolio_service
        self.telegram_bot = telegram_bot
        self.config = config
        
        # Risk thresholds from config
        self.max_daily_loss = config.get('risk', {}).get('max_daily_loss', 0.05)  # 5%
        self.max_position_size = config.get('risk', {}).get('max_position_size', 0.1)  # 10%
        self.max_active_positions = config.get('risk', {}).get('max_active_positions', 5)
        self.max_correlation = config.get('risk', {}).get('max_correlation', 0.7)
        self.stop_loss_atr_multiplier = config.get('risk', {}).get('stop_loss_atr_multiplier', 2.0)
        
        # Risk state tracking
        self.daily_pnl = 0.0
        self.daily_loss_limit = 0.0
        self.risk_alerts = []
        self.last_risk_check = datetime.now()
        self.risk_check_interval = 60  # 1 minute
        
        # Alert thresholds
        self.pnl_alert_threshold = 0.02  # 2% PnL change
        self.position_size_alert_threshold = 0.08  # 8% position size
        
        logger.info("Risk Monitor initialized")
    
    async def assess_risk(
        self, 
        symbol: str, 
        score: float, 
        signal_type: str, 
        market_data: Dict[str, Any]
    ) -> RiskAssessment:
        """
        Assess risk for a trading signal.
        
        Args:
            symbol: Trading symbol
            score: Signal score (0-1)
            signal_type: Type of signal (long/short)
            market_data: Market data for analysis
            
        Returns:
            Risk assessment with risk level and factors
        """
        try:
            risk_factors = []
            risk_level = "low"
            
            # Check signal score
            if score < 0.6:
                risk_factors.append(f"Low signal score: {score:.2f}")
                risk_level = "medium"
            
            # Check position size limits
            position_size_risk = await self._check_position_size_risk(symbol, market_data)
            if position_size_risk:
                risk_factors.append(position_size_risk)
                risk_level = "high"
            
            # Check correlation risk
            correlation_risk = await self._check_correlation_risk(symbol)
            if correlation_risk:
                risk_factors.append(correlation_risk)
                risk_level = "medium"
            
            # Check daily loss limit
            daily_loss_risk = await self._check_daily_loss_risk()
            if daily_loss_risk:
                risk_factors.append(daily_loss_risk)
                risk_level = "high"
            
            # Check active positions limit
            position_count_risk = await self._check_position_count_risk()
            if position_count_risk:
                risk_factors.append(position_count_risk)
                risk_level = "medium"
            
            # Check market volatility
            volatility_risk = self._check_volatility_risk(market_data)
            if volatility_risk:
                risk_factors.append(volatility_risk)
                risk_level = "medium"
            
            # Determine final risk level
            if len([f for f in risk_factors if "high" in f.lower()]) > 0:
                risk_level = "high"
            elif len([f for f in risk_factors if "medium" in f.lower()]) > 2:
                risk_level = "medium"
            
            # Create risk assessment
            assessment = RiskAssessment(
                symbol=symbol,
                risk_level=risk_level,
                risk_factors=risk_factors,
                score=score,
                signal_type=signal_type,
                timestamp=datetime.now(),
                recommendations=self._generate_risk_recommendations(risk_level, risk_factors)
            )
            
            logger.info(f"Risk assessment for {symbol}: {risk_level} risk level, {len(risk_factors)} factors")
            
            # Send risk alert if high risk
            if risk_level == "high":
                await self._send_risk_alert(symbol, assessment)
            
            return assessment
            
        except Exception as e:
            logger.error(f"Risk assessment failed for {symbol}: {e}")
            # Return high risk assessment on failure
            return RiskAssessment(
                symbol=symbol,
                risk_level="high",
                risk_factors=[f"Risk assessment failed: {str(e)}"],
                score=score,
                signal_type=signal_type,
                timestamp=datetime.now(),
                recommendations=["Do not trade until risk assessment is fixed"]
            )
    
    async def _check_position_size_risk(self, symbol: str, market_data: Dict[str, Any]) -> Optional[str]:
        """Check if position size would exceed limits."""
        try:
            # Get current portfolio value
            portfolio_value = await self.portfolio_service.get_portfolio_value()
            if not portfolio_value:
                return "Cannot determine portfolio value"
            
            # Get current price
            current_price = market_data.get("ticker", {}).get("last", 0)
            if not current_price:
                return "Cannot determine current price"
            
            # Calculate maximum position size
            max_position_value = portfolio_value * self.max_position_size
            
            # For now, assume we want to use 80% of max position size
            suggested_position_value = max_position_value * 0.8
            
            if suggested_position_value < 100:  # Minimum $100 position
                return f"Position size too small: ${suggested_position_value:.2f}"
            
            return None
            
        except Exception as e:
            logger.error(f"Position size risk check failed: {e}")
            return f"Position size validation error: {str(e)}"
    
    async def _check_correlation_risk(self, symbol: str) -> Optional[str]:
        """Check correlation with existing positions."""
        try:
            # Get current positions
            positions = await self.portfolio_service.get_positions()
            if not positions or len(positions) == 0:
                return None
            
            # Simple correlation check based on symbol similarity
            # In a real system, this would use historical price correlation
            correlated_symbols = []
            for pos in positions:
                if self._are_symbols_correlated(symbol, pos.symbol):
                    correlated_symbols.append(pos.symbol)
            
            if len(correlated_symbols) > 0:
                return f"High correlation with existing positions: {', '.join(correlated_symbols)}"
            
            return None
            
        except Exception as e:
            logger.error(f"Correlation risk check failed: {e}")
            return f"Correlation validation error: {str(e)}"
    
    def _are_symbols_correlated(self, symbol1: str, symbol2: str) -> bool:
        """Simple correlation check based on symbol similarity."""
        # Extract base currency (e.g., BTC from BTC-USDT)
        base1 = symbol1.split('-')[0] if '-' in symbol1 else symbol1
        base2 = symbol2.split('-')[0] if '-' in symbol2 else symbol2
        
        # Check if same base currency
        if base1 == base2:
            return True
        
        # Check for common correlation patterns
        correlated_pairs = [
            ('BTC', 'ETH'),  # Bitcoin and Ethereum often correlated
            ('ETH', 'BNB'),  # Ethereum and Binance Coin
            ('ADA', 'DOT'),  # Cardano and Polkadot
        ]
        
        for pair in correlated_pairs:
            if (base1 in pair and base2 in pair):
                return True
        
        return False
    
    async def _check_daily_loss_risk(self) -> Optional[str]:
        """Check if daily loss limit would be exceeded."""
        try:
            # Get current daily PnL
            daily_pnl = await self.portfolio_service.get_daily_pnl()
            
            # Calculate daily loss limit
            portfolio_value = await self.portfolio_service.get_portfolio_value()
            if portfolio_value:
                daily_loss_limit = portfolio_value * self.max_daily_loss
                
                if daily_pnl < -daily_loss_limit:
                    return f"Daily loss limit exceeded: ${daily_pnl:.2f} < -${daily_loss_limit:.2f}"
                
                # Check if approaching limit
                if daily_pnl < -daily_loss_limit * 0.8:
                    return f"Approaching daily loss limit: ${daily_pnl:.2f} (80% of limit)"
            
            return None
            
        except Exception as e:
            logger.error(f"Daily loss risk check failed: {e}")
            return f"Daily loss validation error: {str(e)}"
    
    async def _check_position_count_risk(self) -> Optional[str]:
        """Check if active position count would exceed limits."""
        try:
            # Get current position count
            positions = await self.portfolio_service.get_positions()
            current_count = len(positions) if positions else 0
            
            if current_count >= self.max_active_positions:
                return f"Maximum active positions reached: {current_count}/{self.max_active_positions}"
            
            # Check if approaching limit
            if current_count >= self.max_active_positions * 0.8:
                return f"Approaching position limit: {current_count}/{self.max_active_positions}"
            
            return None
            
        except Exception as e:
            logger.error(f"Position count risk check failed: {e}")
            return f"Position count validation error: {str(e)}"
    
    def _check_volatility_risk(self, market_data: Dict[str, Any]) -> Optional[str]:
        """Check market volatility risk."""
        try:
            ohlcv = market_data.get("ohlcv", [])
            if not ohlcv or len(ohlcv) < 20:
                return "Insufficient market data for volatility analysis"
            
            # Calculate simple volatility (price range over last 20 candles)
            prices = [float(candle[4]) for candle in ohlcv[-20:]]  # Close prices
            if len(prices) < 2:
                return "Insufficient price data"
            
            price_range = max(prices) - min(prices)
            avg_price = sum(prices) / len(prices)
            volatility = price_range / avg_price if avg_price > 0 else 0
            
            # High volatility threshold (5%)
            if volatility > 0.05:
                return f"High market volatility: {volatility:.2%}"
            
            return None
            
        except Exception as e:
            logger.error(f"Volatility risk check failed: {e}")
            return f"Volatility validation error: {str(e)}"
    
    def _generate_risk_recommendations(self, risk_level: str, risk_factors: List[str]) -> List[str]:
        """Generate risk mitigation recommendations."""
        recommendations = []
        
        if risk_level == "high":
            recommendations.extend([
                "Do not execute this trade",
                "Review risk parameters",
                "Consider reducing position size",
                "Wait for better market conditions"
            ])
        elif risk_level == "medium":
            recommendations.extend([
                "Proceed with caution",
                "Consider reducing position size",
                "Set tighter stop losses",
                "Monitor closely"
            ])
        else:
            recommendations.extend([
                "Trade appears safe",
                "Use standard position sizing",
                "Set normal stop losses"
            ])
        
        # Add specific recommendations based on risk factors
        for factor in risk_factors:
            if "position size" in factor.lower():
                recommendations.append("Reduce position size by 50%")
            elif "correlation" in factor.lower():
                recommendations.append("Consider closing correlated positions first")
            elif "daily loss" in factor.lower():
                recommendations.append("Wait for daily reset or reduce risk")
            elif "volatility" in factor.lower():
                recommendations.append("Use wider stop losses for volatility")
        
        return list(set(recommendations))  # Remove duplicates
    
    async def _send_risk_alert(self, symbol: str, assessment: RiskAssessment):
        """Send risk alert through Telegram."""
        try:
            alert_message = (
                f"🚨 HIGH RISK ALERT: {symbol}\n"
                f"Risk Level: {assessment.risk_level.upper()}\n"
                f"Risk Factors:\n"
            )
            
            for factor in assessment.risk_factors[:5]:  # Limit to 5 factors
                alert_message += f"• {factor}\n"
            
            alert_message += f"\nRecommendations:\n"
            for rec in assessment.recommendations[:3]:  # Limit to 3 recommendations
                alert_message += f"• {rec}\n"
            
            await self.telegram_bot.send_notification(
                "High Risk Alert",
                alert_message,
                "error"
            )
            
            # Store alert
            self.risk_alerts.append({
                "symbol": symbol,
                "risk_level": assessment.risk_level,
                "timestamp": datetime.now(),
                "factors": assessment.risk_factors,
                "message": alert_message
            })
            
        except Exception as e:
            logger.error(f"Failed to send risk alert: {e}")
    
    async def monitor_portfolio_risk(self) -> Dict[str, Any]:
        """Monitor overall portfolio risk metrics."""
        try:
            # Get portfolio state
            portfolio_state = await self.portfolio_service.get_portfolio_state()
            if not portfolio_state:
                return {"error": "Cannot get portfolio state"}
            
            # Calculate risk metrics
            total_exposure = portfolio_state.get("total_exposure", 0)
            portfolio_value = await self.portfolio_service.get_portfolio_value()
            
            risk_metrics = {
                "timestamp": datetime.now(),
                "portfolio_value": portfolio_value,
                "total_exposure": total_exposure,
                "exposure_ratio": total_exposure / portfolio_value if portfolio_value > 0 else 0,
                "daily_pnl": portfolio_state.get("daily_pnl", 0),
                "daily_loss_limit": portfolio_value * self.max_daily_loss if portfolio_value else 0,
                "position_count": portfolio_state.get("position_count", 0),
                "max_positions": self.max_active_positions,
                "risk_level": "low"
            }
            
            # Determine overall risk level
            risk_score = 0
            if risk_metrics["exposure_ratio"] > 0.8:
                risk_score += 3
            elif risk_metrics["exposure_ratio"] > 0.6:
                risk_score += 2
            elif risk_metrics["exposure_ratio"] > 0.4:
                risk_score += 1
            
            if risk_metrics["daily_pnl"] < -risk_metrics["daily_loss_limit"] * 0.8:
                risk_score += 2
            
            if risk_metrics["position_count"] > self.max_active_positions * 0.8:
                risk_score += 1
            
            # Set risk level based on score
            if risk_score >= 4:
                risk_metrics["risk_level"] = "high"
            elif risk_score >= 2:
                risk_metrics["risk_level"] = "medium"
            else:
                risk_metrics["risk_level"] = "low"
            
            # Send alert if risk level changed
            await self._check_risk_level_change(risk_metrics)
            
            return risk_metrics
            
        except Exception as e:
            logger.error(f"Portfolio risk monitoring failed: {e}")
            return {"error": str(e)}
    
    async def _check_risk_level_change(self, current_metrics: Dict[str, Any]):
        """Check if risk level has changed and send alerts."""
        try:
            # This would compare with previous risk level
            # For now, just log the current risk level
            risk_level = current_metrics.get("risk_level", "unknown")
            logger.info(f"Current portfolio risk level: {risk_level}")
            
            if risk_level == "high":
                await self._send_portfolio_risk_alert(current_metrics)
                
        except Exception as e:
            logger.error(f"Risk level change check failed: {e}")
    
    async def _send_portfolio_risk_alert(self, metrics: Dict[str, Any]):
        """Send portfolio risk alert."""
        try:
            alert_message = (
                f"📊 PORTFOLIO RISK ALERT\n"
                f"Risk Level: {metrics['risk_level'].upper()}\n"
                f"Portfolio Value: ${metrics['portfolio_value']:,.2f}\n"
                f"Total Exposure: ${metrics['total_exposure']:,.2f}\n"
                f"Exposure Ratio: {metrics['exposure_ratio']:.1%}\n"
                f"Daily PnL: ${metrics['daily_pnl']:,.2f}\n"
                f"Position Count: {metrics['position_count']}/{metrics['max_positions']}"
            )
            
            await self.telegram_bot.send_notification(
                "Portfolio Risk Alert",
                alert_message,
                "warning"
            )
            
        except Exception as e:
            logger.error(f"Failed to send portfolio risk alert: {e}")
    
    async def reset_daily_metrics(self):
        """Reset daily risk metrics."""
        try:
            self.daily_pnl = 0.0
            self.daily_loss_limit = 0.0
            self.risk_alerts = []
            self.last_risk_check = datetime.now()
            
            logger.info("Daily risk metrics reset")
            
        except Exception as e:
            logger.error(f"Failed to reset daily risk metrics: {e}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get summary of current risk state."""
        return {
            "daily_pnl": self.daily_pnl,
            "daily_loss_limit": self.daily_loss_limit,
            "max_daily_loss": self.max_daily_loss,
            "max_position_size": self.max_position_size,
            "max_active_positions": self.max_active_positions,
            "risk_alerts_count": len(self.risk_alerts),
            "last_risk_check": self.last_risk_check,
            "risk_check_interval": self.risk_check_interval
        }
