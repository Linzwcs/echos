# file: src/MuzaiCore/models/device_model.py
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class IOChannel:
    id: str
    name: str


@dataclass(frozen=True)
class AudioDevice:
    id: str
    name: str
    input_channels: List[IOChannel]
    output_channels: List[IOChannel]


@dataclass(frozen=True)
class MIDIDevice:
    id: str
    name: str
