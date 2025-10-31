"""
Muzai Core Models Package.

This package contains dataclasses and simple data structures that represent the
serializable state of the Muzai application. These models are used as Data
Transfer Objects (DTOs) for saving/loading projects, communicating state between
the core and the UI, and for undo/redo history.

They are designed to be plain data containers with minimal to no logic.
"""

# from clip_model
from .api_model import ToolResponse
from .clip_model import AnyClip, AudioClip, Clip, MIDIClip, Note

# from device_model
from .device_model import AudioDevice, IOChannel, MIDIDevice

# from engine_model
from .engine_model import NotePlaybackInfo, TransportContext, TransportStatus

# from node_model
from .node_model import NodeState, PluginState, TrackState

# from parameter_model
from .parameter_model import (
    AutomationCurveType,
    AutomationLane,
    AutomationPoint,
    ParameterState,
)

# from plugin_model
from .plugin_model import PluginCategory, PluginDescriptor

# from project_model
from .project_model import ProjectState

# from timelime_model (Note: filename has a typo, should likely be "timeline")
from .timeline_model import TempoEvent, TimeSignatureEvent
from .routing_model import Connection, Port, PortType, PortDirection
from .mixer_model import Send

__all__ = [
    "ToolResponse",
    # clip_model
    "AnyClip",
    "AudioClip",
    "Clip",
    "MIDIClip",
    "Note",
    # device_model
    "AudioDevice",
    "IOChannel",
    "MIDIDevice",
    # engine_model
    "NotePlaybackInfo",
    "TransportContext",
    "TransportStatus",
    # node_model
    "NodeState",
    "PluginState",
    "TrackState",
    # parameter_model
    "AutomationCurveType",
    "AutomationLane",
    "AutomationPoint",
    "ParameterState",
    # plugin_model
    "PluginCategory",
    "PluginDescriptor",
    # project_model
    "ProjectState",
    # timelime_model
    "TempoEvent",
    "TimeSignatureEvent",
    # routing_model,
    "Connection"
    "Port",
    "PortType",
    "PortDirection",
    # mixer,
    "Send",
]
