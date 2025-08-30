"""
Tools system for the AiBotBS Runtime Agent System.
Provides common tools for agents to interact with external systems.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from .base import Context, Tool


class ToolCategory(Enum):
    """Tool categories for organization."""
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    UTILITY = "utility"
    EXCHANGE = "exchange"
    POLICY = "policy"
    FILESYSTEM = "filesystem"
    CLOCK = "clock"


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    data: Any = None
    error: str | None = None
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """Registry for managing and discovering tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._tools_by_category: dict[ToolCategory, list[str]] = {}
        self._tools_by_agent: dict[str, list[str]] = {}
        self.logger = logging.getLogger("tool_registry")

    def register_tool(self, tool: Tool, category: ToolCategory, agent_id: str | None = None) -> None:
        """Register a tool with the registry."""
        try:
            tool_name = tool.name

            if tool_name in self._tools:
                self.logger.warning(f"Tool {tool_name} already registered, overwriting")

            # Register tool
            self._tools[tool_name] = tool

            # Add to category
            if category not in self._tools_by_category:
                self._tools_by_category[category] = []
            self._tools_by_category[category].append(tool_name)

            # Add to agent if specified
            if agent_id:
                if agent_id not in self._tools_by_agent:
                    self._tools_by_agent[agent_id] = []
                self._tools_by_agent[agent_id].append(tool_name)

            self.logger.info(f"Registered tool: {tool_name} (category: {category.value})")

        except Exception as e:
            self.logger.error(f"Failed to register tool {tool.name}: {e}")

    def unregister_tool(self, tool_name: str) -> None:
        """Unregister a tool from the registry."""
        try:
            if tool_name not in self._tools:
                return

            tool = self._tools[tool_name]

            # Remove from all categories
            for category, tools in self._tools_by_category.items():
                if tool_name in tools:
                    tools.remove(tool_name)

            # Remove from all agents
            for agent_id, tools in self._tools_by_agent.items():
                if tool_name in tools:
                    tools.remove(tool_name)

            # Remove tool
            del self._tools[tool_name]

            self.logger.info(f"Unregistered tool: {tool_name}")

        except Exception as e:
            self.logger.error(f"Failed to unregister tool {tool_name}: {e}")

    def get_tool(self, tool_name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(tool_name)

    def get_tools_by_category(self, category: ToolCategory) -> list[Tool]:
        """Get all tools in a category."""
        tool_names = self._tools_by_category.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_tools_by_agent(self, agent_id: str) -> list[Tool]:
        """Get all tools registered by an agent."""
        tool_names = self._tools_by_agent.get(agent_id, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def list_categories(self) -> list[ToolCategory]:
        """List all tool categories."""
        return list(self._tools_by_category.keys())

    def get_tool_schema(self, tool_name: str) -> dict[str, Any] | None:
        """Get schema for a specific tool."""
        tool = self.get_tool(tool_name)
        if tool:
            return tool.get_schema()
        return None

    def get_all_schemas(self) -> dict[str, dict[str, Any]]:
        """Get schemas for all tools."""
        return {name: tool.get_schema() for name, tool in self._tools.items()}


# Global tool registry instance
_global_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _global_tool_registry


# Tool implementations

class ExchangeTool(Tool):
    """Tool for exchange operations."""

    def __init__(self, exchange_name: str = "okx", mode: str = "dry-run"):
        super().__init__("exchange", f"Exchange operations for {exchange_name}")
        self.exchange_name = exchange_name
        self.mode = mode  # dry-run, paper, live
        self.logger = logging.getLogger(f"exchange_tool_{exchange_name}")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute exchange operation."""
        try:
            operation = parameters.get("operation")

            if operation == "get_balance":
                return await self._get_balance(parameters)
            elif operation == "get_positions":
                return await self._get_positions(parameters)
            elif operation == "place_order":
                return await self._place_order(parameters)
            elif operation == "cancel_order":
                return await self._cancel_order(parameters)
            elif operation == "get_order_status":
                return await self._get_order_status(parameters)
            else:
                raise ValueError(f"Unknown exchange operation: {operation}")

        except Exception as e:
            self.logger.error(f"Exchange operation failed: {e}")
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["get_balance", "get_positions", "place_order", "cancel_order", "get_order_status"],
                "description": "Exchange operation to perform"
            },
            "symbol": {
                "type": "string",
                "description": "Trading symbol"
            },
            "side": {
                "type": "string",
                "enum": ["buy", "sell"],
                "description": "Order side"
            },
            "quantity": {
                "type": "number",
                "description": "Order quantity"
            },
            "price": {
                "type": "number",
                "description": "Order price"
            }
        }

    async def _get_balance(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get account balance."""
        if self.mode == "dry-run":
            return {
                "mode": "dry-run",
                "balance": {
                    "USDT": 10000.0,
                    "BTC": 0.5,
                    "ETH": 5.0
                }
            }
        else:
            # Real exchange call would go here
            return {"error": "Live exchange not implemented"}

    async def _get_positions(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get open positions."""
        if self.mode == "dry-run":
            return {
                "mode": "dry-run",
                "positions": [
                    {
                        "symbol": "BTC/USDT",
                        "side": "long",
                        "size": 0.1,
                        "entry_price": 50000.0,
                        "unrealized_pnl": 500.0
                    }
                ]
            }
        else:
            return {"error": "Live exchange not implemented"}

    async def _place_order(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Place an order."""
        if self.mode == "dry-run":
            order_id = f"dry_run_{uuid4().hex[:8]}"
            return {
                "mode": "dry-run",
                "order_id": order_id,
                "status": "placed",
                "symbol": parameters.get("symbol"),
                "side": parameters.get("side"),
                "quantity": parameters.get("quantity"),
                "price": parameters.get("price")
            }
        else:
            return {"error": "Live exchange not implemented"}

    async def _cancel_order(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Cancel an order."""
        if self.mode == "dry-run":
            return {
                "mode": "dry-run",
                "status": "cancelled",
                "order_id": parameters.get("order_id")
            }
        else:
            return {"error": "Live exchange not implemented"}

    async def _get_order_status(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get order status."""
        if self.mode == "dry-run":
            return {
                "mode": "dry-run",
                "order_id": parameters.get("order_id"),
                "status": "pending"
            }
        else:
            return {"error": "Live exchange not implemented"}


class PolicyTool(Tool):
    """Tool for accessing policy configuration."""

    def __init__(self, policy_data: dict[str, Any]):
        super().__init__("policy", "Access policy configuration")
        self.policy_data = policy_data

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute policy operation."""
        try:
            operation = parameters.get("operation")

            if operation == "get":
                key = parameters.get("key")
                return self._get_policy_value(key)
            elif operation == "list":
                return self._list_policy_keys()
            elif operation == "search":
                pattern = parameters.get("pattern", "")
                return self._search_policy(pattern)
            else:
                raise ValueError(f"Unknown policy operation: {operation}")

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["get", "list", "search"],
                "description": "Policy operation to perform"
            },
            "key": {
                "type": "string",
                "description": "Policy key to retrieve"
            },
            "pattern": {
                "type": "string",
                "description": "Search pattern for policy keys"
            }
        }

    def _get_policy_value(self, key: str) -> Any:
        """Get policy value by key."""
        keys = key.split(".")
        value = self.policy_data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None

        return value

    def _list_policy_keys(self) -> list[str]:
        """List all policy keys."""
        def _flatten_dict(d, prefix=""):
            keys = []
            for k, v in d.items():
                if isinstance(v, dict):
                    keys.extend(_flatten_dict(v, f"{prefix}{k}."))
                else:
                    keys.append(f"{prefix}{k}")
            return keys

        return _flatten_dict(self.policy_data)

    def _search_policy(self, pattern: str) -> dict[str, Any]:
        """Search policy by pattern."""
        results = {}
        pattern_lower = pattern.lower()

        def _search_dict(d, prefix=""):
            for k, v in d.items():
                current_key = f"{prefix}{k}"
                if pattern_lower in current_key.lower():
                    results[current_key] = v
                elif isinstance(v, dict):
                    _search_dict(v, f"{current_key}.")

        _search_dict(self.policy_data)
        return results


class FilesystemTool(Tool):
    """Tool for filesystem operations."""

    def __init__(self, base_path: str = "."):
        super().__init__("filesystem", "Filesystem operations")
        self.base_path = base_path

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute filesystem operation."""
        try:
            operation = parameters.get("operation")

            if operation == "read":
                return await self._read_file(parameters)
            elif operation == "write":
                return await self._write_file(parameters)
            elif operation == "list":
                return await self._list_directory(parameters)
            elif operation == "exists":
                return await self._file_exists(parameters)
            else:
                raise ValueError(f"Unknown filesystem operation: {operation}")

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "list", "exists"],
                "description": "Filesystem operation to perform"
            },
            "path": {
                "type": "string",
                "description": "File or directory path"
            },
            "content": {
                "type": "string",
                "description": "Content to write (for write operation)"
            }
        }

    async def _read_file(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Read a file."""
        import os

        path = os.path.join(self.base_path, parameters.get("path", ""))

        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}

        try:
            with open(path) as f:
                content = f.read()
            return {"content": content, "path": path}
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}

    async def _write_file(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Write a file."""
        import os

        path = os.path.join(self.base_path, parameters.get("path", ""))
        content = parameters.get("content", "")

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, 'w') as f:
                f.write(content)

            return {"status": "written", "path": path}
        except Exception as e:
            return {"error": f"Failed to write file: {e}"}

    async def _list_directory(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """List directory contents."""
        import os

        path = os.path.join(self.base_path, parameters.get("path", ""))

        if not os.path.exists(path):
            return {"error": f"Directory not found: {path}"}

        try:
            items = os.listdir(path)
            return {"items": items, "path": path}
        except Exception as e:
            return {"error": f"Failed to list directory: {e}"}

    async def _file_exists(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Check if file exists."""
        import os

        path = os.path.join(self.base_path, parameters.get("path", ""))
        exists = os.path.exists(path)

        return {"exists": exists, "path": path}


class ClockTool(Tool):
    """Tool for time and scheduling operations."""

    def __init__(self):
        super().__init__("clock", "Time and scheduling operations")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute clock operation."""
        try:
            operation = parameters.get("operation")

            if operation == "now":
                return self._get_current_time()
            elif operation == "sleep":
                return await self._sleep(parameters)
            elif operation == "schedule":
                return self._schedule_task(parameters)
            elif operation == "format":
                return self._format_time(parameters)
            else:
                raise ValueError(f"Unknown clock operation: {operation}")

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["now", "sleep", "schedule", "format"],
                "description": "Clock operation to perform"
            },
            "seconds": {
                "type": "number",
                "description": "Seconds to sleep (for sleep operation)"
            },
            "timestamp": {
                "type": "string",
                "description": "Timestamp to format (for format operation)"
            },
            "format": {
                "type": "string",
                "description": "Time format string (for format operation)"
            }
        }

    def _get_current_time(self) -> dict[str, Any]:
        """Get current time."""
        now = datetime.now(UTC)
        return {
            "timestamp": now.isoformat(),
            "unix_timestamp": now.timestamp(),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "timezone": str(now.tzinfo)
        }

    async def _sleep(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Sleep for specified seconds."""
        seconds = parameters.get("seconds", 1)
        await asyncio.sleep(seconds)
        return {"slept": seconds, "status": "completed"}

    def _schedule_task(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Schedule a task (placeholder for future implementation)."""
        return {"status": "scheduled", "message": "Task scheduling not yet implemented"}

    def _format_time(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Format timestamp."""
        timestamp_str = parameters.get("timestamp")
        format_str = parameters.get("format", "%Y-%m-%d %H:%M:%S")

        try:
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str)
            else:
                dt = datetime.now(UTC)

            formatted = dt.strftime(format_str)
            return {"formatted": formatted, "timestamp": dt.isoformat()}
        except Exception as e:
            return {"error": f"Failed to format time: {e}"}


class UtilityTool(Tool):
    """Tool for utility operations."""

    def __init__(self):
        super().__init__("utility", "Utility operations")

    async def execute(self, parameters: dict[str, Any], context: Context) -> Any:
        """Execute utility operation."""
        try:
            operation = parameters.get("operation")

            if operation == "generate_id":
                return self._generate_id(parameters)
            elif operation == "validate":
                return self._validate_data(parameters)
            elif operation == "transform":
                return self._transform_data(parameters)
            elif operation == "calculate":
                return self._calculate(parameters)
            else:
                raise ValueError(f"Unknown utility operation: {operation}")

        except Exception as e:
            return {"error": str(e)}

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["generate_id", "validate", "transform", "calculate"],
                "description": "Utility operation to perform"
            },
            "length": {
                "type": "integer",
                "description": "Length for ID generation"
            },
            "data": {
                "type": "object",
                "description": "Data to validate or transform"
            },
            "expression": {
                "type": "string",
                "description": "Mathematical expression to calculate"
            }
        }

    def _generate_id(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Generate a unique ID."""
        import random
        import string

        length = parameters.get("length", 8)
        chars = string.ascii_letters + string.digits
        id_str = ''.join(random.choice(chars) for _ in range(length))

        return {"id": id_str, "length": length}

    def _validate_data(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Validate data structure."""
        data = parameters.get("data", {})

        # Simple validation - check if data is not empty
        is_valid = bool(data)
        errors = []

        if not is_valid:
            errors.append("Data is empty")

        return {
            "valid": is_valid,
            "errors": errors,
            "data": data
        }

    def _transform_data(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Transform data structure."""
        data = parameters.get("data", {})

        # Simple transformation - convert to uppercase if string
        if isinstance(data, str):
            transformed = data.upper()
        elif isinstance(data, dict):
            transformed = {k.upper(): v for k, v in data.items()}
        else:
            transformed = data

        return {
            "original": data,
            "transformed": transformed
        }

    def _calculate(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Calculate mathematical expression."""
        expression = parameters.get("expression", "")

        try:
            # Safe evaluation of mathematical expressions
            allowed_names = {
                'abs': abs, 'round': round, 'min': min, 'max': max,
                'sum': sum, 'len': len, 'int': int, 'float': float
            }

            result = eval(expression, {"__builtins__": {}}, allowed_names)

            return {
                "expression": expression,
                "result": result
            }
        except Exception as e:
            return {"error": f"Calculation failed: {e}"}


# Register default tools
def register_default_tools():
    """Register default tools with the global registry."""
    try:
        registry = get_tool_registry()

        # Register utility tools
        registry.register_tool(UtilityTool(), ToolCategory.UTILITY)
        registry.register_tool(ClockTool(), ToolCategory.CLOCK)

        # Register filesystem tool
        registry.register_tool(FilesystemTool(), ToolCategory.FILESYSTEM)

        # Register exchange tool (dry-run mode)
        registry.register_tool(ExchangeTool("okx", "dry-run"), ToolCategory.EXCHANGE)

        # Register policy tool with empty policy (will be updated later)
        registry.register_tool(PolicyTool({}), ToolCategory.POLICY)

        logging.getLogger("tools").info("Default tools registered successfully")

    except Exception as e:
        logging.getLogger("tools").error(f"Failed to register default tools: {e}")


# Auto-register default tools when module is imported
register_default_tools()
