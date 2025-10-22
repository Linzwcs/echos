# file: src/MuzaiCore/implementations/real/audio_engine.py
import sounddevice as sd  # 使用一个流行的Python音频库
import numpy as np
from typing import Optional

from ...interfaces import IAudioEngine, IProject
from ...models.engine_model import TransportStatus, TransportContext


class RealAudioEngine(IAudioEngine):
    """
    A real audio engine that interfaces with the OS audio drivers.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 512):
        self._project: Optional[IProject] = None
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._current_sample_pos = 0
        self._stream = None

    def load_project(self, project: IProject):
        self._project = project

    def play(self):
        if self._stream and self._stream.active:
            return

        def audio_callback(outdata: np.ndarray, frames: int, time, status):
            """This function is called by the sound card driver."""
            if status:
                print(status)

            # This is the critical part: render the next block of audio
            buffer = self._render_next_block(frames)
            outdata[:] = buffer

        # Start the audio stream. The driver will now repeatedly call our callback.
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=2,  # Stereo output
            callback=audio_callback)
        self._stream.start()
        if self._project:
            self._project.set_transport_status(TransportStatus.PLAYING)
        print("RealEngine: Playback started.")

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._current_sample_pos = 0
        if self._project:
            self._project.set_transport_status(TransportStatus.STOPPED)
        print("RealEngine: Playback stopped.")

    def _render_next_block(self, num_samples: int) -> np.ndarray:
        """The core DSP function that generates the actual audio."""
        if not self._project:
            return np.zeros((num_samples, 2), dtype=np.float32)

        # 1. Get context and processing order (same as mock engine!)
        current_beat = self._project.timeline.samples_to_beats(
            self._current_sample_pos)
        context = TransportContext(...)
        processing_order = self._project.router.get_processing_order()

        # 2. Create the final output buffer
        master_output_buffer = np.zeros((num_samples, 2), dtype=np.float32)

        # 3. Process each node
        node_outputs = {}  # Store intermediate results
        for node_id in processing_order:
            node = self._project.get_node_by_id(node_id)
            if not node: continue

            # a. Gather inputs for this node
            # A real implementation would sum buffers from connected nodes.
            input_buffer = np.zeros((num_samples, 2), dtype=np.float32)

            # b. Get MIDI events for this block (from clips on the track)
            # This logic needs to be implemented.
            midi_events = []

            # c. Call the node's process_block method, which now does real work
            # and returns a numpy array.
            output_buffer = node.process_block(input_buffer, midi_events,
                                               context)

            # d. For now, let's just sum all track outputs to master
            master_output_buffer += output_buffer

        # 4. Advance time
        self._current_sample_pos += num_samples

        # 5. Return the final mixed audio
        return master_output_buffer
