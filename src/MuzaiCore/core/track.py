# file: src/MuzaiCore/core/track.py
import uuid
from typing import List, Optional, Dict
from enum import Enum
import numpy as np
from .parameter import Parameter

from .mixer import MixerChannel
from ..interfaces import ITrack, IParameter, IMixerChannel

from ..models import Port, PortType, PortDirection
from ..models.clip_model import AnyClip


class TrackRecordMode(Enum):
    """录音模式"""
    NORMAL = "normal"  # 标准录音
    OVERDUB = "overdub"  # 叠加录音
    REPLACE = "replace"  # 替换录音
    LOOP = "loop"  # 循环录音


class Track(ITrack):
    """
    所有轨道类型的基类
    轨道主要负责时间线数据（片段）的容器
    所有信号处理委托给其关联的混音器通道
    """

    def __init__(self, name: str, node_id: Optional[str] = None):

        self.clips: List[AnyClip] = []

        self._node_id = node_id or str(uuid.uuid4())
        self._name = name
        # 组合：每个轨道拥有一个混音器通道
        self._mixer_channel: IMixerChannel = MixerChannel()

        # 录音相关
        self._is_armed = False
        self._record_mode = TrackRecordMode.NORMAL
        self._input_source_id: Optional[str] = None

        # 轨道冻结（用于节省CPU）
        self._is_frozen = False
        self._frozen_audio_path: Optional[str] = None

        # 轨道颜色和图标（用于UI）
        self.color: Optional[str] = None  # 例如 "#FF5733"
        self.icon: Optional[str] = None

        # 端口由轨道拥有，因为它是主要的可路由实体
        self._input_ports: List[Port] = []
        self._output_ports: List[Port] = []

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def mixer_channel(self) -> IMixerChannel:
        """返回关联的混音器通道"""
        return self._mixer_channel

    @property
    def is_armed(self) -> bool:
        return self._is_armed

    @property
    def record_mode(self) -> TrackRecordMode:
        return self._record_mode

    @property
    def input_source_id(self) -> str:
        return self._input_source_id or ""

    @property
    def is_frozen(self) -> bool:
        return self._is_frozen

    @property
    def name(self) -> str:
        return self._name

    def set_armed(self, armed: bool):
        self._is_armed = armed
        self._mixer_channel.is_record_enabled = armed
        print(f"Track '{self.name}' armed: {armed}")

    def set_record_mode(self, mode: TrackRecordMode):
        self._record_mode = mode
        print(f"Track '{self.name}' record mode: {mode.value}")

    def set_input_source(self, source_id: str):
        """设置此轨道监听的硬件输入通道"""
        self._input_source_id = source_id
        print(f"Track '{self.name}' input source: {source_id}")

    def set_frozen(self, frozen: bool, flatten: bool = False):
        """
        冻结/解冻轨道
        frozen: 是否冻结
        flatten: 如果为True，则永久应用冻结（破坏性操作）
        """
        self._is_frozen = frozen
        if frozen:
            if flatten:
                print(
                    f"Track '{self.name}' frozen and flattened (destructive)")
                # 在真实实现中，这里会永久渲染音频并移除插件
            else:
                print(f"Track '{self.name}' frozen (non-destructive)")
                # 渲染音频但保留插件状态
        else:
            print(f"Track '{self.name}' unfrozen")
            self._frozen_audio_path = None

    def get_parameters(self) -> Dict[str, IParameter]:
        """
        获取此轨道的所有参数
        主要是其关联混音器通道的参数
        """
        return self._mixer_channel.get_parameters()

    def get_ports(self, port_type: Optional[PortType] = None) -> List[Port]:
        all_ports = self._input_ports + self._output_ports
        if port_type:
            return [p for p in all_ports if p.port_type == port_type]
        return all_ports

    def process_block(self, input_buffer, midi_events, context):
        """
        轨道的主处理函数
        1. 生成源信号（来自片段或输入）
        2. 将信号传递给混音器通道进行处理
        """
        # 如果轨道被冻结，直接返回冻结的音频
        if self._is_frozen and self._frozen_audio_path:
            return self._read_frozen_audio(context)

        # 步骤1：生成源信号（由子类实现具体逻辑）
        source_signal, source_midi = self._generate_source_signal(
            input_buffer, midi_events, context)

        # 步骤2：将所有混音和处理委托给混音器通道

        return self.mixer_channel.process_block(source_signal, source_midi,
                                                context)

    def _generate_source_signal(self, input_buffer, midi_events, context):
        """
        子类实现的抽象方法，用于生成源信号
        默认情况下是直通
        """
        return input_buffer, midi_events

    def _read_frozen_audio(self, context):
        """读取冻结的音频文件"""
        # 在真实实现中，这里会从磁盘读取预渲染的音频
        print(f"      -> Track '{self.name}': Reading frozen audio")
        # 修正：返回一个正确形状的静音缓冲区，而不是字符串。
        return np.zeros((context.block_size, 2), dtype=np.float32)

    def add_clip(self, clip: AnyClip):
        """在轨道上添加片段"""
        self.clips.append(clip)
        print(f"Added clip '{clip.clip_id[:8]}' to track '{self.name}'")

    def remove_clip(self, clip_id: str) -> bool:
        """从轨道移除片段"""
        for i, clip in enumerate(self.clips):
            if clip.clip_id == clip_id:
                self.clips.pop(i)
                print(f"Removed clip {clip_id[:8]} from track '{self.name}'")
                return True
        return False


