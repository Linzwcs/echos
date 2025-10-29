# file: src/MuzaiCore/core/event_bus.py
"""
A simple, in-memory domain event bus.
"""
from collections import defaultdict
from typing import Callable, List, Dict, Type, Any, TypeVar
from ..interfaces.system.ievent_bus import IEventBus
from ..models.event_model import BaseEvent


class EventBus(IEventBus):
    """A central dispatcher for domain events."""

    def __init__(self):
        self._subscribers: Dict[Type[BaseEvent],
                                List[Callable]] = defaultdict(list)
        print("EventBus: Initialized.")

    def subscribe(self, event_type: BaseEvent, handler: Callable):
        """Register a handler for a specific event type."""
        # Special case: subscribing to the base class means listening to ALL events.
        if event_type is BaseEvent:
            # We add this handler to a special list or handle it differently during publish.
            # For simplicity here, we will handle it in the publish method.
            pass

        self._subscribers[event_type].append(handler)
        print(
            f"EventBus: Handler '{handler.__name__}' subscribed to '{event_type.__name__}'"
        )

    def publish(self, event: BaseEvent):  # <-- USE THE BASE CLASS TYPE HINT
        """Publish an event to all registered handlers."""
        event_type = type(event)

        # Notify handlers for the specific event type
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(
                        f"Error in specific event handler for {event_type.__name__}: {e}"
                    )

        # Notify handlers subscribed to the BaseEvent (catch-all)
        if BaseEvent in self._subscribers:
            for handler in self._subscribers[BaseEvent]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in catch-all event handler: {e}")
