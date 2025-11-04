# file: src/MuzaiCore/models/event_model.py
"""
Defines all domain events that can be published within the core.
These are public data structures, part of the application's shared language.
All events inherit from a common BaseEvent.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List

from .clip_model import Note, AnyClip
from .routing_model import Connection
from .mixer_model import Send
from .timeline_model import Tempo, TimeSignature


@dataclass(frozen=True)
class BaseEvent:

    timestamp: datetime = field(default_factory=datetime.now)
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(frozen=True)
class ProjectLoaded(BaseEvent):
    project: "Project"


@dataclass(frozen=True)
class ProjectClosed(BaseEvent):
    project: "Project"


@dataclass(frozen=True)
class NodeAdded(BaseEvent):
    node: "INode"


@dataclass(frozen=True)
class NodeRemoved(BaseEvent):
    node_id: str


@dataclass(frozen=True)
class NodeRenamed:
    node_id: str
    old_name: str
    new_name: str


@dataclass(frozen=True)
class ConnectionAdded(BaseEvent):
    connection: "Connection"


@dataclass(frozen=True)
class ConnectionRemoved(BaseEvent):
    connection: "Connection"


@dataclass(frozen=True)
class InsertAdded(BaseEvent):
    owner_node_id: str
    plugin: "IPlugin"
    index: int


@dataclass(frozen=True)
class InsertRemoved(BaseEvent):
    owner_node_id: str
    plugin_id: str


@dataclass(frozen=True)
class InsertMoved(BaseEvent):

    owner_node_id: str
    plugin_id: str
    old_index: int
    new_index: int


@dataclass(frozen=True)
class PluginEnabledChanged(BaseEvent):

    plugin_id: str
    is_enabled: bool


@dataclass(frozen=True)
class ParameterChanged(BaseEvent):

    owner_node_id: str
    param_name: str
    new_value: Any


@dataclass(frozen=True)
class TempoChanged(BaseEvent):

    tempos: tuple[Tempo]


@dataclass(frozen=True)
class TimeSignatureChanged(BaseEvent):

    time_signatures: tuple[TimeSignature]


@dataclass(frozen=True)
class ClipAdded(BaseEvent):

    owner_track_id: str
    clip: AnyClip


@dataclass(frozen=True)
class ClipRemoved(BaseEvent):

    owner_track_id: str
    clip_id: str


@dataclass(frozen=True)
class NoteAdded(BaseEvent):

    owner_clip_id: str
    notes: List[Note]


@dataclass(frozen=True)
class NoteRemoved(BaseEvent):

    owner_clip_id: str
    notes: List[Note]


@dataclass(frozen=True)
class SendAdded(BaseEvent):

    owner_node_id: str
    send: Send


@dataclass(frozen=True)
class SendRemoved(BaseEvent):

    owner_node_id: str
    send_id: str
    target_bus_node_id: str
