# file: src/MuzaiCore/models/engine_model.py
from enum import Enum
from dataclasses import dataclass


class TransportStatus(Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(frozen=True)
class TransportContext:
    current_beat: float
    sample_rate: int
    block_size: int
    tempo: float


@dataclass(frozen=True)
class MIDIEvent:
    note_pitch: int
    velocity: int
    start_sample: int  # Offset within the current block
