# file: src/MuzaiCore/interfaces/IAudioEngine.py
from abc import ABC, abstractmethod
from typing import List
import numpy as np
from .iproject import IProject
from .ilifecycle import ILifecycleAware
from .isync import ISyncController
from .ievent_bus import IEventBus
from .itimeline import ITimeline


class IEngine(ILifecycleAware, ABC):
    """
    音频引擎的接口，定义了播放、停止和处理音频块的核心功能。
    """

    @property
    @abstractmethod
    def sync_controller(self) -> ISyncController:
        pass

    @property
    @abstractmethod
    def timeline(self) -> ITimeline:
        pass

    @abstractmethod
    def set_timeline(self, timeline: ITimeline):
        pass

    @abstractmethod
    def play(self):
        """开始播放。"""
        pass

    @abstractmethod
    def stop(self):
        """停止播放并回到开头。"""
        pass

        pass

    @abstractmethod
    def report_latency(self) -> float:
        """
        报告总延迟（以秒为单位）。
        这包括硬件延迟、插件延迟等。
        """
        pass

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """返回引擎是否正在播放。"""
        pass

    @property
    @abstractmethod
    def current_beat(self) -> float:
        """返回当前播放头的节拍位置。"""
        pass

    @property
    @abstractmethod
    def block_size(self) -> bool:
        """返回引擎是否正在播放。"""
        pass

    @property
    @abstractmethod
    def sample_rate(self) -> float:
        """返回当前播放头的节拍位置。"""
        pass

    @property
    @abstractmethod
    def transport_status(self) -> float:
        """返回当前播放头的节拍位置。"""
        pass

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self) -> List[ILifecycleAware]:
        return [self.sync_controller]
