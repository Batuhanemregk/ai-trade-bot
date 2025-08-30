"""
Orchestrator Agent for AiBotBS.
Coordinates other agents and manages task execution workflows.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from domain.errors import AgentError

from ..core.base import BaseAgent, Context, Message, MessageType
from ..core.memory import MemoryType, get_memory_manager
from ..core.tools import Tool, get_tool_registry


@dataclass
class WorkflowDefinition:
    """Definition of a workflow."""
    name: str
    description: str
    steps: list[dict[str, Any]]
    triggers: list[str] = field(default_factory=list)
    schedule: str | None = None
    enabled: bool = True
    max_concurrent: int = 1
    timeout: int = 3600  # seconds
    retry_policy: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowInstance:
    """Instance of a workflow execution."""
    id: UUID = field(default_factory=uuid4)
    workflow_name: str = ""
    status: str = "pending"  # pending, running, completed, failed, cancelled
    started_at: datetime | None = None
    completed_at: datetime | None = None
    current_step: int = 0
    total_steps: int = 0
    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class OrchestratorAgent(BaseAgent):
    """Orchestrator agent that coordinates other agents."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "orchestrator", config)

        # Workflow management
        self._workflows: dict[str, WorkflowDefinition] = {}
        self._active_workflows: dict[UUID, WorkflowInstance] = {}
        self._workflow_queue: asyncio.Queue = asyncio.Queue()

        # Agent coordination
        self._agent_registry: dict[str, dict[str, Any]] = {}
        self._agent_health: dict[str, dict[str, Any]] = {}

        # Task scheduling
        self._scheduled_tasks: dict[str, asyncio.Task] = {}
        self._task_scheduler = None

        # Performance tracking
        self._performance_metrics = {
            "workflows_executed": 0,
            "workflows_completed": 0,
            "workflows_failed": 0,
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }

        # Register message handlers
        self._register_message_handlers()

        # Register tools
        self._register_tools()

    async def _initialize(self) -> None:
        """Initialize the orchestrator."""
        self.logger.info("Initializing orchestrator agent")

        # Load workflow definitions
        await self._load_workflow_definitions()

        # Start workflow processor
        asyncio.create_task(self._workflow_processor())

        # Start agent health monitor
        asyncio.create_task(self._agent_health_monitor())

        # Start task scheduler
        await self._start_task_scheduler()

        self.logger.info("Orchestrator agent initialized")

    async def _cleanup(self) -> None:
        """Cleanup when stopping the agent."""
        self.logger.info("Cleaning up orchestrator agent")

        # Cancel all active workflows
        for workflow_id, workflow in self._active_workflows.items():
            if workflow.status == "running":
                workflow.status = "cancelled"
                workflow.completed_at = datetime.utcnow()

        # Cancel scheduled tasks
        for task_name, task in self._scheduled_tasks.items():
            task.cancel()

        # Stop task scheduler
        if self._task_scheduler:
            self._task_scheduler.cancel()

        self.logger.info("Orchestrator agent cleanup completed")

    def _register_message_handlers(self) -> None:
        """Register message handlers."""
        self.register_message_handler(MessageType.TASK, self._handle_task_message)
        self.register_message_handler(MessageType.STATUS_UPDATE, self._handle_status_update)
        self.register_message_handler(MessageType.DATA_UPDATE, self._handle_data_update)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

    def _register_tools(self) -> None:
        """Register orchestrator-specific tools."""
        from ..core.tools import ToolCategory

        # Get tool registry
        registry = get_tool_registry()

        # Register orchestrator tools
        registry.register_tool(WorkflowManagementTool(self), ToolCategory.UTILITY)
        registry.register_tool(AgentManagementTool(self), ToolCategory.UTILITY)
        registry.register_tool(PerformanceAnalysisTool(self), ToolCategory.ANALYSIS)

    async def _load_workflow_definitions(self) -> None:
        """Load workflow definitions from configuration."""
        try:
            # Load from config
            workflows_config = self.config.get("workflows", {})

            for workflow_name, workflow_config in workflows_config.items():
                workflow = WorkflowDefinition(
                    name=workflow_name,
                    description=workflow_config.get("description", ""),
                    steps=workflow_config.get("steps", []),
                    triggers=workflow_config.get("triggers", []),
                    schedule=workflow_config.get("schedule"),
                    enabled=workflow_config.get("enabled", True),
                    max_concurrent=workflow_config.get("max_concurrent", 1),
                    timeout=workflow_config.get("timeout", 3600),
                    retry_policy=workflow_config.get("retry_policy", {})
                )

                self._workflows[workflow_name] = workflow
                self.logger.info(f"Loaded workflow: {workflow_name}")

            # Load from memory if available
            memory = get_memory_manager()
            stored_workflows = await memory.get("orchestrator:workflows", MemoryType.PERSISTENT)
            if stored_workflows:
                for workflow_data in stored_workflows:
                    workflow = WorkflowDefinition(**workflow_data)
                    self._workflows[workflow.name] = workflow
                    self.logger.info(f"Loaded stored workflow: {workflow.name}")

        except Exception as e:
            self.logger.error(f"Failed to load workflow definitions: {e}")

    async def _workflow_processor(self) -> None:
        """Process workflow queue."""
        while self._running:
            try:
                # Get workflow from queue
                try:
                    workflow_data = await asyncio.wait_for(
                        self._workflow_queue.get(), timeout=1.0
                    )
                except TimeoutError:
                    continue

                # Process workflow
                await self._process_workflow(workflow_data)

                # Mark task as done
                self._workflow_queue.task_done()

            except Exception as e:
                self.logger.error(f"Error processing workflow: {e}")

    async def _process_workflow(self, workflow_data: dict[str, Any]) -> None:
        """Process a workflow."""
        try:
            workflow_name = workflow_data.get("workflow_name")
            parameters = workflow_data.get("parameters", {})
            trigger = workflow_data.get("trigger", "manual")

            if workflow_name not in self._workflows:
                raise AgentError(f"Workflow not found: {workflow_name}")

            workflow_def = self._workflows[workflow_name]

            # Check if workflow is enabled
            if not workflow_def.enabled:
                self.logger.info(f"Workflow {workflow_name} is disabled")
                return

            # Check concurrent execution limit
            active_count = sum(1 for w in self._active_workflows.values()
                             if w.workflow_name == workflow_name and w.status == "running")

            if active_count >= workflow_def.max_concurrent:
                self.logger.warning(f"Workflow {workflow_name} concurrent limit reached")
                return

            # Create workflow instance
            workflow_instance = WorkflowInstance(
                workflow_name=workflow_name,
                total_steps=len(workflow_def.steps),
                metadata={"trigger": trigger, "parameters": parameters}
            )

            self._active_workflows[workflow_instance.id] = workflow_instance

            # Execute workflow
            asyncio.create_task(self._execute_workflow(workflow_instance, workflow_def))

        except Exception as e:
            self.logger.error(f"Failed to process workflow: {e}")

    async def _execute_workflow(self, workflow_instance: WorkflowInstance,
                               workflow_def: WorkflowDefinition) -> None:
        """Execute a workflow."""
        try:
            workflow_instance.status = "running"
            workflow_instance.started_at = datetime.utcnow()

            self.logger.info(f"Starting workflow: {workflow_instance.workflow_name}")

            # Execute steps
            for step_index, step_config in enumerate(workflow_def.steps):
                if workflow_instance.status == "cancelled":
                    break

                workflow_instance.current_step = step_index + 1

                try:
                    step_result = await self._execute_workflow_step(step_config, workflow_instance)
                    workflow_instance.results[f"step_{step_index + 1}"] = step_result

                except Exception as e:
                    error_msg = f"Step {step_index + 1} failed: {e}"
                    workflow_instance.errors.append(error_msg)
                    self.logger.error(error_msg)

                    # Check retry policy
                    if not await self._should_retry_step(workflow_instance, workflow_def, step_index):
                        workflow_instance.status = "failed"
                        break

            # Finalize workflow
            if workflow_instance.status == "running":
                workflow_instance.status = "completed"

            workflow_instance.completed_at = datetime.utcnow()

            # Update performance metrics
            if workflow_instance.completed_at and workflow_instance.started_at:
                execution_time = (workflow_instance.completed_at - workflow_instance.started_at).total_seconds()
                self._update_performance_metrics(execution_time, workflow_instance.status == "completed")

            self.logger.info(f"Workflow {workflow_instance.workflow_name} completed with status: {workflow_instance.status}")

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            workflow_instance.status = "failed"
            workflow_instance.errors.append(str(e))
            workflow_instance.completed_at = datetime.utcnow()

        finally:
            # Clean up completed workflows after some time
            asyncio.create_task(self._cleanup_completed_workflow(workflow_instance.id))

    async def _execute_workflow_step(self, step_config: dict[str, Any],
                                   workflow_instance: WorkflowInstance) -> Any:
        """Execute a single workflow step."""
        step_type = step_config.get("type")

        if step_type == "agent_task":
            return await self._execute_agent_task(step_config, workflow_instance)
        elif step_type == "condition":
            return await self._evaluate_condition(step_config, workflow_instance)
        elif step_type == "delay":
            return await self._execute_delay(step_config, workflow_instance)
        elif step_type == "parallel":
            return await self._execute_parallel_tasks(step_config, workflow_instance)
        elif step_type == "loop":
            return await self._execute_loop(step_config, workflow_instance)
        else:
            raise AgentError(f"Unknown step type: {step_type}")

    async def _execute_agent_task(self, step_config: dict[str, Any],
                                workflow_instance: WorkflowInstance) -> Any:
        """Execute an agent task."""
        agent_type = step_config.get("agent_type")
        task_name = step_config.get("task_name")
        parameters = step_config.get("parameters", {})

        if not agent_type:
            raise AgentError("Missing agent_type in step config")
        if not task_name:
            raise AgentError("Missing task_name in step config")

        # Find available agent
        agent_id = await self._find_available_agent(agent_type)
        if not agent_id:
            raise AgentError(f"No available agent of type: {agent_type}")

        # Create task message
        task_message = Message(
            type=MessageType.TASK,
            priority=MessageType.NORMAL,
            from_agent=self.agent_id,
            to_agent=agent_id,
            subject=task_name,
            body={
                "workflow_id": str(workflow_instance.id),
                "step_index": workflow_instance.current_step,
                "parameters": parameters,
                "context": workflow_instance.metadata
            },
            correlation_id=uuid4()
        )

        # Send task and wait for result
        await self.send_message(task_message)

        # For now, simulate result (in practice, this would wait for response)
        await asyncio.sleep(0.1)

        return {
            "agent_type": agent_type,
            "agent_id": agent_id,
            "task_name": task_name,
            "status": "completed"
        }

    async def _evaluate_condition(self, step_config: dict[str, Any],
                                workflow_instance: WorkflowInstance) -> bool:
        """Evaluate a condition step."""
        condition = step_config.get("condition")
        if not condition:
            return True

        try:
            # Create evaluation context
            context_vars = {
                "workflow": workflow_instance,
                "results": workflow_instance.results,
                "parameters": workflow_instance.metadata.get("parameters", {}),
                "current_step": workflow_instance.current_step
            }

            # Evaluate condition (be careful with eval in production)
            result = eval(condition, {"__builtins__": {}}, context_vars)
            return bool(result)

        except Exception as e:
            self.logger.error(f"Failed to evaluate condition: {e}")
            return False

    async def _execute_delay(self, step_config: dict[str, Any],
                           workflow_instance: WorkflowInstance) -> None:
        """Execute a delay step."""
        duration = step_config.get("duration", 1)
        await asyncio.sleep(duration)

    async def _execute_parallel_tasks(self, step_config: dict[str, Any],
                                    workflow_instance: WorkflowInstance) -> list[Any]:
        """Execute parallel tasks."""
        tasks = step_config.get("tasks", [])
        results = []

        # Create tasks
        task_coros = []
        for task_config in tasks:
            task_coro = self._execute_workflow_step(task_config, workflow_instance)
            task_coros.append(task_coro)

        # Execute in parallel
        if task_coros:
            results = await asyncio.gather(*task_coros, return_exceptions=True)

        return results

    async def _execute_loop(self, step_config: dict[str, Any],
                          workflow_instance: WorkflowInstance) -> list[Any]:
        """Execute a loop step."""
        iterations = step_config.get("iterations", 1)
        step_to_loop = step_config.get("step")
        results = []

        for i in range(iterations):
            if workflow_instance.status == "cancelled":
                break

            try:
                result = await self._execute_workflow_step(step_to_loop, workflow_instance)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Loop iteration {i + 1} failed: {e}")
                break

        return results

    async def _should_retry_step(self, workflow_instance: WorkflowInstance,
                                workflow_def: WorkflowDefinition,
                                step_index: int) -> bool:
        """Check if a step should be retried."""
        retry_policy = workflow_def.retry_policy
        max_retries = retry_policy.get("max_retries", 0)
        retry_delay = retry_policy.get("retry_delay", 5)

        # Count current retries for this step
        step_key = f"step_{step_index + 1}"
        current_retries = workflow_instance.metadata.get(f"{step_key}_retries", 0)

        if current_retries < max_retries:
            # Increment retry count
            workflow_instance.metadata[f"{step_key}_retries"] = current_retries + 1

            # Wait before retry
            await asyncio.sleep(retry_delay)
            return True

        return False

    async def _find_available_agent(self, agent_type: str) -> str | None:
        """Find an available agent of the specified type."""
        # For now, return the first agent of the type
        # In practice, this would check agent health and availability
        if agent_type in self._agent_registry:
            agents = self._agent_registry[agent_type]
            for agent_id, agent_info in agents.items():
                if agent_info.get("status") == "running":
                    return agent_id

        return None

    async def _start_task_scheduler(self) -> None:
        """Start the task scheduler."""
        self._task_scheduler = asyncio.create_task(self._scheduler_loop())

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Check for scheduled workflows
                await self._check_scheduled_workflows()

                # Wait before next check
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)

    async def _check_scheduled_workflows(self) -> None:
        """Check for workflows that should be executed based on schedule."""
        current_time = datetime.utcnow()

        for workflow_name, workflow_def in self._workflows.items():
            if not workflow_def.enabled or not workflow_def.schedule:
                continue

            # Simple cron-like schedule parsing (could be enhanced)
            if await self._should_execute_scheduled_workflow(workflow_def, current_time):
                await self._queue_workflow(workflow_name, {"trigger": "schedule"})

    async def _should_execute_scheduled_workflow(self, workflow_def: WorkflowDefinition,
                                               current_time: datetime) -> bool:
        """Check if a scheduled workflow should execute."""
        schedule = workflow_def.schedule

        # Simple schedule formats (could be enhanced with cron parsing)
        if schedule == "hourly":
            return current_time.minute == 0
        elif schedule == "daily":
            return current_time.hour == 0 and current_time.minute == 0
        elif schedule == "weekly":
            return current_time.weekday() == 0 and current_time.hour == 0 and current_time.minute == 0

        return False

    async def _queue_workflow(self, workflow_name: str, metadata: dict[str, Any]) -> None:
        """Queue a workflow for execution."""
        workflow_data = {
            "workflow_name": workflow_name,
            "parameters": metadata.get("parameters", {}),
            "trigger": metadata.get("trigger", "manual")
        }

        await self._workflow_queue.put(workflow_data)
        self.logger.info(f"Queued workflow: {workflow_name}")

    async def _agent_health_monitor(self) -> None:
        """Monitor agent health."""
        while self._running:
            try:
                # Update agent health status
                await self._update_agent_health()

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Agent health monitor error: {e}")
                await asyncio.sleep(30)

    async def _update_agent_health(self) -> None:
        """Update agent health information."""
        # This would typically query agents for their health status
        # For now, we'll just log that we're monitoring
        self.logger.debug("Updating agent health status")

    async def _cleanup_completed_workflow(self, workflow_id: UUID) -> None:
        """Clean up a completed workflow after some time."""
        await asyncio.sleep(300)  # Wait 5 minutes

        if workflow_id in self._active_workflows:
            del self._active_workflows[workflow_id]

    def _update_performance_metrics(self, execution_time: float, success: bool) -> None:
        """Update performance metrics."""
        self._performance_metrics["workflows_executed"] += 1

        if success:
            self._performance_metrics["workflows_completed"] += 1
        else:
            self._performance_metrics["workflows_failed"] += 1

        self._performance_metrics["total_execution_time"] += execution_time
        self._performance_metrics["average_execution_time"] = (
            self._performance_metrics["total_execution_time"] /
            self._performance_metrics["workflows_executed"]
        )

    async def _handle_task_message(self, message: Message) -> None:
        """Handle task messages."""
        # This would handle incoming tasks from other agents
        self.logger.debug(f"Received task message: {message.subject}")

    async def _handle_status_update(self, message: Message) -> None:
        """Handle status update messages."""
        # Update agent status
        agent_id = message.from_agent
        status_data = message.body

        if agent_id not in self._agent_health:
            self._agent_health[agent_id] = {}

        self._agent_health[agent_id].update(status_data)
        self._agent_health[agent_id]["last_update"] = datetime.utcnow().isoformat()

    async def _handle_data_update(self, message: Message) -> None:
        """Handle data update messages."""
        # Process data updates from other agents
        self.logger.debug(f"Received data update: {message.subject}")

    async def _handle_command(self, message: Message) -> None:
        """Handle command messages."""
        command = message.body.get("command")
        parameters = message.body.get("parameters", {})

        try:
            if command == "start_workflow":
                workflow_name = parameters.get("workflow_name")
                if not workflow_name:
                    raise AgentError("Missing workflow_name parameter")

                await self._queue_workflow(workflow_name, parameters)
                result = {"status": "queued", "workflow_name": workflow_name}

            elif command == "list_workflows":
                result = {
                    "workflows": list(self._workflows.keys()),
                    "active": len([w for w in self._active_workflows.values() if w.status == "running"])
                }

            elif command == "get_workflow_status":
                workflow_name = parameters.get("workflow_name")
                if not workflow_name:
                    raise AgentError("Missing workflow_name parameter")

                active_instances = [w for w in self._active_workflows.values()
                                  if w.workflow_name == workflow_name]

                result = {
                    "workflow_name": workflow_name,
                    "active_instances": len(active_instances),
                    "instances": [
                        {
                            "id": str(w.id),
                            "status": w.status,
                            "current_step": w.current_step,
                            "total_steps": w.total_steps,
                            "started_at": w.started_at.isoformat() if w.started_at else None,
                            "completed_at": w.completed_at.isoformat() if w.completed_at else None
                        }
                        for w in active_instances
                    ]
                }

            elif command == "cancel_workflow":
                workflow_id = parameters.get("workflow_id")
                if not workflow_id:
                    raise AgentError("Missing workflow_id parameter")

                try:
                    workflow_uuid = UUID(workflow_id)
                    if workflow_uuid in self._active_workflows:
                        workflow = self._active_workflows[workflow_uuid]
                        if workflow.status == "running":
                            workflow.status = "cancelled"
                            workflow.completed_at = datetime.utcnow()
                            result = {"status": "cancelled", "workflow_id": workflow_id}
                        else:
                            result = {"status": "not_running", "workflow_id": workflow_id}
                    else:
                        result = {"status": "not_found", "workflow_id": workflow_id}
                except ValueError:
                    result = {"status": "invalid_id", "workflow_id": workflow_id}

            elif command == "get_performance":
                result = self._performance_metrics.copy()

            else:
                result = {"error": f"Unknown command: {command}"}

            # Send response
            response = Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject=f"command_response_{command}",
                body=result,
                reply_to=message.id
            )
            await self.send_message(response)

        except Exception as e:
            self.logger.error(f"Error handling command: {e}")
            error_response = Message(
                type=MessageType.ERROR,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="command_error",
                body={"error": str(e)},
                reply_to=message.id
            )
            await self.send_message(error_response)

    def get_workflow_status(self) -> dict[str, Any]:
        """Get overall workflow status."""
        return {
            "total_workflows": len(self._workflows),
            "active_workflows": len([w for w in self._active_workflows.values() if w.status == "running"]),
            "pending_workflows": len([w for w in self._active_workflows.values() if w.status == "pending"]),
            "completed_workflows": len([w for w in self._active_workflows.values() if w.status == "completed"]),
            "failed_workflows": len([w for w in self._active_workflows.values() if w.status == "failed"]),
            "performance_metrics": self._performance_metrics.copy()
        }


