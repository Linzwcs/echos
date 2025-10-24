# file: src/MuzaiCore/interfaces/ITrack.py
from abc import ABC, abstractmethod
from enum import Enum

from .INode import INode
from .IMixerChannel import IMixerChannel  # <-- Import new interface


class TrackRecordMode(Enum):
    NORMAL = "normal"
    OVERDUB = "overdub"
    REPLACE = "replace"


class ITrack(INode, ABC):
    """
    Represents a track on the timeline, which holds clips.
    It delegates all its signal processing to an associated MixerChannel.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def mixer_channel(self) -> IMixerChannel:  # <-- The key change
        """The associated mixer channel strip for this track."""
        pass

    # Track-specific properties can be added here
    @property
    @abstractmethod
    def is_armed(self) -> bool:
        """Is the track armed for recording?"""
        pass

    # +++ NEW PROPERTIES for professional workflow +++
    @property
    @abstractmethod
    def record_mode(self) -> TrackRecordMode:
        pass

    @property
    @abstractmethod
    def input_source_id(self) -> str:
        """ID of the hardware input channel this track is listening to."""
        pass

    @property
    @abstractmethod
    def is_frozen(self) -> bool:
        pass

    @abstractmethod
    def set_armed(self, armed: bool):
        pass

    @abstractmethod
    def set_frozen(self, frozen: bool, flatten: bool = False):
        """
        Sets the frozen state. If flatten is True, the action is destructive
        and cannot be undone.
        """
        pass
