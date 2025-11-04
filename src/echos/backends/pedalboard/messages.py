from dataclasses import dataclass
from typing import List, Tuple, Union, Any

from ...models import Note, AnyClip, PluginDescriptor, TimelineState


@dataclass(frozen=True)
class BaseMessage:
    pass


@dataclass(frozen=True)
class TimelineMessage(BaseMessage):
    pass


@dataclass(frozen=True)
class GraphMessage(BaseMessage):
    pass


@dataclass(frozen=True)
class EngineMessage(BaseMessage):
    pass


@dataclass(frozen=True)
class RealTimeMessage(BaseMessage):
    pass


@dataclass(frozen=True)
class NonRealTimeMessage(BaseMessage):
    pass


@dataclass(frozen=True)
class ClearProject(NonRealTimeMessage):
    pass


@dataclass(frozen=True)
class AddNode(NonRealTimeMessage, GraphMessage):
    node_id: str
    node_type: str


@dataclass(frozen=True)
class RemoveNode(NonRealTimeMessage, GraphMessage):
    node_id: str


@dataclass(frozen=True)
class AddConnection(NonRealTimeMessage, GraphMessage):

    source_node_id: str
    dest_node_id: str


@dataclass(frozen=True)
class RemoveConnection(NonRealTimeMessage, GraphMessage):

    source_node_id: str
    dest_node_id: str


@dataclass(frozen=True)
class AddPlugin(NonRealTimeMessage, GraphMessage):

    owner_node_id: str
    plugin_instance_id: str
    plugin_unique_id: str
    index: int


@dataclass(frozen=True)
class RemovePlugin(NonRealTimeMessage, GraphMessage):

    owner_node_id: str
    plugin_instance_id: str


@dataclass(frozen=True)
class MovePlugin(NonRealTimeMessage, GraphMessage):

    owner_node_id: str
    plugin_instance_id: str
    old_index: int
    new_index: int


@dataclass(frozen=True)
class UpdateTrackClips(NonRealTimeMessage, GraphMessage):

    track_id: str
    clips: Tuple[AnyClip, ...]


@dataclass(frozen=True)
class AddTrackClip(NonRealTimeMessage, GraphMessage):
    track_id: str
    clip: AnyClip


@dataclass(frozen=True)
class AddNotesToClip(NonRealTimeMessage, GraphMessage):

    owner_node_id: str
    clip_id: str
    notes: Tuple[Note, ...]


@dataclass(frozen=True)
class RemoveNotesFromClip(NonRealTimeMessage, GraphMessage):

    owner_node_id: str
    clip_id: str
    note_ids: Tuple[int, ...]


@dataclass(frozen=True)
class SetPluginBypass(RealTimeMessage, GraphMessage):

    owner_node_id: str
    plugin_instance_id: str
    is_bypassed: bool


@dataclass(frozen=True)
class SetParameter(RealTimeMessage, GraphMessage):

    owner_node_id: str
    parameter_path: str
    value: Any


@dataclass(frozen=True)
class SetBypass(RealTimeMessage, GraphMessage):

    owner_node_id: str
    plugin_instance_id: str
    is_bypassed: bool


@dataclass(frozen=True)
class SetTimelineState(NonRealTimeMessage, TimelineMessage):
    timeline_state: TimelineState


@dataclass(frozen=True)
class UpdatePluginRegistry(NonRealTimeMessage):
    descriptors: Tuple[PluginDescriptor, ...]


AnyMessage = Union[ClearProject, AddNode, RemoveNode, AddConnection,
                   RemoveConnection, AddPlugin, RemovePlugin, MovePlugin,
                   SetPluginBypass, SetParameter, SetBypass, UpdateTrackClips,
                   AddTrackClip, AddNotesToClip, RemoveNotesFromClip,
                   SetTimelineState]
