from collections import defaultdict
from typing import Callable, List, Dict, Type
from ..interfaces.system.ievent_bus import IEventBus
from ..models.event_model import BaseEvent


class EventBus(IEventBus):

    def __init__(self):
        self._subscribers: Dict[Type[BaseEvent],
                                List[Callable]] = defaultdict(list)
        print("EventBus: Initialized.")

    def subscribe(self, event_type: Type[BaseEvent], handler: Callable):
        self._subscribers[event_type].append(handler)
        print(
            f"EventBus: Handler '{handler.__name__}' subscribed to '{event_type.__name__}'"
        )

    def unsubscribe(self, event_type: Type[BaseEvent], handler: Callable):

        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                print(
                    f"EventBus: Handler '{handler.__name__}' unsubscribed from '{event_type.__name__}'"
                )
            except ValueError:
                pass

    def publish(self, event: BaseEvent):

        event_type = type(event)
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(
                        f"EventBus Error: Handler '{handler.__name__}' failed for {event_type.__name__}: {e}"
                    )

        if BaseEvent in self._subscribers and event_type != BaseEvent:
            for handler in self._subscribers[BaseEvent]:
                try:
                    handler(event)
                except Exception as e:
                    print(
                        f"EventBus Error: Catch-all handler '{handler.__name__}' failed: {e}"
                    )

    def clear(self):
        self._subscribers.clear()
        print("EventBus: All subscriptions cleared.")
