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
class NotePlaybackInfo:
    """
    Represents a note that is scheduled to begin playing within the
    current processing block. This is a higher-level abstraction than
    raw Note On/Off MIDI events.
    """
    note_pitch: int
    velocity: int
    start_sample: int  # Offset within the current block where the note starts.
    duration_samples: int  # The total duration of the note in samples.
