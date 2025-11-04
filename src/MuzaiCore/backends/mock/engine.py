import numpy as np
from .sync_controller import MockSyncController
from ...interfaces.system.iengine import IEngine
from ...interfaces.system.itimeline import ITimeline
from ...models import TransportStatus


class Engine(IEngine):

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
        if self._status != TransportStatus.PLAYING:
            self._status = TransportStatus.PLAYING
            print(
                f"MockEngine: Playback started at beat {self.current_beat:.2f}"
            )

    def stop(self):
        if self._status != TransportStatus.STOPPED:
            self._status = TransportStatus.STOPPED
            self._playhead_position_samples = 0
            print("MockEngine: Playback stopped and playhead reset.")

    def report_latency(self) -> float:
        return 0.0

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
