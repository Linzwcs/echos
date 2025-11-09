# file: src/MuzaiCore/interfaces/IAudioEngine.py
from abc import ABC, abstractmethod
from typing import Optional

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
    def pause(self):
        pass

    @abstractmethod
    def seek(self, beat: float):
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


class IEngineController(ILifecycleAware, ABC):

    @property
    @abstractmethod
    def engine(self) -> Optional[IEngine]:
        pass

    @abstractmethod
    def attach_engine(self, engine: IEngine) -> bool:
        pass

    @abstractmethod
    def detach_engine(self) -> bool:
        pass

    @abstractmethod
    def play(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def pause(self):
        pass

    @abstractmethod
    def seek(self, beat: float):
        pass

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        pass

    @property
    @abstractmethod
    def current_beat(self) -> float:
        pass
