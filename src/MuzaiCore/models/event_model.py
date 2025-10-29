# file: src/MuzaiCore/models/event_model.py
"""
Defines all domain events that can be published within the core.
These are public data structures, part of the application's shared language.
All events inherit from a common BaseEvent.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional

from .clip_model import Note, AnyClip
from .routing_model import Connection


# ----------------- The Base Event -----------------
@dataclass
class BaseEvent:
    """The base class for all domain events."""
    timestamp: datetime = field(default_factory=datetime.utcnow, init=False)
    event_id: uuid.UUID = field(default_factory=uuid.uuid4, init=False)


# ========================================================================
# IProjectSync Events
# ========================================================================
@dataclass
class ProjectLoaded(BaseEvent):
    """Fired when a project has been fully loaded into memory."""
    project: "Project"


@dataclass
class ProjectClosed(BaseEvent):
    """Fired when a project is about to be closed and cleaned up."""
    project: "Project"


# ========================================================================
# IGraphSync Events
# ========================================================================
@dataclass
class NodeAdded(BaseEvent):
    """Fired when a node is added to the project."""
    node: "INode"


@dataclass
class NodeRemoved(BaseEvent):
    """Fired when a node is removed from the project."""
    node_id: str


@dataclass
class ConnectionAdded(BaseEvent):
    """Fired when a connection is made between two nodes."""
    connection: "Connection"


@dataclass
class ConnectionRemoved(BaseEvent):
    """Fired when a connection between two nodes is broken."""
    connection: "Connection"


# ========================================================================
# IMixerSync Events
# ========================================================================
@dataclass
class InsertAdded(BaseEvent):
    """Fired when a plugin is added to a track's insert chain."""
    owner_node_id: str
    plugin: "IPlugin"
    index: int


@dataclass
class InsertRemoved(BaseEvent):
    """Fired when a plugin is removed from a track's insert chain."""
    owner_node_id: str
    plugin_id: str


@dataclass
class InsertMoved(BaseEvent):
    """
    Fired when a plugin's position is changed within a track's insert chain.
    
    This event signals a structural change in the audio signal flow for a specific track,
    requiring subscribers (like a SyncController) to potentially rebuild connections
    in the audio backend.
    """

    owner_node_id: str
    """The unique ID of the track or node that owns the insert chain."""

    plugin_id: str
    """The unique ID of the plugin instance that was moved."""

    old_index: int
    """The original index (position) of the plugin in the chain before the move."""

    new_index: int
    """The requested new index (position) for the plugin in the chain."""


@dataclass
class PluginEnabledChanged(BaseEvent):
    """Fired when a plugin's bypass state is changed."""
    plugin_id: str
    is_enabled: bool


@dataclass
class ParameterChanged(BaseEvent):
    """Fired when a parameter's base value changes."""
    owner_node_id: str
    param_name: str
    new_value: Any


# ========================================================================
# ITransportSync Events
# ========================================================================
@dataclass
class TempoChanged(BaseEvent):
    """Fired when a tempo event is added or changed."""
    beat: float
    new_bpm: float


@dataclass
class TimeSignatureChanged(BaseEvent):
    """Fired when a time signature event is added or changed."""
    beat: float
    numerator: int
    denominator: int


# ========================================================================
# ITrackSync Events
# ========================================================================
@dataclass
class ClipAdded(BaseEvent):
    """Fired when a clip is added to a track."""
    owner_track_id: str
    clip: AnyClip


@dataclass
class ClipRemoved(BaseEvent):
    """Fired when a clip is removed from a track."""
    owner_track_id: str
    clip_id: str


# ========================================================================
# IClipSync Events
# ========================================================================
@dataclass
class NoteAdded(BaseEvent):
    """Fired when one or more notes are added to a clip."""
    owner_clip_id: str
    notes: List[Note]


@dataclass
class NoteRemoved(BaseEvent):
    """Fired when one or more notes are removed from a clip."""
    owner_clip_id: str
    notes: List[Note]
