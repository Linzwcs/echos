# file: src/MuzaiCore/implementations/mock/audio_engine.py
import time
import threading
from typing import Optional

from ...interfaces import IAudioEngine, IProject
from ...models.engine_model import TransportStatus, TransportContext


class MockAudioEngine(IAudioEngine):
    """
    一个模拟的音频引擎，现在使用一个后台线程来模拟实时播放和时间推进。
    """

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 512):
        self._project: Optional[IProject] = None
        self._is_playing: bool = False
        self._current_beat: float = 0.0
        self._sample_rate: int = sample_rate
        self._buffer_size: int = buffer_size

        # --- 线程相关属性 ---
        self._playback_thread: Optional[threading.Thread] = None
        # 使用 threading.Event 来安全地控制线程的停止
        self._stop_event: threading.Event = threading.Event()
        # 使用锁来保护共享状态（如 _is_playing 和 _current_beat），防止多线程冲突
        self._lock: threading.Lock = threading.Lock()

    def set_project(self, project: IProject):
        """将引擎与一个项目关联。"""
        self._project = project

    def play(self):
        """开始播放，并启动后台模拟线程。"""
        if not self._project:
            print("Warning: AudioEngine has no project set.")
            return

        with self._lock:
            if self._is_playing:
                print("AudioEngine: Already playing.")
                return

            print("AudioEngine: Playback started.")
            self._is_playing = True
            # 更新项目的状态
            self._project.set_transport_status(TransportStatus.PLAYING)

        # 启动后台线程
        self._stop_event.clear()  # 重置停止信号
        self._playback_thread = threading.Thread(target=self._playback_loop,
                                                 daemon=True)
        self._playback_thread.start()

    def stop(self):
        """停止播放，并安全地终止后台线程。"""
        if not self._project:
            return

        with self._lock:
            if not self._is_playing:
                return  # 已经停止了，无需操作

            print("AudioEngine: Playback stopped.")
            self._is_playing = False
            self._current_beat = 0.0  # 停止时通常会归零
            # 更新项目的状态
            self._project.set_transport_status(TransportStatus.STOPPED)

        # 发送停止信号并等待线程结束
        if self._playback_thread and self._playback_thread.is_alive():
            self._stop_event.set()
            self._playback_thread.join()  # 等待线程完全退出
        self._playback_thread = None

    def _playback_loop(self):
        """
        后台线程的主循环。
        模拟音频设备的回调，以固定的时间间隔调用 render_next_block。
        """
        # 计算每个块的持续时间（秒）
        seconds_per_block = self._buffer_size / self._sample_rate

        print(
            f"AudioEngine: Starting playback loop (updates every {seconds_per_block:.4f} seconds)."
        )

        while not self._stop_event.is_set():
            start_time = time.perf_counter()

            # 在锁的保护下调用 render_next_block
            with self._lock:
                self.render_next_block()

            # (可选) 在这里可以打印播放头位置，用于调试
            # print(f"Current Beat: {self.current_beat:.2f}")

            # 计算处理所花费的时间，并休眠剩余的时间，以模拟实时性
            end_time = time.perf_counter()
            processing_time = end_time - start_time
            sleep_time = seconds_per_block - processing_time

            if sleep_time > 0:
                # 等待直到下一个块的时间点
                self._stop_event.wait(sleep_time)

        print("AudioEngine: Playback loop finished.")

    def render_next_block(self):
        """
        模拟处理下一个音频块，主要任务是推进播放头。
        注意：这个方法现在应该只在 _playback_loop 中被调用，并且在锁的保护下。
        """
        # 这个方法现在不再需要检查 _is_playing，因为调用它的循环会处理
        if not self._project:
            return

        current_seconds = self._project.timeline.beats_to_seconds(
            self._current_beat)
        seconds_per_block = self._buffer_size / self._sample_rate
        next_seconds = current_seconds + seconds_per_block
        self._current_beat = self._project.timeline.seconds_to_beats(
            next_seconds)

    def report_latency(self) -> float:
        """报告一个模拟的延迟。"""
        buffer_latency_seconds = self._buffer_size / self._sample_rate
        simulated_hardware_latency_seconds = 0.005  # 5ms
        return buffer_latency_seconds + simulated_hardware_latency_seconds

    @property
    def is_playing(self) -> bool:
        with self._lock:
            return self._is_playing

    @property
    def current_beat(self) -> float:
        with self._lock:
            return self._current_beat
