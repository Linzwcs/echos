# file: src/MuzaiCore/interfaces/IAudioEngine.py
from abc import ABC, abstractmethod

from .ilifecycle import ILifecycleAware
from .isync import ISyncController
from .itimeline import IEngineTimeline
from ...models.engine_model import TransportStatus


class IEngine(ILifecycleAware, ABC):

    @property
    @abstractmethod
    def sync_controller(self) -> ISyncController:
        pass

    @property
    @abstractmethod
    def timeline(self) -> IEngineTimeline:
        pass

    @abstractmethod
    def play(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def report_latency(self) -> float:
        pass

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        pass

    @property
    @abstractmethod
    def current_beat(self) -> float:
        pass

    @property
    @abstractmethod
    def block_size(self) -> bool:
        pass

    @property
    @abstractmethod
    def sample_rate(self) -> float:
        pass

    @property
    @abstractmethod
    def transport_status(self) -> TransportStatus:
        pass
