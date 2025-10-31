"""
Muzai Core Interfaces Package.

This package defines the abstract base classes (interfaces) that form the public API
of the Muzai Core. These interfaces define the contracts for major components
like the audio engine, project management, routing, tracks, and plugins.

By programming against these interfaces, the UI layer (or any other client) can
remain decoupled from the specific implementation details of the core.
"""

from .iengine import IEngine
from .icommand import ICommand, ICommandManager
from .idaw_manager import IDAWManager
from .idevice_manager import IDeviceManager
from .imixer_channel import IMixerChannel
from .inode import INode, ITrack, IPlugin
from .iparameter import IParameter
from .iplugin_registry import IPluginRegistry
from .iproject import IProject
from .irouter import IRouter
from .itimeline import ITimeline
from .ipersistence import IProjectSerializer

from .isync import ISyncController
from .ievent_bus import IEventBus
from .ifactory import INodeFactory

__all__ = [
    "IEngine", "ICommand", "ICommandManager", "IDAWManager", "IDeviceManager",
    "IMixerChannel", "INode", "INodeFactory", "IParameter", "IPlugin",
    "IPluginRegistry", "IProject", "IRouter", "ITimeline", "ITrack",
    "IProjectSerializer", "ISyncController", "IEventBus"
]
