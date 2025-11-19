"""
Event Bus Implementation
=========================

RabbitMQ-based event bus for asynchronous communication between services.
"""

import json
import logging
from typing import Callable, Dict, List, Optional, Type
import asyncio
from datetime import datetime

import aio_pika
from aio_pika import ExchangeType, Message, connect_robust
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange, AbstractQueue

from shared.events.events import Event, EventType
from shared.monitoring import (
    events_published_total,
    events_consumed_total,
    event_processing_duration_seconds,
    event_processing_errors_total,
)

logger = logging.getLogger(__name__)


class EventBus:
    """
    Event bus for publishing and subscribing to domain events.

    Uses RabbitMQ with topic exchange for flexible routing.

    Usage:
        # Publishing
        event_bus = await get_event_bus()
        await event_bus.publish(vulnerability_event)

        # Subscribing
        @event_bus.subscribe(EventType.VULNERABILITY_DETECTED)
        async def handle_vulnerability(event: VulnerabilityEvent):
            print(f"New vulnerability: {event.vulnerability_id}")

        await event_bus.start_consuming()
    """

    def __init__(
        self,
        rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/",
        exchange_name: str = "vulnzero.events",
    ):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name

        self.connection: Optional[AbstractConnection] = None
        self.channel: Optional[AbstractChannel] = None
        self.exchange: Optional[AbstractExchange] = None

        # Event handlers registry
        self._handlers: Dict[EventType, List[Callable]] = {}

        # Consumer queue
        self._queue: Optional[AbstractQueue] = None
        self._consumer_tag: Optional[str] = None

    async def connect(self):
        """Establish connection to RabbitMQ"""
        if self.connection and not self.connection.is_closed:
            return

        try:
            logger.info(f"Connecting to RabbitMQ at {self.rabbitmq_url}")

            # Create robust connection (auto-reconnect)
            self.connection = await connect_robust(
                self.rabbitmq_url,
                timeout=30,
            )

            # Create channel
            self.channel = await self.connection.channel()

            # Set QoS (prefetch 10 messages)
            await self.channel.set_qos(prefetch_count=10)

            # Declare exchange (topic type for pattern matching)
            self.exchange = await self.channel.declare_exchange(
                self.exchange_name,
                ExchangeType.TOPIC,
                durable=True,
            )

            logger.info(f"✓ Connected to RabbitMQ, exchange: {self.exchange_name}")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Close connection to RabbitMQ"""
        try:
            if self._consumer_tag and self._queue:
                await self._queue.cancel(self._consumer_tag)

            if self.channel and not self.channel.is_closed:
                await self.channel.close()

            if self.connection and not self.connection.is_closed:
                await self.connection.close()

            logger.info("✓ Disconnected from RabbitMQ")

        except Exception as e:
            logger.warning(f"Error disconnecting from RabbitMQ: {e}")

    async def publish(
        self,
        event: Event,
        routing_key: Optional[str] = None,
    ):
        """
        Publish an event to the event bus.

        Args:
            event: Event to publish
            routing_key: Custom routing key (defaults to event type)

        Raises:
            Exception if not connected or publish fails
        """
        if not self.exchange:
            await self.connect()

        if routing_key is None:
            routing_key = event.event_type.value

        try:
            # Serialize event
            event_json = event.json()

            # Create message
            message = Message(
                body=event_json.encode(),
                content_type="application/json",
                content_encoding="utf-8",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                timestamp=datetime.utcnow(),
                message_id=event.event_id,
                type=event.event_type.value,
            )

            # Publish
            await self.exchange.publish(
                message,
                routing_key=routing_key,
            )

            # Metrics
            events_published_total.labels(
                event_type=event.event_type.value,
                source_service=event.source_service,
            ).inc()

            logger.info(
                f"Published event: {event.event_type.value} "
                f"(id={event.event_id}, routing_key={routing_key})"
            )

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type.value}: {e}")
            raise

    def subscribe(
        self,
        event_type: EventType,
        event_class: Type[Event] = Event,
    ):
        """
        Decorator to register event handler.

        Args:
            event_type: Type of event to handle
            event_class: Event class to deserialize to

        Usage:
            @event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
            async def handle_vulnerability(event: VulnerabilityEvent):
                print(f"Handling vulnerability {event.vulnerability_id}")
        """

        def decorator(func: Callable):
            if event_type not in self._handlers:
                self._handlers[event_type] = []

            # Store handler with event class for deserialization
            self._handlers[event_type].append((func, event_class))

            logger.info(f"Registered handler {func.__name__} for {event_type.value}")

            return func

        return decorator

    async def start_consuming(
        self,
        queue_name: Optional[str] = None,
        routing_patterns: Optional[List[str]] = None,
    ):
        """
        Start consuming events from the event bus.

        Args:
            queue_name: Name of queue (defaults to service-specific)
            routing_patterns: Routing patterns to bind (defaults to all registered handlers)

        This will run indefinitely, processing events as they arrive.
        """
        if not self.channel:
            await self.connect()

        try:
            # Default queue name based on service
            if queue_name is None:
                import os
                service_name = os.getenv("SERVICE_NAME", "unknown-service")
                queue_name = f"{service_name}.events"

            # Declare queue
            self._queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                auto_delete=False,
            )

            # Bind queue to exchange for each event type we handle
            if routing_patterns is None:
                routing_patterns = [event_type.value for event_type in self._handlers.keys()]

            for pattern in routing_patterns:
                await self._queue.bind(
                    self.exchange,
                    routing_key=pattern,
                )
                logger.info(f"Bound queue {queue_name} to pattern: {pattern}")

            # Start consuming
            logger.info(f"Starting to consume events from queue: {queue_name}")

            async with self._queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        await self._process_message(message)

        except Exception as e:
            logger.error(f"Error consuming events: {e}")
            raise

    async def _process_message(self, message: aio_pika.IncomingMessage):
        """Process incoming message and dispatch to handlers"""
        import time

        start_time = time.time()

        try:
            # Parse event
            event_data = json.loads(message.body.decode())
            event_type_str = event_data.get("event_type")

            if not event_type_str:
                logger.warning("Received message without event_type, skipping")
                return

            # Find event type
            try:
                event_type = EventType(event_type_str)
            except ValueError:
                logger.warning(f"Unknown event type: {event_type_str}, skipping")
                return

            # Get handlers for this event type
            handlers = self._handlers.get(event_type, [])

            if not handlers:
                logger.debug(f"No handlers registered for {event_type.value}, skipping")
                return

            # Process each handler
            for handler_func, event_class in handlers:
                try:
                    # Deserialize to appropriate event class
                    event = event_class(**event_data)

                    # Call handler
                    if asyncio.iscoroutinefunction(handler_func):
                        await handler_func(event)
                    else:
                        handler_func(event)

                    # Metrics
                    events_consumed_total.labels(
                        event_type=event_type.value,
                        handler=handler_func.__name__,
                        status="success",
                    ).inc()

                    logger.debug(
                        f"Processed event {event_type.value} with {handler_func.__name__}"
                    )

                except Exception as e:
                    # Log error but continue processing other handlers
                    logger.error(
                        f"Error in handler {handler_func.__name__} "
                        f"for event {event_type.value}: {e}",
                        exc_info=True,
                    )

                    # Metrics
                    events_consumed_total.labels(
                        event_type=event_type.value,
                        handler=handler_func.__name__,
                        status="error",
                    ).inc()

                    event_processing_errors_total.labels(
                        event_type=event_type.value,
                        handler=handler_func.__name__,
                        error_type=type(e).__name__,
                    ).inc()

            # Record processing duration
            duration = time.time() - start_time
            event_processing_duration_seconds.labels(
                event_type=event_type.value,
            ).observe(duration)

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Message will be requeued due to exception


# Global event bus instance
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """
    Get or create global event bus instance.

    Returns:
        EventBus instance (connected)
    """
    global _event_bus

    if _event_bus is None:
        import os

        rabbitmq_url = os.getenv(
            "RABBITMQ_URL",
            "amqp://guest:guest@rabbitmq:5672/",
        )

        _event_bus = EventBus(rabbitmq_url=rabbitmq_url)
        await _event_bus.connect()

    return _event_bus


async def close_event_bus():
    """Close global event bus connection"""
    global _event_bus

    if _event_bus:
        await _event_bus.disconnect()
        _event_bus = None
