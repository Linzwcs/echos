# file: src/MuzaiCore/backends/dawdreamer/messages.py
"""
Defines the data structures for messages sent from the main thread to the
real-time audio thread. Using dataclasses provides type safety and a clear
contract for communication.
"""
from dataclasses import dataclass, field
from typing import List, Union, Optional
from ...models import Note, AutomationPoint


@dataclass
class BaseMessage:
    """A base class for all messages, not used directly."""
    pass


@dataclass
class UpdateAutomation(BaseMessage):
    node_id: str
    param_name: str
    points: List[AutomationPoint]
    is_enabled: bool


# --- Node Operations ---
@dataclass
class AddNode(BaseMessage):
    node_id: str
    node_type: str  # 'plugin' or 'sum'
    plugin_path: Optional[str] = None


@dataclass
class RemoveNode(BaseMessage):
    node_id: str


# --- Connection Operations ---
@dataclass
class AddConnection(BaseMessage):
    source_node_id: str
    dest_node_id: str


@dataclass
class RemoveConnection(BaseMessage):
    source_node_id: str
    dest_node_id: str


# --- Parameter Operations ---
@dataclass
class SetParameter(BaseMessage):
    node_id: str
    param_name: str
    value: float


# --- MIDI Operations ---
@dataclass
class AddNotes(BaseMessage):
    node_id: str  # The ID of the instrument plugin node
    notes: List[Note] = field(default_factory=list)


@dataclass
class SetPluginBypass(BaseMessage):
    node_id: str
    bypass: bool


@dataclass
class SetTempo(BaseMessage):
    beat: float
    bpm: float


@dataclass
class SetTimeSignature(BaseMessage):
    beat: float
    numerator: int
    denominator: int


@dataclass
class RemoveClip(BaseMessage):
    track_id: str
    clip_id: str


# 更新 AnyMessage 类型提示
AnyMessage = Union[AddNode, RemoveNode, AddConnection, RemoveConnection,
                   SetParameter, AddNotes, SetPluginBypass, SetTempo,
                   SetTimeSignature, RemoveClip]
