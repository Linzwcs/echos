import numpy as np
import threading
import queue
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import time

try:
    import pedalboard as pb
    from pedalboard import Pedalboard, VST3Plugin, AudioUnitPlugin
    PEDALBOARD_AVAILABLE = True
except ImportError:
    PEDALBOARD_AVAILABLE = False
    print(
        "Warning: pedalboard not available. Install with: pip install pedalboard"
    )

from ...interfaces.system import IEngine, ITimeline
from ...models import TransportStatus, TransportContext
from ...models.event_model import *
from ..common.message_queue import RealTimeMessageQueue
from .sync_controller import PedalboardSyncController
from .render_graph import PedalboardRenderGraph


@dataclass
class AudioMessage:
    """实时音频线程消息"""
    type: str  # "graph_update", "transport", "parameter"
    data: dict


class PedalboardEngine(IEngine):
    """
    基于 Pedalboard 的音频引擎
    
    职责：
    1. 管理实时音频处理线程
    2. 维护 Pedalboard 处理图
    3. 处理音频回调
    4. 同步前端状态到音频线程
    """

    def __init__(
        self,
        sample_rate: int = 48000,
        block_size: int = 512,
        output_channels: int = 2,
    ):
        super().__init__()

        if not PEDALBOARD_AVAILABLE:
            raise RuntimeError("Pedalboard library not available")

        self._sample_rate = sample_rate
        self._block_size = block_size
        self._output_channels = output_channels

        # 组件
        self._sync_controller = PedalboardSyncController()
        self._render_graph = PedalboardRenderGraph(sample_rate, block_size)
        self._timeline: Optional[ITimeline] = None

        # 状态
        self._status = TransportStatus.STOPPED
        self._current_beat = 0.0
        self._is_running = False

        # 线程通信
        self._message_queue = RealTimeMessageQueue()
        self._audio_thread: Optional[threading.Thread] = None
        self._audio_lock = threading.RLock()

        # 音频缓冲
        self._output_buffer = np.zeros((output_channels, block_size),
                                       dtype=np.float32)

        print(
            f"PedalboardEngine initialized: {sample_rate}Hz, {block_size} samples"
        )

    # ========================================================================
    # IEngine 接口实现
    # ========================================================================

    @property
    def sync_controller(self) -> PedalboardSyncController:
        return self._sync_controller

    @property
    def timeline(self) -> ITimeline:
        return self._timeline

    def set_timeline(self, timeline: ITimeline):
        """设置时间线引用"""
        self._timeline = timeline
        print(f"PedalboardEngine: Timeline set (tempo={timeline.tempo}BPM)")

    def play(self):
        """开始播放"""
        if self._status == TransportStatus.PLAYING:
            return

        self._status = TransportStatus.PLAYING

        # 发送播放消息到音频线程
        self._message_queue.push(
            AudioMessage(type="transport", data={"action": "play"}))

        # 启动音频线程（如果未运行）
        if not self._is_running:
            self._start_audio_thread()

        print("PedalboardEngine: Playback started")

    def stop(self):
        """停止播放"""
        if self._status == TransportStatus.STOPPED:
            return

        self._status = TransportStatus.STOPPED
        self._current_beat = 0.0

        self._message_queue.push(
            AudioMessage(type="transport", data={"action": "stop"}))

        print("PedalboardEngine: Playback stopped")

    def report_latency(self) -> float:
        """报告总延迟"""
        # 硬件延迟 + 插件延迟
        hardware_latency = self._block_size / self._sample_rate
        plugin_latency = self._render_graph.get_total_latency(
        ) / self._sample_rate
        return hardware_latency + plugin_latency

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

    # ========================================================================
    # 生命周期管理
    # ========================================================================

    def _get_children(self) -> List:
        return [self._sync_controller]

    def _on_mount(self, event_bus):
        """挂载到事件总线"""
        self._event_bus = event_bus

        # 挂载同步控制器
        self._sync_controller.mount(event_bus)

        # 连接同步控制器到渲染图
        self._sync_controller.set_render_graph(self._render_graph)

        print("PedalboardEngine: Mounted to event bus")

    def _on_unmount(self):
        """从事件总线卸载"""
        self._stop_audio_thread()
        self._sync_controller.unmount()
        self._event_bus = None
        print("PedalboardEngine: Unmounted")

    # ========================================================================
    # 音频线程管理
    # ========================================================================

    def _start_audio_thread(self):
        """启动音频处理线程"""
        if self._is_running:
            return

        self._is_running = True
        self._audio_thread = threading.Thread(
            target=self._audio_processing_loop,
            name="PedalboardAudioThread",
            daemon=True)
        self._audio_thread.start()
        print("PedalboardEngine: Audio thread started")

    def _stop_audio_thread(self):
        """停止音频处理线程"""
        if not self._is_running:
            return

        self._is_running = False

        if self._audio_thread:
            self._audio_thread.join(timeout=2.0)
            self._audio_thread = None

        print("PedalboardEngine: Audio thread stopped")

    def _audio_processing_loop(self):
        """
        音频处理主循环（实时线程）
        
        这是一个简化的实现。在生产环境中，这应该由：
        - PortAudio/JACK 音频回调驱动
        - 或者 sounddevice 的流回调
        """
        print("PedalboardEngine: Audio processing loop started")

        # 计算每个块的时间
        block_time = self._block_size / self._sample_rate

        try:
            while self._is_running:
                loop_start = time.perf_counter()

                # 1. 处理消息队列（非阻塞）
                self._message_queue.drain(self._handle_audio_message)

                # 2. 如果正在播放，处理音频
                if self._status == TransportStatus.PLAYING:
                    self._process_audio_block()
                else:
                    # 不播放时生成静音
                    self._output_buffer.fill(0.0)

                # 3. 精确的时间同步
                elapsed = time.perf_counter() - loop_start
                sleep_time = block_time - elapsed

                if sleep_time > 0:
                    time.sleep(sleep_time)
                elif elapsed > block_time * 1.5:
                    # 检测欠载（处理时间过长）
                    print(
                        f"Warning: Audio processing overload! {elapsed*1000:.1f}ms (target: {block_time*1000:.1f}ms)"
                    )

        except Exception as e:
            print(f"PedalboardEngine: Audio thread error: {e}")
            import traceback
            traceback.print_exc()

        print("PedalboardEngine: Audio processing loop ended")

    def _process_audio_block(self):
        """
        处理单个音频块
        
        这是实时音频处理的核心
        """
        with self._audio_lock:
            # 创建传输上下文
            context = TransportContext(
                current_beat=self._current_beat,
                sample_rate=self._sample_rate,
                block_size=self._block_size,
                tempo=self._timeline.tempo if self._timeline else 120.0)

            # 让渲染图处理音频
            self._output_buffer = self._render_graph.process_block(context)

            # 更新播放头位置
            if self._timeline:
                beats_per_sample = (context.tempo / 60.0) / self._sample_rate
                self._current_beat += beats_per_sample * self._block_size

    def _handle_audio_message(self, message: AudioMessage):
        """
        处理来自主线程的消息（在音频线程中）
        
        这些操作必须是实时安全的：
        - 无内存分配
        - 无锁（或极短的锁）
        - 无系统调用
        """
        if message.type == "transport":
            action = message.data.get("action")
            if action == "play":
                # 已在主线程设置，这里只是确认
                pass
            elif action == "stop":
                self._current_beat = 0.0

        elif message.type == "graph_update":
            # 图更新由 RenderGraph 处理
            pass

        elif message.type == "parameter":
            # 参数更新
            node_id = message.data.get("node_id")
            param_name = message.data.get("param_name")
            value = message.data.get("value")
            # TODO: 应用参数变化
            pass
