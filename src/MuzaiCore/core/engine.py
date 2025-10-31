# file: src/MuzaiCore/engine/mock_engine.py
import numpy as np
from ..interfaces.system.iengine import IEngine
from ..interfaces.system.itimeline import ITimeline
from .sync_controller import MockSyncController

from ..models import TransportStatus


class Engine(IEngine):
    """
    IEngine 接口的模拟（Mock）实现，用于测试和开发。
    它模拟了播放控制和时间跟踪，但不执行实际的音频渲染。
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        block_size: int = 512,
    ):
        super().__init__()
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._sync_controller = MockSyncController()
        self._current_beat: int = 0
        self._status: TransportStatus = TransportStatus.STOPPED
        self._timeline = None
        print(
            f"MockEngine initialized: SR={self.sample_rate}, BS={self.block_size}, Tempo= None BPM"
        )

    @property
    def sync_controller(self) -> MockSyncController:
        return self._sync_controller

    @property
    def timeline(self) -> ITimeline:
        return self._timeline

    def set_timeline(self, timeline: ITimeline):
        self._timeline = timeline
        print(
            f"MockEngine initialized: SR={self.sample_rate}, BS={self.block_size}, Tempo={self.timeline.tempo} BPM"
        )

    def play(self):
        """开始模拟播放。"""
        if self._status != TransportStatus.PLAYING:
            self._status = TransportStatus.PLAYING
            print(
                f"MockEngine: Playback started at beat {self.current_beat:.2f}"
            )

    def stop(self):
        """停止模拟播放并将播放头重置为零。"""
        if self._status != TransportStatus.STOPPED:
            self._status = TransportStatus.STOPPED
            self._playhead_position_samples = 0
            print("MockEngine: Playback stopped and playhead reset.")

    def report_latency(self) -> float:
        """报告模拟的总延迟（对于mock总是为0）。"""
        return 0.0

    @property
    def is_playing(self) -> bool:
        """返回引擎是否正在播放。"""
        return self._status == TransportStatus.PLAYING

    @property
    def current_beat(self) -> float:
        return self._current_beat

    @property
    def block_size(self) -> int:
        """返回引擎的块大小（以样本为单位）。"""
        return self._block_size

    @property
    def sample_rate(self) -> int:
        """返回引擎的采样率（以赫兹为单位）。"""
        return self._sample_rate

    @property
    def transport_status(self) -> TransportStatus:
        """返回当前的播放状态（播放/停止）。"""
        return self._status
