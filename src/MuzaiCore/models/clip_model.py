# file: src/MuzaiCore/models/clip_model.py
from dataclasses import dataclass, field
from typing import Set, Union
import uuid


@dataclass(frozen=True)
class Note:
    pitch: int
    velocity: int
    start_beat: float
    duration_beats: float


@dataclass
class Clip:
    """Base class for all clip types."""
    start_beat: float
    duration_beats: float
    clip_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    name: str = "clip"
    is_looped: bool = False
    loop_start_beat: float = 0.0  # Relative to clip start
    loop_duration_beats: float = 0.0  # If 0, loops the whole clip


@dataclass
class MIDIClip(Clip):
    notes: Set[Note] = field(default_factory=set)


@dataclass
class AudioClip(Clip):
    source_file_path: str = None
    gain_db: float = 0.0
    # For warping/timestretching
    original_tempo: float = 120.0
    warp_markers: dict = field(default_factory=dict)


AnyClip = Union[MIDIClip, AudioClip]
