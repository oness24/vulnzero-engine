"""
Event Handler Utilities
========================

Base classes and decorators for event handlers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Callable, Type

from shared.events.events import Event, EventType

logger = logging.getLogger(__name__)


class EventHandler(ABC):
    """
    Base class for event handlers.

    Usage:
        class VulnerabilityDetectedHandler(EventHandler):
            event_type = EventType.VULNERABILITY_DETECTED

            async def handle(self, event: VulnerabilityEvent):
                # Process vulnerability detected event
                print(f"New vulnerability: {event.vulnerability_id}")

        # Register with event bus
        handler = VulnerabilityDetectedHandler()
        event_bus.subscribe(handler.event_type)(handler.handle)
    """

    event_type: EventType

    @abstractmethod
    async def handle(self, event: Event):
        """
        Handle the event.

        Args:
            event: The event to handle

        Raises:
            Exception if handling fails (will be logged and tracked)
        """
        pass

    def __init__(self):
        """Initialize handler"""
        if not hasattr(self, "event_type"):
            raise ValueError(f"EventHandler {self.__class__.__name__} must define event_type")


def event_handler(
    event_type: EventType,
    event_class: Type[Event] = Event,
):
    """
    Simple decorator for event handlers.

    Args:
        event_type: Type of event to handle
        event_class: Event class for type hints

    Usage:
        @event_handler(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
        async def on_vulnerability_detected(event: VulnerabilityEvent):
            print(f"Vulnerability detected: {event.cve_id}")

        # This is equivalent to:
        # @event_bus.subscribe(EventType.VULNERABILITY_DETECTED, VulnerabilityEvent)
    """

    def decorator(func: Callable):
        # Add metadata to function for later registration
        func._event_type = event_type
        func._event_class = event_class
        return func

    return decorator


# Example handlers for common scenarios
class LoggingEventHandler(EventHandler):
    """
    Simple handler that logs all events.

    Useful for debugging and monitoring.
    """

    def __init__(self, event_type: EventType):
        self.event_type = event_type
        super().__init__()

    async def handle(self, event: Event):
        """Log event details"""
        logger.info(
            f"[EVENT] {event.event_type.value} "
            f"from {event.source_service} "
            f"at {event.timestamp} "
            f"(id={event.event_id})"
        )


class MetricsEventHandler(EventHandler):
    """
    Handler that updates Prometheus metrics based on events.

    Automatically tracks event counts and durations.
    """

    def __init__(self, event_type: EventType):
        self.event_type = event_type
        super().__init__()

    async def handle(self, event: Event):
        """Update metrics based on event"""
        from shared.monitoring import (
            vulnerabilities_detected_total,
            patches_generated_total,
            deployments_total,
        )

        # Update business metrics based on event type
        if event.event_type == EventType.VULNERABILITY_DETECTED:
            severity = event.data.get("severity", "unknown")
            source = event.data.get("scanner_source", "unknown")
            vulnerabilities_detected_total.labels(
                severity=severity,
                source=source,
            ).inc()

        elif event.event_type == EventType.PATCH_GENERATED:
            patch_type = event.data.get("patch_type", "unknown")
            patches_generated_total.labels(type=patch_type).inc()

        elif event.event_type == EventType.DEPLOYMENT_SUCCEEDED:
            method = event.data.get("deployment_method", "unknown")
            deployments_total.labels(method=method, status="success").inc()

        elif event.event_type == EventType.DEPLOYMENT_FAILED:
            method = event.data.get("deployment_method", "unknown")
            deployments_total.labels(method=method, status="failed").inc()
