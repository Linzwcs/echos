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
        """Gets the managed engine instance, if it exists."""
        pass

    @abstractmethod
    def attach_engine(self, engine: IEngine) -> bool:
        """
        Creates and attaches an audio engine to the project.
        This method will also mount the engine and its sync_controller to the
        project's event bus to start synchronization.
        """
        pass

    @abstractmethod
    def detach_engine(self) -> bool:
        """
        Detaches and disposes the audio engine from the project.
        This method will unmount the engine and its sync_controller.
        """
        pass

    @abstractmethod
    def play(self):
        """Starts or resumes playback."""
        pass

    @abstractmethod
    def stop(self):
        """Stops playback and returns to the beginning or last start position."""
        pass

    @abstractmethod
    def pause(self):
        """Pauses playback at the current position."""
        pass

    @abstractmethod
    def seek(self, beat: float):
        """Seeks the playhead to a specific beat."""
        pass

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Returns True if the engine is currently playing."""
        pass

    @property
    @abstractmethod
    def current_beat(self) -> float:
        """Gets the current playback position in beats."""
        pass
