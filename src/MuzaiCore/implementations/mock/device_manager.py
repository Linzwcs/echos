# file: src/MuzaiCore/implementations/mock/device_manager.py
from typing import List
from ...interfaces import IDeviceManager
from ...models.device_model import AudioDevice, MIDIDevice, IOChannel


class MockDeviceManager(IDeviceManager):
    """A mock device manager with pre-defined virtual hardware."""

    def __init__(self):
        self._audio_devices: List[AudioDevice] = []
        self._midi_devices: List[MIDIDevice] = []

    def scan_devices(self):
        print("MockDeviceManager: Scanning for virtual I/O devices...")
        # Mock Audio Device
        mock_audio_inputs = [
            IOChannel("in_1", "Input 1"),
            IOChannel("in_2", "Input 2")
        ]
        mock_audio_outputs = [
            IOChannel("out_1", "Main Out L"),
            IOChannel("out_2", "Main Out R")
        ]
        self._audio_devices = [
            AudioDevice("mock_audio_interface", "Mock Audio Interface",
                        mock_audio_inputs, mock_audio_outputs)
        ]
        # Mock MIDI Device
        self._midi_devices = [
            MIDIDevice("mock_midi_keyboard", "Mock MIDI Keyboard")
        ]
        print(
            f"MockDeviceManager: Found {len(self._audio_devices)} audio and {len(self._midi_devices)} MIDI devices."
        )

    def get_audio_input_devices(self) -> List[AudioDevice]:
        return self._audio_devices

    def get_audio_output_devices(self) -> List[AudioDevice]:
        return self._audio_devices

    def get_midi_input_devices(self) -> List[MIDIDevice]:
        return self._midi_devices

    def set_active_audio_device(self, device_id: str, sample_rate: int,
                                block_size: int):
        print(
            f"MockDeviceManager: Setting active device to {device_id} with SR={sample_rate}, BS={block_size}. (No-op in mock)"
        )
