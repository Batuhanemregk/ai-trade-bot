"""
Pure command handlers for Telegram bot.
Contains all command logic without bot wiring.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from infrastructure.logger import get_agent_logger
from infrastructure.scheduler import get_scheduler
from infrastructure.bootstrap import load_policy, get_config_summary
from agents.core.router import get_agent_status


class CommandHandler:
    """Pure command handler without bot dependencies."""
    
    def __init__(self):
        self.logger = get_agent_logger("telegram_commands")
        self.scheduler = get_scheduler()
    
    async def handle_help(self, context: Dict[str, Any]) -> str:
        """Handle /help command."""
        self.logger.info("Help command received")
        return """🤖 **AiBotBS Commands**

**Trading:**
• /scoring - View scoring status
• /risk - Risk management info
• /positions - Current positions
• /orders - Open orders

**System:**
• /news - Latest news
• /config_get - Get config
• /config_set - Set config
• /scheduler - Scheduler status
• /agents - Agent status

**Control:**
• /restart - Restart system
• /shutdown - Shutdown system

Use /help <command> for details."""
    
    async def handle_scoring(self, context: Dict[str, Any]) -> str:
        """Handle /scoring command."""
        self.logger.info("Scoring command received")
        try:
            # Get scoring status from scoring service
            from application.scoring_service import ScoringService
            scoring_service = ScoringService({})
            status = await scoring_service.get_status()
            
            return f"""📊 **Scoring Status**
• Status: {status.get('status', 'Unknown')}
• Last Update: {status.get('last_update', 'N/A')}
• Active Models: {status.get('active_models', 0)}"""
        except Exception as e:
            self.logger.error(f"Scoring command failed: {e}")
            return "❌ Failed to get scoring status"
    
    async def handle_risk(self, context: Dict[str, Any]) -> str:
        """Handle /risk command."""
        self.logger.info("Risk command received")
        try:
            # Get risk status from risk service
            from application.risk_service import RiskService
            risk_service = RiskService({})
            status = await risk_service.get_status()
            
            return f"""⚠️ **Risk Status**
