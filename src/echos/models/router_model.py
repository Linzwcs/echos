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

    port_id: str
    port_type: PortType
    direction: PortDirection
    channels: int = 2


@dataclass(frozen=True)
class Connection:

    source_node_id: str
    dest_node_id: str
    source_port_id: str = "main_out"
    dest_port_id: str = "main_in"
