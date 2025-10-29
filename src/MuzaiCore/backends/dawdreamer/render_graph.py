from typing import Dict, Set, Tuple, Optional, List

from ...interfaces.system import INode, ITrack, IPlugin, IProject
from ...models import Connection, PluginDescriptor, Note
from ..common.message_queue import RealTimeMessageQueue
from .messages import (AddNode, RemoveNode, AddConnection, RemoveConnection,
                       SetParameter, AddNotes, SetPluginBypass, SetTempo,
                       SetTimeSignature, RemoveClip)


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

    def add_plugin_processor(self, node_id: str, plugin_path: Optional[str]):
        """Instructs the audio thread to create a plugin processor."""
        processor_name = f"proc_{node_id}"
        self._node_id_to_processor_name[node_id] = processor_name
        self._queue.push(
            AddNode(node_id=node_id,
                    node_type='plugin',
                    plugin_path=plugin_path))

    def add_sum_processor(self, node_id: str):
        """Instructs the audio thread to create a summing processor (for busses/tracks)."""
        processor_name = f"proc_{node_id}"
        self._node_id_to_processor_name[node_id] = processor_name
        self._queue.push(AddNode(node_id=node_id, node_type='sum'))

    def remove_processor(self, node_id: str):
        """Instructs the audio thread to remove a processor."""
        if node_id in self._node_id_to_processor_name:
            del self._node_id_to_processor_name[node_id]
            self._queue.push(RemoveNode(node_id=node_id))

    def create_connection(self, source_node_id: str, dest_node_id: str):
        """Instructs the audio thread to connect two processors."""
        self._queue.push(
            AddConnection(source_node_id=source_node_id,
                          dest_node_id=dest_node_id))

    def destroy_connection(self, source_node_id: str, dest_node_id: str):
        """Instructs the audio thread to disconnect two processors."""
        self._queue.push(
            RemoveConnection(source_node_id=source_node_id,
                             dest_node_id=dest_node_id))

    # --- Parameter & Data Operations ---

    def set_parameter(self, node_id: str, param_name: str, value: float):
        """Instructs the audio thread to set a parameter on a processor."""
        self._queue.push(
            SetParameter(node_id=node_id, param_name=param_name, value=value))

    def set_plugin_bypass(self, plugin_id: str, bypass: bool):
        """Instructs the audio thread to set the bypass state of a plugin."""
        self._queue.push(SetPluginBypass(node_id=plugin_id, bypass=bypass))

    def add_notes_to_instrument(self, instrument_node_id: str,
                                notes: List[Note]):
        """Instructs the audio thread to add MIDI notes to an instrument."""
        self._queue.push(AddNotes(node_id=instrument_node_id, notes=notes))

    def remove_clip_data(self, track_id: str, clip_id: str):
        """Instructs the audio thread to clear data related to a clip."""
        # For DawDreamer, this typically means clearing all MIDI from the track's instrument.
        self._queue.push(RemoveClip(track_id=track_id, clip_id=clip_id))

    # --- Transport Operations ---

    def set_tempo(self, beat: float, bpm: float):
        """Instructs the audio thread to change the tempo."""
        self._queue.push(SetTempo(beat=beat, bpm=bpm))

    def set_time_signature(self, beat: float, numerator: int,
                           denominator: int):
        """Instructs the audio thread to change the time signature."""
        self._queue.push(
            SetTimeSignature(beat=beat,
                             numerator=numerator,
                             denominator=denominator))

    def clear_all(self):
        """Instructs the audio thread to remove all processors and connections."""
        # A more robust implementation would send individual RemoveNode messages
        # for all known nodes. For now, a dedicated "clear" message could be created,
        # or we rely on the SyncController to handle this.
        # Let's assume for now it's the SyncController's job to iterate and remove.
        print(
            "DawDreamerRenderGraph: Clear request received. It's the SyncController's job to manage removal."
        )
        self._node_id_to_processor_name.clear()
