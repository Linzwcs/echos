from abc import ABC, abstractmethod
from typing import List
from .ievent_bus import IEventBus
from .ilifecycle import ILifecycleAware
from .iserializable import ISerializable
from ...models.timeline_model import Tempo, TimeSignature
from ...models.state_model import TimelineState


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


class IWritableTimeline(ABC):

    @abstractmethod
    def set_state(self, new_state: TimelineState) -> TimelineState:
        pass


class IMusicalTimeConverter(ABC):

    @abstractmethod
    def beats_to_seconds(self, beats: float) -> float:
        pass

    @abstractmethod
    def seconds_to_beats(self, seconds: float) -> float:
        pass


class IDomainTimeline(
        ILifecycleAware,
        ISerializable,
        IReadonlyTimeline,
        IMusicalTimeConverter,
        IWritableTimeline,
        ABC,
):

    @property
    @abstractmethod
    def timeline_state(self) -> TimelineState:
        pass

    @abstractmethod
    def set_tempo(self, beat: float, bpm: float):
        pass

    @abstractmethod
    def set_time_signature(self, beat: float, bpm: float):
        pass

    @abstractmethod
    def remove_tempo(
        self,
        beat: float,
        numerator: int,
        denominator: int,
    ):
        pass

    @abstractmethod
    def remove_time_signature(
        self,
        beat: float,
        numerator: int,
        denominator: int,
    ):
        pass


class IEngineTimeline(
        IReadonlyTimeline,
        IWritableTimeline,
        ABC,
):
    pass
