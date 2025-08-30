"""
Message Queue for the AiBotBS Runtime Agent System.
Handles message queuing and priority management.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .base import Message, MessageType, MessagePriority


class MessageQueue:
    """Message queue with priority management."""
    
    def __init__(self):
        self.logger = logging.getLogger("message_queue")
        
        # Priority queues
        self._high_priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._normal_priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._low_priority_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Statistics
        self._messages_enqueued = 0
        self._messages_processed = 0
    
    async def enqueue(self, message_type: str, body: dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL) -> None:
        """Enqueue a message with specified priority."""
        try:
            # Create a proper Message object
            message = Message(
                id=str(uuid4()),
                type=MessageType.TASK,
                priority=priority,
                from_agent="system",
                to_agent="orchestrator",
                subject=message_type,
                body=body,
                metadata={"enqueued": True, "timestamp": datetime.now(UTC).isoformat()}
            )
            
            # Add to appropriate priority queue
            if priority == MessagePriority.HIGH:
                await self._high_priority_queue.put((1, message))
            elif priority == MessagePriority.LOW:
                await self._low_priority_queue.put((3, message))
            else:  # NORMAL
                await self._normal_priority_queue.put((2, message))
            
            self._messages_enqueued += 1
            self.logger.debug(f"Message enqueued: {message_type} (priority: {priority.value})")
            
        except Exception as e:
            self.logger.warning(f"Failed to enqueue message: {e}")
    
    async def dequeue_high_priority(self) -> Message | None:
        """Dequeue from high priority queue."""
        try:
            if not self._high_priority_queue.empty():
                _, message = await self._high_priority_queue.get()
                self._messages_processed += 1
                return message
        except Exception as e:
            self.logger.error(f"Error dequeuing high priority message: {e}")
        return None
    
    async def dequeue_normal_priority(self) -> Message | None:
        """Dequeue from normal priority queue."""
        try:
            if not self._normal_priority_queue.empty():
                _, message = await self._normal_priority_queue.get()
                self._messages_processed += 1
                return message
        except Exception as e:
            self.logger.error(f"Error dequeuing normal priority message: {e}")
        return None
    
    async def dequeue_low_priority(self) -> Message | None:
        """Dequeue from low priority queue."""
        try:
            if not self._low_priority_queue.empty():
                _, message = await self._low_priority_queue.get()
                self._messages_processed += 1
                return message
        except Exception as e:
            self.logger.error(f"Error dequeuing low priority message: {e}")
        return None
    
    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            "high_priority_size": self._high_priority_queue.qsize(),
            "normal_priority_size": self._normal_priority_queue.qsize(),
            "low_priority_size": self._low_priority_queue.qsize(),
            "messages_enqueued": self._messages_enqueued,
            "messages_processed": self._messages_processed
        }
    
    def is_empty(self) -> bool:
        """Check if all queues are empty."""
        return (self._high_priority_queue.empty() and 
                self._normal_priority_queue.empty() and 
                self._low_priority_queue.empty())
