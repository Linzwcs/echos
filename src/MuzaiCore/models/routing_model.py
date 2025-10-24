# file: src/MuzaiCore/subsystems/routing/routing_types.py
from enum import Enum
from dataclasses import dataclass


class PortType(Enum):
    AUDIO = "audio"
    MIDI = "midi"


class PortDirection(Enum):
    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True)
class Port:
    owner_node_id: str
    port_id: str
    port_type: PortType
    direction: PortDirection
    channel_count: int = 2


@dataclass(frozen=True)
class Connection:
    source_port: Port
    dest_port: Port
