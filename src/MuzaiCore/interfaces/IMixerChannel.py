# file: src/MuzaiCore/interfaces/IMixerChannel.py
from abc import ABC, abstractmethod
from typing import List, Dict

from git import Optional
from .IParameter import IParameter
from .IAudioProcessor import IAudioProcessor
from ..core.plugin import PluginInstance


class IMixerChannel(IAudioProcessor, ABC):
    """
    Represents a channel strip in a virtual mixer.
    It handles all signal processing for a track: inserts, sends, fader.
    """

    @property
    @abstractmethod
    def volume(self) -> IParameter:
        pass

    @property
    @abstractmethod
    def pan(self) -> IParameter:
        pass

    @property
    @abstractmethod
    def inserts(self) -> List[PluginInstance]:
        """The list of insert plugins on this channel."""
        pass

    @property
    @abstractmethod
    def sends(self) -> List['Send']:
        """The list of sends on this channel."""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, IParameter]:
        """Gets all parameters for this channel, including plugins."""
        pass

    # +++ NEW PROPERTIES for grouping +++
    @property
    @abstractmethod
    def group_id(self) -> Optional[str]:
        """The ID of the group this channel belongs to."""
        pass

    @property
    @abstractmethod
    def vca_controller_id(self) -> Optional[str]:
        """The ID of the VCATrack controlling this channel."""
        pass
