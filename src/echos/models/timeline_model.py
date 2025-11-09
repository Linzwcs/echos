from dataclasses import dataclass


@dataclass
class Tempo:
    beat: float
    bpm: float


@dataclass
class TimeSignature:
    beat: float
    numerator: int
    denominator: int
