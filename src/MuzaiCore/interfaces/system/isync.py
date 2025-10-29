# file: src/MuzaiCore/interfaces/system/igraph_sync.py
from abc import ABC, abstractmethod
from typing import Any, Optional, List
from ...interfaces.system.ievent_bus import IEventBus
from ...models import Connection, Note, AnyClip
from ...models import event_model


class IGraphSync(ABC):
    """
    Defines a minimal, backend-agnostic interface for an object that can
    receive and process graph state changes.

    The Router will emit events to an object implementing this interface.
    """

    @abstractmethod
    def on_node_added(self, event: event_model.NodeAdded):
        """Called when a node is added to the logical graph."""
        pass

    @abstractmethod
    def on_node_removed(self, event: event_model.NodeRemoved):
        """Called when a node is removed from the logical graph."""
        pass

    @abstractmethod
    def on_connection_added(self, event: event_model.ConnectionAdded):
        """Called when a connection is made in the logical graph."""
        pass

    @abstractmethod
    def on_connection_removed(self, event: event_model.ConnectionRemoved):
        """Called when a connection is broken in the logical graph."""
        pass


class IMixerSync(ABC):
    """Listens to changes within a node's mixer channel or a plugin's state."""

    @abstractmethod
    def on_insert_added(self, event: event_model.InsertAdded):
        pass

    @abstractmethod
    def on_insert_removed(self, event: event_model.InsertRemoved):
        pass

    @abstractmethod
    def on_insert_moved(self, event: event_model.InsertMoved):
        """Called when a plugin is re-ordered in an insert chain."""
        pass

    @abstractmethod
    def on_plugin_enabled_changed(self,
                                  event: event_model.PluginEnabledChanged):
        pass

    @abstractmethod
    def on_parameter_changed(self, event: event_model.ParameterChanged):
        pass


class ITransportSync(ABC):
    """
    Listens ONLY to global, project-wide time context changes that are
    emitted by the ITimeline object.
    """

    @abstractmethod
    def on_tempo_changed(self, event: event_model.TempoChanged):
        ...

    @abstractmethod
    def on_time_signature_changed(self,
                                  event: event_model.TimeSignatureChanged):
        ...


class ITrackSync(ABC):
    """
    Listens to changes in a track's content, such as adding or removing clips.
    Emitted by ITrack objects.
    """

    @abstractmethod
    def on_clip_added(self, event: event_model.ClipAdded):
        ...

    @abstractmethod
    def on_clip_removed(self, event: event_model.ClipRemoved):
        ...


class IClipSync(ABC):
    """
    Listens to changes in a clip's content, such as adding or removing notes.
    Emitted by IClip objects.
    """

    @abstractmethod
    def on_notes_added(self, event: event_model.NoteAdded):
        ...

    @abstractmethod
    def on_notes_removed(self, event: event_model.NoteRemoved):
        ...


class IProjectSync(ABC):

    @abstractmethod
    def on_project_loaded(self, event: event_model.ProjectLoaded):
        """A special event to trigger a full, clean sync from a project state."""
        pass

    @abstractmethod
    def on_project_closed(self, event: event_model.ProjectClosed):
        """A special event to trigger a full cleanup of the backend."""
        pass


class ISyncController(
        IGraphSync,
        IMixerSync,
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

    @abstractmethod
    def register_event_handlers(self, event_bus: IEventBus):
        """
        Subscribes the controller's methods to the domain event bus.
        This method is called once upon initialization to wire up the system.
        
        This abstract method FORCES every implementation to explicitly define
        how it reacts to domain events.
        """
        pass
