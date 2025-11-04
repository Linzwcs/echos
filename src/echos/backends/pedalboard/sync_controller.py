from typing import TYPE_CHECKING
from .messages import (AnyMessage, AddNode, RemoveNode, AddConnection,
                       RemoveConnection, AddPlugin, RemovePlugin,
                       SetPluginBypass, ClearProject, UpdateTrackClips,
                       AddTrackClip, MovePlugin, SetTimelineState,
                       AddNotesToClip, RemoveNotesFromClip, SetParameter)
from ...interfaces.system.isync import ISyncController
from ...models import event_model
from .messages import BaseMessage

if TYPE_CHECKING:
    from .engine import PedalboardEngine


class PedalboardSyncController(ISyncController):

    def __init__(self, engine: 'PedalboardEngine'):
        super().__init__()
        self._engine = engine
        print(
            "PedalboardSyncController: Created as an internal component of the Engine."
        )

    def _post_command(self, msg: BaseMessage):

        if self._engine:
            self._engine.post_command(msg)
        else:
            print(
                f"Sync: Warning - Engine not available. Dropping message: {msg}"
            )

    def _on_mount(self, event_bus):
        self._event_bus = event_bus

        event_bus.subscribe(event_model.ProjectLoaded, self.on_project_loaded)
        event_bus.subscribe(event_model.ProjectClosed, self.on_project_closed)

        event_bus.subscribe(event_model.NodeAdded, self.on_node_added)
        event_bus.subscribe(event_model.NodeRemoved, self.on_node_removed)
        event_bus.subscribe(event_model.ConnectionAdded,
                            self.on_connection_added)
        event_bus.subscribe(event_model.ConnectionRemoved,
                            self.on_connection_removed)

        event_bus.subscribe(event_model.InsertAdded, self.on_insert_added)
        event_bus.subscribe(event_model.InsertRemoved, self.on_insert_removed)
        event_bus.subscribe(event_model.InsertMoved, self.on_insert_moved)
        event_bus.subscribe(event_model.PluginEnabledChanged,
                            self.on_plugin_enabled_changed)
        event_bus.subscribe(event_model.ParameterChanged,
                            self.on_parameter_changed)

        event_bus.subscribe(event_model.TimelineStateChanged,
                            self.on_timeline_state_changed)

        event_bus.subscribe(event_model.ClipAdded, self.on_clip_added)
        event_bus.subscribe(event_model.ClipRemoved, self.on_clip_removed)

        event_bus.subscribe(event_model.NoteAdded, self.on_notes_added)
        event_bus.subscribe(event_model.NoteRemoved, self.on_notes_removed)

        print("PedalboardSyncController: Mounted - all events subscribed")

    def _on_unmount(self):

        if not self._event_bus:
            return

        event_bus = self._event_bus
        event_bus.unsubscribe(event_model.ProjectLoaded,
                              self.on_project_loaded)
        event_bus.unsubscribe(event_model.ProjectClosed,
                              self.on_project_closed)
        event_bus.unsubscribe(event_model.NodeAdded, self.on_node_added)
        event_bus.unsubscribe(event_model.NodeRemoved, self.on_node_removed)
        event_bus.unsubscribe(event_model.ConnectionAdded,
                              self.on_connection_added)
        event_bus.unsubscribe(event_model.ConnectionRemoved,
                              self.on_connection_removed)
        event_bus.unsubscribe(event_model.InsertAdded, self.on_insert_added)
        event_bus.unsubscribe(event_model.InsertRemoved,
                              self.on_insert_removed)
        event_bus.unsubscribe(event_model.InsertMoved, self.on_insert_moved)
        event_bus.unsubscribe(event_model.PluginEnabledChanged,
                              self.on_plugin_enabled_changed)
        event_bus.unsubscribe(event_model.ParameterChanged,
                              self.on_parameter_changed)
        event_bus.unsubscribe(event_model.TempoChanged, self.on_tempo_changed)
        event_bus.unsubscribe(event_model.TimeSignatureChanged,
                              self.on_time_signature_changed)
        event_bus.unsubscribe(event_model.ClipAdded, self.on_clip_added)
        event_bus.unsubscribe(event_model.ClipRemoved, self.on_clip_removed)
        event_bus.unsubscribe(event_model.NoteAdded, self.on_notes_added)
        event_bus.unsubscribe(event_model.NoteRemoved, self.on_notes_removed)

        self._event_bus = None
        print("PedalboardSyncController: Unmounted")

    def on_project_loaded(self, event: event_model.ProjectLoaded):
        pass

    def on_project_closed(self, event: event_model.ProjectClosed):
        pass

    def on_node_added(self, event: event_model.NodeAdded):
        self._post_command(
            AddNode(node_id=event.node_id, node_type=event.node_type))

    def on_node_removed(self, event: event_model.NodeRemoved):
        self._post_command(RemoveNode(node_id=event.node_id))

    def on_connection_added(self, event: event_model.ConnectionAdded):
        conn = event.connection
        self._post_command(
            AddConnection(source_node_id=conn.source_port.owner_node_id,
                          dest_node_id=conn.dest_port.owner_node_id))

    def on_connection_removed(self, event: event_model.ConnectionRemoved):
        conn = event.connection
        self._post_command(
            RemoveConnection(source_node_id=conn.source_port.owner_node_id,
                             dest_node_id=conn.dest_port.owner_node_id))

    def on_insert_added(self, event: event_model.InsertAdded):
        self._post_command(
            AddPlugin(owner_node_id=event.owner_node_id,
                      plugin_instance_id=event.plugin_instance_id,
                      plugin_unique_id=event.plugin_unique_id,
                      index=event.index))

    def on_insert_removed(self, event: event_model.InsertRemoved):
        self._post_command(
            RemovePlugin(owner_node_id=event.owner_node_id,
                         plugin_instance_id=event.plugin_id))

    def on_insert_moved(self, event: event_model.InsertMoved):
        self._post_command(
            MovePlugin(owner_node_id=event.owner_node_id,
                       plugin_instance_id=event.plugin_id,
                       old_index=event.old_index,
                       new_index=event.new_index))
        print(
            f"Sync: Plugin move command posted for plugin {event.plugin_id}.")

    def on_plugin_enabled_changed(self,
                                  event: event_model.PluginEnabledChanged):

        self._post_command(
            SetPluginBypass(plugin_instance_id=event.plugin_id,
                            is_bypassed=not event.is_enabled))

    def on_parameter_changed(self, event: event_model.ParameterChanged):
        self._post_command(
            SetParameter(owner_node_id=event.owner_node_id,
                         parameter_path=event.param_name,
                         value=event.new_value))

    def on_clip_added(self, event: event_model.ClipAdded):
        self._post_command(
            AddTrackClip(track_id=event.owner_track_id, clip=event.clip))

    def on_clip_removed(self, event: event_model.ClipRemoved):
        self._post_command(
            UpdateTrackClips(track_id=event.owner_track_id,
                             clips=event.remaining_clips))
        print(f"Sync: Clip removal on track {event.owner_track_id} synced.")

    def on_notes_added(self, event: event_model.NoteAdded):
        pass

    def on_notes_removed(self, event: event_model.NoteRemoved):
        pass

    def on_timeline_state_changed(self,
                                  event: event_model.TimelineStateChanged):
        return self._post_command(SetTimelineState(event.timeline_state))
