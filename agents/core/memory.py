"""
Memory system for agents.
Provides ephemeral and persistent storage for agent state and data.
"""

import asyncio
import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class MemoryType(str, Enum):
    """Memory types."""
    EPHEMERAL = "ephemeral"      # In-memory, lost on restart
    PERSISTENT = "persistent"     # File-based, survives restart
    CACHE = "cache"               # TTL-based cache
    SHARED = "shared"             # Shared between agents
    WORKING = "working"           # Temporary working memory


class MemoryPriority(str, Enum):
    """Memory priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryItem:
    """A memory item."""
    key: str
    value: Any
    memory_type: MemoryType = MemoryType.EPHEMERAL
    priority: MemoryPriority = MemoryPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    access_count: int = 0
    size_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the memory item has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def access(self) -> None:
        """Mark the item as accessed."""
        self.accessed_at = datetime.utcnow()
        self.access_count += 1

    def get_age(self) -> timedelta:
        """Get the age of the memory item."""
        return datetime.utcnow() - self.created_at

    def get_idle_time(self) -> timedelta:
        """Get the idle time of the memory item."""
        return datetime.utcnow() - self.accessed_at


class MemoryBackend(ABC):
    """Abstract base class for memory backends."""

    @abstractmethod
    async def get(self, key: str) -> MemoryItem | None:
        """Get a memory item by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, **kwargs) -> bool:
        """Set a memory item."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a memory item."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        pass

    @abstractmethod
    async def keys(self, pattern: str | None = None) -> list[str]:
        """Get all keys, optionally filtered by pattern."""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all memory."""
        pass

    @abstractmethod
    async def size(self) -> int:
        """Get the size of memory in bytes."""
        pass

    @abstractmethod
    async def cleanup(self) -> int:
        """Clean up expired items, return count of cleaned items."""
        pass


