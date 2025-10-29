# file: src/MuzaiCore/interfaces/system/igraph_sync.py
from abc import ABC, abstractmethod
from typing import Any, Optional, List

from .inode import INode, IPlugin
from .iproject import IProject
from ...models import Connection, Note, AnyClip


class IGraphSync(ABC):
    """
    Defines a minimal, backend-agnostic interface for an object that can
    receive and process graph state changes.

    The Router will emit events to an object implementing this interface.
    """

    @abstractmethod
    def on_node_added(self, node: INode):
        """Called when a node is added to the logical graph."""
        pass

    @abstractmethod
    def on_node_removed(self, node_id: str):
        """Called when a node is removed from the logical graph."""
        pass

    @abstractmethod
    def on_connection_added(self, connection: Connection):
        """Called when a connection is made in the logical graph."""
        pass

    @abstractmethod
    def on_connection_removed(self, connection: Connection):
        """Called when a connection is broken in the logical graph."""
        pass


class IMixerSync(ABC):
    """Listens to changes within a node's mixer channel or a plugin's state."""

    @abstractmethod
    def on_insert_added(self, owner_node_id: str, plugin: IPlugin, index: int):
        pass

    @abstractmethod
    def on_insert_removed(self, owner_node_id: str, plugin_id: str):
        pass

    @abstractmethod
    def on_insert_moved(self, owner_node_id: str, plugin_id: str,
                        old_index: int, new_index: int):
        pass

    @abstractmethod
    def on_plugin_enabled_changed(self, plugin_id: str, is_enabled: bool):
        pass

    @abstractmethod
    def on_parameter_changed(self, owner_node_id: str, param_name: str,
                             value: Any):
        pass


class ITransportSync(ABC):
    """
    Listens ONLY to global, project-wide time context changes that are
    emitted by the ITimeline object.
    """

    @abstractmethod
    def on_tempo_changed(self, beat: float, new_bpm: float):
        ...

    @abstractmethod
    def on_time_signature_changed(self, beat: float, numerator: int,
                                  denominator: int):
        ...


class ITrackSync(ABC):
    """
    Listens to changes in a track's content, such as adding or removing clips.
    Emitted by ITrack objects.
    """

    @abstractmethod
    def on_clip_added(self, owner_track_id: str, clip: AnyClip):
        ...

    @abstractmethod
    def on_clip_removed(self, owner_track_id: str, clip_id: str):
        ...


class IClipSync(ABC):
    """
    Listens to changes in a clip's content, such as adding or removing notes.
    Emitted by IClip objects.
    """

    @abstractmethod
    def on_notes_added(self, owner_clip_id: str, notes: List[Note]):
        ...

    @abstractmethod
    def on_notes_removed(self, owner_clip_id: str, notes: List[Note]):
        ...


class IProjectSync(ABC):

    @abstractmethod
    def on_project_loaded(self, project: IProject):
        """A special event to trigger a full, clean sync from a project state."""
        pass

    @abstractmethod
    def on_project_closed(self, project: IProject):
        """A special event to trigger a full cleanup of the backend."""
        pass


class ISyncController(
        IGraphSync,
        IMixerSync,
        ITransportSync,
        ITransportSync,
        IClipSync,
        IProjectSync,
        ABC,
):
    """
    The main sync controller interface aggregates all listener contracts.
    It is the single component that subscribes to all domain model events
    and translates them for the backend.
    """
    pass
