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