class EphemeralMemoryBackend(MemoryBackend):
    """In-memory memory backend."""

    def __init__(self):
        self._storage: dict[str, MemoryItem] = {}
        self._total_size = 0

    async def get(self, key: str) -> MemoryItem | None:
        """Get a memory item by key."""
        item = self._storage.get(key)
        if item and not item.is_expired():
            item.access()
            return item
        elif item and item.is_expired():
            # Remove expired item
            await self.delete(key)
        return None

    async def set(self, key: str, value: Any, **kwargs) -> bool:
        """Set a memory item."""
        try:
            # Calculate size (rough estimate)
            size_bytes = len(str(value).encode('utf-8'))

            # Remove old item if it exists
            if key in self._storage:
                old_item = self._storage[key]
                self._total_size -= old_item.size_bytes
                await self.delete(key)

            # Create new item
            item = MemoryItem(
                key=key,
                value=value,
                memory_type=kwargs.get('memory_type', MemoryType.EPHEMERAL),
                priority=kwargs.get('priority', MemoryPriority.NORMAL),
                expires_at=kwargs.get('expires_at'),
                size_bytes=size_bytes,
                metadata=kwargs.get('metadata', {})
            )

            self._storage[key] = item
            self._total_size += size_bytes

            return True

        except Exception as e:
            logging.error(f"Failed to set memory item {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a memory item."""
        if key in self._storage:
            item = self._storage[key]
            self._total_size -= item.size_bytes
            del self._storage[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        item = self._storage.get(key)
        return item is not None and not item.is_expired()

    async def keys(self, pattern: str | None = None) -> list[str]:
        """Get all keys, optionally filtered by pattern."""
        keys = list(self._storage.keys())

        if pattern:
            # Simple pattern matching (could be enhanced with regex)
            filtered_keys = []
            for key in keys:
                if pattern in key:
                    filtered_keys.append(key)
            return filtered_keys

        return keys

    async def clear(self) -> bool:
        """Clear all memory."""
        self._storage.clear()
        self._total_size = 0
        return True

    async def size(self) -> int:
        """Get the size of memory in bytes."""
        return self._total_size

    async def cleanup(self) -> int:
        """Clean up expired items."""
        expired_keys = []
        for key, item in self._storage.items():
            if item.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            await self.delete(key)

        return len(expired_keys)


class SQLiteMemoryBackend(MemoryBackend):
    """SQLite-based persistent memory backend."""

    def __init__(self, db_path: str = "state/memory.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _init_db(self) -> None:
        """Initialize the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create memory table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS memory (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        memory_type TEXT NOT NULL,
                        priority TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        accessed_at TEXT NOT NULL,
                        expires_at TEXT,
                        access_count INTEGER DEFAULT 0,
                        size_bytes INTEGER DEFAULT 0,
                        metadata TEXT
                    )
                """)

                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memory_expires ON memory(expires_at)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memory_priority ON memory(priority)
                """)

                conn.commit()

        except Exception as e:
            logging.error(f"Failed to initialize SQLite memory backend: {e}")
            raise

    async def get(self, key: str) -> MemoryItem | None:
        """Get a memory item by key."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT key, value, memory_type, priority, created_at, accessed_at,
                           expires_at, access_count, size_bytes, metadata
                    FROM memory WHERE key = ?
                """, (key,))

                row = cursor.fetchone()
                if row:
                    # Check if expired
                    expires_at = None
                    if row[6]:  # expires_at
                        expires_at = datetime.fromisoformat(row[6])

                    if expires_at and datetime.utcnow() > expires_at:
                        # Remove expired item
                        await self.delete(key)
                        return None

                    # Update access time and count
                    cursor.execute("""
                        UPDATE memory 
                        SET accessed_at = ?, access_count = access_count + 1
                        WHERE key = ?
                    """, (datetime.utcnow().isoformat(), key))

                    conn.commit()

                    # Create memory item
                    item = MemoryItem(
                        key=row[0],
                        value=json.loads(row[1]),
                        memory_type=MemoryType(row[2]),
                        priority=MemoryPriority(row[3]),
                        created_at=datetime.fromisoformat(row[4]),
                        accessed_at=datetime.fromisoformat(row[5]),
                        expires_at=expires_at,
                        access_count=row[7] + 1,
                        size_bytes=row[8],
                        metadata=json.loads(row[9]) if row[9] else {}
                    )

                    return item

                return None

        except Exception as e:
            logging.error(f"Failed to get memory item {key}: {e}")
            return None

    async def set(self, key: str, value: Any, **kwargs) -> bool:
        """Set a memory item."""
        try:
            # Calculate size
            size_bytes = len(json.dumps(value).encode('utf-8'))

            # Serialize value and metadata
            serialized_value = json.dumps(value)
            serialized_metadata = json.dumps(kwargs.get('metadata', {}))

            # Format dates
            created_at = datetime.utcnow().isoformat()
            accessed_at = created_at
            expires_at = None
            if kwargs.get('expires_at'):
                expires_at = kwargs['expires_at'].isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert or replace
                cursor.execute("""
                    INSERT OR REPLACE INTO memory 
                    (key, value, memory_type, priority, created_at, accessed_at,
                     expires_at, access_count, size_bytes, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    key,
                    serialized_value,
                    kwargs.get('memory_type', MemoryType.PERSISTENT).value,
                    kwargs.get('priority', MemoryPriority.NORMAL).value,
                    created_at,
                    accessed_at,
                    expires_at,
                    0,  # access_count
                    size_bytes,
                    serialized_metadata
                ))

                conn.commit()
                return True

        except Exception as e:
            logging.error(f"Failed to set memory item {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a memory item."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memory WHERE key = ?", (key,))
                conn.commit()
                return cursor.rowcount > 0

        except Exception as e:
            logging.error(f"Failed to delete memory item {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM memory WHERE key = ?", (key,))
                return cursor.fetchone() is not None

        except Exception as e:
            logging.error(f"Failed to check existence of {key}: {e}")
            return False

    async def keys(self, pattern: str | None = None) -> list[str]:
        """Get all keys, optionally filtered by pattern."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if pattern:
                    cursor.execute("SELECT key FROM memory WHERE key LIKE ?", (f"%{pattern}%",))
                else:
                    cursor.execute("SELECT key FROM memory")

                rows = cursor.fetchall()
                return [row[0] for row in rows]

        except Exception as e:
            logging.error(f"Failed to get keys: {e}")
            return []

    async def clear(self) -> bool:
        """Clear all memory."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memory")
                conn.commit()
                return True

        except Exception as e:
            logging.error(f"Failed to clear memory: {e}")
            return False

    async def size(self) -> int:
        """Get the size of memory in bytes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(size_bytes) FROM memory")
                result = cursor.fetchone()
                return result[0] if result[0] else 0

        except Exception as e:
            logging.error(f"Failed to get memory size: {e}")
            return 0

    async def cleanup(self) -> int:
        """Clean up expired items."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM memory WHERE expires_at < ?",
                             (datetime.utcnow().isoformat(),))
                deleted_count = cursor.rowcount
                conn.commit()
                return deleted_count

        except Exception as e:
            logging.error(f"Failed to cleanup memory: {e}")
            return 0


