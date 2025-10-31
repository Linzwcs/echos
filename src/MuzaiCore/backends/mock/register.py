from typing import Optional, List
from ...interfaces.system.iplugin_registry import IPluginRegistry
from ...models import PluginDescriptor, PluginCategory, Port, PortType, PortDirection


class MockPluginRegistry(IPluginRegistry):
    """
    Mock插件注册表
    
    提供一组内置的虚拟插件供测试使用：
    - 乐器：BasicSynth, DrumSampler, ElectricPiano
    - 效果器：Reverb, Delay, Compressor, EQ
    - MIDI效果：Arpeggiator, Chord
    """

    def __init__(self):
        self._plugins: List[PluginDescriptor] = []
        self.scan_for_plugins()

    def scan_for_plugins(self):
        """
        扫描并注册所有Mock插件
        
        在实际应用中，这会扫描系统中的VST/AU插件
        Mock版本只注册预定义的虚拟插件
        """
        self._plugins.clear()
        self._register_mock_plugins()
        print(
            f"MockPluginRegistry: Registered {len(self._plugins)} mock plugins"
        )

    def _register_mock_plugins(self):
        """注册所有Mock插件"""

        # ========================================================================
        # 乐器插件
        # ========================================================================

        # 1. 基础合成器
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.basic_synth",
                name="Basic Synthesizer",
                vendor="MuzaiCore",
                meta="Simple subtractive synthesizer",
                category=PluginCategory.INSTRUMENT,
                reports_latency=True,
                latency_samples=0,
                available_ports=[
                    Port(
                        owner_node_id="",  # 会在实例化时填充
                        port_id="midi_in",
                        port_type=PortType.MIDI,
                        direction=PortDirection.INPUT,
                        channel_count=1),
                    Port(owner_node_id="",
                         port_id="audio_out",
                         port_type=PortType.AUDIO,
                         direction=PortDirection.OUTPUT,
                         channel_count=2),
                ],
                default_parameters={
                    "attack": 0.01,  # 秒
                    "decay": 0.1,
                    "sustain": 0.7,  # 0-1
                    "release": 0.3,
                    "cutoff": 1000.0,  # Hz
                    "resonance": 0.3,  # 0-1
                    "oscillator": "saw",  # "sine", "saw", "square", "triangle"
                    "volume": 0.8,  # 0-1
                }))

        # 2. 鼓采样器
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.drum_sampler",
                name="Drum Sampler",
                vendor="MuzaiCore",
                meta="Multi-pad drum sampler with built-in kits",
                category=PluginCategory.INSTRUMENT,
                reports_latency=False,
                latency_samples=0,
                available_ports=[
                    Port("", "midi_in", PortType.MIDI, PortDirection.INPUT, 1),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters={
                    "kit": "electronic",  # "electronic", "acoustic", "808"
                    "kick_volume": 0.8,
                    "snare_volume": 0.7,
                    "hihat_volume": 0.6,
                    "pitch": 0.0,  # -12 to +12 semitones
                    "reverb": 0.2,
                    "compression": 0.5,
                }))

        # 3. 电钢琴
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.electric_piano",
                name="Electric Piano",
                vendor="MuzaiCore",
                meta="Vintage electric piano emulation",
                category=PluginCategory.INSTRUMENT,
                reports_latency=True,
                latency_samples=128,
                available_ports=[
                    Port("", "midi_in", PortType.MIDI, PortDirection.INPUT, 1),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters={
                    "tone": "bright",  # "bright", "warm", "vintage"
                    "tremolo_rate": 5.0,  # Hz
                    "tremolo_depth": 0.3,
                    "chorus": 0.4,
                    "velocity_curve": "linear",
                    "volume": 0.75,
                }))

        # 4. Pad合成器
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.pad_synth",
                name="Pad Synthesizer",
                vendor="MuzaiCore",
                meta="Lush pad sounds for ambient music",
                category=PluginCategory.INSTRUMENT,
                reports_latency=True,
                latency_samples=256,
                available_ports=[
                    Port("", "midi_in", PortType.MIDI, PortDirection.INPUT, 1),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters={
                    "attack": 0.5,
                    "release": 2.0,
                    "brightness": 0.5,
                    "detune": 0.1,
                    "unison": 3,  # 1-8 voices
                    "reverb": 0.6,
                    "volume": 0.7,
                }))

        # ========================================================================
        # 效果器插件
        # ========================================================================

        # 5. 混响
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.reverb",
                name="Reverb",
                vendor="MuzaiCore",
                meta="Algorithmic reverb effect",
                category=PluginCategory.EFFECT,
                reports_latency=True,
                latency_samples=512,
                available_ports=[
                    Port("", "audio_in", PortType.AUDIO, PortDirection.INPUT,
                         2),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters={
                    "room_size": 0.5,  # 0-1
                    "damping": 0.5,
                    "wet": 0.3,  # 干湿比
                    "dry": 0.7,
                    "width": 1.0,  # 立体声宽度
                    "pre_delay": 0.0,  # 毫秒
                }))

        # 6. 延迟
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.delay",
                name="Delay",
                vendor="MuzaiCore",
                meta="Stereo delay with tempo sync",
                category=PluginCategory.EFFECT,
                reports_latency=False,
                latency_samples=0,
                available_ports=[
                    Port("", "audio_in", PortType.AUDIO, PortDirection.INPUT,
                         2),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters={
                    "time_left": 0.25,  # 节拍 (1/4 note)
                    "time_right": 0.5,  # 节拍 (1/2 note)
                    "feedback": 0.3,  # 0-1
                    "wet": 0.3,
                    "dry": 0.7,
                    "filter": 5000.0,  # Hz
                    "sync": True,  # 同步到宿主
                }))

        # 7. 压缩器
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.compressor",
                name="Compressor",
                vendor="MuzaiCore",
                meta="Dynamic range compressor",
                category=PluginCategory.EFFECT,
                reports_latency=True,
                latency_samples=64,
                available_ports=[
                    Port("", "audio_in", PortType.AUDIO, PortDirection.INPUT,
                         2),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters={
                    "threshold": -20.0,  # dB
                    "ratio": 4.0,  # 1:1 to 20:1
                    "attack": 10.0,  # 毫秒
                    "release": 100.0,  # 毫秒
                    "knee": 0.0,  # dB
                    "makeup_gain": 0.0,  # dB
                    "mix": 1.0,  # 0-1 (parallel compression)
                }))

        # 8. 均衡器
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.eq",
                name="EQ",
                vendor="MuzaiCore",
                meta="4-band parametric equalizer",
                category=PluginCategory.EFFECT,
                reports_latency=False,
                latency_samples=0,
                available_ports=[
                    Port("", "audio_in", PortType.AUDIO, PortDirection.INPUT,
                         2),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters={
                    # 低频段
                    "low_freq": 100.0,  # Hz
                    "low_gain": 0.0,  # dB
                    "low_q": 1.0,
                    # 中低频段
                    "mid_low_freq": 500.0,
                    "mid_low_gain": 0.0,
                    "mid_low_q": 1.0,
                    # 中高频段
                    "mid_high_freq": 2000.0,
                    "mid_high_gain": 0.0,
                    "mid_high_q": 1.0,
                    # 高频段
                    "high_freq": 8000.0,
                    "high_gain": 0.0,
                    "high_q": 1.0,
                }))

        # 9. 失真
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.distortion",
                name="Distortion",
                vendor="MuzaiCore",
                meta="Analog-style distortion/overdrive",
                category=PluginCategory.EFFECT,
                reports_latency=False,
                latency_samples=0,
                available_ports=[
                    Port("", "audio_in", PortType.AUDIO, PortDirection.INPUT,
                         2),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters={
                    "drive": 0.5,  # 0-1
                    "tone": 0.5,  # 0-1 (暗-亮)
                    "mix": 1.0,  # 0-1
                    "type": "soft",  # "soft", "hard", "tube", "fuzz"
                    "output_gain": 0.0,  # dB
                }))

        # ========================================================================
        # MIDI效果器
        # ========================================================================

        # 10. 琶音器
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.arpeggiator",
                name="Arpeggiator",
                vendor="MuzaiCore",
                meta="MIDI arpeggiator with multiple patterns",
                category=PluginCategory.MIDI_EFFECT,
                reports_latency=False,
                latency_samples=0,
                available_ports=[
                    Port("", "midi_in", PortType.MIDI, PortDirection.INPUT, 1),
                    Port("", "midi_out", PortType.MIDI, PortDirection.OUTPUT,
                         1),
                ],
                default_parameters={
                    "rate": 0.25,  # 节拍 (1/16 note)
                    "pattern": "up",  # "up", "down", "updown", "random"
                    "octaves": 1,  # 1-4
                    "gate": 0.8,  # 0-1
                    "swing": 0.0,  # 0-1
                }))

        # 11. 和弦生成器
        self._plugins.append(
            PluginDescriptor(
                unique_plugin_id="muzaicore.builtin.chord",
                name="Chord Generator",
                vendor="MuzaiCore",
                meta="Generate chords from single notes",
                category=PluginCategory.MIDI_EFFECT,
                reports_latency=False,
                latency_samples=0,
                available_ports=[
                    Port("", "midi_in", PortType.MIDI, PortDirection.INPUT, 1),
                    Port("", "midi_out", PortType.MIDI, PortDirection.OUTPUT,
                         1),
                ],
                default_parameters={
                    "type": "major",  # "major", "minor", "7th", "9th", "sus4"
                    "voicing": "close",  # "close", "open", "drop2"
                    "inversion": 0,  # 0-3
                    "velocity_curve": 1.0,
                }))

    def get_plugin_descriptor(
            self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        """
        根据ID获取插件描述符
        
        Args:
            unique_plugin_id: 插件唯一标识
            
        Returns:
            PluginDescriptor或None
        """
        for plugin in self._plugins:
            if plugin.unique_plugin_id == unique_plugin_id:
                return plugin
        return None

    def list_plugins(self) -> List[PluginDescriptor]:
        """
        列出所有可用插件
        
        Returns:
            插件描述符列表
        """
        return self._plugins.copy()

    def list_plugins_by_category(
            self, category: PluginCategory) -> List[PluginDescriptor]:
        """
        按类别列出插件
        
        Args:
            category: 插件类别
            
        Returns:
            该类别的插件描述符列表
        """
        return [p for p in self._plugins if p.category == category]
