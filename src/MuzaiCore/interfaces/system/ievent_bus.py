from abc import ABC, abstractmethod


class IEventBus(ABC):

    @abstractmethod
    def subscribe(self, event_type, handler):
        pass

    @abstractmethod
    def unsubscribe(self, event_type, handler):
        pass

    @abstractmethod
    def publish(self, event):
        pass

    @abstractmethod
    def clear(self):
        pass
