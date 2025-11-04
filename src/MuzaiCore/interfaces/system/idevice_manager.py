# file: src/MuzaiCore/interfaces/IDeviceManager.py
from abc import ABC, abstractmethod
from typing import List
from ...models.device_model import AudioDevice, MIDIDevice


class IDeviceManager(ABC):

    @abstractmethod
    def scan_devices(self):
        pass

    @abstractmethod
    def get_audio_input_devices(self) -> List[AudioDevice]:
        pass

    @abstractmethod
    def get_audio_output_devices(self) -> List[AudioDevice]:
        pass

    @abstractmethod
    def get_midi_input_devices(self) -> List[MIDIDevice]:
        pass

    @abstractmethod
    def set_active_audio_device(self, device_id: str, sample_rate: int,
                                block_size: int):
        pass
