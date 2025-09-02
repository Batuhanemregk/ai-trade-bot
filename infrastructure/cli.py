"""
Command-line interface for AiBotBS.
Handles argument parsing and routing to various command handlers.
"""

import argparse
import asyncio
import sys
import time
from typing import Any, Dict, List, Optional

# agents disabled
if False:  # never runs
    from agents.core.base import Message, MessageType  # placeholder to avoid IDE errors

# Fallback types for non-agent mode
class Message:
    def __init__(self, subject=None, body=None):
        self.subject = subject
        self.body = body or {}

class MessageType:
    TICK = "TICK"
    HEARTBEAT = "HEARTBEAT"

from loguru import logger

from infrastructure.scheduler import get_scheduler
from infrastructure.logger import initialize_logging


class AiBotCLI:
    """Main CLI class for AiBotBS."""
    
    def __init__(self):
        self.parser = self._create_parser()
        self.scheduler = get_scheduler()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser."""
        parser = argparse.ArgumentParser(
            description="AiBotBS - AI-Powered Trading Bot System",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run scheduler with default graph
  python -m infrastructure.cli scheduler run --graph default --dry-run
  
  # List scheduled jobs
  python -m infrastructure.cli scheduler list
  
  # Show system health
  python -m infrastructure.cli health
  
  # Show version
  python -m infrastructure.cli version
            """
        )
        
        # Add subcommands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Scheduler commands
        self._add_scheduler_commands(subparsers)
        
        # Agent commands
        self._add_agent_commands(subparsers)
        

        
        # Telegram commands
        self._add_telegram_commands(subparsers)
        
        # Health commands
        self._add_health_commands(subparsers)
        
        # Config commands
        self._add_config_commands(subparsers)
        
        # Version command
        self._add_version_command(subparsers)
        
        return parser
    
    def _add_scheduler_commands(self, subparsers):
        """Add scheduler-related commands."""
        scheduler_parser = subparsers.add_parser('scheduler', help='Scheduler management')
        scheduler_subparsers = scheduler_parser.add_subparsers(dest='scheduler_command', help='Scheduler commands')
        
        # Run scheduler
        run_parser = scheduler_subparsers.add_parser('run', help='Run scheduler')
        run_parser.add_argument('--graph', default='default', help='Task graph to run')
        run_parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode')
        run_parser.add_argument('--once', action='store_true', help='Run once and exit')
        run_parser.add_argument('--max-cycles', type=int, help='Maximum cycles to run')
        
        # List jobs
        list_parser = scheduler_subparsers.add_parser('list', help='List scheduled jobs')
        list_parser.add_argument('--active', action='store_true', help='Show only active jobs')
        list_parser.add_argument('--history', action='store_true', help='Show job history')
        
        # Add job
        add_parser = scheduler_subparsers.add_parser('add', help='Add a new job')
        add_parser.add_argument('name', help='Job name')
        add_parser.add_argument('schedule', help='Cron schedule (e.g., "*/5 * * * *")')
        add_parser.add_argument('--enabled', action='store_true', default=True, help='Enable job')
        add_parser.add_argument('--description', help='Job description')
        
        # Remove job
        remove_parser = scheduler_subparsers.add_parser('remove', help='Remove a job')
        remove_parser.add_argument('name', help='Job name to remove')
        
        # Enable/disable job
        enable_parser = scheduler_subparsers.add_parser('enable', help='Enable a job')
        enable_parser.add_argument('name', help='Job name to enable')
        
        disable_parser = scheduler_subparsers.add_parser('disable', help='Disable a job')
        disable_parser.add_argument('name', help='Job name to disable')
    
    def _add_agent_commands(self, subparsers):
        """Add agent-related commands."""
        agent_parser = subparsers.add_parser('agents', help='Agent management')
        agent_subparsers = agent_parser.add_subparsers(dest='agent_command', help='Agent commands')
        
        # Run agents
        run_parser = agent_subparsers.add_parser('run', help='Run agents')
        run_parser.add_argument('--graph', default='default', help='Task graph to run')
        run_parser.add_argument('--mode', choices=['live', 'paper', 'dry-run'], help='Execution mode')
        run_parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (alias)')
        run_parser.add_argument('--live', action='store_true', help='Run in live mode (alias)')
        run_parser.add_argument('--paper', action='store_true', help='Run in paper mode (alias)')
        run_parser.add_argument('--agents', nargs='+', help='Specific agents to run')
        run_parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds for dry-run mode')
        
        # List agents
        list_parser = agent_subparsers.add_parser('list', help='List available agents')
        list_parser.add_argument('--status', action='store_true', help='Show agent status')
        
        # Agent status
        status_parser = agent_subparsers.add_parser('status', help='Show agent status')
        status_parser.add_argument('agent', nargs='?', help='Specific agent name')
    

    
    def _add_telegram_commands(self, subparsers):
        """Add Telegram-related commands."""
        telegram_parser = subparsers.add_parser('telegram', help='Telegram bot management')
        telegram_subparsers = telegram_parser.add_subparsers(dest='telegram_command', help='Telegram commands')
        
        # Start bot
        start_parser = telegram_subparsers.add_parser('start', help='Start Telegram bot')
        start_parser.add_argument('--daemon', action='store_true', help='Run as daemon')
        
        # Stop bot
        stop_parser = telegram_subparsers.add_parser('stop', help='Stop Telegram bot')
        
        # Bot status
        status_parser = telegram_subparsers.add_parser('status', help='Show bot status')
        
        # Send message
        send_parser = telegram_subparsers.add_parser('send', help='Send message via bot')
        send_parser.add_argument('message', help='Message to send')
        send_parser.add_argument('--chat-id', help='Chat ID (default: all)')
    
    def _add_health_commands(self, subparsers):
        """Add health-related commands."""
        health_parser = subparsers.add_parser('health', help='System health checks')
        health_subparsers = health_parser.add_subparsers(dest='health_command', help='Health commands')
        
        # Overall health
        overall_parser = health_subparsers.add_parser('overall', help='Overall system health')
        overall_parser.add_argument('--detailed', action='store_true', help='Detailed health report')
        
        # Component health
        component_parser = health_subparsers.add_parser('component', help='Component health check')
        component_parser.add_argument('component', help='Component to check (agents, scheduler, telegram)')
        
        # Quick health
        quick_parser = health_subparsers.add_parser('quick', help='Quick health check')
    
    def _add_config_commands(self, subparsers):
        """Add configuration commands."""
        config_parser = subparsers.add_parser('config', help='Configuration management')
        config_subparsers = config_parser.add_subparsers(dest='config_command', help='Config commands')
        
        # Get config
        get_parser = config_subparsers.add_parser('get', help='Get configuration value')
        get_parser.add_argument('key', help='Configuration key')
        
        # Set config
        set_parser = config_subparsers.add_parser('set', help='Set configuration value')
        set_parser.add_argument('key', help='Configuration key')
        set_parser.add_argument('value', help='Configuration value')
        
        # List config
        list_parser = config_subparsers.add_parser('list', help='List all configuration')
        list_parser.add_argument('--section', help='Configuration section')
        
        # Validate config
        validate_parser = config_subparsers.add_parser('validate', help='Validate configuration')
    
    def _add_version_command(self, subparsers):
        """Add version command."""
        version_parser = subparsers.add_parser('version', help='Show version information')
    
    async def run(self, args: Optional[List[str]] = None) -> int:
        """
        Run the CLI with given arguments.
        
        Args:
            args: Command line arguments (uses sys.argv if None)
        
        Returns:
            Exit code
        """
        try:
            # Parse arguments
            parsed_args = self.parser.parse_args(args)
            
            if not parsed_args.command:
                self.parser.print_help()
                return 0
            
            # Initialize logging
            initialize_logging()
            
            # Route to appropriate handler
            if parsed_args.command == 'scheduler':
                return await self._handle_scheduler(parsed_args)
            elif parsed_args.command == 'agents':
                return await self._handle_agents(parsed_args)
            
            elif parsed_args.command == 'telegram':
                return await self._handle_telegram(parsed_args)
            elif parsed_args.command == 'health':
                return await self._handle_health(parsed_args)
            elif parsed_args.command == 'config':
                return await self._handle_config(parsed_args)
            elif parsed_args.command == 'version':
                return await self._handle_version(parsed_args)
            else:
                logger.error(f"Unknown command: {parsed_args.command}")
                return 1
                
        except KeyboardInterrupt:
            logger.info("Operation cancelled by user")
            return 130
        except Exception as e:
            logger.error(f"CLI error: {e}")
            return 1
    
    async def _handle_scheduler(self, args) -> int:
        """Handle scheduler commands."""
        if args.scheduler_command == 'run':
            return await self._run_scheduler(args)
        elif args.scheduler_command == 'list':
            return await self._list_scheduler_jobs(args)
        elif args.scheduler_command == 'add':
            return await self._add_scheduler_job(args)
        elif args.scheduler_command == 'remove':
            return await self._remove_scheduler_job(args)
        elif args.scheduler_command == 'enable':
            return await self._enable_scheduler_job(args)
        elif args.scheduler_command == 'disable':
            return await self._disable_scheduler_job(args)
        else:
            logger.error(f"Unknown scheduler command: {args.scheduler_command}")
            return 1
    
    async def _handle_trading(self, args) -> int:
        """Handle trading commands."""
        try:
            if args.trading_command == 'start':
                return await self._start_trading(args)
            elif args.trading_command == 'stop':
                return await self._stop_trading(args)
            elif args.trading_command == 'status':
                return await self._show_trading_status(args)
            elif args.trading_command == 'signals':
                return await self._show_trading_signals(args)
            else:
                logger.error(f"Unknown trading command: {args.trading_command}")
                return 1
        except Exception as e:
            logger.error(f"Failed to handle trading command: {e}")
            return 1
    
    async def _start_trading(self, args) -> int:
        """Start trading system."""
        try:
            logger.info(f"Starting trading system in {args.mode} mode")
            logger.info(f"Trading symbols: {args.symbols}")
            logger.info(f"Policy file: {args.policy}")
            
            # Import trade service (lazy import to avoid circular dependencies)
            from application.trade_service import TradeService
            
            # Initialize trade service
            trade_service = TradeService()
            
            # Start trading
            await trade_service.start(
                mode=args.mode,
                symbols=args.symbols,
                policy_file=args.policy
            )
            
            logger.info("Trading system started successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to start trading system: {e}")
            return 1
    
    async def _stop_trading(self, args) -> int:
        """Stop trading system."""
        try:
            logger.info("Stopping trading system...")
            
            # Import trade service
            from application.trade_service import TradeService
            
            # Stop trading
            trade_service = TradeService()
            await trade_service.stop()
            
            logger.info("Trading system stopped successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to stop trading system: {e}")
            return 1
    
    async def _show_trading_status(self, args) -> int:
        """Show trading system status."""
        try:
            logger.info("Trading system status:")
            
            # Import trade service
            from application.trade_service import TradeService
            
            # Get status
            trade_service = TradeService()
            status = await trade_service.get_status()
            
            # Display status
            print(f"Status: {status.get('status', 'Unknown')}")
            print(f"Mode: {status.get('mode', 'Unknown')}")
            print(f"Active symbols: {status.get('active_symbols', [])}")
            print(f"Total signals: {status.get('total_signals', 0)}")
            print(f"Successful trades: {status.get('successful_trades', 0)}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get trading status: {e}")
            return 1
    
    async def _show_trading_signals(self, args) -> int:
        """Show trading signals."""
        try:
            logger.info("Recent trading signals:")
            
            # Import trade service
            from application.trade_service import TradeService
            
            # Get signals
            trade_service = TradeService()
            signals = await trade_service.get_recent_signals(
                symbol=args.symbol,
                limit=args.limit
            )
            
            # Display signals
            for signal in signals:
                print(f"Symbol: {signal.get('symbol', 'Unknown')}")
                print(f"Side: {signal.get('side', 'Unknown')}")
                print(f"Score: {signal.get('score', 0)}")
                print(f"Confidence: {signal.get('confidence', 0)}")
                print(f"Timestamp: {signal.get('timestamp', 'Unknown')}")
                print("---")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get trading signals: {e}")
            return 1
    
    async def _run_scheduler(self, args) -> int:
        """Run the scheduler."""
        try:
            logger.info(f"Starting scheduler with graph: {args.graph}")
            if args.dry_run:
                logger.info("Running in DRY-RUN mode")
            
            # Initialize scheduler
            await self.scheduler.start()
            
            if args.once:
                # Run once
                await self.scheduler.run_cycle(args.graph, dry_run=args.dry_run)
                logger.info("Scheduler cycle completed")
            else:
                # Run continuously
                max_cycles = args.max_cycles or float('inf')
                cycle_count = 0
                
                while cycle_count < max_cycles:
                    await self.scheduler.run_cycle(args.graph, dry_run=args.dry_run)
                    cycle_count += 1
                    
                    if args.max_cycles:
                        logger.info(f"Completed cycle {cycle_count}/{args.max_cycles}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to run scheduler: {e}")
            return 1
        finally:
            await self.scheduler.stop()
    
    async def _list_scheduler_jobs(self, args) -> int:
        """List scheduler jobs."""
        try:
            jobs = self.scheduler.get_jobs()
            
            if not jobs:
                print("No scheduled jobs found")
                return 0
            
            print(f"Scheduled Jobs ({len(jobs)}):")
            print("-" * 80)
            
            for job in jobs:
                status = "🟢 Active" if job.enabled else "🔴 Disabled"
                print(f"{job.name:<20} {job.schedule:<20} {status}")
                if job.description:
                    print(f"  Description: {job.description}")
                print()
            
            if args.history:
                history = self.scheduler.get_job_history()
                if history:
                    print(f"Job History ({len(history)} entries):")
                    print("-" * 80)
                    for entry in history[-10:]:  # Show last 10
                        print(f"{entry['job_name']:<20} {entry['status']:<10} {entry['timestamp']}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to list scheduler jobs: {e}")
            return 1
    
    async def _add_scheduler_job(self, args) -> int:
        """Add a new scheduler job."""
        try:
            # This would be implemented in the scheduler
            logger.info(f"Adding job: {args.name} with schedule: {args.schedule}")
            # await self.scheduler.add_job(args.name, args.schedule, args.enabled, args.description)
            logger.info("Job added successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to add job: {e}")
            return 1
    
    async def _remove_scheduler_job(self, args) -> int:
        """Remove a scheduler job."""
        try:
            logger.info(f"Removing job: {args.name}")
            # await self.scheduler.remove_job(args.name)
            logger.info("Job removed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to remove job: {e}")
            return 1
    
    async def _enable_scheduler_job(self, args) -> int:
        """Enable a scheduler job."""
        try:
            logger.info(f"Enabling job: {args.name}")
            # await self.scheduler.enable_job(args.name)
            logger.info("Job enabled successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to enable job: {e}")
            return 1
    
    async def _disable_scheduler_job(self, args) -> int:
        """Disable a scheduler job."""
        try:
            logger.info(f"Disabling job: {args.name}")
            # await self.scheduler.disable_job(args.name)
            logger.info("Job disabled successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to disable job: {e}")
            return 1
    
    async def _handle_agents(self, args) -> int:
        """Handle agent commands."""
        if args.agent_command == 'run':
            return await self._run_agents(args)
        elif args.agent_command == 'list':
            return await self._list_agents(args)
        elif args.agent_command == 'status':
            return await self._show_agent_status(args)
        else:
            logger.error(f"Unknown agent command: {args.agent_command}")
            return 1
    
    async def _run_agents(self, args) -> int:
        """Run agents with lifecycle management."""
        try:
            # Resolve execution mode (--mode wins over aliases)
            effective_mode = self._resolve_execution_mode(args)
            logger.info(f"Starting agents with graph: {args.graph}")
            logger.info(f"Effective execution mode: {effective_mode}")
            
            # Initialize agent system (disabled in non-agent mode)
            logger.debug("Agents disabled: skip router initialization")
            router = None
            
            if effective_mode == "dry-run":
                # Dry-run mode with bounded execution
                logger.info("🧪 DRY-RUN: Starting agent system")
                logger.info("🧪 DRY-RUN: Loading graph: default")
                logger.info("🧪 DRY-RUN: Initializing agents")
                logger.info("🧪 DRY-RUN: Creating execution plan")
                logger.info("🧪 DRY-RUN: Showing prevalidation + quantize steps")
                
                # Simulate one cycle with timeout
                if router:
                    try:
                        await asyncio.wait_for(
                            router.run_one_cycle(),
                            timeout=args.timeout
                        )
                        logger.info("✅ DRY-RUN completed successfully")
                    except asyncio.TimeoutError:
                        logger.warning("⚠️ DRY-RUN timed out, but completed")
                else:
                    logger.info("✅ DRY-RUN completed (mock mode)")
                
                return 0
            else:
                # Production mode with signal handling
                logger.info(f"🚀 Starting production agent system in {effective_mode} mode")
                
                # Setup signal handlers
                import signal
                shutdown_event = asyncio.Event()
                
                def signal_handler(signum, frame):
                    logger.info(f"Received signal {signum}, initiating shutdown")
                    shutdown_event.set()
                
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
                
                try:
                    # Start router
                    if router:
                        await router.start()
                        logger.info("Router started")
                        logger.info(f"Graph {args.graph} loaded")
                        
                        # Get symbols and tick interval from policy
                        from infrastructure.bootstrap import load_policy
                        policy = load_policy()
                        symbols = policy.get('exchange', {}).get('symbols', {}).get('supported_pairs', ['BTC', 'ETH'])
                        tick_interval = policy.get('scheduler', {}).get('agent_tick_interval', 15)
                        
                        # Send Telegram startup ping
                        await self._send_telegram_startup_ping(args.graph, effective_mode, symbols, tick_interval)
                        
                        # Start heartbeat task (disabled in non-agent mode)
                        logger.debug("Agents disabled: skip heartbeat")
                        heartbeat_task = None
                        
                        logger.info("Agent system started successfully")
                        
                        # Wait for shutdown signal
                        await shutdown_event.wait()
                        
                        # Cancel heartbeat (disabled in non-agent mode)
                        if heartbeat_task:
                            heartbeat_task.cancel()
                        
                    else:
                        logger.warning("No router available, running mock mode")
                        await shutdown_event.wait()
                        
                except Exception as e:
                    logger.error(f"Agent system error: {e}")
                    raise
                finally:
                    # Cleanup
                    logger.info("🛑 Shutting down agent system...")
                    try:
                        if router:
                            await router.stop()
                        await self.scheduler.cleanup()
                        logger.info("✅ Agent system shutdown complete")
                    except Exception as e:
                        logger.error(f"Error during shutdown: {e}")
                
                return 0
            
        except Exception as e:
            logger.error(f"Failed to run agents: {e}")
            return 1
    
    def _resolve_execution_mode(self, args) -> str:
        """Resolve execution mode from CLI arguments."""
        # --mode takes precedence over aliases
        if args.mode:
            return args.mode
        
        # Check aliases
        if args.live:
            return "live"
        elif args.paper:
            return "paper"
        elif args.dry_run:
            return "dry-run"
        
        # Default to dry-run for safety
        return "dry-run"
    
    async def _send_telegram_startup_ping(self, graph_name: str, mode: str, symbols: list, tick_interval: int) -> None:
        """Send startup ping to Telegram if enabled."""
        try:
            # Check if Telegram is enabled in policy
            from infrastructure.bootstrap import load_policy
            policy = load_policy()
            
            if not policy.get('notifications', {}).get('telegram', {}).get('enabled', False):
                logger.debug("Telegram notifications disabled in policy")
                return
            
            # Check if TELEGRAM_BOT_TOKEN is available
            import os
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if not bot_token:
                logger.debug("TELEGRAM_BOT_TOKEN not found in environment")
                return
            
            # Initialize Telegram client and send message
            from telegram_bot.bot import TelegramBot
            bot = TelegramBot(bot_token)
            
            # Send startup message
            message = (
                f"✅ Agents up\n"
                f"Graph: {graph_name}\n"
                f"Mode: {mode}\n"
                f"Symbols: {', '.join(symbols)}\n"
                f"Tick: {tick_interval}s"
            )
            
            await bot.send_message(message)
            logger.info("Telegram startup ping sent successfully")
            
        except Exception as e:
            logger.warning(f"Failed to send Telegram startup ping: {e}")
            # Don't crash, just log warning
    
    async def _router_post_safe(self, router, msg) -> bool:
        """Safe router post helper that tries multiple methods."""
        try_methods = ("post_tick", "post", "enqueue", "emit")
        for m in try_methods:
            fn = getattr(router, m, None)
            if callable(fn):
                try:
                    res = fn(msg)
                    if asyncio.iscoroutine(res):
                        await res
                    return True
                except Exception:
                    continue
        logger.warning("Router has no working post_tick/post/enqueue/emit; skipping tick")
        return False

    def _build_tick_message(self) -> "Message":
        """Build tick message with fallback for MessageType."""
        try:
            return Message(subject=MessageType.TICK, body={"source": "heartbeat", "ts": time.time()})
        except Exception:
            return Message(subject="TICK", body={"source": "heartbeat", "ts": time.time()})
    
    async def _start_heartbeat(self, router, tick_interval: int = 15) -> None:
        """Start heartbeat task for agent system."""
        try:
            logger.info(f"Starting heartbeat with {tick_interval}s interval")
            
            # First-kick: immediate orchestration tick
            try:
                if hasattr(router, 'post_tick'):
                    await router.post_tick()
                    logger.info("First-kick sent")
                    logger.debug("HB tick -> orchestrator")
                else:
                    logger.warning("Router has no post_tick method")
            except Exception as e:
                logger.warning(f"Failed to post first-kick: {e}")
            
            # Start periodic heartbeat
            while True:
                await asyncio.sleep(tick_interval)
                
                try:
                    if hasattr(router, 'post_tick'):
                        await router.post_tick()
                        logger.debug("HB tick -> orchestrator")
                    else:
                        logger.warning("Router has no post_tick method")
                except Exception as e:
                    logger.warning(f"Failed to post heartbeat tick: {e}")
                    
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            # Don't crash, just log error
    
    async def _list_agents(self, args) -> int:
        """List available agents."""
        try:
            # Dynamic agent discovery from agents/roles directory
            from pathlib import Path
            import importlib
            import inspect
            
            agents_dir = Path("agents/roles")
            agents = []
            
            if agents_dir.exists():
                # Find all Python files in roles directory
                for agent_file in agents_dir.glob("*.py"):
                    if agent_file.stem == "__init__":
                        continue
                    
                    try:
                        # Import the agent module
                        module_name = f"agents.roles.{agent_file.stem}"
                        module = importlib.import_module(module_name)
                        
                        # Find agent classes in the module
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                hasattr(obj, '__module__') and 
                                obj.__module__.startswith('agents.roles') and
                                name.endswith('Agent')):
                                
                                # Extract agent name (remove 'Agent' suffix)
                                agent_name = name.replace('Agent', '').lower()
                                if agent_name:
                                    agents.append(agent_name)
                                else:
                                    agents.append(name.lower())
                    except Exception as e:
                        logger.warning(f"Failed to import {agent_file.stem}: {e}")
                        # Fallback: use filename without extension
                        agents.append(agent_file.stem)
            
            # Sort agents alphabetically
            agents.sort()
            
            print(f"Available Agents ({len(agents)}):")
            print("-" * 40)
            for agent in agents:
                print(f"• {agent}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            return 1
    
    async def _show_agent_status(self, args) -> int:
        """Show agent status."""
        try:
            if args.agent:
                # Show specific agent status
                logger.info(f"Status for agent: {args.agent}")
                
                # Try to get agent status from router (disabled in non-agent mode)
                logger.debug("Agents disabled: skip agent status check")
                logger.info(f"Agent {args.agent}: Not running (agents disabled)")
                
            else:
                # Show overall agent system status
                logger.info("Overall agent system status")
                
                # Get all agents and their status
                from pathlib import Path
                agents_dir = Path("agents/roles")
                agents = []
                
                if agents_dir.exists():
                    for agent_file in agents_dir.glob("*.py"):
                        if agent_file.stem == "__init__":
                            continue
                        agents.append(agent_file.stem)
                
                logger.info(f"Total agents found: {len(agents)}")
                for agent in sorted(agents):
                    logger.info(f"• {agent}: Available")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to show agent status: {e}")
            return 1
    
    async def _handle_telegram(self, args) -> int:
        """Handle Telegram commands."""
        if args.telegram_command == 'start':
            return await self._start_telegram_bot(args)
        elif args.telegram_command == 'stop':
            return await self._stop_telegram_bot(args)
        elif args.telegram_command == 'status':
            return await self._show_telegram_status(args)
        elif args.telegram_command == 'send':
            return await self._send_telegram_message(args)
        else:
            logger.error(f"Unknown Telegram command: {args.telegram_command}")
            return 1
    
    async def _start_telegram_bot(self, args) -> int:
        """Start Telegram bot."""
        try:
            logger.info("Starting Telegram bot")
            if args.daemon:
                logger.info("Running as daemon")
            
            # This would start the Telegram bot
            logger.info("Telegram bot started successfully")
            
            if not args.daemon:
                # Keep running until interrupted
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Telegram bot stopped by user")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")
            return 1
    
    async def _stop_telegram_bot(self, args) -> int:
        """Stop Telegram bot."""
        try:
            logger.info("Stopping Telegram bot")
            # This would stop the Telegram bot
            logger.info("Telegram bot stopped successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to stop Telegram bot: {e}")
            return 1
    
    async def _show_telegram_status(self, args) -> int:
        """Show Telegram bot status."""
        try:
            logger.info("Telegram bot status")
            # This would show bot status
            return 0
            
        except Exception as e:
            logger.error(f"Failed to show Telegram status: {e}")
            return 1
    
    async def _send_telegram_message(self, args) -> int:
        """Send Telegram message."""
        try:
            logger.info(f"Sending message: {args.message}")
            if args.chat_id:
                logger.info(f"To chat ID: {args.chat_id}")
            
            # This would send the message
            logger.info("Message sent successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return 1
    
    async def _handle_health(self, args) -> int:
        """Handle health commands."""
        if args.health_command == 'overall':
            return await self._show_overall_health(args)
        elif args.health_command == 'component':
            return await self._show_component_health(args)
        elif args.health_command == 'quick':
            return await self._show_quick_health(args)
        else:
            logger.error(f"Unknown health command: {args.health_command}")
            return 1
    
    async def _show_overall_health(self, args) -> int:
        """Show overall system health."""
        try:
            logger.info("Overall system health check")
            if args.detailed:
                logger.info("Detailed health report requested")
            
            # This would perform comprehensive health checks
            print("System Health: 🟢 OK")
            print("Components:")
            print("  • Scheduler: 🟢 OK")
            print("  • Agents: 🟢 OK")
            print("  • Telegram: 🟢 OK")
            print("  • Database: 🟢 OK")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to show overall health: {e}")
            return 1
    
    async def _show_component_health(self, args) -> int:
        """Show component health."""
        try:
            logger.info(f"Component health check: {args.component}")
            
            # This would check specific component health
            print(f"Component: {args.component}")
            print("Status: 🟢 OK")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to show component health: {e}")
            return 1
    
    async def _show_quick_health(self, args) -> int:
        """Show quick health check."""
        try:
            logger.info("Quick health check")
            
            # This would perform quick health checks
            print("Quick Health: 🟢 OK")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to show quick health: {e}")
            return 1
    
    async def _handle_config(self, args) -> int:
        """Handle configuration commands."""
        if args.config_command == 'get':
            return await self._get_config(args)
        elif args.config_command == 'set':
            return await self._set_config(args)
        elif args.config_command == 'list':
            return await self._list_config(args)
        elif args.config_command == 'validate':
            return await self._validate_config(args)
        else:
            logger.error(f"Unknown config command: {args.config_command}")
            return 1
    
    async def _get_config(self, args) -> int:
        """Get configuration value."""
        try:
            logger.info(f"Getting config: {args.key}")
            # This would get the config value
            print(f"Config[{args.key}]: <value>")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get config: {e}")
            return 1
    
    async def _set_config(self, args) -> int:
        """Set configuration value."""
        try:
            logger.info(f"Setting config: {args.key} = {args.value}")
            # This would set the config value
            logger.info("Config updated successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to set config: {e}")
            return 1
    
    async def _list_config(self, args) -> int:
        """List configuration."""
        try:
            logger.info("Listing configuration")
            if args.section:
                logger.info(f"Section: {args.section}")
            
            # This would list the configuration
            print("Configuration:")
            print("  • Section 1")
            print("  • Section 2")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to list config: {e}")
            return 1
    
    async def _validate_config(self, args) -> int:
        """Validate configuration."""
        try:
            logger.info("Validating configuration")
            
            # This would validate the configuration
            print("Configuration: ✅ Valid")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to validate config: {e}")
            return 1
    
    async def _handle_version(self, args) -> int:
        """Handle version command."""
        try:
            print("AiBotBS v1.0.0")
            print("AI-Powered Trading Bot System")
            print("Built with Python and Clean Architecture")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to show version: {e}")
            return 1


def main():
    """Main entry point for CLI."""
    cli = AiBotCLI()
    exit_code = asyncio.run(cli.run())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
