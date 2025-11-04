from abc import ABC, abstractmethod
from echos.interfaces.system.ievent_bus import IEventBus
from .ilifecycle import ILifecycleAware
from ...models import event_model


class IGraphSync(ABC):

    @abstractmethod
    def on_node_added(self, event: event_model.NodeAdded):
        pass

    @abstractmethod
    def on_node_removed(self, event: event_model.NodeRemoved):
        pass

    @abstractmethod
    def on_connection_added(self, event: event_model.ConnectionAdded):
        pass

    @abstractmethod
    def on_connection_removed(self, event: event_model.ConnectionRemoved):
        pass


class IMixerSync(ABC):

    @abstractmethod
    def on_insert_added(self, event: event_model.InsertAdded):
        pass

    @abstractmethod
    def on_insert_removed(self, event: event_model.InsertRemoved):
        pass

    @abstractmethod
    def on_insert_moved(self, event: event_model.InsertMoved):
        pass

    @abstractmethod
    def on_plugin_enabled_changed(
        self,
        event: event_model.PluginEnabledChanged,
    ):
        pass

    @abstractmethod
    def on_parameter_changed(
        self,
        event: event_model.ParameterChanged,
    ):
        pass


class ITransportSync(ABC):

    @abstractmethod
    def on_timeline_state_changed(self,
                                  event: event_model.TimeSignatureChanged):
        pass


class ITrackSync(ABC):

    @abstractmethod
    def on_clip_added(self, event: event_model.ClipAdded):
        pass

    @abstractmethod
    def on_clip_removed(self, event: event_model.ClipRemoved):
        pass


class IClipSync(ABC):

    @abstractmethod
    def on_notes_added(self, event: event_model.NoteAdded):
        pass

    @abstractmethod
    def on_notes_removed(self, event: event_model.NoteRemoved):
        pass


class IProjectSync(ABC):

    @abstractmethod
    def on_project_loaded(self, event: event_model.ProjectLoaded):
        pass

    @abstractmethod
    def on_project_closed(self, event: event_model.ProjectClosed):
        pass


class ISyncController(
        IGraphSync,
        IMixerSync,
        ITransportSync,
        IClipSync,
        IProjectSync,
        ILifecycleAware,
        ABC,
):

    def _get_children(self):
        return []