class InstrumentTrack(Track):
    """
    保存MIDI片段并生成信号的轨道
    其第一个插件通常是虚拟乐器
    """

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

        # 乐器轨道生成MIDI，不从外部接收
        # 但可以接收音频用于侧链
        self._input_ports = [
            Port(self.node_id, "sidechain_in", PortType.AUDIO,
                 PortDirection.INPUT, 2)
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(self, input_buffer, midi_events, context):
        """
        从片段生成MIDI事件
        在真实引擎中，这里会查看self.clips，
        找到当前块中开始的所有MIDI音符，并创建MIDIEvent对象列表
        """

        return input_buffer, midi_events

    def _collect_midi_notes_in_range(self, context):
        """收集当前时间范围内的MIDI音符"""
        from ..models.clip_model import MIDIClip

        notes = []
        current_beat = context.current_beat
        beat_duration = (context.block_size /
                         context.sample_rate) * (context.tempo / 60.0)
        end_beat = current_beat + beat_duration

        for clip in self.clips:
            if isinstance(clip, MIDIClip):
                # 检查片段是否在当前时间范围内
                if clip.start_beat <= end_beat and (
                        clip.start_beat + clip.duration_beats) >= current_beat:
                    # 收集此片段中的音符
                    for note in clip.notes:
                        note_abs_beat = clip.start_beat + note.start_beat
                        if current_beat <= note_abs_beat < end_beat:
                            notes.append(note)

        return notes


class AudioTrack(Track):
    """保存音频片段或接收实时音频输入的轨道"""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
        self._input_ports = [
            Port(self.node_id, "audio_in", PortType.AUDIO, PortDirection.INPUT,
                 2)
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(self, input_buffer, midi_events, context):
        """
        从片段读取音频并与实时输入混合
        在真实引擎中，此方法会从其片段读取音频
        并将其与实时input_buffer混合
        """
        # 读取片段中的音频
        clip_audio = self._read_clips_in_range(context)

        # 混合片段音频和输入音频
        # mixed_audio = clip_audio + input_buffer

        return input_buffer, midi_events

    def _read_clips_in_range(self, context):
        """读取当前时间范围内的音频片段"""
        from ..models.clip_model import AudioClip

        # 在真实实现中，这里会从磁盘读取音频文件
        # 并根据时间位置、增益、warping等进行处理
        return None


class BusTrack(Track):
    """充当总线/编组的轨道，主要用于子混音"""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
        # 总线只有音频输入和输出，不保存片段
        self.clips = []
        self._input_ports = [
            Port(self.node_id, "audio_in", PortType.AUDIO, PortDirection.INPUT,
                 8)  # 支持更多输入通道
        ]
        self._output_ports = [
            Port(self.node_id, "audio_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

    def _generate_source_signal(self, input_buffer, midi_events, context):
        """总线只处理路由到它的音频，不生成自己的信号"""
        return input_buffer, []


class VCATrack(Track):
    """
    不处理音频但控制其他混音器通道推子的特殊轨道
    它是一个节点，但其process_block不做任何事情
    """

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)
        # VCA轨道没有端口和片段
        self._input_ports = []
        self._output_ports = []
        self.clips = []

        # VCA控制的通道列表
        self._controlled_channels: List[str] = []

    def add_controlled_channel(self, channel_id: str):
        """添加由此VCA控制的通道"""
        if channel_id not in self._controlled_channels:
            self._controlled_channels.append(channel_id)
            print(f"VCA '{self.name}' now controls channel {channel_id[:8]}")

    def remove_controlled_channel(self, channel_id: str):
        """移除由此VCA控制的通道"""
        if channel_id in self._controlled_channels:
            self._controlled_channels.remove(channel_id)
            print(
                f"VCA '{self.name}' no longer controls channel {channel_id[:8]}"
            )

    def get_controlled_channels(self) -> List[str]:
        return self._controlled_channels.copy()

    def process_block(self, input_buffer, midi_events, context):
        """
        VCA推子不处理音频。它们的影响是在
        音频引擎处理受控轨道的推子阶段计算的
        """
        # VCA的音量参数会在引擎中被读取并应用到受控通道
        return None


class MasterTrack(BusTrack):
    """
    主输出轨道
    这是信号链的最终输出点
    """

    def __init__(self, name: str = "Master", node_id: Optional[str] = None):
        super().__init__(name, node_id)
        # 主轨道有专门的输出到硬件
        self._output_ports = [
            Port(self.node_id, "hardware_out", PortType.AUDIO,
                 PortDirection.OUTPUT, 2)
        ]

        # 主轨道通常有内置的限制器或最大化器
        self.has_builtin_limiter = True
        self.limiter_threshold = Parameter("limiter_threshold", -0.3)
