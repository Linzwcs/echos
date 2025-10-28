# file: src/MuzaiCore/drivers/real/device_manager.py
"""
Real Device Manager
===================
管理真实的音频和MIDI硬件设备

使用sounddevice和python-rtmidi进行设备发现和管理
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
from ...models.device_model import AudioDevice, MIDIDevice, IOChannel


class RealDeviceManager(IDeviceManager):
    """
    真实设备管理器
    
    功能：
    1. 扫描系统音频设备
    2. 扫描MIDI输入/输出设备
    3. 配置活动设备
    4. 查询设备能力
    """

    def __init__(self):
        self._audio_devices: List[AudioDevice] = []
        self._midi_devices: List[MIDIDevice] = []
        self._active_audio_device_id: Optional[str] = None
        self._active_sample_rate: int = 48000
        self._active_block_size: int = 512

    def scan_devices(self):
        """扫描所有可用的音频和MIDI设备"""
        print("RealDeviceManager: Scanning for hardware devices...")

        self._scan_audio_devices()
        self._scan_midi_devices()

        print(
            f"RealDeviceManager: Found {len(self._audio_devices)} audio devices"
        )
        print(
            f"RealDeviceManager: Found {len(self._midi_devices)} MIDI devices")

    def _scan_audio_devices(self):
        """扫描音频设备"""
        self._audio_devices.clear()

        try:
            devices = sd.query_devices()

            for idx, device_info in enumerate(devices):

                input_channels = []
                for ch in range(device_info['max_input_channels']):
                    input_channels.append(
                        IOChannel(id=f"in_{ch}", name=f"Input {ch + 1}"))

                output_channels = []
                for ch in range(device_info['max_output_channels']):
                    output_channels.append(
                        IOChannel(id=f"out_{ch}", name=f"Output {ch + 1}"))

                # 只添加有输入或输出的设备
                if input_channels or output_channels:
                    audio_device = AudioDevice(id=str(idx),
                                               name=device_info['name'],
                                               input_channels=input_channels,
                                               output_channels=output_channels)
                    self._audio_devices.append(audio_device)

                    # 显示设备信息
                    print(f"  Audio: {device_info['name']}")
                    print(f"    - Inputs: {device_info['max_input_channels']}")
                    print(
                        f"    - Outputs: {device_info['max_output_channels']}")
                    print(
                        f"    - Sample Rate: {device_info['default_samplerate']}Hz"
                    )

        except Exception as e:
            print(f"RealDeviceManager: Error scanning audio devices: {e}")

    def _scan_midi_devices(self):
        """扫描MIDI设备"""
        self._midi_devices.clear()

        if not RTMIDI_AVAILABLE:
            print("  MIDI: python-rtmidi not available, skipping MIDI scan")
            return

        try:
            # 扫描MIDI输入
            midi_in = rtmidi.MidiIn()
            port_count = midi_in.get_port_count()

            for i in range(port_count):
                port_name = midi_in.get_port_name(i)
                midi_device = MIDIDevice(id=f"midi_in_{i}", name=port_name)
                self._midi_devices.append(midi_device)
                print(f"  MIDI In: {port_name}")

            # 扫描MIDI输出
            midi_out = rtmidi.MidiOut()
            port_count = midi_out.get_port_count()

            for i in range(port_count):
                port_name = midi_out.get_port_name(i)
                # 检查是否已经添加（某些设备同时有输入和输出）
                if not any(d.name == port_name for d in self._midi_devices):
                    midi_device = MIDIDevice(id=f"midi_out_{i}",
                                             name=port_name)
                    self._midi_devices.append(midi_device)
                    print(f"  MIDI Out: {port_name}")

        except Exception as e:
            print(f"RealDeviceManager: Error scanning MIDI devices: {e}")

    def get_audio_input_devices(self) -> List[AudioDevice]:
        """获取所有有输入的音频设备"""
        return [d for d in self._audio_devices if d.input_channels]

    def get_audio_output_devices(self) -> List[AudioDevice]:
        """获取所有有输出的音频设备"""
        return [d for d in self._audio_devices if d.output_channels]

    def get_midi_input_devices(self) -> List[MIDIDevice]:
        """获取所有MIDI输入设备"""
        return self._midi_devices

    def set_active_audio_device(self, device_id: str, sample_rate: int,
                                block_size: int):
        """
        设置活动音频设备
        
        这会影响后续创建的音频引擎实例
        
        Args:
            device_id: 设备ID
            sample_rate: 采样率
            block_size: 缓冲区大小
        """
        # 验证设备存在
        device_exists = any(d.id == device_id for d in self._audio_devices)

        if not device_exists:
            print(f"RealDeviceManager: Device {device_id} not found")
            return

        self._active_audio_device_id = device_id
        self._active_sample_rate = sample_rate
        self._active_block_size = block_size

        print(f"RealDeviceManager: Active device set to {device_id}")
        print(f"  - Sample Rate: {sample_rate}Hz")
        print(f"  - Block Size: {block_size} samples")

        # 在真实实现中，这里可能需要：
        # 1. 验证设备支持这些参数
        # 2. 更新sounddevice的默认设置
        # 3. 通知所有活动的音频引擎

        try:
            sd.default.device = int(device_id)
            sd.default.samplerate = sample_rate
            sd.default.blocksize = block_size
        except Exception as e:
            print(f"RealDeviceManager: Error setting default device: {e}")

    def get_active_device_info(self) -> dict:
        """获取当前活动设备的信息"""
        if not self._active_audio_device_id:
            return {
                'device_id': None,
                'device_name': 'Default',
                'sample_rate': self._active_sample_rate,
                'block_size': self._active_block_size
            }

        device = next((d for d in self._audio_devices
                       if d.id == self._active_audio_device_id), None)

        return {
            'device_id': self._active_audio_device_id,
            'device_name': device.name if device else 'Unknown',
            'sample_rate': self._active_sample_rate,
            'block_size': self._active_block_size,
            'input_channels': len(device.input_channels) if device else 0,
            'output_channels': len(device.output_channels) if device else 0
        }

    def test_audio_device(self, device_id: str, duration: float = 1.0) -> bool:
        """
        测试音频设备
        
        播放一个短的测试音调
        
        Args:
            device_id: 设备ID
            duration: 测试持续时间（秒）
            
        Returns:
            测试是否成功
        """
        try:
            import numpy as np

            # 生成440Hz测试音调
            sample_rate = 48000
            t = np.linspace(0, duration, int(sample_rate * duration))
            test_tone = 0.3 * np.sin(2 * np.pi * 440 * t)

            # 转换为立体声
            stereo_tone = np.column_stack([test_tone, test_tone])

            # 播放
            sd.play(stereo_tone, sample_rate, device=int(device_id))
            sd.wait()

            print(f"RealDeviceManager: Test tone played on device {device_id}")
            return True

        except Exception as e:
            print(f"RealDeviceManager: Test failed: {e}")
            return False

    def get_device_latency(self, device_id: str) -> dict:
        """
        获取设备延迟信息
        
        Args:
            device_id: 设备ID
            
        Returns:
            延迟信息字典
        """
        try:
            device_info = sd.query_devices(int(device_id))

            return {
                'input_latency':
                device_info.get('default_low_input_latency', 0) * 1000,  # ms
                'output_latency':
                device_info.get('default_low_output_latency', 0) * 1000,  # ms
                'high_input_latency':
                device_info.get('default_high_input_latency', 0) * 1000,
                'high_output_latency':
                device_info.get('default_high_output_latency', 0) * 1000
            }
        except Exception as e:
            print(f"RealDeviceManager: Error getting latency info: {e}")
            return {}
