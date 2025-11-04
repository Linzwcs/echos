# file: src/MuzaiCore/models/timeline_model.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Tempo:
    beat: float
    bpm: float


@dataclass(frozen=True)
class TimeSignature:
    beat: float
    numerator: int
    denominator: int


@dataclass
class TimelineState:
    tempos: list[Tempo]
    time_signatures: list[TimeSignature]
