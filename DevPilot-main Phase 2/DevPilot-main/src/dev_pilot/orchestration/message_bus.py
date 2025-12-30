"""
Message Bus Module

Provides the communication infrastructure for inter-agent messaging.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
import asyncio
from collections import defaultdict
from loguru import logger
import json

from src.dev_pilot.agents.agent_message import AgentMessage, MessageType, MessagePriority


class MessageBus(ABC):
    """
    Abstract base class for message bus implementations.
    
    Provides publish/subscribe pattern for agent communication.
    """
    
    @abstractmethod
    async def publish(self, message: AgentMessage):
        """Publish a message to the bus."""
        pass
    
    @abstractmethod
    async def subscribe(
        self, 
        subscriber_id: str, 
        handler: Callable,
        message_types: Optional[List[MessageType]] = None,
        sender_filter: Optional[str] = None
    ):
        """Subscribe to messages."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscriber_id: str):
        """Unsubscribe from messages."""
        pass
    
    @abstractmethod
    async def send_direct(self, recipient_id: str, message: AgentMessage):
        """Send a message directly to a specific recipient."""
        pass


class Subscription:
    """Represents a message subscription."""
    
    def __init__(
        self,
        subscriber_id: str,
        handler: Callable,
        message_types: Optional[List[MessageType]] = None,
        sender_filter: Optional[str] = None
    ):
        self.subscriber_id = subscriber_id
        self.handler = handler
        self.message_types = set(message_types) if message_types else None
        self.sender_filter = sender_filter
        self.created_at = datetime.utcnow()
        self.messages_received = 0
    
    def matches(self, message: AgentMessage) -> bool:
        """Check if a message matches this subscription."""
        # Check message type filter
        if self.message_types and message.message_type not in self.message_types:
            return False
        
        # Check sender filter
        if self.sender_filter and message.sender != self.sender_filter:
            return False
        
        return True


