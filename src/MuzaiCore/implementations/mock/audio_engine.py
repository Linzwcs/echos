# file: src/MuzaiCore/implementations/mock/audio_engine.py
import time
import threading
from typing import Optional

from ...interfaces import IAudioEngine, IProject
from ...models.engine_model import TransportStatus, TransportContext


class MockAudioEngine(IAudioEngine):
    """
    Simulates a real-time audio engine using a background thread.
    It doesn't process real audio but mimics the block-based processing loop.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 512):
        self._project: Optional[IProject] = None
        self._sample_rate = sample_rate
        self._block_size = block_size

        self._current_sample_pos = 0
        self._is_running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def load_project(self, project: IProject):
        print(f"MockEngine: Project '{project.project_id}' loaded.")
        self._project = project

    def play(self):
        if self._is_running or not self._project:
            return

        self._is_running = True
        self._project.set_transport_status(TransportStatus.PLAYING)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("MockEngine: Playback started.")

    def stop(self):
        if not self._is_running:
            return

        self._is_running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join()  # Wait for the thread to finish

        self._current_sample_pos = 0
        if self._project:
            self._project.set_transport_status(TransportStatus.STOPPED)
        print("MockEngine: Playback stopped.")

    def _run(self):
        """The main processing loop that runs in a separate thread."""
        block_duration_sec = self._block_size / self._sample_rate

        while not self._stop_event.is_set():
            loop_start_time = time.perf_counter()

            if not self._project:
                time.sleep(block_duration_sec)
                continue

            # 1. Calculate current time context
            current_beat = self._project.timeline.samples_to_beats(
                self._current_sample_pos)
            context = TransportContext(current_beat=current_beat,
                                       sample_rate=self._sample_rate,
                                       block_size=self._block_size,
                                       tempo=self._project.tempo)

            print(f"--- Engine Block --- Beat: {current_beat:.2f} ---")

            # 2. Get processing order from the router
            try:
                processing_order = self._project.router.get_processing_order()
            except Exception as e:
                print(f"ERROR: Could not get processing order: {e}")
                time.sleep(block_duration_sec)
                continue

            # 3. "Process" each node in order
            for node_id in processing_order:
                node = self._project.get_node_by_id(node_id)
                if node:
                    # In a real engine, we'd pass audio buffers. Here, we pass placeholders.
                    node.process_block(input_buffer=None,
                                       midi_events=[],
                                       context=context)
                    print(
                        f"  -> Processed Node: {node_id} ({type(node).__name__})"
                    )

            # 4. Advance time
            self._current_sample_pos += self._block_size

            # 5. Sleep to simulate real-time
            loop_end_time = time.perf_counter()
            processing_time = loop_end_time - loop_start_time
            sleep_duration = max(0, block_duration_sec - processing_time)
            time.sleep(sleep_duration)
