# file: src/MuzaiCore/backends/dawdreamer/render_graph.py
from typing import Dict, Set, Tuple, Optional, List

from ...interfaces.system import INode, ITrack, IPlugin
from ...models import Connection, PluginDescriptor, Note
from ..common.message_queue import RealTimeMessageQueue


class DawDreamerRenderGraph:
    """
    Manages the state of the DawDreamer RenderEngine graph from the main thread.

    This class acts as a "shadow" or proxy for the real-time DSP graph. It
    translates high-level, domain-specific changes (e.g., "add an insert
    plugin to a track") into a sequence of low-level, atomic messages
    for the audio thread to consume. This ensures thread safety and allows
    for complex, transactional updates to the DSP graph.
    """

    def __init__(self, message_queue: RealTimeMessageQueue):
        self._queue = message_queue

        # --- Internal State ---
        # Maps a MuzaiCore node_id to the DawDreamer processor name(s) it represents.
        # A single domain node (like a Track) can map to multiple processors.
        self._node_id_to_processors: Dict[str, List[str]] = {}

        # Maps a processor name back to its owning MuzaiCore node_id.
        self._processor_to_node_id: Dict[str, str] = {}

        # Keeps track of all active connections by processor names.
        self._connections: Set[Tuple[str, str]] = set()

        # For tracks, we need to know the signal chain to correctly insert plugins.
        # Maps track_id to an ordered list of its insert plugin_ids.
        self._track_insert_chains: Dict[str, List[str]] = {}

        print("DawDreamerRenderGraph: Initialized.")

    def add_node(self,
                 node: INode,
                 descriptor: Optional[PluginDescriptor] = None) -> None:
        """
        High-level method to add any type of node to the render graph.
        It intelligently delegates to the correct specific handler.
        """
        if node.node_id in self._node_id_to_processors:
            print(
                f"Warning: Node '{node.node_id}' already in graph. Ignoring.")
            return

        if isinstance(node, ITrack):
            self._add_track_processors(node)
        elif isinstance(node, IPlugin):
            # Adding a plugin is usually part of an "add insert" operation,
            # but we can support adding it as a standalone node.
            self._add_plugin_processor(node, descriptor)
        else:
            print(
                f"Warning: Unknown node type for RenderGraph: {type(node).__name__}"
            )

    def remove_node(self, node_id: str) -> None:
        """Removes a node and all its associated processors and connections."""
        if node_id not in self._node_id_to_processors:
            return

        # Removing a track also removes its insert plugins from the chain logic.
        if node_id in self._track_insert_chains:
            del self._track_insert_chains[node_id]

        processors_to_remove = self._node_id_to_processors.pop(node_id)
        for proc_name in processors_to_remove:
            self._remove_single_processor(proc_name)

    def add_connection(self, connection: Connection) -> None:
        """Adds a direct connection between the output of one node and the input of another."""
        # Find the representative output/input processors for each domain node.
        source_proc = self._get_node_output_processor(
            connection.source_port.owner_node_id)
        dest_proc = self._get_node_input_processor(
            connection.dest_port.owner_node_id)

        if not source_proc or not dest_proc:
            print(
                f"Error: Cannot connect. Source or destination processor not found."
            )
            return

        self._create_connection(source_proc, dest_proc)

    def add_insert_to_track(self, track_id: str, plugin_node: IPlugin,
                            index: int):
        """
        Handles the complex logic of inserting a plugin into a track's signal chain.
        This is a transactional, high-level operation.
        """
        if not isinstance(plugin_node, IPlugin):
            return

        # 1. Add the plugin processor itself to the engine.
        self._add_plugin_processor(plugin_node, plugin_node.descriptor)
        new_plugin_proc_name = self._node_id_to_processors[
            plugin_node.node_id][0]

        # 2. Update the logical insert chain for the track.
        chain = self._track_insert_chains.get(track_id, [])
        chain.insert(index, plugin_node.node_id)
        self._track_insert_chains[track_id] = chain

        # 3. Rebuild the physical connections for this track's entire insert chain.
        self._rebuild_track_connections(track_id)

    def set_parameter(self, node_id: str, param_name: str,
                      value: float) -> None:
        """Queues a parameter change for any processor owned by the node."""
        if node_id not in self._node_id_to_processors:
            return

        # Note: This is simplified. A plugin might have multiple processors.
        # We assume the first processor is the one to receive the parameter.
        target_processor = self._node_id_to_processors[node_id][0]
        self._queue.push({
            'op': 'SET_PARAMETER',
            'processor_name': target_processor,
            'param_name': param_name,
            'value': value,
        })

    def clear(self) -> None:
        """Clears the entire render graph, removing all processors."""
        all_node_ids = list(self._node_id_to_processors.keys())
        for node_id in all_node_ids:
            self.remove_node(node_id)
        self._connections.clear()
        self._track_insert_chains.clear()

    # --- Private Helper Methods for Processor Management ---

    def _add_track_processors(self, track: ITrack):
        """Translates a Track domain object into one or more processors."""
        # For any track, we create a summing junction that represents its
        # main input/bus. This is where other tracks can route audio to.
        track_bus_proc = f"proc_{track.node_id}_bus"
        self._register_processor(track.node_id, track_bus_proc)
        self._queue.push({'op': 'ADD_NODE', 'processor_name': track_bus_proc})

        # Initialize an empty insert chain for this track
        self._track_insert_chains[track.node_id] = []

    def _add_plugin_processor(self, plugin: IPlugin,
                              descriptor: PluginDescriptor):
        """Adds a single processor for a plugin."""
        plugin_proc = f"proc_{plugin.node_id}"
        self._register_processor(plugin.node_id, plugin_proc)

        msg = {'op': 'ADD_NODE', 'processor_name': plugin_proc}
        if descriptor and 'path' in descriptor.meta:
            msg['plugin_path'] = descriptor.meta['path']
        self._queue.push(msg)

    def _remove_single_processor(self, processor_name: str):
        """Removes one processor and its connections."""
        if processor_name not in self._processor_to_node_id:
            return

        del self._processor_to_node_id[processor_name]

        # Find and queue removal of all associated connections
        conns_to_remove = [c for c in self._connections if processor_name in c]
        for source, dest in conns_to_remove:
            self._destroy_connection(source, dest)

        self._queue.push({
            'op': 'REMOVE_NODE',
            'processor_name': processor_name
        })

    def _rebuild_track_connections(self, track_id: str):
        """
        Re-wires the entire signal chain for a track. This is called
        after adding, removing, or reordering an insert.
        """
        chain = self._track_insert_chains.get(track_id, [])
        track_bus_proc = self._get_node_input_processor(track_id)

        # 1. Disconnect everything currently connected to the track's bus
        conns_to_remove = [
            c for c in self._connections if c[1] == track_bus_proc
        ]
        for source, dest in conns_to_remove:
            self._destroy_connection(source, dest)

        # 2. Build the new chain
        current_source = self._get_track_source_processor(
            track_id)  # The instrument/audio input

        # Connect source to the first insert, or directly to the bus if no inserts
        if not chain:
            if current_source:
                self._create_connection(current_source, track_bus_proc)
            return

        # Connect source to first plugin
        first_plugin_proc = self._get_node_output_processor(chain[0])
        if current_source and first_plugin_proc:
            self._create_connection(current_source, first_plugin_proc)

        # Connect plugins in series
        for i in range(len(chain) - 1):
            source_plugin_proc = self._get_node_output_processor(chain[i])
            dest_plugin_proc = self._get_node_input_processor(chain[i + 1])
            if source_plugin_proc and dest_plugin_proc:
                self._create_connection(source_plugin_proc, dest_plugin_proc)

        # Connect last plugin to the track's main bus
        last_plugin_proc = self._get_node_output_processor(chain[-1])
        if last_plugin_proc and track_bus_proc:
            self._create_connection(last_plugin_proc, track_bus_proc)

    # --- Private Helper Methods for Connections and State ---

    def _create_connection(self, source_proc: str, dest_proc: str):
        if (source_proc, dest_proc) not in self._connections:
            self._connections.add((source_proc, dest_proc))
            self._queue.push({
                'op': 'ADD_CONNECTION',
                'source_name': source_proc,
                'dest_name': dest_proc
            })

    def _destroy_connection(self, source_proc: str, dest_proc: str):
        if (source_proc, dest_proc) in self._connections:
            self._connections.remove((source_proc, dest_proc))
            self._queue.push({
                'op': 'REMOVE_CONNECTION',
                'source_name': source_proc,
                'dest_name': dest_proc
            })

    def _register_processor(self, owner_node_id: str, processor_name: str):
        if owner_node_id not in self._node_id_to_processors:
            self._node_id_to_processors[owner_node_id] = []
        self._node_id_to_processors[owner_node_id].append(processor_name)
        self._processor_to_node_id[processor_name] = owner_node_id

    def _get_node_input_processor(self, node_id: str) -> Optional[str]:
        """Gets the main processor that receives audio for a given node."""
        if node_id in self._node_id_to_processors:
            # By convention, the first registered processor is the main input.
            return self._node_id_to_processors[node_id][0]
        return None

    def _get_node_output_processor(self, node_id: str) -> Optional[str]:
        """Gets the main processor that sends audio from a given node."""
        # In our simple model, input and output processors are the same.
        return self._get_node_input_processor(node_id)

    def _get_track_source_processor(self, track_id: str) -> Optional[str]:
        """Finds the 'source of sound' processor for a track, if any."""
        # This is a placeholder for logic that would find the instrument plugin
        # on an instrument track.
        return None
