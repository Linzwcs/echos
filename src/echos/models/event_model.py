import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List

from .clip_model import Note, AnyClip
from .router_model import Connection
from .mixer_model import Send
from .timeline_model import Tempo, TimeSignature, TimelineState


@dataclass
class BaseEvent:

    timestamp: datetime = field(default_factory=datetime.now)
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass(kw_only=True)
class ProjectLoaded(BaseEvent):
    timeline_state: TimelineState


@dataclass(kw_only=True)
class ProjectClosed(BaseEvent):
    pass


@dataclass(kw_only=True)
class NodeAdded(BaseEvent):
    node_id: str
    node_type: str


@dataclass(kw_only=True)
class NodeRemoved(BaseEvent):
    node_id: str


@dataclass(kw_only=True)
class NodeRenamed:
    node_id: str
    old_name: str
    new_name: str


@dataclass(kw_only=True)
class ConnectionAdded(BaseEvent):
    connection: "Connection"


@dataclass(kw_only=True)
class ConnectionRemoved(BaseEvent):
    connection: "Connection"


@dataclass(kw_only=True)
class InsertAdded(BaseEvent):
    owner_node_id: str
    plugin_instance_id: str
    plugin_unique_id: str
    index: int


@dataclass(kw_only=True)
class InsertRemoved(BaseEvent):

    owner_node_id: str
    plugin_instance_id: str


@dataclass(kw_only=True)
class InsertMoved(BaseEvent):

    owner_node_id: str
    plugin_instance_id: str
    old_index: int
    new_index: int


@dataclass(kw_only=True)
class PluginEnabledChanged(BaseEvent):

    plugin_id: str
    is_enabled: bool


@dataclass(kw_only=True)
class ParameterChanged(BaseEvent):

    owner_node_id: str
    param_name: str
    new_value: Any


@dataclass(kw_only=True)
class TimelineStateChanged(BaseEvent):
    timeline_state: TimelineState


@dataclass(kw_only=True)
class TempoChanged(BaseEvent):
    tempos: tuple[Tempo]


@dataclass(kw_only=True)
class TimeSignatureChanged(BaseEvent):
    time_signatures: tuple[TimeSignature]


@dataclass(kw_only=True)
class ClipAdded(BaseEvent):

    owner_track_id: str
    clip: AnyClip


@dataclass(kw_only=True)
class ClipRemoved(BaseEvent):

    owner_track_id: str
    clip_id: str


@dataclass(kw_only=True)
class NoteAdded(BaseEvent):

    owner_clip_id: str
    notes: List[Note]


@dataclass(kw_only=True)
class NoteRemoved(BaseEvent):

    owner_clip_id: str
    notes: List[Note]


@dataclass(kw_only=True)
class SendAdded(BaseEvent):

    owner_node_id: str
    send: Send


@dataclass(kw_only=True)
class SendRemoved(BaseEvent):

    owner_node_id: str
    send_id: str
    target_bus_node_id: str
