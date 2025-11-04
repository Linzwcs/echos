from abc import ABC, abstractmethod
from typing import List
from .ievent_bus import IEventBus
from .ilifecycle import ILifecycleAware
from ...models.timeline_model import Tempo, TimeSignature


class IReadonlyTimeline(ABC):

    @property
    @abstractmethod
    def tempos(self) -> List[Tempo]:
        pass

    @property
    @abstractmethod
    def time_signatures(self) -> List[TimeSignature]:
        pass

    @abstractmethod
    def get_tempo_at_beat(self, beat: float) -> float:
        pass

    @abstractmethod
    def get_time_signature_at_beat(self, beat: float) -> TimeSignature:
        pass

    @abstractmethod
    def beats_to_seconds(self, beats: float) -> float:
        pass

    @abstractmethod
    def seconds_to_beats(self, seconds: float) -> float:
        pass


class IDomainTimeline(
        ILifecycleAware,
        IReadonlyTimeline,
        ABC,
):

    @abstractmethod
    def set_tempo_at_beat(self, beat: float, bpm: float):
        pass

    @abstractmethod
    def set_time_signature_at_beat(
        self,
        beat: float,
        numerator: int,
        denominator: int,
    ):
        pass

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self) -> List[ILifecycleAware]:
        return []


class IEngineTimeline(IReadonlyTimeline):

    @abstractmethod
    def update_tempos(self, tempos: List[Tempo]):
        pass

    @abstractmethod
    def update_time_signatures(self, time_signatures: List[TimeSignature]):
        pass
