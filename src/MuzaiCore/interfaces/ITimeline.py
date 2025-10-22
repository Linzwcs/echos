# file: src/MuzaiCore/interfaces/ITimeline.py
from abc import ABC, abstractmethod
from typing import List
from ..models.timeline_model import TempoEvent, TimeSignatureEvent  # <-- New model


class ITimeline(ABC):

    @abstractmethod
    def samples_to_beats(self, sample_position: int) -> float:
        pass

    @abstractmethod
    def beats_to_samples(self, beat_position: float) -> int:
        pass

    @abstractmethod
    def seconds_to_beats(self, seconds: float) -> float:
        pass

    @abstractmethod
    def beats_to_seconds(self, beats: float) -> float:
        pass

    # +++ NEW METHODS for Tempo/Time Signature Tracks +++
    @abstractmethod
    def set_tempo_at_beat(self, beat: float, bpm: float):
        """Sets the tempo at a specific beat, creating a tempo change point."""
        pass

    @abstractmethod
    def set_time_signature_at_beat(self, beat: float, numerator: int,
                                   denominator: int):
        """Sets the time signature at a specific beat."""
        pass

    @abstractmethod
    def get_tempo_events(self) -> List[TempoEvent]:
        pass

    @abstractmethod
    def get_time_signature_events(self) -> List[TimeSignatureEvent]:
        pass
