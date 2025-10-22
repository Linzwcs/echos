# file: src/MuzaiCore/models/timeline_model.py
from dataclasses import dataclass


@dataclass(frozen=True)
class TempoEvent:
    """Represents a point of tempo change on the timeline."""
    beat: float
    bpm: float


@dataclass(frozen=True)
class TimeSignatureEvent:
    """Represents a point of time signature change on the timeline."""
    beat: float
    numerator: int
    denominator: int
