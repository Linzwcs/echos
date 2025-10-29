# file: src/MuzaiCore/core/mixer.py
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import uuid
import numpy as np
from dataclasses import dataclass, field

from .parameter import Parameter
from .plugin import Plugin
from ..interfaces.system.isync import IMixerSync
from ..interfaces.system import IParameter, IMixerChannel, IPlugin
from ..models import NotePlaybackInfo, TransportContext


@dataclass
class Send:
    """表示从一个通道到总线的发送"""
    send_id: str
    target_bus_node_id: str
    level: Parameter = field(
        default_factory=lambda: Parameter("send_level", -100.0))  # 默认静音
    is_post_fader: bool = True  # 默认推子后发送
    is_enabled: bool = True


class MixerChannel(IMixerChannel):
    """
    混音器通道条的具体实现
    处理完整的信号链：输入增益 -> 插入效果 -> 发送 -> 推子 -> 输出
    """

    def __init__(self, channel_id: Optional[str] = None):
        self._channel_id = channel_id or str(uuid.uuid4())

        self._volume = Parameter("volume", -6.0)  # dB
        self._pan = Parameter("pan", 0.0)  # -1.0 (L) 到 +1.0 (R)
        self.input_gain = Parameter("input_gain", 0.0)  # dB

        self.is_muted = False
        self.is_solo = False
        self.is_record_enabled = False

        self.phase_inverted = False
        self.stereo_width = Parameter("stereo_width", 1.0)  # 0.0-2.0

        # 插入效果链
        self._inserts: List[IPlugin] = []

        # 发送列表
        self._sends: List[Send] = []

        # 分组和VCA控制
        self._group_id: Optional[str] = None
        self._vca_controller_id: Optional[str] = None

        # 自动化模式
        self.automation_mode = "read"  # read, write, touch, latch, off

    @property
    def channel_id(self) -> str:
        """获取通道的唯一ID"""
        return self._channel_id

    @property
    def volume(self) -> IParameter:
        """获取通道的音量参数对象 (推子)"""
        return self._volume

    @property
    def pan(self) -> IParameter:
        """获取通道的声像参数对象"""
        return self._pan

    @property
    def inserts(self) -> List[IPlugin]:
        """获取此通道上的插入效果列表"""
        return self._inserts

    @property
    def sends(self) -> List[Send]:
        """获取此通道上的发送列表"""
        return self._sends

    @property
    def group_id(self) -> Optional[str]:
        """获取此通道所属的编组ID"""
        return self._group_id

    @property
    def vca_controller_id(self) -> Optional[str]:
        """获取控制此通道的VCA控制器ID"""
        return self._vca_controller_id

    def get_parameters(self) -> Dict[str, IParameter]:
        """获取此通道的所有参数，包括插件和发送的参数"""
        params = {
            "volume": self.volume,
            "pan": self.pan,
            "input_gain": self.input_gain,
            "stereo_width": self.stereo_width
        }

        # 添加插入效果的参数
        for i, plugin in enumerate(self._inserts):
            for p_name, p_obj in plugin.get_parameters().items():
                params[f"insert_{i}_{p_name}"] = p_obj

        # 添加发送的参数
        for i, send in enumerate(self._sends):
            params[f"send_{i}_level"] = send.level

        return params

    def process_block(self, input_buffer: np.ndarray,
                      midi_events: List[NotePlaybackInfo],
                      context: TransportContext) -> Optional[np.ndarray]:
        """
        处理通道条的完整信号链
        
        信号流程：
        1. 输入增益
        2. 插入效果（串行）
        3. 推子前发送
        4. 推子（音量和声像）
        5. 推子后发送
        6. 输出
        """
        if self.is_muted:
            return np.zeros_like(
                input_buffer
            ) if input_buffer is not None else None  # 静音时返回静音信号

        # 1. 应用输入增益
        processed_buffer = self._apply_input_gain(input_buffer, context)

        # 2. 处理插入效果
        for plugin in self._inserts:
            if plugin.is_enabled:
                processed_buffer = plugin.process_block(
                    processed_buffer, midi_events, context)

        # 3. 处理推子前发送
        pre_fader_sends = [
            s for s in self._sends if not s.is_post_fader and s.is_enabled
        ]
        self._process_sends(pre_fader_sends, processed_buffer, context)

        # 4. 应用推子（音量和声像）
        final_output = self._apply_fader(processed_buffer, context)

        # 5. 处理推子后发送
        post_fader_sends = [
            s for s in self._sends if s.is_post_fader and s.is_enabled
        ]
        self._process_sends(post_fader_sends, final_output, context)

        return final_output

    def _apply_input_gain(self, buffer: Optional[np.ndarray],
                          context: TransportContext) -> Optional[np.ndarray]:
        """应用输入增益"""
        if buffer is None:
            return None

        gain_db = self.input_gain.get_value_at(context)

        print(f"        Applying input gain: {gain_db:.2f} dB to buffer")
        return buffer

    def _apply_fader(self, buffer: Optional[np.ndarray],
                     context: TransportContext) -> Optional[np.ndarray]:
        """应用音量和声像"""
        if buffer is None:
            return None

        volume_db = self.volume.get_value_at(context)
        pan_value = self.pan.get_value_at(context)

        print(
            f"        Applying fader: Volume={volume_db:.2f} dB, Pan={pan_value:.2f}"
        )
        return buffer  # 返回应用声像后的缓冲区 panned_buffer

    def _apply_panning(self, buffer: np.ndarray,
                       pan_value: float) -> np.ndarray:

        return buffer

    def _process_sends(self, sends: List[Send], buffer: Optional[np.ndarray],
                       context: TransportContext):
        """处理发送到总线"""
        if buffer is None:
            return

        for send in sends:
            send_level_db = send.level.get_value_at(context)
            # 在真实实现中:
            # send_gain = 10 ** (send_level_db / 20.0)
            # send_buffer = buffer * send_gain
            # context.get_bus(send.target_bus_node_id).add_to_buffer(send_buffer)

            print(
                f"        Sending to bus {send.target_bus_node_id[:8]}: {send_level_db:.2f} dB"
            )

    def subscribe(self, listener: IMixerSync):
        """订阅混音器事件"""
        if listener not in self._mixer_listeners:
            self._mixer_listeners.append(listener)

    def add_insert(self, plugin: Plugin, index: Optional[int] = None):
        if index is None:
            self._inserts.append(plugin)
            actual_index = len(self._inserts) - 1
        else:
            self._inserts.insert(index, plugin)
            actual_index = index

        for listener in self._mixer_listeners:
            listener.on_insert_added(self._channel_id, plugin, actual_index)

    def remove_insert(self, plugin_instance_id: str) -> bool:
        for i, plugin in enumerate(self._inserts):
            if plugin.node_id == plugin_instance_id:
                removed_plugin = self._inserts.pop(i)
                for listener in self._mixer_listeners:
                    listener.on_insert_removed(self._channel_id,
                                               plugin_instance_id)
                return True
        return False

    def move_insert(self, plugin_instance_id: str, new_index: int) -> bool:
        old_index = -1
        plugin_to_move = None

        for i, plugin in enumerate(self._inserts):
            if plugin.node_id == plugin_instance_id:
                plugin_to_move = plugin
                old_index = i
                break

        if plugin_to_move:
            self._inserts.pop(old_index)
            self._inserts.insert(new_index, plugin_to_move)

            # 通知监听者
            for listener in self._mixer_listeners:
                listener.on_insert_moved(self._channel_id, plugin_instance_id,
                                         old_index, new_index)
            return True
        return False

    def add_send(self,
                 target_bus_node_id: str,
                 is_post_fader: bool = True) -> Send:
        """添加一个到目标总线的发送"""
        new_send = Send(send_id=str(uuid.uuid4()),
                        target_bus_node_id=target_bus_node_id,
                        is_post_fader=is_post_fader)
        self._sends.append(new_send)
        print(
            f"Added {'post' if is_post_fader else 'pre'}-fader send from channel {self.channel_id[:8]} to bus {target_bus_node_id[:8]}"
        )
        return new_send

    def remove_send(self, send_id: str) -> bool:
        """根据ID移除一个发送"""
        for i, send in enumerate(self._sends):
            if send.send_id == send_id:
                self._sends.pop(i)
                print(
                    f"Removed send {send_id[:8]} from channel {self.channel_id[:8]}"
                )
                return True
        print(
            f"Warning: Send {send_id[:8]} not found on channel {self.channel_id[:8]}"
        )
        return False

    def set_group(self, group_id: Optional[str]):
        """将此通道分配到一个编组"""
        self._group_id = group_id
        if group_id:
            print(
                f"Channel {self.channel_id[:8]} assigned to group {group_id[:8]}"
            )
        else:
            print(f"Channel {self.channel_id[:8]} removed from group")

    def set_vca_controller(self, vca_id: Optional[str]):
        """将此通道分配给一个VCA控制器"""
        self._vca_controller_id = vca_id
        if vca_id:
            print(
                f"Channel {self.channel_id[:8]} is now controlled by VCA {vca_id[:8]}"
            )
        else:
            print(f"Channel {self.channel_id[:8]} removed from VCA control")
