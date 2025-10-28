# file: src/MuzaiCore/backends/dawdreamer/transport.py
import sounddevice as sd
import numpy as np
import dawdreamer as daw
from typing import Dict, Optional

from ...interfaces.system import ITransport, ITimeline
from ..common.message_queue import RealTimeMessageQueue


class DawDreamerTransport(ITransport):
    """
    The real-time component of the DawDreamer backend.
    This class runs the audio callback loop. It is the "Consumer" that
    drains the message queue and applies changes to the daw.RenderEngine.
    """

    def __init__(self, engine: daw.RenderEngine,
                 message_queue: RealTimeMessageQueue, sample_rate: int,
                 block_size: int):
        self._engine = engine
        self._queue = message_queue
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._stream = None
        self._is_playing = False

        # This is the audio thread's own mapping. It's built from messages
        # sent by the main thread's DawDreamerRenderGraph.
        self._node_id_to_processor_name: Dict[str, str] = {}
        self._timeline: Optional[ITimeline] = None

    def set_project_timeline(self, timeline: ITimeline):
        self._timeline = timeline

    def play(self):
        if self._is_playing:
            return
        try:
            self._stream = sd.OutputStream(samplerate=self._sample_rate,
                                           blocksize=self._block_size,
                                           channels=2,
                                           dtype='float32',
                                           callback=self._audio_callback)
            self._stream.start()
            self._is_playing = True
            print("DawDreamerTransport: Playback started.")
        except Exception as e:
            print(f"Error starting audio stream: {e}")

    def stop(self):
        if not self._is_playing or not self._stream:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._is_playing = False
        print("DawDreamerTransport: Playback stopped.")

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info,
                        status):
        """This is the heart of the real-time audio processing."""
        if status:
            print(f"Sounddevice status: {status}")

        # 1. Consume all pending messages from the main thread.
        # This is the crucial step for state synchronization.
        self._process_messages()

        # 2. Tell DawDreamer to render `frames` of audio.
        self._engine.render(
            frames)  # DawDreamer's render takes num_samples, not seconds

        # 3. Get the audio and send it to the output buffer.
        audio, _, _ = self._engine.get_audio(
        )  # Assumes master is connected to output
        if audio is not None and audio.shape[1] >= frames:
            # DawDreamer provides audio as (channels, samples). We need to transpose for sounddevice.
            outdata[:] = audio[:, :frames].T
        else:
            outdata.fill(0)

    def _process_messages(self):
        """Drains the queue and applies instructions to the DawDreamer engine."""
        self._queue.drain(self._handle_message)

    def _handle_message(self, msg: dict):
        """
        The command executor in the audio thread. It translates the simple
        message DTOs into actual calls on the daw.RenderEngine object.
        THIS IS A CRITICAL REAL-TIME SAFE SECTION.
        """
        try:
            op = msg.get('op')
            node_id = msg.get('node_id')

            # --- Node Operations ---
            if op == 'ADD_NODE':
                processor_name = f"proc_{node_id}"
                self._node_id_to_processor_name[node_id] = processor_name
                if 'plugin_path' in msg:
                    self._engine.make_plugin_processor(processor_name,
                                                       msg['plugin_path'])
                else:  # It's a track or bus, make a summing junction
                    self._engine.make_add_processor(processor_name, [])

            elif op == 'REMOVE_NODE':
                if node_id in self._node_id_to_processor_name:
                    name_to_remove = self._node_id_to_processor_name.pop(
                        node_id)
                    self._engine.remove_processor(name_to_remove)

            # --- Connection Operations ---
            elif op == 'ADD_CONNECTION':
                source_name = self._node_id_to_processor_name.get(
                    msg['source_node_id'])
                dest_name = self._node_id_to_processor_name.get(
                    msg['dest_node_id'])
                if source_name and dest_name:
                    self._engine.add_connection(source_name, dest_name)

            elif op == 'REMOVE_CONNECTION':
                source_name = self._node_id_to_processor_name.get(
                    msg['source_node_id'])
                dest_name = self._node_id_to_processor_name.get(
                    msg['dest_node_id'])
                if source_name and dest_name:
                    self._engine.remove_connection(source_name, dest_name)

            # --- Parameter Operations ---
            elif op == 'SET_PARAMETER':
                processor_name = self._node_id_to_processor_name.get(node_id)
                if processor_name:
                    processor = self._engine.get_processor(processor_name)
                    # A robust solution would cache param name to index mapping.
                    # This linear search is slow but demonstrates the principle.
                    for i in range(processor.get_parameter_count()):
                        if processor.get_parameter_name(
                                i) == msg['param_name']:
                            processor.set_parameter(i, msg['value'])
                            break

            # --- MIDI Operations ---
            elif op == 'ADD_NOTES':
                processor_name = self._node_id_to_processor_name.get(node_id)
                processor = self._engine.get_processor(processor_name)
                if processor and self._timeline:
                    for note in msg['notes']:
                        start_sec = self._timeline.beats_to_seconds(
                            note.start_beat)
                        duration_sec = self._timeline.beats_to_seconds(
                            note.duration_beats)
                        processor.add_midi_note(note.pitch, note.velocity,
                                                start_sec, duration_sec)

        except Exception as e:
            # In a real-time thread, we must never crash. Log errors instead.
            print(
                f"Audio Thread Error handling message '{msg.get('op')}': {e}")
