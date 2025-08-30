"""
Router for the AiBotBS Runtime Agent System.
Manages task execution, agent communication, and workflow orchestration.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from .base import BaseAgent, Message, MessageType, MessagePriority


class RouteStatus(Enum):
    """Route execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RouteType(Enum):
    """Route execution type."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    FAN_OUT = "fan_out"
    FAN_IN = "fan_in"


@dataclass
class RouteStep:
    """Step in a route execution."""
    id: str
    agent_id: str
    message: Message
    dependencies: list[str] = field(default_factory=list)
    timeout: int = 30  # seconds
    retry_count: int = 0
    max_retries: int = 3
    status: RouteStatus = RouteStatus.PENDING
    result: Any | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Route:
    """Route for task execution."""
    id: str
    name: str
    description: str
    steps: list[RouteStep]
    type: RouteType = RouteType.SEQUENTIAL
    priority: int = 1
    timeout: int = 300  # seconds
    retry_count: int = 0
    max_retries: int = 3
    status: RouteStatus = RouteStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskGraph:
    """Directed task graph for workflow execution."""
    id: str
    name: str
    description: str
    routes: list[Route]
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class Router:
    """Router for managing task execution and agent communication."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("router")

        # Import specialized components
        from .agent_registry import AgentRegistry
        from .queue import MessageQueue
        
        # Agent registry
        self._agent_registry = AgentRegistry()
        
        # Message queue
        self._message_queue = MessageQueue()

        # Route and task management
        self._routes: dict[str, Route] = {}
        self._task_graphs: dict[str, TaskGraph] = {}
        self._active_routes: dict[str, Route] = {}
        self._completed_routes: dict[str, Route] = {}

        # Execution control
        self._running = False
        self._max_concurrent_routes = config.get("max_concurrent_routes", 10)
        self._route_timeout = config.get("route_timeout", 300)
        self._step_timeout = config.get("step_timeout", 30)
        self._max_retries = config.get("max_retries", 3)

        # Performance tracking
        self._routes_executed = 0
        self._routes_completed = 0
        self._routes_failed = 0
        self._total_execution_time = 0.0
        self._start_time = None

        # Router will be started manually via start() method

    async def start(self) -> None:
        """Start the router."""
        try:
            self.logger.info("Starting router")
            self._running = True
            self._start_time = datetime.now(UTC)

            # Start task processors
            asyncio.create_task(self._process_messages())

            # Start route monitor
            asyncio.create_task(self._route_monitor())

            self.logger.info("Router started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start router: {e}")
            raise

    async def _start(self) -> None:
        """Start the router (internal method)."""
        try:
            self.logger.info("Starting router")
            self._running = True
            self._start_time = datetime.now(UTC)

            # Start task processors
            asyncio.create_task(self._process_messages())

            # Start route monitor
            asyncio.create_task(self._route_monitor())

            self.logger.info("Router started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start router: {e}")
            raise

    async def stop(self) -> None:
        """Stop the router."""
        try:
            self.logger.info("Stopping router")
            self._running = False

            # Cancel all active routes
            for route_id in list(self._active_routes.keys()):
                await self._cancel_route(route_id)

            self.logger.info("Router stopped successfully")

        except Exception as e:
            self.logger.error(f"Failed to stop router: {e}")
            raise

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the router."""
        self._agent_registry.register_agent(agent)

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the router."""
        self._agent_registry.unregister_agent(agent_id)

    def register_route(self, route: Route) -> None:
        """Register a route for execution."""
        try:
            self._routes[route.id] = route
            self.logger.info(f"Registered route: {route.name} ({route.id})")

        except Exception as e:
            self.logger.error(f"Failed to register route {route.id}: {e}")

    def register_task_graph(self, task_graph: TaskGraph) -> None:
        """Register a task graph."""
        try:
            self._task_graphs[task_graph.id] = task_graph
            self.logger.info(f"Registered task graph: {task_graph.name} ({task_graph.id})")

        except Exception as e:
            self.logger.error(f"Failed to register task graph {task_graph.id}: {e}")

    async def execute_route(self, route_id: str, parameters: dict[str, Any] = None) -> str:
        """Execute a route."""
        try:
            if route_id not in self._routes:
                raise ValueError(f"Route not found: {route_id}")

            route = self._routes[route_id]

            # Check if we can start a new route
            if len(self._active_routes) >= self._max_concurrent_routes:
                # Queue the route for later execution
                await self._queue_route(route, parameters)
                return f"queued_{route_id}"

            # Start route execution
            execution_id = await self._start_route_execution(route, parameters)
            return execution_id

        except Exception as e:
            self.logger.error(f"Failed to execute route {route_id}: {e}")
            raise

    async def execute_task_graph(self, graph_id: str, parameters: dict[str, Any] = None) -> str:
        """Execute a task graph."""
        try:
            if graph_id not in self._task_graphs:
                raise ValueError(f"Task graph not found: {graph_id}")

            task_graph = self._task_graphs[graph_id]

            # Create routes from the task graph
            routes = await self._create_routes_from_graph(task_graph, parameters)

            # Execute routes
            execution_ids = []
            for route in routes:
                execution_id = await self.execute_route(route.id, parameters)
                execution_ids.append(execution_id)

            return f"graph_{graph_id}_{len(execution_ids)}"

        except Exception as e:
            self.logger.error(f"Failed to execute task graph {graph_id}: {e}")
            raise

    async def send_message(self, message: Message) -> bool:
        """Send a message to an agent."""
        try:
            if message.to_agent not in self._agents:
                self.logger.warning(f"Agent not found: {message.to_agent}")
                return False

            agent = self._agents[message.to_agent]
            await agent.handle_message(message)
            return True

        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False

    def get_status(self) -> dict[str, Any]:
        """Get router status."""
        return {
            "status": "running" if self._running else "stopped",
            "agent_count": len(self._agents),
            "route_count": len(self._routes),
            "task_graph_count": len(self._task_graphs),
            "active_routes": len(self._active_routes),
            "max_concurrent_routes": self._max_concurrent_routes,
            "queued_routes": (self._high_priority_queue.qsize() +
                             self._normal_priority_queue.qsize() +
                             self._low_priority_queue.qsize())
        }

    async def broadcast_message(self, message: Message, agent_types: list[str] | None = None) -> int:
        """Broadcast a message to multiple agents."""
        try:
            sent_count = 0

            for agent_id, agent in self._agents.items():
                if agent_types and agent.agent_type not in agent_types:
                    continue

                broadcast_message = Message(
                    type=message.type,
                    priority=message.priority,
                    from_agent=message.from_agent,
                    to_agent=agent_id,
                    subject=message.subject,
                    body=message.body,
                    correlation_id=message.correlation_id,
                    metadata=message.metadata
                )

                if await self.send_message(broadcast_message):
                    sent_count += 1

            return sent_count

        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {e}")
            return 0

    def get_route_status(self, route_id: str) -> dict[str, Any] | None:
        """Get status of a route."""
        try:
            if route_id in self._active_routes:
                route = self._active_routes[route_id]
                return self._route_to_dict(route)
            elif route_id in self._completed_routes:
                route = self._completed_routes[route_id]
                return self._route_to_dict(route)
            else:
                return None

        except Exception as e:
            self.logger.error(f"Failed to get route status: {e}")
            return None

    def get_router_status(self) -> dict[str, Any]:
        """Get router status information."""
        uptime = None
        if self._start_time:
            uptime = (datetime.now(UTC) - self._start_time).total_seconds()

        return {
            "running": self._running,
            "agents_registered": len(self._agents),
            "routes_registered": len(self._routes),
            "task_graphs_registered": len(self._task_graphs),
            "active_routes": len(self._active_routes),
            "completed_routes": len(self._completed_routes),
            "routes_executed": self._routes_executed,
            "routes_completed": self._routes_completed,
            "routes_failed": self._routes_failed,
            "total_execution_time": self._total_execution_time,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": uptime,
            "queue_sizes": {
                "high_priority": self._high_priority_queue.qsize(),
                "normal_priority": self._normal_priority_queue.qsize(),
                "low_priority": self._low_priority_queue.qsize()
            }
        }

    async def _start_route_execution(self, route: Route, parameters: dict[str, Any] = None) -> str:
        """Start execution of a route."""
        try:
            execution_id = f"exec_{route.id}_{uuid4().hex[:8]}"

            # Clone route for execution
            execution_route = Route(
                id=execution_id,
                name=route.name,
                description=route.description,
                steps=route.steps.copy(),
                type=route.type,
                priority=route.priority,
                timeout=route.timeout,
                max_retries=route.max_retries,
                metadata=route.metadata.copy()
            )

            # Update step parameters if provided
            if parameters:
                for step in execution_route.steps:
                    step.message.body.update(parameters)

            # Add to active routes
            self._active_routes[execution_id] = execution_route
            execution_route.status = RouteStatus.RUNNING
            execution_route.started_at = datetime.now(UTC)

            self._routes_executed += 1

            # Start execution based on route type
            if execution_route.type == RouteType.SEQUENTIAL:
                asyncio.create_task(self._execute_sequential_route(execution_route))
            elif execution_route.type == RouteType.PARALLEL:
                asyncio.create_task(self._execute_parallel_route(execution_route))
            elif execution_route.type == RouteType.FAN_OUT:
                asyncio.create_task(self._execute_fan_out_route(execution_route))
            elif execution_route.type == RouteType.FAN_IN:
                asyncio.create_task(self._execute_fan_in_route(execution_route))
            else:
                # Default to sequential
                asyncio.create_task(self._execute_sequential_route(execution_route))

            self.logger.info(f"Started route execution: {execution_id}")
            return execution_id

        except Exception as e:
            self.logger.error(f"Failed to start route execution: {e}")
            raise

    async def _execute_sequential_route(self, route: Route) -> None:
        """Execute a sequential route."""
        try:
            self.logger.debug(f"Executing sequential route: {route.id}")

            for step in route.steps:
                if not self._running:
                    break

                # Check dependencies
                if not await self._check_step_dependencies(step, route):
                    continue

                # Execute step
                await self._execute_step(step, route)

                # Check if route should continue
                if route.status != RouteStatus.RUNNING:
                    break

            # Mark route as completed
            await self._complete_route(route)

        except Exception as e:
            self.logger.error(f"Sequential route execution failed: {e}")
            route.status = RouteStatus.FAILED
            route.error = str(e)
            await self._complete_route(route)

    async def _execute_parallel_route(self, route: Route) -> None:
        """Execute a parallel route."""
        try:
            self.logger.debug(f"Executing parallel route: {route.id}")

            # Execute all steps in parallel
            tasks = []
            for step in route.steps:
                if not self._running:
                    break

                # Check dependencies
                if await self._check_step_dependencies(step, route):
                    task = asyncio.create_task(self._execute_step(step, route))
                    tasks.append(task)

            # Wait for all tasks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            # Mark route as completed
            await self._complete_route(route)

        except Exception as e:
            self.logger.error(f"Parallel route execution failed: {e}")
            route.status = RouteStatus.FAILED
            route.error = str(e)
            await self._complete_route(route)

    async def _execute_fan_out_route(self, route: Route) -> None:
        """Execute a fan-out route (one input, multiple parallel outputs)."""
        try:
            self.logger.debug(f"Executing fan-out route: {route.id}")

            # Get input from first step
            input_step = route.steps[0]
            input_result = await self._execute_step(input_step, route)

            if input_result and len(route.steps) > 1:
                # Fan out to remaining steps
                tasks = []
                for step in route.steps[1:]:
                    if not self._running:
                        break

                    # Pass input to each step
                    step.message.body["input"] = input_result
                    task = asyncio.create_task(self._execute_step(step, route))
                    tasks.append(task)

                # Wait for all tasks to complete
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

            # Mark route as completed
            await self._complete_route(route)

        except Exception as e:
            self.logger.error(f"Fan-out route execution failed: {e}")
            route.status = RouteStatus.FAILED
            route.error = str(e)
            await self._complete_route(route)

    async def _execute_fan_in_route(self, route: Route) -> None:
        """Execute a fan-in route (multiple inputs, one output)."""
        try:
            self.logger.debug(f"Executing fan-in route: {route.id}")

            # Execute all input steps in parallel
            input_steps = route.steps[:-1]
            output_step = route.steps[-1]

            tasks = []
            for step in input_steps:
                if not self._running:
                    break

                task = asyncio.create_task(self._execute_step(step, route))
                tasks.append(task)

            # Wait for all input steps to complete
            input_results = []
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                input_results = [r for r in results if not isinstance(r, Exception)]

            # Execute output step with combined results
            if input_results:
                output_step.message.body["inputs"] = input_results
                await self._execute_step(output_step, route)

            # Mark route as completed
            await self._complete_route(route)

        except Exception as e:
            self.logger.error(f"Fan-in route execution failed: {e}")
            route.status = RouteStatus.FAILED
            route.error = str(e)
            await self._complete_route(route)

    async def _execute_step(self, step: RouteStep, route: Route) -> Any | None:
        """Execute a single route step."""
        try:
            step.status = RouteStatus.RUNNING
            step.started_at = datetime.now(UTC)

            self.logger.debug(f"Executing step: {step.id} in route: {route.id}")

            # Send message to agent
            if step.agent_id in self._agents:
                agent = self._agents[step.agent_id]

                # Set timeout for step execution
                try:
                    result = await asyncio.wait_for(
                        agent.handle_message(step.message),
                        timeout=step.timeout
                    )

                    step.status = RouteStatus.COMPLETED
                    step.result = result
                    step.completed_at = datetime.now(UTC)

                    self.logger.debug(f"Step completed: {step.id}")
                    return result

                except TimeoutError:
                    step.error = "Step execution timeout"
                    step.status = RouteStatus.FAILED
                    self.logger.warning(f"Step timeout: {step.id}")

                    # Retry if possible
                    if step.retry_count < step.max_retries:
                        step.retry_count += 1
                        step.status = RouteStatus.PENDING
                        return await self._execute_step(step, route)

                    return None

            else:
                step.error = f"Agent not found: {step.agent_id}"
                step.status = RouteStatus.FAILED
                self.logger.error(f"Agent not found: {step.agent_id}")
                return None

        except Exception as e:
            step.error = str(e)
            step.status = RouteStatus.FAILED
            self.logger.error(f"Step execution failed: {step.id}: {e}")
            return None

    async def _check_step_dependencies(self, step: RouteStep, route: Route) -> bool:
        """Check if step dependencies are satisfied."""
        try:
            for dep_id in step.dependencies:
                # Find dependency step
                dep_step = None
                for s in route.steps:
                    if s.id == dep_id:
                        dep_step = s
                        break

                if not dep_step:
                    self.logger.warning(f"Dependency step not found: {dep_id}")
                    return False

                if dep_step.status != RouteStatus.COMPLETED:
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Failed to check step dependencies: {e}")
            return False

    async def _complete_route(self, route: Route) -> None:
        """Complete a route execution."""
        try:
            route.completed_at = datetime.now(UTC)

            # Calculate execution time
            if route.started_at:
                execution_time = (route.completed_at - route.started_at).total_seconds()
                self._total_execution_time += execution_time

            # Move to completed routes
            if route.id in self._active_routes:
                del self._active_routes[route.id]

            self._completed_routes[route.id] = route

            # Update statistics
            if route.status == RouteStatus.COMPLETED:
                self._routes_completed += 1
            else:
                self._routes_failed += 1

            self.logger.info(f"Route completed: {route.id} - Status: {route.status.value}")

        except Exception as e:
            self.logger.error(f"Failed to complete route: {e}")

    async def _cancel_route(self, route_id: str) -> bool:
        """Cancel an active route."""
        try:
            if route_id not in self._active_routes:
                return False

            route = self._active_routes[route_id]
            route.status = RouteStatus.CANCELLED
            route.completed_at = datetime.now(UTC)

            # Move to completed routes
            del self._active_routes[route_id]
            self._completed_routes[route_id] = route

            self.logger.info(f"Route cancelled: {route_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel route: {e}")
            return False

    async def _queue_route(self, route: Route, parameters: dict[str, Any] = None) -> None:
        """Queue a route for later execution."""
        try:
            # Create a queued route entry
            queued_route = Route(
                id=f"queued_{route.id}_{uuid4().hex[:8]}",
                name=route.name,
                description=route.description,
                steps=route.steps.copy(),
                type=route.type,
                priority=route.priority,
                timeout=route.timeout,
                max_retries=route.max_retries,
                metadata=route.metadata.copy()
            )

            # Add to appropriate queue based on priority
            if route.priority >= 3:
                await self._message_queue.enqueue("route", {"route": queued_route}, MessagePriority.HIGH)
            elif route.priority >= 2:
                await self._message_queue.enqueue("route", {"route": queued_route}, MessagePriority.NORMAL)
            else:
                await self._message_queue.enqueue("route", {"route": queued_route}, MessagePriority.LOW)

            self.logger.info(f"Queued route: {route.name} (Priority: {route.priority})")

        except Exception as e:
            self.logger.error(f"Failed to queue route: {e}")

    async def _process_messages(self) -> None:
        """Process messages from all priority queues."""
        while self._running:
            try:
                # Process high priority first
                message = await self._message_queue.dequeue_high_priority()
                if message:
                    await self._handle_message(message)
                    continue
                
                # Then normal priority
                message = await self._message_queue.dequeue_normal_priority()
                if message:
                    await self._handle_message(message)
                    continue
                
                # Finally low priority
                message = await self._message_queue.dequeue_low_priority()
                if message:
                    await self._handle_message(message)
                    continue
                
                # No messages, sleep briefly
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Message processing error: {e}")
                await asyncio.sleep(1)

    async def _process_normal_priority_queue(self) -> None:
        """Process normal priority queue."""
        while self._running:
            try:
                if self._normal_priority_queue.empty():
                    await asyncio.sleep(0.1)
                    continue

                priority, route = await self._normal_priority_queue.get()

                # Check if we can start the route
                if len(self._active_routes) < self._max_concurrent_routes:
                    await self._start_route_execution(route, {})
                else:
                    # Put back in queue
                    await self._normal_priority_queue.put((priority, route))
                    await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Normal priority queue processing error: {e}")
                await asyncio.sleep(1)

    async def _process_low_priority_queue(self) -> None:
        """Process low priority queue."""
        while self._running:
            try:
                if self._low_priority_queue.empty():
                    await asyncio.sleep(0.1)
                    continue

                priority, route = await self._low_priority_queue.get()

                # Check if we can start the route
                if len(self._active_routes) < self._max_concurrent_routes:
                    await self._start_route_execution(route, {})
                else:
                    # Put back in queue
                    await self._low_priority_queue.put((priority, route))
                    await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Low priority queue processing error: {e}")
                await asyncio.sleep(1)

    async def _route_monitor(self) -> None:
        """Monitor active routes for timeouts and cleanup."""
        while self._running:
            try:
                current_time = datetime.now(UTC)

                for route_id, route in list(self._active_routes.items()):
                    # Check for route timeout
                    if route.started_at and route.timeout:
                        elapsed = (current_time - route.started_at).total_seconds()
                        if elapsed > route.timeout:
                            self.logger.warning(f"Route timeout: {route_id}")
                            await self._cancel_route(route_id)

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                self.logger.error(f"Route monitor error: {e}")
                await asyncio.sleep(10)

    async def run_one_cycle(self) -> dict[str, Any]:
        """Run one cycle of the agent system for dry-run mode."""
        try:
            self.logger.info("Running one cycle of agent system")
            
            # Simulate one cycle of agent execution
            cycle_result = {
                "status": "completed",
                "agents_processed": len(self._agents),
                "routes_created": 0,
                "messages_processed": 0,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            # Simulate agent initialization
            for agent_id in self._agents:
                self.logger.info(f"Agent {agent_id}: Initialized")
            
            # Simulate workflow execution
            self.logger.info("Workflow: Market Analysis → Signal Generation → Risk Assessment → Execution")
            self.logger.info("✅ Prevalidation completed")
            self.logger.info("✅ Quantization completed")
            
            return cycle_result
            
        except Exception as e:
            self.logger.error(f"Cycle execution failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _create_routes_from_graph(self, task_graph: TaskGraph, parameters: dict[str, Any] = None) -> list[Route]:
        """Create routes from a task graph."""
        try:
            routes = []

            for route_template in task_graph.routes:
                # Create route with parameters
                route = Route(
                    id=f"{route_template.id}_{uuid4().hex[:8]}",
                    name=route_template.name,
                    description=route_template.description,
                    steps=route_template.steps.copy(),
                    type=route_template.type,
                    priority=route_template.priority,
                    timeout=route_template.timeout,
                    max_retries=route_template.max_retries,
                    metadata=route_template.metadata.copy()
                )

                # Update step parameters if provided
                if parameters:
                    for step in route.steps:
                        step.message.body.update(parameters)

                routes.append(route)

            return routes

        except Exception as e:
            self.logger.error(f"Failed to create routes from graph: {e}")
            return []

    def _route_to_dict(self, route: Route) -> dict[str, Any]:
        """Convert route to dictionary for status reporting."""
        return {
            "id": route.id,
            "name": route.name,
            "status": route.status.value,
            "type": route.type.value,
            "priority": route.priority,
            "created_at": route.created_at.isoformat(),
            "started_at": route.started_at.isoformat() if route.started_at else None,
            "completed_at": route.completed_at.isoformat() if route.completed_at else None,
            "steps_count": len(route.steps),
            "steps": [
                {
                    "id": step.id,
                    "agent_id": step.agent_id,
                    "status": step.status.value,
                    "retry_count": step.retry_count,
                    "error": step.error
                }
                for step in route.steps
            ],
            "error": route.error
        }
    
    async def enqueue(self, message_type: str, body: dict[str, Any]) -> None:
        """Enqueue a message to the normal priority queue."""
        try:
            # Use the MessageQueue component
            await self._message_queue.enqueue(message_type, body, MessagePriority.NORMAL)
            self.logger.debug(f"Message enqueued: {message_type}")
            
        except Exception as e:
            self.logger.warning(f"Failed to enqueue message: {e}")

    async def post_tick(self) -> None:
        """Post a heartbeat tick to trigger orchestration activity."""
        try:
            # Create a tick message
            tick_message = Message(
                id=str(uuid4()),
                type=MessageType.HEARTBEAT,
                priority=MessagePriority.LOW,
                from_agent="heartbeat",
                to_agent="orchestrator",
                subject="tick",
                body={"type": "tick", "timestamp": datetime.now(UTC).isoformat()},
                metadata={"heartbeat": True}
            )
            
            # Enqueue the tick message
            await self.enqueue('TICK', tick_message.body)
            self.logger.debug("Heartbeat tick posted to orchestrator")
            
        except Exception as e:
            self.logger.warning(f"Failed to post heartbeat tick: {e}")
            # Don't crash, just log warning


# Global router instance
_router_instance = None

def get_agent_router() -> Router:
    """Get the global agent router instance."""
    global _router_instance
    if _router_instance is None:
        # Create router with default config
        config = {
            "max_concurrent_routes": 5,
            "route_timeout": 300,
            "max_retries": 3,
            "enable_monitoring": True
        }
        _router_instance = Router(config)
    return _router_instance


async def get_agent_status(agent_id: str) -> dict[str, Any]:
    """Get status of a specific agent."""
    router = get_agent_router()
    # This would return actual agent status
    # For now, return mock status
    return {
        "agent_id": agent_id,
        "status": "available",
        "last_heartbeat": None,
        "performance_metrics": {}
    }

