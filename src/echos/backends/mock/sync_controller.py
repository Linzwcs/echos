from ...interfaces.system.isync import ISyncController
from ...models import event_model
from ...interfaces.system.ievent_bus import IEventBus


class MockSyncController(ISyncController):

    def _on_mount(self, event_bus: IEventBus):
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
        event_bus.subscribe(event_model.PluginEnabledChanged,
                            self.on_plugin_enabled_changed)
        event_bus.subscribe(event_model.ParameterChanged,
                            self.on_parameter_changed)

        event_bus.subscribe(event_model.TempoChanged, self.on_tempo_changed)
        event_bus.subscribe(event_model.TimeSignatureChanged,
                            self.on_time_signature_changed)

        event_bus.subscribe(event_model.ClipAdded, self.on_clip_added)
        event_bus.subscribe(event_model.ClipRemoved, self.on_clip_removed)

        event_bus.subscribe(event_model.NoteAdded, self.on_notes_added)
        event_bus.subscribe(event_model.NoteRemoved, self.on_notes_removed)

        print(
            "MockSyncController: All ISyncController methods have been registered as event handlers."
        )

    def _on_unmount(self):
        event_bus = self._event_bus
        event_bus.unsubscribe(event_model.ProjectLoaded,
                              self.on_project_loaded)
        event_bus.unsubscribe(event_model.ProjectClosed,
                              self.on_project_closed)

        # IGraphSync Events
        event_bus.unsubscribe(event_model.NodeAdded, self.on_node_added)
        event_bus.unsubscribe(event_model.NodeRemoved, self.on_node_removed)
        event_bus.unsubscribe(event_model.ConnectionAdded,
                              self.on_connection_added)
        event_bus.unsubscribe(event_model.ConnectionRemoved,
                              self.on_connection_removed)

        # IMixerSync Events
        event_bus.unsubscribe(event_model.InsertAdded, self.on_insert_added)
        event_bus.unsubscribe(event_model.InsertRemoved,
                              self.on_insert_removed)
        event_bus.unsubscribe(event_model.PluginEnabledChanged,
                              self.on_plugin_enabled_changed)
        event_bus.unsubscribe(event_model.ParameterChanged,
                              self.on_parameter_changed)

        # ITransportSync Events
        event_bus.unsubscribe(event_model.TempoChanged, self.on_tempo_changed)
        event_bus.unsubscribe(event_model.TimeSignatureChanged,
                              self.on_time_signature_changed)

        # ITrackSync Events
        event_bus.unsubscribe(event_model.ClipAdded, self.on_clip_added)
        event_bus.unsubscribe(event_model.ClipRemoved, self.on_clip_removed)

        # IClipSync Events
        event_bus.unsubscribe(event_model.NoteAdded, self.on_notes_added)
        event_bus.unsubscribe(event_model.NoteRemoved, self.on_notes_removed)

        self._event_bus = None
        print(
            "DawDreamerSyncController: All ISyncController methods have been registered as event handlers."
        )

    def on_project_loaded(self, event: event_model.ProjectLoaded):
        print(f"Mock Sync: on_project_loaded called with event: {event}")

    def on_project_closed(self, event: event_model.ProjectClosed):
        print(f"Mock Sync: on_project_closed called with event: {event}")

    def on_node_added(self, event: event_model.NodeAdded):
        print(f"Mock Sync: on_node_added called with event: {event}")

    def on_node_removed(self, event: event_model.NodeRemoved):
        print(f"Mock Sync: on_node_removed called with event: {event}")

    def on_connection_added(self, event: event_model.ConnectionAdded):
        print(f"Mock Sync: on_connection_added called with event: {event}")

    def on_connection_removed(self, event: event_model.ConnectionRemoved):
        print(f"Mock Sync: on_connection_removed called with event: {event}")

    def on_insert_added(self, event: event_model.InsertAdded):
        print(f"Mock Sync: on_insert_added called with event: {event}")

    def on_insert_removed(self, event: event_model.InsertRemoved):
        print(f"Mock Sync: on_insert_removed called with event: {event}")

    def on_insert_moved(self, event: event_model.InsertMoved):
        print(f"Mock Sync: on_insert_moved called with event: {event}")

    def on_plugin_enabled_changed(self,
                                  event: event_model.PluginEnabledChanged):
        print(
            f"Mock Sync: on_plugin_enabled_changed called with event: {event}")

    def on_parameter_changed(self, event: event_model.ParameterChanged):
        print(f"Mock Sync: on_parameter_changed called with event: {event}")

    def on_tempo_changed(self, event: event_model.TempoChanged):
        print(f"Mock Sync: on_tempo_changed called with event: {event}")

    def on_time_signature_changed(self,
                                  event: event_model.TimeSignatureChanged):
        print(
            f"Mock Sync: on_time_signature_changed called with event: {event}")

    def on_clip_added(self, event: event_model.ClipAdded):
        print(f"Mock Sync: on_clip_added called with event: {event}")

    def on_clip_removed(self, event: event_model.ClipRemoved):
        print(f"Mock Sync: on_clip_removed called with event: {event}")

    def on_notes_added(self, event: event_model.NoteAdded):
        print(f"Mock Sync: on_notes_added called with event: {event}")

    def on_notes_removed(self, event: event_model.NoteRemoved):
        print(f"Mock Sync: on_notes_removed called with event: {event}")
