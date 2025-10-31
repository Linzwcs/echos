from abc import ABC, abstractmethod
from typing import List, Optional


class IEventBus(ABC):
    """A central dispatcher for domain events."""

    @abstractmethod
    def subscribe(self, event_type, handler):
        ...

    @abstractmethod
    def unsubscribe(self, event_type, handler):
        ...

    @abstractmethod
    def publish(self, event):
        ...

    @abstractmethod
    def clear(self):
        """Clears all subscriptions."""
        pass