# Tool classes for the orchestrator

class WorkflowManagementTool(Tool):
    """Tool for managing workflows."""

    def __init__(self, orchestrator: OrchestratorAgent):
        super().__init__("workflow_management", "Manage workflows and execution")
        self.orchestrator = orchestrator

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute workflow management operation."""
        operation = parameters.get("operation")

        if operation == "start":
            workflow_name = parameters.get("workflow_name")
            workflow_params = parameters.get("parameters", {})
            await self.orchestrator._queue_workflow(workflow_name, workflow_params)
            return {"status": "queued", "workflow_name": workflow_name}

        elif operation == "list":
            return {"workflows": list(self.orchestrator._workflows.keys())}

        elif operation == "status":
            return self.orchestrator.get_workflow_status()

        else:
            raise AgentError(f"Unknown workflow operation: {operation}")

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["start", "list", "status"],
                "description": "Workflow operation to perform"
            },
            "workflow_name": {
                "type": "string",
                "description": "Name of the workflow to start"
            },
            "parameters": {
                "type": "object",
                "description": "Parameters for the workflow"
            }
        }


class AgentManagementTool(Tool):
    """Tool for managing agents."""

    def __init__(self, orchestrator: OrchestratorAgent):
        super().__init__("agent_management", "Manage agent registration and health")
        self.orchestrator = orchestrator

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute agent management operation."""
        operation = parameters.get("operation")

        if operation == "list":
            return {"agents": list(self.orchestrator._agent_registry.keys())}

        elif operation == "health":
            return {"health": self.orchestrator._agent_health}

        else:
            raise AgentError(f"Unknown agent operation: {operation}")

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["list", "health"],
                "description": "Agent operation to perform"
            }
        }


class PerformanceAnalysisTool(Tool):
    """Tool for analyzing performance."""

    def __init__(self, orchestrator: OrchestratorAgent):
        super().__init__("performance_analysis", "Analyze system performance metrics")
        self.orchestrator = orchestrator

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute performance analysis operation."""
        operation = parameters.get("operation")

        if operation == "metrics":
            return self.orchestrator._performance_metrics.copy()

        elif operation == "summary":
            metrics = self.orchestrator._performance_metrics
            return {
                "total_workflows": metrics["workflows_executed"],
                "success_rate": metrics["workflows_completed"] / max(metrics["workflows_executed"], 1),
                "average_time": metrics["average_execution_time"]
            }

        else:
            raise AgentError(f"Unknown performance operation: {operation}")

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["metrics", "summary"],
                "description": "Performance analysis operation to perform"
            }
        }
