# file: src/MuzaiCore/interfaces/IMixerChannel.py
from abc import ABC, abstractmethod
from typing import List, Dict

from typing import Optional
from .iparameter import IParameter
from .iaudio_processor import IAudioProcessor
from .inode import IPlugin
from .isync import IMixerSync


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
    def inserts(self) -> List[IPlugin]:
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

    @abstractmethod
    def add_insert(self, plugin: "IPlugin") -> None:
        """Adds a plugin to the insert chain."""
        pass

    @abstractmethod
    def remove_insert(self, plugin_id: str) -> None:
        """Removes a plugin from the insert chain by its ID."""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, IParameter]:
        pass

    @abstractmethod
    def add_insert(self, plugin: IPlugin, index: Optional[int] = None):
        pass

    @abstractmethod
    def remove_insert(self, plugin_instance_id: str) -> bool:
        pass

    @abstractmethod
    def move_insert(self, plugin_instance_id: str, new_index: int) -> bool:
        pass

    @abstractmethod
    def add_send(self,
                 target_bus_node_id: str,
                 is_post_fader: bool = True) -> "Send":
        pass

    @abstractmethod
    def remove_send(self, send_id: str) -> bool:
        pass

    @abstractmethod
    def set_group(self, group_id: Optional[str]):
        pass

    @abstractmethod
    def set_vca_controller(self, vca_id: Optional[str]):
        pass

    @abstractmethod
    def subscribe(self, listener: IMixerSync):
        pass
