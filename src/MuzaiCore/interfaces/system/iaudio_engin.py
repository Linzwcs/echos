# file: src/MuzaiCore/interfaces/IAudioEngine.py
from abc import ABC, abstractmethod
import numpy as np
from .iproject import IProject


class IAudioEngine(ABC):
    """
    音频引擎的接口，定义了播放、停止和处理音频块的核心功能。
    """

    @abstractmethod
    def set_project(self, project: IProject):
        """将引擎与一个项目关联。"""
        pass

    @abstractmethod
    def play(self):
        """开始播放。"""
        pass

    @abstractmethod
    def stop(self):
        """停止播放并回到开头。"""
        pass

    @abstractmethod
    def render_next_block(self):
        """
        处理下一个音频数据块。
        这是音频处理的核心循环，通常由音频硬件回调函数驱动。
        在我们的模拟中，我们将手动或在一个模拟线程中调用它。
        """
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
