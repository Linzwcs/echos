"""
Muzai Core Interfaces Package.

This package defines the abstract base classes (interfaces) that form the public API
of the Muzai Core. These interfaces define the contracts for major components
like the audio engine, project management, routing, tracks, and plugins.

By programming against these interfaces, the UI layer (or any other client) can
remain decoupled from the specific implementation details of the core.
"""

from .IAudioEngine import IAudioEngine
from .IAudioProcessor import IAudioProcessor
from .ICommand import ICommand, ICommandManager
from .IDAWManager import IDAWManager
from .IDeviceManager import IDeviceManager
from .IMixerChannel import IMixerChannel
from .INode import INode
from .IParameter import IParameter
from .IPlugin import IPlugin
from .IPluginRegistry import IPluginRegistry
from .IProject import IProject
from .IRouter import IRouter
from .ITimeline import ITimeline
from .ITrack import ITrack, TrackRecordMode

__all__ = [
    "IAudioEngine",
    "IAudioProcessor",
    "ICommand",
    "ICommandManager",
    "IDAWManager",
    "IDeviceManager",
    "IMixerChannel",
    "INode",
    "IParameter",
    "IPlugin",
    "IPluginRegistry",
    "IProject",
    "IRouter",
    "ITimeline",
    "ITrack",
    "TrackRecordMode",
]
