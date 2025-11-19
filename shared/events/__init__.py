"""Event-driven communication system for VulnZero services"""

from shared.events.event_bus import (
    EventBus,
    get_event_bus,
    close_event_bus,
)
from shared.events.events import (
    Event,
    EventType,
    VulnerabilityEvent,
    PatchEvent,
    DeploymentEvent,
    AssetEvent,
    ScanEvent,
)
from shared.events.handlers import (
    EventHandler,
    event_handler,
)

__all__ = [
    # Event bus
    "EventBus",
    "get_event_bus",
    "close_event_bus",
    # Events
    "Event",
    "EventType",
    "VulnerabilityEvent",
    "PatchEvent",
    "DeploymentEvent",
    "AssetEvent",
    "ScanEvent",
    # Handlers
    "EventHandler",
    "event_handler",
]
