# file: src/MuzaiCore/backends/dawdreamer/transport.py
"""
DawDreamer实时传输控制器
负责音频流的播放、停止和位置控制
"""
import sounddevice as sd
import numpy as np
import dawdreamer as daw
from typing import Dict, Optional, Tuple
import threading

from ...interfaces.system import ITransport, ITimeline
from ..common.message_queue import RealTimeMessageQueue
from .message_handler import MessageHandler, AudioThreadStateHandler


class DawDreamerTransport(ITransport):
    """
    DawDreamer后端的实时传输控制器
    
    特点：
    - 使用sounddevice提供实时音频输出
    - 通过消息队列与主线程通信
    - 处理播放、停止、循环等控制
    """

    def __init__(
        self,
        engine: daw.RenderEngine,
        message_queue: RealTimeMessageQueue,
        sample_rate: int,
        block_size: int,
    ):
        self._engine = engine
        self._queue = message_queue
        self._sample_rate = sample_rate
        self._block_size = block_size

        # 音频流（sounddevice）
        self._stream: Optional[sd.OutputStream] = None
        self._is_playing = False

        # 播放状态
        self._current_sample = 0
        self._is_loop_enabled = False
        self._loop_start_beat = 0.0
        self._loop_end_beat = 0.0

        # 时间线引用
        self._timeline: Optional[ITimeline] = None

        # 音频线程状态和消息处理器
        self._state = AudioThreadStateHandler()
        self._message_handler = MessageHandler()

        # 线程锁（用于线程安全的状态访问）
        self._lock = threading.Lock()

        print("DawDreamerTransport: Initialized")

    def set_project_timeline(self, timeline: ITimeline):
        """设置项目时间线（用于节拍/秒转换）"""
        with self._lock:
            self._timeline = timeline
            self._state.timeline = timeline

            if timeline:
                # 同步速度到引擎
                self._engine.set_bpm(timeline.tempo)
                print(
                    f"DawDreamerTransport: Timeline set (tempo={timeline.tempo} BPM)"
                )

    # ========================================================================
    # ITransport 接口实现
    # ========================================================================

    def play(self) -> None:
        """开始或恢复播放"""
        if self._is_playing:
            print("DawDreamerTransport: Already playing")
            return

        try:
            # 创建音频流
            self._stream = sd.OutputStream(samplerate=self._sample_rate,
                                           blocksize=self._block_size,
                                           channels=2,
                                           dtype='float32',
                                           callback=self._audio_callback)

            # 启动流
            self._stream.start()
            self._is_playing = True

            print(
                f"DawDreamerTransport: Playback started at beat {self.get_playback_position_beats():.2f}"
            )

        except Exception as e:
            print(f"DawDreamerTransport Error: Failed to start playback: {e}")
            self._is_playing = False

    def stop(self) -> None:
        """停止播放并回到开头"""
        if not self._is_playing or not self._stream:
            return

        try:
            # 停止并关闭流
            self._stream.stop()
            self._stream.close()
            self._stream = None
            self._is_playing = False

            # 重置播放位置
            with self._lock:
                self._current_sample = 0
                self._engine.set_transport_sample_position(0)

            print("DawDreamerTransport: Playback stopped")

        except Exception as e:
            print(f"DawDreamerTransport Error: Failed to stop playback: {e}")

    @property
    def is_playing(self) -> bool:
        """是否正在播放"""
        return self._is_playing

    def set_playback_position_beats(self, position_beats: float) -> None:
        """设置播放位置（节拍）"""
        if not self._timeline:
            print("DawDreamerTransport Warning: No timeline set")
            return

        with self._lock:
            # 转换节拍到样本
            seconds = self._timeline.beats_to_seconds(position_beats)
            self._current_sample = int(seconds * self._sample_rate)

            # 同步到引擎
            self._engine.set_transport_sample_position(self._current_sample)

        print(
            f"DawDreamerTransport: Position set to beat {position_beats:.2f}")

    def get_playback_position_beats(self) -> float:
        """获取当前播放位置（节拍）"""
        if not self._timeline:
            return 0.0

        with self._lock:
            seconds = self._current_sample / self._sample_rate
            return self._timeline.seconds_to_beats(seconds)

    def enable_looping(self, is_enabled: bool) -> None:
        """启用或禁用循环"""
        with self._lock:
            self._is_loop_enabled = is_enabled

        status = "enabled" if is_enabled else "disabled"
        print(f"DawDreamerTransport: Looping {status}")

    def set_loop_range_beats(self, start_beats: float,
                             end_beats: float) -> None:
        """设置循环范围（节拍）"""
        if end_beats <= start_beats:
            print("DawDreamerTransport Warning: Invalid loop range")
            return

        with self._lock:
            self._loop_start_beat = start_beats
            self._loop_end_beat = end_beats

        print(
            f"DawDreamerTransport: Loop range set to {start_beats:.2f} - {end_beats:.2f} beats"
        )

    def get_loop_range_beats(self) -> Tuple[float, float]:
        """获取循环范围（节拍）"""
        with self._lock:
            return (self._loop_start_beat, self._loop_end_beat)

    # ========================================================================
    # 音频回调（实时音频处理）
    # ========================================================================

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info,
                        status):
        """
        音频回调函数（由sounddevice调用）
        
        这是实时音频处理的核心
        必须保证低延迟和无阻塞
        """
        if status:
            print(f"Sounddevice status: {status}")

        try:
            # 1. 处理所有待处理的消息
            self._process_messages()

            # 2. 渲染音频
            self._engine.render(frames)

            # 3. 获取音频数据
            audio, _, _ = self._engine.get_audio('master_out')

            if audio is not None and audio.shape[1] >= frames:
                # 转置并复制到输出缓冲区
                # DawDreamer: (channels, samples)
                # sounddevice: (samples, channels)
                outdata[:] = audio[:, :frames].T
            else:
                # 没有音频，输出静音
                outdata.fill(0)

            # 4. 更新播放位置
            with self._lock:
                self._current_sample += frames

                # 5. 检查循环
                if self._is_loop_enabled and self._timeline:
                    current_beat = self.get_playback_position_beats()

                    if current_beat >= self._loop_end_beat:
                        # 回到循环起点
                        self.set_playback_position_beats(self._loop_start_beat)

        except Exception as e:
            # 实时线程中的错误处理
            # 输出静音并记录错误
            outdata.fill(0)
            print(f"Audio Thread Error: {e}")

    def _process_messages(self):
        """
        处理所有待处理的消息
        
        这在每个音频块之前调用
        """
        self._queue.drain(lambda msg: self._message_handler.handle(
            msg, self._engine, self._state))

    # ========================================================================
    # 调试和监控
    # ========================================================================

    def get_engine_info(self) -> Dict:
        """获取引擎信息（用于调试）"""
        return {
            "sample_rate": self._sample_rate,
            "block_size": self._block_size,
            "is_playing": self._is_playing,
            "current_beat": self.get_playback_position_beats(),
            "loop_enabled": self._is_loop_enabled,
            "processor_count": len(self._state.node_id_to_processor_name)
        }

    def __del__(self):
        """析构函数 - 确保资源释放"""
        if self._is_playing:
            self.stop()
