"""
Event Bus Implementation - Infrastructure layer concrete event bus.
Follows SOLID principles and Clean Architecture patterns.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from loguru import logger

from domain.events import (
    Event, EventType, EventPriority, EventHandler, EventBus,
    EventSubscriber, EventPublisher, EventFilter, EventMetrics
)


class AsyncEventBus(EventBus):
    """
    Asynchronous event bus implementation.
    
    This follows the Observer Pattern and provides:
    - Asynchronous event publishing
    - Event filtering and routing
    - Handler management
    - Event metrics and monitoring
    """
    
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self.subscribers: List[EventSubscriber] = []
        self.metrics = EventMetrics()
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
        
        # Event processing settings
        self.batch_size = 10
        self.processing_interval = 0.1  # seconds
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
        logger.info("AsyncEventBus initialized")
    
    async def start(self):
        """Start the event bus processing."""
        if self.running:
            logger.warning("Event bus already running")
            return
        
        self.running = True
        self.processing_task = asyncio.create_task(self._process_events_loop())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop the event bus processing."""
        if not self.running:
            logger.warning("Event bus not running")
            return
        
        self.running = False
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event bus stopped")
    
    async def publish(self, event: Event) -> bool:
        """
        Publish an event to the event bus.
        
        Args:
            event: Event to publish
            
        Returns:
            True if event was queued successfully, False otherwise
        """
        try:
            # Check if queue is full
            if self.event_queue.qsize() >= self.max_queue_size:
                logger.warning(f"Event queue full ({self.max_queue_size}), dropping event: {event.type.value}")
                return False
            
            # Add event to queue
            await self.event_queue.put(event)
            
            # Record metrics
            self.metrics.record_event(event)
            
            logger.debug(f"Event queued: {event.type.value} from {event.source}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            return False
    
    def subscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Event handler to register
            
        Returns:
            True if subscription successful, False otherwise
        """
        try:
            if handler not in self.handlers[event_type]:
                self.handlers[event_type].append(handler)
                
                # Update metrics
                self.metrics.record_handler(event_type, len(self.handlers[event_type]))
                
                logger.info(f"Handler subscribed to {event_type.value}: {handler.__class__.__name__}")
                return True
            
            logger.debug(f"Handler already subscribed to {event_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe handler: {e}")
            return False
    
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Event handler to unregister
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        try:
            if event_type in self.handlers and handler in self.handlers[event_type]:
                self.handlers[event_type].remove(handler)
                
                # Update metrics
                self.metrics.record_handler(event_type, len(self.handlers[event_type]))
                
                logger.info(f"Handler unsubscribed from {event_type.value}: {handler.__class__.__name__}")
                return True
            
            logger.debug(f"Handler not subscribed to {event_type.value}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe handler: {e}")
            return False
    
    def add_subscriber(self, subscriber: EventSubscriber) -> bool:
        """
        Add a general event subscriber.
        
        Args:
            subscriber: Event subscriber to add
            
        Returns:
            True if addition successful, False otherwise
        """
        try:
            if subscriber not in self.subscribers:
                self.subscribers.append(subscriber)
                logger.info(f"Subscriber added: {subscriber.__class__.__name__}")
                return True
            
            logger.debug("Subscriber already added")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add subscriber: {e}")
            return False
    
    def remove_subscriber(self, subscriber: EventSubscriber) -> bool:
        """
        Remove a general event subscriber.
        
        Args:
            subscriber: Event subscriber to remove
            
        Returns:
            True if removal successful, False otherwise
        """
        try:
            if subscriber in self.subscribers:
                self.subscribers.remove(subscriber)
                logger.info(f"Subscriber removed: {subscriber.__class__.__name__}")
                return True
            
            logger.debug("Subscriber not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove subscriber: {e}")
            return False
    
    async def process_events(self) -> int:
        """
        Process all pending events.
        
        Returns:
            Number of events processed
        """
        processed_count = 0
        
        try:
            # Process events in batches
            while not self.event_queue.empty() and processed_count < self.batch_size:
                try:
                    event = self.event_queue.get_nowait()
                    await self._process_single_event(event)
                    processed_count += 1
                    
                except asyncio.QueueEmpty:
                    break
                except Exception as e:
                    logger.error(f"Failed to process event: {e}")
                    continue
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Event processing failed: {e}")
            return processed_count
    
    async def _process_events_loop(self):
        """Main event processing loop."""
        logger.info("Event processing loop started")
        
        while self.running:
            try:
                # Process events
                processed = await self.process_events()
                
                if processed > 0:
                    logger.debug(f"Processed {processed} events")
                
                # Wait before next processing cycle
                await asyncio.sleep(self.processing_interval)
                
            except asyncio.CancelledError:
                logger.info("Event processing loop cancelled")
                break
            except Exception as e:
                logger.error(f"Event processing loop error: {e}")
                await asyncio.sleep(1.0)  # Wait before retrying
        
        logger.info("Event processing loop stopped")
    
    async def _process_single_event(self, event: Event):
        """Process a single event."""
        try:
            # Notify general subscribers
            await self._notify_subscribers(event)
            
            # Notify specific handlers
            await self._notify_handlers(event)
            
            # Mark event as processed
            self.event_queue.task_done()
            
        except Exception as e:
            logger.error(f"Failed to process event {event.id}: {e}")
    
    async def _notify_subscribers(self, event: Event):
        """Notify general event subscribers."""
        for subscriber in self.subscribers:
            try:
                if event.type in subscriber.get_subscribed_events():
                    await subscriber.on_event(event)
            except Exception as e:
                logger.error(f"Subscriber notification failed: {e}")
    
    async def _notify_handlers(self, event: Event):
        """Notify specific event handlers."""
        handlers = self.handlers.get(event.type, [])
        
        for handler in handlers:
            try:
                if handler.can_handle(event):
                    success = await handler.handle(event)
                    if not success:
                        logger.warning(f"Handler {handler.__class__.__name__} failed to handle event")
                        
            except Exception as e:
                logger.error(f"Handler {handler.__class__.__name__} error: {e}")
    
    async def publish_with_filter(self, event: Event, event_filter: EventFilter) -> bool:
        """
        Publish an event only if it matches the filter.
        
        Args:
            event: Event to publish
            event_filter: Filter to apply
            
        Returns:
            True if event was published, False if filtered out
        """
        if event_filter.matches(event):
            return await self.publish(event)
        else:
            logger.debug(f"Event filtered out: {event.type.value}")
            return False
    
    async def publish_batch(self, events: List[Event]) -> int:
        """
        Publish multiple events in batch.
        
        Args:
            events: List of events to publish
            
        Returns:
            Number of events successfully published
        """
        published_count = 0
        
        for event in events:
            if await self.publish(event):
                published_count += 1
        
        logger.info(f"Batch published {published_count}/{len(events)} events")
        return published_count
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get event queue status."""
        return {
            "queue_size": self.event_queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "running": self.running,
            "handler_counts": {
                event_type.value: len(handlers)
                for event_type, handlers in self.handlers.items()
            },
            "subscriber_count": len(self.subscribers)
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics."""
        return {
            "queue_status": self.get_queue_status(),
            "event_metrics": self.metrics.get_summary(),
            "processing_settings": {
                "batch_size": self.batch_size,
                "processing_interval": self.processing_interval,
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay
            }
        }
    
    async def flush_queue(self) -> int:
        """Flush all events from the queue (for testing/debugging)."""
        flushed_count = 0
        
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
                self.event_queue.task_done()
                flushed_count += 1
            except asyncio.QueueEmpty:
                break
        
        logger.info(f"Flushed {flushed_count} events from queue")
        return flushed_count


class EventPublisherImpl(EventPublisher):
    """
    Concrete event publisher implementation.
    
    This provides a simple interface for publishing events
    without needing to manage the event bus directly.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
    
    async def publish_event(self, event: Event) -> bool:
        """Publish a single event."""
        return await self.event_bus.publish(event)
    
    async def publish_events(self, events: List[Event]) -> int:
        """Publish multiple events."""
        if hasattr(self.event_bus, 'publish_batch'):
            return await self.event_bus.publish_batch(events)
        else:
            # Fallback to individual publishing
            published_count = 0
            for event in events:
                if await self.event_bus.publish(event):
                    published_count += 1
            return published_count


class EventSubscriberImpl(EventSubscriber):
    """
    Concrete event subscriber implementation.
    
    This provides a base implementation for event subscribers
    that can be extended for specific use cases.
    """
    
    def __init__(self, subscribed_events: List[EventType]):
        self.subscribed_events = subscribed_events
        self.received_events: List[Event] = []
        self.event_count = 0
    
    async def on_event(self, event: Event) -> None:
        """Handle received event."""
        self.received_events.append(event)
        self.event_count += 1
        
        # Call the specific event handler
        await self.handle_event(event)
    
    def get_subscribed_events(self) -> List[EventType]:
        """Get list of subscribed event types."""
        return self.subscribed_events
    
    async def handle_event(self, event: Event) -> None:
        """
        Handle a specific event.
        
        Override this method in subclasses to implement
        specific event handling logic.
        """
        logger.debug(f"Event subscriber received event: {event.type.value}")
    
    def get_received_events(self) -> List[Event]:
        """Get list of received events."""
        return self.received_events.copy()
    
    def get_event_count(self) -> int:
        """Get total count of received events."""
        return self.event_count
    
    def clear_events(self):
        """Clear received events history."""
        self.received_events.clear()
        self.event_count = 0
