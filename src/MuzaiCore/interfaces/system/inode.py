from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from .iaudio_processor import IAudioProcessor
from .imixer_channel import IMixerChannel
from ...models import Port, TrackRecordMode


class INode(IAudioProcessor, ABC):

    @property
    @abstractmethod
    def node_id(self) -> str:
        pass

    @abstractmethod
    def get_ports(self, port_type: Optional[str] = None) -> List[Port]:
        pass


class IPlugin(INode, ABC):
    # IPlugin inherits node_id and process_block from INode
    @abstractmethod
    def get_latency_samples(self) -> int:
        """Returns the processing latency introduced by the plugin in samples."""
        pass


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
    def mixer_channel(self) -> "IMixerChannel":  # <-- The key change
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
    def record_mode(self) -> "TrackRecordMode":
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
