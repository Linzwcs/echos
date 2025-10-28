# file: src/MuzaiCore/backends/common/device_manager.py
"""
Manages discovery of real audio and MIDI hardware devices.
This is a shared component as it's independent of the audio graph implementation.
"""
import sounddevice as sd
from typing import List, Optional

try:
    import rtmidi
    RTMIDI_AVAILABLE = True
except ImportError:
    RTMIDI_AVAILABLE = False
    print(
        "Warning: python-rtmidi not available. MIDI functionality will be limited."
    )

from ...interfaces import IDeviceManager
from ...models import AudioDevice, MIDIDevice, IOChannel


class DeviceManager(IDeviceManager):
    """
    Real device manager using sounddevice and python-rtmidi.
    """

    def __init__(self):
        self._audio_devices: List[AudioDevice] = []
        self._midi_devices: List[MIDIDevice] = []
        self._active_audio_device_id: Optional[str] = None
        self._active_sample_rate: int = 48000
        self._active_block_size: int = 512

    def scan_devices(self):
        """Scans all available audio and MIDI devices."""
        print("DeviceManager: Scanning for hardware devices...")
        self._scan_audio_devices()
        self._scan_midi_devices()
        print(
            f"DeviceManager: Found {len(self._audio_devices)} audio and {len(self._midi_devices)} MIDI devices."
        )

    def _scan_audio_devices(self):
        self._audio_devices.clear()
        try:
            devices = sd.query_devices()
            for idx, device_info in enumerate(devices):
                if device_info['max_input_channels'] > 0 or device_info[
                        'max_output_channels'] > 0:
                    self._audio_devices.append(
                        AudioDevice(id=str(idx),
                                    name=device_info['name'],
                                    input_channels=[
                                        IOChannel(f"in_{c}", f"Input {c+1}")
                                        for c in range(
                                            device_info['max_input_channels'])
                                    ],
                                    output_channels=[
                                        IOChannel(f"out_{c}", f"Output {c+1}")
                                        for c in range(
                                            device_info['max_output_channels'])
                                    ]))
        except Exception as e:
            print(f"Error scanning audio devices: {e}")

    def _scan_midi_devices(self):
        self._midi_devices.clear()
        if not RTMIDI_AVAILABLE:
            return
        try:
            midi_in = rtmidi.MidiIn()
            for i in range(midi_in.get_port_count()):
                self._midi_devices.append(
                    MIDIDevice(id=f"midi_in_{i}",
                               name=midi_in.get_port_name(i)))
        except Exception as e:
            print(f"Error scanning MIDI devices: {e}")

    def get_audio_input_devices(self) -> List[AudioDevice]:
        return [d for d in self._audio_devices if d.input_channels]

    def get_audio_output_devices(self) -> List[AudioDevice]:
        return [d for d in self._audio_devices if d.output_channels]

    def get_midi_input_devices(self) -> List[MIDIDevice]:
        return self._midi_devices

    def set_active_audio_device(self, device_id: str, sample_rate: int,
                                block_size: int):
        if not any(d.id == device_id for d in self._audio_devices):
            raise ValueError(f"Device with ID {device_id} not found.")
        self._active_audio_device_id = device_id
        self._active_sample_rate = sample_rate
        self._active_block_size = block_size
        print(
            f"Active audio device set to '{device_id}' ({sample_rate}Hz, {block_size} samples)"
        )
