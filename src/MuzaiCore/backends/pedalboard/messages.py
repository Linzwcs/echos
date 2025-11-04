from dataclasses import dataclass
from typing import List, Tuple, Union, Any

from ...models import Note, Tempo, TimeSignature, AnyClip, PluginDescriptor


@dataclass(frozen=True)
class BaseMessage:
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
class AddNode(NonRealTimeMessage):
    node_id: str
    node_type: str


@dataclass(frozen=True)
class RemoveNode(NonRealTimeMessage):
    node_id: str


@dataclass(frozen=True)
class AddConnection(NonRealTimeMessage):

    source_node_id: str
    dest_node_id: str


@dataclass(frozen=True)
class RemoveConnection(NonRealTimeMessage):

    source_node_id: str
    dest_node_id: str


@dataclass(frozen=True)
class AddPlugin(NonRealTimeMessage):

    owner_node_id: str
    plugin_unique_id: str
    index: int


@dataclass(frozen=True)
class RemovePlugin(NonRealTimeMessage):

    owner_node_id: str
    plugin_instance_id: str


@dataclass(frozen=True)
class MovePlugin(NonRealTimeMessage):

    owner_node_id: str
    plugin_id: str
    old_index: int
    new_index: int


@dataclass(frozen=True)
class UpdateTrackClips(NonRealTimeMessage):

    track_id: str
    clips: Tuple[AnyClip, ...]


@dataclass(frozen=True)
class AddTrackClip(NonRealTimeMessage):
    track_id: str
    clip: AnyClip


@dataclass(frozen=True)
class AddNotesToClip(NonRealTimeMessage):

    owner_node_id: str
    clip_id: str
    notes: Tuple[Note, ...]


@dataclass(frozen=True)
class RemoveNotesFromClip(NonRealTimeMessage):

    owner_node_id: str
    clip_id: str
    note_ids: Tuple[int, ...]


@dataclass(frozen=True)
class SetNodeParameter(RealTimeMessage):

    node_id: str
    parameter_name: str
    value: Any


@dataclass(frozen=True)
class SetPluginParameter(RealTimeMessage):

    own_node_id: str
    plugin_instance_id: str
    parameter_name: str
    value: Any


@dataclass(frozen=True)
class SetPluginBypass(RealTimeMessage):

    owner_node_id: str
    plugin_instance_id: str
    is_bypassed: bool


@dataclass(frozen=True)
class SetParameter(RealTimeMessage):

    owner_node_id: str
    parameter_path: str
    value: Any


@dataclass(frozen=True)
class SetBypass(RealTimeMessage):

    owner_node_id: str
    plugin_instance_id: str
    is_bypassed: bool


@dataclass(frozen=True)
class SetTempos(NonRealTimeMessage):
    tempos: list[Tempo]


@dataclass(frozen=True)
class SetTimeSignatures(NonRealTimeMessage):
    time_signatures: list[TimeSignature]


@dataclass(frozen=True)
class UpdatePluginRegistry(NonRealTimeMessage):

    descriptors: Tuple[PluginDescriptor, ...]


AnyMessage = Union[ClearProject, AddNode, RemoveNode, AddConnection,
                   RemoveConnection, AddPlugin, RemovePlugin, MovePlugin,
                   SetNodeParameter, SetPluginParameter, SetPluginBypass,
                   SetParameter, SetBypass, UpdateTrackClips, AddTrackClip,
                   AddNotesToClip, RemoveNotesFromClip, SetTempos,
                   SetTimeSignatures]