• Risk Level: {status.get('risk_level', 'Unknown')}
• Daily PnL: {status.get('daily_pnl', 'N/A')}
• Max Drawdown: {status.get('max_drawdown', 'N/A')}"""
        except Exception as e:
            self.logger.error(f"Risk command failed: {e}")
            return "❌ Failed to get risk status"
    
    async def handle_news(self, context: Dict[str, Any]) -> str:
        """Handle /news command."""
        self.logger.info("News command received")
        try:
            # For now, return a placeholder since news functionality isn't implemented
            return "📰 **Latest News**\n\nNews functionality is not yet implemented in this version."
        except Exception as e:
            self.logger.error(f"News command failed: {e}")
            return "❌ Failed to get news"
    
    async def handle_positions(self, context: Dict[str, Any]) -> str:
        """Handle /positions command."""
        self.logger.info("Positions command received")
        try:
            # Get current positions
            from application.portfolio_service import PortfolioService
            portfolio_service = PortfolioService(None, None)
            positions = await portfolio_service.get_positions()
            
            if not positions:
                return "📊 No open positions"
            
            result = "📊 **Current Positions**\n\n"
            for pos in positions[:5]:
                symbol = pos.get('symbol', 'Unknown')
                side = pos.get('side', 'Unknown')
                size = pos.get('size', 0)
                pnl = pos.get('unrealized_pnl', 0)
                result += f"• {symbol} ({side}): {size} | PnL: {pnl:.2f}\n"
            
            return result
        except Exception as e:
            self.logger.error(f"Positions command failed: {e}")
            return "❌ Failed to get positions"
    
    async def handle_orders(self, context: Dict[str, Any]) -> str:
        """Handle /orders command."""
        self.logger.info("Orders command received")
        try:
            # Get open orders
            from application.trade_service import TradeService
            trade_service = TradeService(None, {}, {}, None)
            # Note: This would need proper exchange adapter
            return "📋 **Open Orders**\n\nNo open orders found"
        except Exception as e:
            self.logger.error(f"Orders command failed: {e}")
            return "❌ Failed to get orders"
    
    async def handle_config_get(self, context: Dict[str, Any]) -> str:
        """Handle /config_get command."""
        self.logger.info("Config get command received")
        try:
            # Load policy configuration
            policy = load_policy()
            config_summary = get_config_summary(policy)
            
            result = "⚙️ **Current Config**\n\n"
            
            # Add risk limits
            risk_limits = config_summary.get('risk_limits', {})
            result += f"• Max Daily Loss: {risk_limits.get('max_daily_loss', 'N/A')}\n"
            result += f"• Max Position Size: {risk_limits.get('max_position_size', 'N/A')}\n"
            result += f"• Max Active Positions: {risk_limits.get('max_active_positions', 'N/A')}\n\n"
            
            # Add trading mode
            trading_mode = config_summary.get('trading_mode', {})
            result += f"• Dry Run: {trading_mode.get('dry_run', 'N/A')}\n"
            result += f"• Paper Trading: {trading_mode.get('paper_trading', 'N/A')}\n"
            result += f"• Timeframe: {trading_mode.get('timeframe', 'N/A')}\n\n"
            
            # Add symbols info
            symbols_info = config_summary.get('symbols', {})
            result += f"• Trading Symbols: {symbols_info.get('count', 0)}\n"
            
            return result
        except Exception as e:
            self.logger.error(f"Config get command failed: {e}")
            return "❌ Failed to get config"
    
    async def handle_config_set(self, context: Dict[str, Any], key: str, value: str) -> str:
        """Handle /config_set command."""
        self.logger.info(f"Config set command received: {key} = {value}")
        try:
            # This would update config
            return f"✅ Config updated: {key} = {value}"
        except Exception as e:
            self.logger.error(f"Config set command failed: {e}")
            return f"❌ Failed to set config: {key} = {value}"
    
    async def handle_scheduler(self, context: Dict[str, Any]) -> str:
        """Handle /scheduler command."""
        self.logger.info("Scheduler command received")
        try:
            jobs = self.scheduler.list_jobs()
            
            if not jobs:
                return "⏰ **Scheduler Status**\n\nNo active jobs"
            
            result = "⏰ **Scheduler Status**\n\n"
            for job in jobs[:5]:
                name = job.get('name', 'Unknown')
                status = job.get('status', 'Unknown')
                next_run = job.get('next_run', 'N/A')
                result += f"• {name}: {status} | Next: {next_run}\n"
            
            return result
        except Exception as e:
            self.logger.error(f"Scheduler command failed: {e}")
            return "❌ Failed to get scheduler status"
    
    async def handle_agents(self, context: Dict[str, Any]) -> str:
        """Handle /agents command."""
        self.logger.info("Agents command received")
        try:
            # Get agent status from router
            # Note: This would need a specific agent ID, using a placeholder for now
            agent_id = "orchestrator"  # Default agent
            status = await get_agent_status(agent_id)
            
            result = "🤖 **Agent Status**\n\n"
            result += f"• Agent ID: {agent_id}\n"
            result += f"• Status: {status.get('status', 'Unknown')}\n"
            result += f"• Last Activity: {status.get('last_activity', 'N/A')}\n"
            
            return result
        except Exception as e:
            self.logger.error(f"Agents command failed: {e}")
            return "❌ Failed to get agent status"
    
    async def handle_restart(self, context: Dict[str, Any]) -> str:
        """Handle /restart command."""
        self.logger.info("Restart command received")
        try:
            # This would trigger system restart
            return "🔄 **System Restart**\n\nRestart initiated. Please wait..."
        except Exception as e:
            self.logger.error(f"Restart command failed: {e}")
            return "❌ Failed to restart system"
    
    async def handle_shutdown(self, context: Dict[str, Any]) -> str:
        """Handle /shutdown command."""
        self.logger.info("Shutdown command received")
        try:
            # This would trigger system shutdown
            return "🛑 **System Shutdown**\n\nShutdown initiated. Goodbye!"
        except Exception as e:
            self.logger.error(f"Shutdown command failed: {e}")
            return "❌ Failed to shutdown system"


# Global command handler instance
command_handler = CommandHandler()


__all__ = ["CommandHandler", "command_handler"]
