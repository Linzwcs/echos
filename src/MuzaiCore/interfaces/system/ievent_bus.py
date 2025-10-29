from abc import ABC, abstractmethod


class IEventBus(ABC):
    """A central dispatcher for domain events."""

    @abstractmethod
    def subscribe(self, event_type, handler):
        ...

    def publish(self, event):
        ...
