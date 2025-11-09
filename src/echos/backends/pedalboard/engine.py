import numpy as np
import threading
import time
from typing import Optional, List
import sounddevice as sd
from .sync_controller import PedalboardSyncController
from .messages import BaseMessage, NonRealTimeMessage, RealTimeMessage, GraphMessage
from .timeline import RealTimeTimeline
from .render_graph import PedalboardRenderGraph
from .message_handler import process_message
from .plugin_ins_manager import PedalboardPluginInstanceManager
from .context import AudioEngineContext
from ..common.message_queue import RealTimeMessageQueue
from ...interfaces.system import IEngine, IEngineTimeline
from ...models import TransportStatus, TransportContext


class PedalboardEngine(IEngine):

    def __init__(
        self,
        sample_rate: int = 48000,
        block_size: int = 512,
        output_channels: int = 2,
        plugin_ins_manager: PedalboardPluginInstanceManager = None,
        device_id: Optional[int] = None,
    ):
        super().__init__()
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._output_channels = output_channels
        self._device_id = device_id

        self._plugin_ins_manager = plugin_ins_manager
        self._render_graph = PedalboardRenderGraph(sample_rate, block_size,
                                                   self._plugin_ins_manager)

        self._rt_message_queue = RealTimeMessageQueue()
        self._nrt_message_queue = RealTimeMessageQueue()
        self._nrt_queue_lock = threading.Lock()

        self._sync_controller = PedalboardSyncController(self)
        self._realtime_timeline = RealTimeTimeline()

        self._status = TransportStatus.STOPPED
        self._current_beat = 0.0
        self._is_running = False

        self._audio_stream: Optional[sd.OutputStream] = None
        self._stream_lock = threading.Lock()

        self._stats_lock = threading.Lock()
        self._cpu_load = 0.0
        self._last_process_time = 0.0
        self._dropped_frames = 0
        self._peak_cpu_load = 0.0

        print(f"\n{'='*70}")
        print("PedalboardEngine Initialized (Real-time Mode)")
        print(f"{'='*70}")
        print(f"Sample Rate:     {sample_rate} Hz")
        print(f"Block Size:      {block_size} samples")
        print(f"Latency:         {block_size/sample_rate*1000:.2f} ms")
        print(f"Output Channels: {output_channels}")
        print(f"Device ID:       {device_id or 'default'}")
        print(f"{'='*70}\n")

    @property
    def sync_controller(self) -> PedalboardSyncController:
        return self._sync_controller

    @property
    def timeline(self) -> Optional[IEngineTimeline]:
        return self._realtime_timeline

    @property
    def is_playing(self) -> bool:
        return self._status == TransportStatus.PLAYING

    @property
    def current_beat(self) -> float:
        return self._current_beat

    @property
    def block_size(self) -> int:
        return self._block_size

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def transport_status(self) -> TransportStatus:
        return self._status

    @property
    def cpu_load(self) -> float:
        with self._stats_lock:
            return self._cpu_load

    def post_command(self, msg: BaseMessage):

        if isinstance(msg, RealTimeMessage):
            self._rt_message_queue.push(msg)
        elif isinstance(msg, NonRealTimeMessage):
            self._nrt_message_queue.push(msg)
        else:
            print(f"Warning: Unknown message type received: {type(msg)}")

    def play(self):
        self.refresh()
        if self._status == TransportStatus.PLAYING:
            print("PedalboardEngine: Already playing")
            return
        print("\nPedalboardEngine: Starting playback...")
        self._start_audio_stream()
        self._status = TransportStatus.PLAYING
        print("✓ Playback started\n")

    def pause(self):

        if self._status != TransportStatus.PLAYING:
            return

        self._status = TransportStatus.PAUSED
        print("PedalboardEngine: Playback paused")

    def stop(self):

        if self._status == TransportStatus.STOPPED:
            return

        print("\nPedalboardEngine: Stopping playback...")
        self._stop_audio_stream()
        self._status = TransportStatus.STOPPED
        self._current_beat = 0.0
        print("✓ Playback stopped\n")

    def seek(self, beat: float):

        self._current_beat = max(0.0, beat)
        print(f"PedalboardEngine: Seeked to beat {self._current_beat:.2f}")

    def _start_audio_stream(self):

        with self._stream_lock:
            if self._audio_stream is not None:
                print("Warning: Audio stream already active")
                return

            try:
                self._audio_stream = sd.OutputStream(
                    samplerate=self._sample_rate,
                    blocksize=self._block_size,
                    channels=self._output_channels,
                    device=self._device_id,
                    callback=self._audio_callback,
                    finished_callback=self._stream_finished_callback,
                )
                self._audio_stream.start()
                print(
                    f"✓ Audio stream started (device: {self._audio_stream.device})"
                )

            except Exception as e:
                print(f"✗ Failed to start audio stream: {e}")
                self._audio_stream = None
                raise

    def _stop_audio_stream(self):

        with self._stream_lock:
            if self._audio_stream is None:
                return

            try:
                self._audio_stream.stop()
                self._audio_stream.close()
                self._audio_stream = None
                print("✓ Audio stream stopped")

            except Exception as e:
                print(f"Warning: Error stopping audio stream: {e}")

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info,
                        status: sd.CallbackFlags):

        start_time = time.perf_counter()

        try:
            if status:
                if status.output_underflow:
                    with self._stats_lock:
                        self._dropped_frames += 1
                    print("Warning: Audio output underflow!")

            self._process_rt_messages()

            if self._status == TransportStatus.PLAYING:
                audio_block = self._process_audio_block()
            else:
                audio_block = np.zeros((self._output_channels, frames),
                                       dtype=np.float32)

            outdata[:] = audio_block.T

        except Exception as e:
            print(f"✗ Error in audio callback: {e}")
            outdata.fill(0)
            import traceback
            traceback.print_exc()

        process_time = time.perf_counter() - start_time
        self._update_performance_stats(process_time, frames)

    def _stream_finished_callback(self):
        print("Audio stream finished")

    def _process_audio_block(self) -> np.ndarray:
        current_tempo = self._realtime_timeline.get_tempo_at_beat(
            self._current_beat)
        current_tempo = current_tempo.bpm

        context = TransportContext(current_beat=self._current_beat,
                                   sample_rate=self._sample_rate,
                                   block_size=self._block_size,
                                   tempo=current_tempo)

        output_buffer = self._render_graph.process_block(context)

        beats_per_sample = (current_tempo / 60.0) / self._sample_rate
        self._current_beat += beats_per_sample * self._block_size

        return output_buffer

    def _update_performance_stats(self, process_time: float, frames: int):

        with self._stats_lock:
            self._last_process_time = process_time

            available_time = frames / self._sample_rate
            self._cpu_load = (process_time / available_time) * 100

            if self._cpu_load > self._peak_cpu_load:
                self._peak_cpu_load = self._cpu_load

    def refresh(self):
        self._process_nrt_messages()

    def _process_rt_messages(self):
        self._rt_message_queue.drain(lambda msg: process_message(
            msg,
            context=AudioEngineContext(graph=self._render_graph,
                                       timeline=self._realtime_timeline)))

    def _process_nrt_messages(self):
        if self._status == TransportStatus.PLAYING:
            return
        self._nrt_message_queue.drain(lambda msg: process_message(
            msg,
            context=AudioEngineContext(graph=self._render_graph,
                                       timeline=self._realtime_timeline)))

    def report_latency(self) -> float:
        hardware_latency = self._block_size / self._sample_rate

        plugin_latency = self._render_graph.get_total_latency(
        ) / self._sample_rate

        stream_latency = 0.0
        if self._audio_stream:
            stream_latency = self._audio_stream.latency

        total_latency = hardware_latency + plugin_latency + stream_latency
        return total_latency

    def _get_children(self) -> List:

        return [self._sync_controller]

    def _on_mount(self, event_bus):

        self._event_bus = event_bus
        print("PedalboardEngine: Mounted to event bus")

    def _on_unmount(self):

        self.stop()
        self._event_bus = None
        print("PedalboardEngine: Unmounted")

    def print_status(self):

        with self._stats_lock:
            cpu_load = self._cpu_load
            peak_cpu = self._peak_cpu_load
            last_process_time = self._last_process_time
            dropped_frames = self._dropped_frames

        tempo = (self._realtime_timeline.get_tempo_at_beat(self._current_beat)
                 if self._realtime_timeline else 120.0)

        print(f"\n{'='*70}")
        print("Engine Status")
        print(f"{'='*70}")
        print(f"Transport:       {self._status.value}")
        print(f"Current Beat:    {self._current_beat:.2f}")
        print(f"Tempo:           {tempo} BPM")
        print(f"CPU Load:        {cpu_load:.1f}% (peak: {peak_cpu:.1f}%)")
        print(f"Last Process:    {last_process_time*1000:.2f} ms")
        print(f"Total Latency:   {self.report_latency()*1000:.2f} ms")
        print(f"Dropped Frames:  {dropped_frames}")
        print(f"Stream Active:   {self._audio_stream is not None}")
        print(f"Pending NRT Msgs:{len(self._nrt_message_queue)}")
        print(f"{'='*70}\n")

    def get_performance_stats(self) -> dict:

        with self._stats_lock:
            cpu_load = self._cpu_load
            peak_cpu = self._peak_cpu_load
            last_process = self._last_process_time
            dropped = self._dropped_frames

        pending_nrt = len(self._nrt_message_queue)
        return {
            'cpu_load_percent': cpu_load,
            'peak_cpu_load_percent': peak_cpu,
            'last_process_time_ms': last_process * 1000,
            'total_latency_ms': self.report_latency() * 1000,
            'dropped_frames': dropped,
            'is_streaming': self._audio_stream is not None,
            'pending_nrt_messages': pending_nrt,
            'render_graph_stats': self._render_graph.get_stats(),
        }

    def reset_performance_stats(self):

        with self._stats_lock:
            self._dropped_frames = 0
            self._peak_cpu_load = 0.0
        print("Performance statistics reset")

    @staticmethod
    def list_audio_devices():
        print("\nAvailable Audio Devices:")
        print(f"{'='*70}")
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if device['max_output_channels'] > 0:
                default = " (DEFAULT)" if idx == sd.default.device[1] else ""
                print(f"[{idx}] {device['name']}{default}")
                print(f"     Channels: {device['max_output_channels']}, "
                      f"Sample Rate: {device['default_samplerate']} Hz")
        print(f"{'='*70}\n")

    def set_output_device(self, device_id: int):
        was_playing = self._status == TransportStatus.PLAYING

        if was_playing:
            self.stop()

        self._device_id = device_id
        print(f"Output device changed to: {device_id}")

        if was_playing:
            self.play()

    def export_to_file(self, output_path: str, duration_seconds: float):
        print(f"\nExporting audio to: {output_path}")
        print(f"Duration: {duration_seconds} seconds")

        original_status = self._status
        original_beat = self._current_beat

        try:
            self._status = TransportStatus.PLAYING
            self._current_beat = 0.0

            total_blocks = int(duration_seconds * self._sample_rate /
                               self._block_size)
            output_audio = []
            self.refresh()

            for block_idx in range(total_blocks):
                self._process_rt_messages()
                audio_block = self._process_audio_block()
                output_audio.append(audio_block)
                if block_idx % 100 == 0:
                    progress = (block_idx / total_blocks) * 100
                    print(f"  Progress: {progress:.1f}%", end='\r')

            print(f"  Progress: 100.0%")
            final_audio = np.concatenate(output_audio, axis=1)
            import soundfile as sf
            sf.write(output_path, final_audio.T, self._sample_rate)
            print(f"✓ Export complete: {output_path}")

        finally:
            self._status = original_status
            self._current_beat = original_beat

    def validate_state(self) -> bool:
        is_valid, issues = self._render_graph.validate_graph()
        if not is_valid:
            print("\n❌ Engine state validation FAILED:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✓ Engine state validation passed")
        return is_valid

    def print_graph_structure(self):

        self._render_graph.print_graph_structure()

    def print_full_diagnostics(self):

        self.print_status()
        self._render_graph.print_stats()
        self.print_graph_structure()
        self.validate_state()
