# file: src/MuzaiCore/backends/dawdreamer/sync_controller.py

from typing import Any, Optional
from ...interfaces.system import (
    ISyncController,
    IProject,
    ITrack,
    IPlugin,
)
from ...interfaces.system.ievent_bus import IEventBus
from ...models import event_model
from .render_graph import DawDreamerRenderGraph
from ...core.track import InstrumentTrack, BusTrack, Track


class DawDreamerSyncController(ISyncController):
    """
    Implements the full ISyncController interface for the DawDreamer backend.
    
    It registers its own public methods as handlers for domain events, fulfilling
    the contract defined by the ISyncController ABC. This makes the class a direct
    translator between high-level domain events and low-level render graph commands.
    """

    def __init__(self, render_graph: DawDreamerRenderGraph):
        self._render_graph = render_graph
        self._project: Optional[IProject] = None
        print(
            "DawDreamerSyncController: Initialized, awaiting event handler registration."
        )

    # ========================================================================
    # 1. Contractual Event Registration (Called by Manager)
    # ========================================================================

    def register_event_handlers(self, event_bus: IEventBus):
        """
        Subscribes the public interface methods directly to the domain event bus,
        fulfilling the ISyncController contract.
        """
        # IProjectSync Events (Note: These are usually called directly by the manager)
        event_bus.subscribe(event_model.ProjectLoaded, self.on_project_loaded)
        event_bus.subscribe(event_model.ProjectClosed, self.on_project_closed)

        # IGraphSync Events
        event_bus.subscribe(event_model.NodeAdded, self.on_node_added)
        event_bus.subscribe(event_model.NodeRemoved, self.on_node_removed)
        event_bus.subscribe(event_model.ConnectionAdded,
                            self.on_connection_added)
        event_bus.subscribe(event_model.ConnectionRemoved,
                            self.on_connection_removed)

        # IMixerSync Events
        event_bus.subscribe(event_model.InsertAdded, self.on_insert_added)
        event_bus.subscribe(event_model.InsertRemoved, self.on_insert_removed)
        event_bus.subscribe(event_model.PluginEnabledChanged,
                            self.on_plugin_enabled_changed)
        event_bus.subscribe(event_model.ParameterChanged,
                            self.on_parameter_changed)

        # ITransportSync Events
        event_bus.subscribe(event_model.TempoChanged, self.on_tempo_changed)
        event_bus.subscribe(event_model.TimeSignatureChanged,
                            self.on_time_signature_changed)

        # ITrackSync Events
        event_bus.subscribe(event_model.ClipAdded, self.on_clip_added)
        event_bus.subscribe(event_model.ClipRemoved, self.on_clip_removed)

        # IClipSync Events
        event_bus.subscribe(event_model.NoteAdded, self.on_notes_added)
        event_bus.subscribe(event_model.NoteRemoved, self.on_notes_removed)

        print(
            "DawDreamerSyncController: All ISyncController methods have been registered as event handlers."
        )

    # ========================================================================
    # 2. Public ISyncController Method Implementations (The Logic Layer)
    # ========================================================================

    # --- IProjectSync Methods ---
    def on_project_loaded(self, event: event_model.ProjectLoaded):
        self._project = event.project
        project = event.project
        print(f"Sync: Handling on_project_loaded for '{project.name}'.")

        # Perform a full sync by firing simulated events for each item
        for node in project.get_all_nodes():
            self.on_node_added(event_model.NodeAdded(node=node))

        for track in [
                t for t in project.get_all_nodes() if isinstance(t, ITrack)
        ]:
            self._rebuild_insert_chain_connections(track.node_id)

        for conn in project.router.get_all_connections():
            self.on_connection_added(
                event_model.ConnectionAdded(connection=conn))

        for node in project.get_all_nodes():
            if hasattr(node, 'get_parameters'):
                for name, param in node.get_parameters().items():
                    self.on_parameter_changed(
                        event_model.ParameterChanged(
                            owner_node_id=node.node_id,
                            param_name=name,
                            new_value=param.value))

    def on_project_closed(self, event: event_model.ProjectClosed):
        print(f"Sync: Handling on_project_closed for '{event.project.name}'.")
        for node in list(event.project.get_all_nodes()):
            self._render_graph.remove_processor(node.node_id)
        self._project = None

    # --- IGraphSync Methods ---
    def on_node_added(self, event: event_model.NodeAdded):
        node = event.node
        if isinstance(node, IPlugin):
            path = node.descriptor.meta.get(
                'path') if node.descriptor else None
            self._render_graph.add_plugin_processor(node.node_id, path)
        elif isinstance(node, Track):
            self._render_graph.add_sum_processor(node.node_id)

    def on_node_removed(self, event: event_model.NodeRemoved):
        self._render_graph.remove_processor(event.node_id)

    def on_connection_added(self, event: event_model.ConnectionAdded):
        conn = event.connection
        self._render_graph.create_connection(conn.source_port.owner_node_id,
                                             conn.dest_port.owner_node_id)

    def on_connection_removed(self, event: event_model.ConnectionRemoved):
        conn = event.connection
        self._render_graph.destroy_connection(conn.source_port.owner_node_id,
                                              conn.dest_port.owner_node_id)

    # --- IMixerSync Methods ---
    def on_insert_added(self, event: event_model.InsertAdded):
        # Any structural change to inserts requires rebuilding the track's internal signal chain
        self._rebuild_insert_chain_connections(event.owner_node_id)

    def on_insert_removed(self, event: event_model.InsertRemoved):
        self._rebuild_insert_chain_connections(event.owner_node_id)

    def on_insert_moved(self, event: event_model.InsertMoved):
        self._rebuild_insert_chain_connections()

    def on_plugin_enabled_changed(self,
                                  event: event_model.PluginEnabledChanged):
        self._render_graph.set_plugin_bypass(event.plugin_id,
                                             not event.is_enabled)

    def on_parameter_changed(self, event: event_model.ParameterChanged):
        value = event.new_value
        if isinstance(value, (float, int)):
            self._render_graph.set_parameter(event.owner_node_id,
                                             event.param_name, float(value))

    # --- ITransportSync Methods ---
    def on_tempo_changed(self, event: event_model.TempoChanged):
        self._render_graph.set_tempo(event.beat, event.new_bpm)

    def on_time_signature_changed(self,
                                  event: event_model.TimeSignatureChanged):
        self._render_graph.set_time_signature(event.beat, event.numerator,
                                              event.denominator)

    # --- ITrackSync Methods ---
    def on_clip_added(self, event: event_model.ClipAdded):
        if self._project is None: return
        from ...models import MIDIClip
        if isinstance(event.clip, MIDIClip):
            track = self._project.get_node_by_id(event.owner_track_id)
            if (isinstance(track, InstrumentTrack)
                    and track.mixer_channel.inserts):
                instrument_id = track.mixer_channel.inserts[0].node_id
                self._render_graph.add_notes_to_instrument(
                    instrument_id, list(event.clip.notes))

    def on_clip_removed(self, event: event_model.ClipRemoved):
        self._render_graph.remove_clip_data(event.owner_track_id,
                                            event.clip_id)

    # --- IClipSync Methods ---
    def on_notes_added(self, event: event_model.NoteAdded):
        # Resyncing the whole clip is the simplest robust solution
        if self._project:
            for track in [
                    t for t in self._project.get_all_nodes()
                    if isinstance(t, ITrack)
            ]:
                for clip in track.clips:
                    if clip.clip_id == event.owner_clip_id:
                        self.on_clip_added(
                            event_model.ClipAdded(owner_track_id=track.node_id,
                                                  clip=clip))
                        return

    def on_notes_removed(self, event: event_model.NoteRemoved):
        self.on_notes_added(
            event_model.NoteAdded(owner_clip_id=event.owner_clip_id, notes=[]))

    def _rebuild_insert_chain_connections(self, track_id: str):
        """
        This helper method recalculates and applies the entire signal path for a track's inserts.
        It's called whenever an insert is added, removed, or moved.
        """
        if not self._project:
            print(
                f"Warning: Cannot rebuild insert chain for track {track_id}. Project not loaded."
            )
            return

        track = self._project.get_node_by_id(track_id)
        if not isinstance(track, ITrack):
            print(f"Warning: Node {track_id} is not a valid track.")
            return

        # 1. Determine the correct, new order of processor IDs in the signal chain
        chain_node_ids = []
        is_instrument = isinstance(track, InstrumentTrack)
        inserts = track.mixer_channel.inserts

        # This logic correctly determines the signal flow based on track type
        if is_instrument and inserts:
            # Convention: first insert is the instrument synth
            chain_node_ids.append(inserts[0].node_id)
            # The rest of the inserts are effects
            chain_node_ids.extend([p.node_id for p in inserts[1:]])
        else:  # For Audio/Bus tracks, the chain is just the inserts
            chain_node_ids.extend([p.node_id for p in inserts])

        # The signal flows from the last insert into the track's main summing processor
        chain_node_ids.append(track_id)

        # 2. Disconnect all previous connections within this chain to ensure a clean state.
        # This is crucial to prevent incorrect or dangling connections.
        all_involved_ids = [p.node_id for p in inserts] + [track_id]
        all_connections = self._project.router.get_all_connections()
        for conn in all_connections:
            # Check if both source and destination are part of this track's internal chain
            if conn.source_port.owner_node_id in all_involved_ids and \
               conn.dest_port.owner_node_id in all_involved_ids:
                # This is an internal connection that needs to be broken before rebuilding.
                self._render_graph.destroy_connection(
                    conn.source_port.owner_node_id,
                    conn.dest_port.owner_node_id)

        # 3. Create the new connections sequentially based on the new order
        if len(chain_node_ids) > 1:
            for i in range(len(chain_node_ids) - 1):
                source_id = chain_node_ids[i]
                dest_id = chain_node_ids[i + 1]
                self._render_graph.create_connection(source_id, dest_id)

        print(
            f"Sync: Successfully rebuilt insert chain for track {track_id[:8]}."
        )
