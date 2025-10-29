# file: src/MuzaiCore/interfaces/system/itransport.py
from abc import ABC, abstractmethod
from typing import Tuple

class ITransport(ABC):
    """
    Defines the contract for controlling playback, position, and looping.
    This is implemented by each backend.
    """

    @abstractmethod
    def play(self) -> None:
        """Starts or resumes playback from the current position."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops playback and resets the playhead to the start or loop start."""
        pass

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """Returns True if the transport is currently playing."""
        pass

    @abstractmethod
    def set_playback_position_beats(self, position_beats: float) -> None:
        """
        Sets the playback head to a specific position in beats.
        This can be called whether playing or stopped.
        """
        pass

    @abstractmethod
    def get_playback_position_beats(self) -> float:
        """Gets the current playback head position in beats."""
        pass

    @abstractmethod
    def enable_looping(self, is_enabled: bool) -> None:
        """Enables or disables the loop range."""
        pass

    @abstractmethod
    def set_loop_range_beats(self, start_beats: float, end_beats: float) -> None:
        """Sets the loop range in beats."""
        pass

    @abstractmethod
    def get_loop_range_beats(self) -> Tuple[float, float]:
        """Gets the current loop range as a (start, end) tuple in beats."""
        pass