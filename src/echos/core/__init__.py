from .event_bus import EventBus
from .history import BaseCommand, CommandManager, MacroCommand
from .manager import DAWManager
from .mixer import MixerChannel
from .parameter import Parameter, ParameterGroup, VCAParameter
from .persistence import ProjectSerializer
from .plugin import Plugin, PluginCache
from .project import Project
from .router import Router
from .timeline import Timeline
from .track import (
    AudioTrack,
    BusTrack,
    InstrumentTrack,
    MasterTrack,
    Track,
    VCATrack,
)

__all__ = [
    # Main entry points
    "DAWManager",
    "Project",

    # Core components
    "Router",
    "Timeline",
    "EventBus",
    "MixerChannel",
    "Parameter",
    "VCAParameter",
    "ParameterGroup",
    "Plugin",
    "PluginCache",
    "ProjectSerializer",

    # Track types
    "Track",
    "InstrumentTrack",
    "AudioTrack",
    "BusTrack",
    "MasterTrack",
    "VCATrack",

    # History and Command Pattern
    "CommandManager",
    "BaseCommand",
    "MacroCommand",
]
