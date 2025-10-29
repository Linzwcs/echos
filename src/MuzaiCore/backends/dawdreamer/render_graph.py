from typing import Dict, Set, Tuple, Optional, List

from ...interfaces.system import INode, ITrack, IPlugin, IProject, IInstrumentTrack
from ...models import Connection, PluginDescriptor, Note
from ..common.message_queue import RealTimeMessageQueue
from .messages import (AddNode, RemoveNode, AddConnection, RemoveConnection,
                       SetParameter, AddNotes)


class DawDreamerRenderGraph:
    """
    Manages the state of the DawDreamer RenderEngine graph from the main thread.
    """

    def __init__(self, message_queue: RealTimeMessageQueue):
        self._queue = message_queue
        self._node_id_to_processors: Dict[str, List[str]] = {}
        self._processor_to_node_id: Dict[str, str] = {}
        self._connections: Set[Tuple[str, str]] = set()
        self._track_insert_chains: Dict[str, List[str]] = {}
        print("DawDreamerRenderGraph: Initialized.")

    def add_node(self,
                 node: INode,
                 descriptor: Optional[PluginDescriptor] = None):
        if node.node_id in self._node_id_to_processors:
            return
        if isinstance(node, ITrack):
            self._add_track_processors(node)
        elif isinstance(node, IPlugin):
            self._add_plugin_processor(node, descriptor)

    def remove_node(self, node_id: str):
        if node_id not in self._node_id_to_processors:
            return
        if node_id in self._track_insert_chains:
            # If it's a track, remove all its insert plugins first
            for plugin_id in self._track_insert_chains[node_id]:
                self.remove_node(plugin_id)
            del self._track_insert_chains[node_id]

        processors_to_remove = self._node_id_to_processors.pop(node_id)
        for proc_name in processors_to_remove:
            self._remove_single_processor(proc_name)

    def add_connection(self, connection: Connection):
        source_proc = self._get_node_output_processor(
            connection.source_port.owner_node_id)
        dest_proc = self._get_node_input_processor(
            connection.dest_port.owner_node_id)
        if source_proc and dest_proc:
            self._create_connection(source_proc, dest_proc)

    def remove_connection(self, connection: Connection):
        source_proc = self._get_node_output_processor(
            connection.source_port.owner_node_id)
        dest_proc = self._get_node_input_processor(
            connection.dest_port.owner_node_id)
        if source_proc and dest_proc:
            self._destroy_connection(source_proc, dest_proc)

    def add_insert_to_track(self, track_id: str, plugin_node: IPlugin,
                            index: int):
        chain = self._track_insert_chains.get(track_id, [])
        chain.insert(index, plugin_node.node_id)
        self._track_insert_chains[track_id] = chain
        self._rebuild_track_connections(track_id)

    def remove_insert_from_track(self, track_id: str, plugin_id: str):
        if track_id in self._track_insert_chains and plugin_id in self._track_insert_chains[
                track_id]:
            self._track_insert_chains[track_id].remove(plugin_id)
            self._rebuild_track_connections(track_id)
        # Also remove the plugin node itself
        self.remove_node(plugin_id)

    def add_notes_to_instrument(self, track_id: str, notes: List[Note]):
        # Find the instrument on this track
        instrument_plugin_id = self._get_track_instrument_plugin(track_id)
        if instrument_plugin_id:
            self._queue.push({
                'op': 'ADD_NOTES',
                'node_id': instrument_plugin_id,
                'notes': notes
            })

    def clear(self):
        all_node_ids = list(self._node_id_to_processors.keys())
        for node_id in all_node_ids:
            self.remove_node(node_id)
        self._connections.clear()
        self._track_insert_chains.clear()

    def full_sync_from_project(self, project: IProject):
        """Rebuilds the entire render graph from a project state."""
        self.clear()

        # 1. Add all tracks first
        tracks = [n for n in project.get_all_nodes() if isinstance(n, ITrack)]
        for track in tracks:
            self.add_node(track)

        # 2. Add all plugins and insert them into tracks
        for track in tracks:
            for i, plugin in enumerate(track.mixer_channel.inserts):
                self.add_node(plugin, plugin.descriptor)
                self.add_insert_to_track(track.node_id, plugin, i)

        # 3. Add all connections
        for conn in project.router.get_all_connections():
            self.add_connection(conn)

        # 4. Sync all parameters
        for node in project.get_all_nodes():
            if hasattr(node, 'get_parameters'):
                for name, param in node.get_parameters().items():
                    self.set_parameter(node.node_id, name, param.value)

    # --- Private Helpers ---

    def _add_track_processors(self, track: ITrack):
        track_bus_proc = f"proc_{track.node_id}_bus"
        self._register_processor(track.node_id, track_bus_proc)
        self._queue.push(AddNode(node_id=track.node_id,
                                 node_type='sum'))  # <-- PUSH DATACLASS
        self._track_insert_chains[track.node_id] = []

    def _add_plugin_processor(self, plugin: IPlugin,
                              descriptor: PluginDescriptor):
        plugin_proc = f"proc_{plugin.node_id}"
        self._register_processor(plugin.node_id, plugin_proc)
        path = descriptor.meta.get('path') if descriptor else None
        self._queue.push(
            AddNode(node_id=plugin.node_id,
                    node_type='plugin',
                    plugin_path=path))  # <-- PUSH DATACLASS

    def _remove_single_processor(self, processor_name: str):
        if processor_name not in self._processor_to_node_id:
            return

        node_id = self._processor_to_node_id.pop(processor_name)
        conns_to_remove = [c for c in self._connections if processor_name in c]
        for source, dest in conns_to_remove:
            self._destroy_connection(source, dest)
        self._queue.push(RemoveNode(node_id=node_id))  # <-- PUSH DATACLASS

    def _create_connection(self, source_proc: str, dest_proc: str):
        if (source_proc, dest_proc) not in self._connections:
            self._connections.add((source_proc, dest_proc))
            self._queue.push(
                AddConnection(
                    source_node_id=self._processor_to_node_id[source_proc],
                    dest_node_id=self._processor_to_node_id[dest_proc])
            )  # <-- PUSH DATACLASS

    def _destroy_connection(self, source_proc: str, dest_proc: str):
        if (source_proc, dest_proc) in self._connections:
            self._connections.remove((source_proc, dest_proc))
            self._queue.push(
                RemoveConnection(
                    source_node_id=self._processor_to_node_id[source_proc],
                    dest_node_id=self._processor_to_node_id[dest_proc])
            )  # <-- PUSH DATACLASS

    def set_parameter(self, node_id: str, param_name: str, value: float):
        if node_id not in self._node_id_to_processors:
            return
        self._queue.push(
            SetParameter(node_id=node_id, param_name=param_name,
                         value=value))  # <-- PUSH DATACLASS

    def add_notes_to_instrument(self, track_id: str, notes: List[Note]):
        instrument_plugin_id = self._get_track_instrument_plugin(track_id)
        if instrument_plugin_id:
            self._queue.push(
                AddNotes(node_id=instrument_plugin_id,
                         notes=notes))  # <-- PUSH DATACLASS

    def _rebuild_track_connections(self, track_id: str):
        chain_ids = self._track_insert_chains.get(track_id, [])
        track_bus_proc = self._get_node_input_processor(track_id)

        # Disconnect all existing inputs to the first plugin and the track bus
        # ... (complex disconnection logic omitted for brevity, full clear is safer)

        # For simplicity, we just rebuild the chain
        if not track_bus_proc: return

        chain_procs = [
            self._get_node_output_processor(pid) for pid in chain_ids
        ]

        # Connect instrument (if any) to the first insert
        instrument_proc = self._get_node_output_processor(
            self._get_track_instrument_plugin(track_id))

        # Chain starts with the instrument, or is empty if no instrument
        all_procs_in_chain = ([instrument_proc] +
                              chain_procs) if instrument_proc else chain_procs

        # Add the final track bus at the end
        all_procs_in_chain.append(track_bus_proc)

        # Connect them sequentially
        for i in range(len(all_procs_in_chain) - 1):
            source = all_procs_in_chain[i]
            dest = all_procs_in_chain[i + 1]
            if source and dest:
                self._create_connection(source, dest)

    def _register_processor(self, owner_node_id: str, processor_name: str):
        if owner_node_id not in self._node_id_to_processors:
            self._node_id_to_processors[owner_node_id] = []
        self._node_id_to_processors[owner_node_id].append(processor_name)
        self._processor_to_node_id[processor_name] = owner_node_id

    def _get_node_input_processor(self,
                                  node_id: Optional[str]) -> Optional[str]:
        if node_id and node_id in self._node_id_to_processors:
            return self._node_id_to_processors[node_id][0]
        return None

    def _get_node_output_processor(self,
                                   node_id: Optional[str]) -> Optional[str]:
        return self._get_node_input_processor(node_id)

    def _get_track_instrument_plugin(self, track_id: str) -> Optional[str]:
        """Finds the instrument plugin on an instrument track."""
        chain = self._track_insert_chains.get(track_id, [])
        # By convention, the first plugin on an instrument track is the instrument.
        if chain:
            return chain[0]
        return None

    def set_plugin_bypass(self, plugin_id: str, bypass: bool):
        """设置插件的旁路状态"""
        if plugin_id not in self._node_id_to_processors:
            return

        from .messages import SetPluginBypass
        self._queue.push(SetPluginBypass(node_id=plugin_id, bypass=bypass))

    def move_insert_in_track(self, track_id: str, plugin_id: str,
                             new_index: int):
        """在轨道的插入链中移动插件"""
        if track_id not in self._track_insert_chains:
            return

        chain = self._track_insert_chains[track_id]
        if plugin_id not in chain:
            return

        # 移除旧位置
        chain.remove(plugin_id)
        # 插入新位置
        chain.insert(new_index, plugin_id)

        # 重建连接
        self._rebuild_track_connections(track_id)

    def set_tempo_at_beat(self, beat: float, bpm: float):
        """设置指定节拍的速度"""
        from .messages import SetTempo
        self._queue.push(SetTempo(beat=beat, bpm=bpm))

    def set_time_signature_at_beat(self, beat: float, numerator: int,
                                   denominator: int):
        """设置指定节拍的拍号"""
        from .messages import SetTimeSignature
        self._queue.push(
            SetTimeSignature(beat=beat,
                             numerator=numerator,
                             denominator=denominator))

    def remove_clip(self, track_id: str, clip_id: str):
        """从轨道移除 clip"""
        from .messages import RemoveClip
        self._queue.push(RemoveClip(track_id=track_id, clip_id=clip_id))
