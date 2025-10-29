# file: src/MuzaiCore/backends/dawdreamer/transport.py
import sounddevice as sd
import numpy as np
import dawdreamer as daw
from typing import Dict, Optional, List

from ...interfaces.system import ITransport, ITimeline
from ..common.message_queue import RealTimeMessageQueue
from ...models import Note
from .message_handler import MessageHandler, AudioThreadStateHandler


class DawDreamerTransport(ITransport):
    """
    The real-time component of the DawDreamer backend.
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
        self._node_id_to_processor_name: Dict[str, str] = {}
        self._timeline: Optional[ITimeline] = None
        self._current_sample = 0
        self._loop_start_beat = 0.0
        self._loop_end_beat = 0.0
        self._is_loop_enabled = False

        self._state = AudioThreadStateHandler()
        self._message_handler = MessageHandler()

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
        self._current_sample = 0
        self._engine.set_bpm(self._timeline.tempo if self._timeline else 120)
        self._engine.set_transport_sample_position(0)
        print("DawDreamerTransport: Playback stopped.")

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def get_playback_position_beats(self) -> float:
        if not self._timeline: return 0.0
        seconds = self._current_sample / self._sample_rate
        return self._timeline.seconds_to_beats(seconds)

    def set_playback_position_beats(self, position_beats: float):
        if not self._timeline: return
        seconds = self._timeline.beats_to_seconds(position_beats)
        self._current_sample = int(seconds * self._sample_rate)
        self._engine.set_transport_sample_position(self._current_sample)

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info,
                        status):
        """This is the heart of the real-time audio processing."""
        if status:
            print(f"Sounddevice status: {status}")

        # 1. Consume all pending messages from the main thread.
        self._process_messages()

        self._engine.render(frames)
        audio, _, _ = self._engine.get_audio('master_out')
        if audio is not None and audio.shape[1] >= frames:
            outdata[:] = audio[:, :frames].T
        else:
            outdata.fill(0)
        self._current_sample += frames

    def _process_messages(self):
        self._queue.drain(lambda msg: self._message_handler.handle(
            msg, self._engine, self._state))