class InMemoryMessageBus(MessageBus):
    """
    In-memory message bus implementation.
    
    Suitable for single-process applications or testing.
    For production with multiple processes, use RedisMessageBus.
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, Subscription] = {}
        self._direct_handlers: Dict[str, Callable] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._message_history: List[AgentMessage] = []
        self._max_history = 1000
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Metrics
        self._metrics = {
            "messages_published": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
        }
        
        logger.info("InMemoryMessageBus initialized")
    
    async def start(self):
        """Start the message bus processing loop."""
        if self._running:
            return
        
        self._running = True
        logger.info("MessageBus started")
        
        # Start the message processing loop
        asyncio.create_task(self._process_messages())
    
    async def stop(self):
        """Stop the message bus."""
        self._running = False
        logger.info("MessageBus stopped")
    
    async def publish(self, message: AgentMessage):
        """
        Publish a message to the bus.
        
        Messages are queued and processed asynchronously.
        """
        await self._message_queue.put(message)
        self._metrics["messages_published"] += 1
        
        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history:
            self._message_history.pop(0)
        
        logger.debug(
            f"Message published: {message.message_type.value} "
            f"from {message.sender} to {message.recipient}"
        )
    
    async def _process_messages(self):
        """Process messages from the queue."""
        while self._running:
            try:
                # Wait for a message with timeout
                try:
                    message = await asyncio.wait_for(
                        self._message_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Route the message
                await self._route_message(message)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                self._metrics["messages_failed"] += 1
    
    async def _route_message(self, message: AgentMessage):
        """Route a message to appropriate handlers."""
        delivered = False
        
        # Handle broadcast messages
        if message.recipient == "BROADCAST":
            for subscription in self._subscriptions.values():
                if subscription.matches(message):
                    try:
                        await self._deliver_to_subscriber(subscription, message)
                        delivered = True
                    except Exception as e:
                        logger.error(f"Error delivering broadcast to {subscription.subscriber_id}: {e}")
        else:
            # Direct message to specific recipient
            if message.recipient in self._direct_handlers:
                try:
                    handler = self._direct_handlers[message.recipient]
                    await handler(message)
                    delivered = True
                    self._metrics["messages_delivered"] += 1
                except Exception as e:
                    logger.error(f"Error delivering to {message.recipient}: {e}")
                    self._metrics["messages_failed"] += 1
            
            # Also check subscriptions
            for subscription in self._subscriptions.values():
                if subscription.subscriber_id == message.recipient and subscription.matches(message):
                    try:
                        await self._deliver_to_subscriber(subscription, message)
                        delivered = True
                    except Exception as e:
                        logger.error(f"Error delivering to {subscription.subscriber_id}: {e}")
        
        if not delivered:
            logger.warning(f"No handler found for message to {message.recipient}")
        
        # Emit event
        await self._emit_event("message_routed", message)
    
    async def _deliver_to_subscriber(self, subscription: Subscription, message: AgentMessage):
        """Deliver a message to a subscriber."""
        subscription.messages_received += 1
        
        if asyncio.iscoroutinefunction(subscription.handler):
            await subscription.handler(message)
        else:
            subscription.handler(message)
        
        self._metrics["messages_delivered"] += 1
    
    async def subscribe(
        self, 
        subscriber_id: str, 
        handler: Callable,
        message_types: Optional[List[MessageType]] = None,
        sender_filter: Optional[str] = None
    ):
        """
        Subscribe to messages.
        
        Args:
            subscriber_id: Unique identifier for the subscriber
            handler: Callback function to handle messages
            message_types: Optional filter for specific message types
            sender_filter: Optional filter for specific sender
        """
        subscription = Subscription(
            subscriber_id=subscriber_id,
            handler=handler,
            message_types=message_types,
            sender_filter=sender_filter
        )
        
        self._subscriptions[subscriber_id] = subscription
        logger.debug(f"Subscriber added: {subscriber_id}")
    
    async def unsubscribe(self, subscriber_id: str):
        """Unsubscribe from messages."""
        if subscriber_id in self._subscriptions:
            del self._subscriptions[subscriber_id]
            logger.debug(f"Subscriber removed: {subscriber_id}")
        
        if subscriber_id in self._direct_handlers:
            del self._direct_handlers[subscriber_id]
    
    async def send_direct(self, recipient_id: str, message: AgentMessage):
        """Send a message directly to a specific recipient."""
        message.recipient = recipient_id
        await self.publish(message)
    
    def register_direct_handler(self, agent_id: str, handler: Callable):
        """Register a direct message handler for an agent."""
        self._direct_handlers[agent_id] = handler
        logger.debug(f"Direct handler registered: {agent_id}")
    
    def unregister_direct_handler(self, agent_id: str):
        """Unregister a direct message handler."""
        if agent_id in self._direct_handlers:
            del self._direct_handlers[agent_id]
    
    # Event system for external observers
    def on_event(self, event_name: str, handler: Callable):
        """Register an event handler."""
        self._event_handlers[event_name].append(handler)
    
    async def _emit_event(self, event_name: str, data: Any):
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers[event_name]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get message bus metrics."""
        return {
            **self._metrics,
            "active_subscriptions": len(self._subscriptions),
            "direct_handlers": len(self._direct_handlers),
            "queue_size": self._message_queue.qsize(),
            "history_size": len(self._message_history),
        }
    
    def get_message_history(
        self, 
        limit: int = 100,
        sender: Optional[str] = None,
        recipient: Optional[str] = None,
        message_type: Optional[MessageType] = None
    ) -> List[AgentMessage]:
        """Get message history with optional filters."""
        messages = self._message_history[-limit:]
        
        if sender:
            messages = [m for m in messages if m.sender == sender]
        if recipient:
            messages = [m for m in messages if m.recipient == recipient]
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        
        return messages


