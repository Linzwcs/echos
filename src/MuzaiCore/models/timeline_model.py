# file: src/MuzaiCore/models/timeline_model.py
from dataclasses import dataclass


@dataclass(order=True, frozen=True)
class Tempo:
    beat: float
    bpm: float


@dataclass(order=True, frozen=True)
class TimeSignature:
    beat: float
    numerator: int
    denominator: int
