# file: src/MuzaiCore/interfaces/IAudioEngine.py
from abc import ABC, abstractmethod
import numpy as np
from .IProject import IProject


class IAudioEngine(ABC):

    @abstractmethod
    def load_project(self, project: IProject) -> None:
        pass

    @abstractmethod
    def play(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def render_next_block(self) -> np.ndarray:
        pass

    @abstractmethod
    def report_latency(self, node_id: str, latency_in_samples: int):
        """
        A node (like a track hosting a plugin) calls this to report its latency.
        The engine uses this information to calculate overall delay compensation.
        """
        pass