class RedisMessageBus(MessageBus):
    """
    Redis-based message bus implementation.
    
    Suitable for distributed systems with multiple processes.
    """
    
    def __init__(self, redis_client):
        self._redis = redis_client
        self._subscriptions: Dict[str, Subscription] = {}
        self._pubsub = None
        self._running = False
        self._channel_prefix = "devpilot:messages:"
        
        logger.info("RedisMessageBus initialized")
    
    async def start(self):
        """Start the Redis message bus."""
        self._pubsub = self._redis.pubsub()
        self._running = True
        
        # Subscribe to the main channel
        await self._pubsub.subscribe(f"{self._channel_prefix}broadcast")
        
        # Start listening
        asyncio.create_task(self._listen())
        
        logger.info("RedisMessageBus started")
    
    async def stop(self):
        """Stop the Redis message bus."""
        self._running = False
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        logger.info("RedisMessageBus stopped")
    
    async def _listen(self):
        """Listen for messages on Redis channels."""
        while self._running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                if message:
                    await self._handle_redis_message(message)
            except Exception as e:
                logger.error(f"Error in Redis listener: {e}")
                await asyncio.sleep(1)
    
    async def _handle_redis_message(self, redis_message):
        """Handle a message received from Redis."""
        try:
            data = redis_message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            
            message = AgentMessage.from_json(data)
            await self._route_message(message)
        except Exception as e:
            logger.error(f"Error handling Redis message: {e}")
    
    async def _route_message(self, message: AgentMessage):
        """Route message to appropriate handlers."""
        for subscription in self._subscriptions.values():
            if subscription.matches(message):
                try:
                    if asyncio.iscoroutinefunction(subscription.handler):
                        await subscription.handler(message)
                    else:
                        subscription.handler(message)
                except Exception as e:
                    logger.error(f"Error delivering to {subscription.subscriber_id}: {e}")
    
    async def publish(self, message: AgentMessage):
        """Publish a message via Redis."""
        channel = self._get_channel(message.recipient)
        await self._redis.publish(channel, message.to_json())
        logger.debug(f"Published to Redis channel: {channel}")
    
    async def subscribe(
        self, 
        subscriber_id: str, 
        handler: Callable,
        message_types: Optional[List[MessageType]] = None,
        sender_filter: Optional[str] = None
    ):
        """Subscribe to messages."""
        subscription = Subscription(
            subscriber_id=subscriber_id,
            handler=handler,
            message_types=message_types,
            sender_filter=sender_filter
        )
        
        self._subscriptions[subscriber_id] = subscription
        
        # Subscribe to the agent's direct channel
        channel = self._get_channel(subscriber_id)
        if self._pubsub:
            await self._pubsub.subscribe(channel)
        
        logger.debug(f"Subscribed to Redis channel: {channel}")
    
    async def unsubscribe(self, subscriber_id: str):
        """Unsubscribe from messages."""
        if subscriber_id in self._subscriptions:
            del self._subscriptions[subscriber_id]
            
            channel = self._get_channel(subscriber_id)
            if self._pubsub:
                await self._pubsub.unsubscribe(channel)
    
    async def send_direct(self, recipient_id: str, message: AgentMessage):
        """Send a direct message via Redis."""
        message.recipient = recipient_id
        await self.publish(message)
    
    def _get_channel(self, recipient: str) -> str:
        """Get the Redis channel name for a recipient."""
        if recipient == "BROADCAST":
            return f"{self._channel_prefix}broadcast"
        return f"{self._channel_prefix}agent:{recipient}"


# Factory function
def create_message_bus(
    bus_type: str = "memory",
    redis_client: Optional[Any] = None
) -> MessageBus:
    """
    Create a message bus instance.
    
    Args:
        bus_type: Type of bus ("memory" or "redis")
        redis_client: Redis client instance (required for redis type)
        
    Returns:
        MessageBus instance
    """
    if bus_type == "memory":
        return InMemoryMessageBus()
    elif bus_type == "redis":
        if not redis_client:
            raise ValueError("Redis client required for redis message bus")
        return RedisMessageBus(redis_client)
    else:
        raise ValueError(f"Unknown message bus type: {bus_type}")