class MemoryManager:
    """Memory manager for agents."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("memory_manager")

        # Initialize backends
        self._backends: dict[MemoryType, MemoryBackend] = {}

        # Ephemeral memory (always available)
        self._backends[MemoryType.EPHEMERAL] = EphemeralMemoryBackend()

        # Persistent memory (if enabled)
        if config.get("persistent_memory", True):
            db_path = config.get("db_path", "state/memory.db")
            self._backends[MemoryType.PERSISTENT] = SQLiteMemoryBackend(db_path)

        # Cache memory (TTL-based)
        self._backends[MemoryType.CACHE] = EphemeralMemoryBackend()

        # Shared memory (between agents)
        self._backends[MemoryType.SHARED] = EphemeralMemoryBackend() # Corrected from EphemeredMemoryBackend

        # Working memory (temporary)
        self._backends[MemoryType.WORKING] = EphemeralMemoryBackend()

        # Statistics
        self._stats = {
            "gets": 0,
            "sets": 0,
            "deletes": 0,
            "cleanups": 0,
            "start_time": datetime.utcnow()
        }

        # Start cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()

    async def get(self, key: str, memory_type: MemoryType = MemoryType.EPHEMERAL) -> Any | None:
        """Get a value from memory."""
        try:
            backend = self._backends.get(memory_type)
            if not backend:
                self.logger.warning(f"Memory backend not available: {memory_type}")
                return None

            item = await backend.get(key)
            if item:
                self._stats["gets"] += 1
                return item.value

            return None

        except Exception as e:
            self.logger.error(f"Failed to get from memory: {e}")
            return None

    async def set(self, key: str, value: Any,
                  memory_type: MemoryType = MemoryType.EPHEMERAL,
                  **kwargs) -> bool:
        """Set a value in memory."""
        try:
            backend = self._backends.get(memory_type)
            if not backend:
                self.logger.warning(f"Memory backend not available: {memory_type}")
                return False

            success = await backend.set(key, value, memory_type=memory_type, **kwargs)
            if success:
                self._stats["sets"] += 1

            return success

        except Exception as e:
            self.logger.error(f"Failed to set in memory: {e}")
            return False

    async def delete(self, key: str, memory_type: MemoryType = MemoryType.EPHEMERAL) -> bool:
        """Delete a value from memory."""
        try:
            backend = self._backends.get(memory_type)
            if not backend:
                self.logger.warning(f"Memory backend not available: {memory_type}")
                return False

            success = await backend.delete(key)
            if success:
                self._stats["deletes"] += 1

            return success

        except Exception as e:
            self.logger.error(f"Failed to delete from memory: {e}")
            return False

    async def exists(self, key: str, memory_type: MemoryType = MemoryType.EPHEMERAL) -> bool:
        """Check if a key exists in memory."""
        try:
            backend = self._backends.get(memory_type)
            if not backend:
                return False

            return await backend.exists(key)

        except Exception as e:
            self.logger.error(f"Failed to check existence: {e}")
            return False

    async def keys(self, pattern: str | None = None,
                   memory_type: MemoryType = MemoryType.EPHEMERAL) -> list[str]:
        """Get keys from memory."""
        try:
            backend = self._backends.get(memory_type)
            if not backend:
                return []

            return await backend.keys(pattern)

        except Exception as e:
            self.logger.error(f"Failed to get keys: {e}")
            return []

    async def clear(self, memory_type: MemoryType = MemoryType.EPHEMERAL) -> bool:
        """Clear memory of a specific type."""
        try:
            backend = self._backends.get(memory_type)
            if not backend:
                return False

            return await backend.clear()

        except Exception as e:
            self.logger.error(f"Failed to clear memory: {e}")
            return False

    async def cleanup(self) -> int:
        """Clean up expired items from all backends."""
        total_cleaned = 0

        for memory_type, backend in self._backends.items():
            try:
                cleaned = await backend.cleanup()
                total_cleaned += cleaned
                if cleaned > 0:
                    self.logger.debug(f"Cleaned {cleaned} items from {memory_type}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup {memory_type}: {e}")

        self._stats["cleanups"] += 1
        return total_cleaned

    def get_stats(self) -> dict[str, Any]:
        """Get memory manager statistics."""
        uptime = (datetime.utcnow() - self._stats["start_time"]).total_seconds()

        # Get backend sizes
        backend_sizes = {}
        for memory_type, backend in self._backends.items():
            try:
                size = asyncio.run(backend.size())
                backend_sizes[memory_type.value] = size
            except Exception:
                backend_sizes[memory_type.value] = 0

        return {
            "uptime": uptime,
            "backends": list(self._backends.keys()),
            "backend_sizes": backend_sizes,
            "stats": self._stats.copy()
        }

    def _start_cleanup_task(self) -> None:
        """Start the periodic cleanup task."""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # Clean up every 5 minutes
                    await self.cleanup()
                except Exception as e:
                    self.logger.error(f"Cleanup task error: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def shutdown(self) -> None:
        """Shutdown the memory manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clean up all backends
        for backend in self._backends.values():
            try:
                await backend.cleanup()
            except Exception as e:
                self.logger.error(f"Failed to cleanup backend: {e}")


# Global memory manager instance
_memory_manager: MemoryManager | None = None


def get_memory_manager(config: dict[str, Any] | None = None) -> MemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager

    if _memory_manager is None:
        if config is None:
            config = {}
        _memory_manager = MemoryManager(config)

    return _memory_manager


async def shutdown_memory_manager() -> None:
    """Shutdown the global memory manager."""
    global _memory_manager

    if _memory_manager:
        await _memory_manager.shutdown()
        _memory_manager = None
