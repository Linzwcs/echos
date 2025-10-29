# file: src/MuzaiCore/core/mixer.py
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import uuid
import numpy as np

from .parameter import Parameter
from .plugin import Plugin
from ..interfaces.system import IParameter, IMixerChannel, IPlugin, IEventBus  # <-- 新增导入
from ..models import NotePlaybackInfo, TransportContext
from ..models.event_model import InsertAdded, InsertRemoved, InsertMoved  # <-- 新增导入


@dataclass
class Send:
    """表示从一个通道到总线的发送"""
    send_id: str
    target_bus_node_id: str
    level: Parameter
    is_post_fader: bool = True
    is_enabled: bool = True


class MixerChannel(IMixerChannel):
    """
    混音器通道条的具体实现
    """

    def __init__(
            self,
            event_bus: IEventBus,  # <-- 新增
            channel_id: Optional[str] = None):
        self._channel_id = channel_id or str(uuid.uuid4())
        self._event_bus = event_bus  # <-- 新增

        self._volume = Parameter(self._channel_id, "volume", -6.0, event_bus)
        self._pan = Parameter(self._channel_id, "pan", 0.0, event_bus)
        self.input_gain = Parameter(self._channel_id, "input_gain", 0.0,
                                    event_bus)
        self.stereo_width = Parameter(self._channel_id, "stereo_width", 1.0,
                                      event_bus)

        self.is_muted = False
        self.is_solo = False
        self._inserts: List[IPlugin] = []
        self._sends: List[Send] = []
        self._group_id: Optional[str] = None
        self._vca_controller_id: Optional[str] = None
        self.automation_mode = "read"

    @property
    def channel_id(self) -> str:
        return self._channel_id

    @property
    def volume(self) -> IParameter:
        return self._volume

    @property
    def pan(self) -> IParameter:
        return self._pan

    @property
    def inserts(self) -> List[IPlugin]:
        return list(self._inserts)

    @property
    def sends(self) -> List[Send]:
        return list(self._sends)

    @property
    def group_id(self) -> Optional[str]:
        return self._group_id

    @property
    def vca_controller_id(self) -> Optional[str]:
        return self._vca_controller_id

    def get_parameters(self) -> Dict[str, IParameter]:
        params = {
            "volume": self.volume,
            "pan": self.pan,
            "input_gain": self.input_gain,
            "stereo_width": self.stereo_width
        }
        for i, plugin in enumerate(self._inserts):
            for p_name, p_obj in plugin.get_parameters().items():
                params[f"insert_{i}_{p_name}"] = p_obj
        for i, send in enumerate(self._sends):
            params[f"send_{i}_level"] = send.level
        return params

    def process_block(self, input_buffer: np.ndarray,
                      midi_events: List[NotePlaybackInfo],
                      context: TransportContext) -> Optional[np.ndarray]:
        if self.is_muted:
            return np.zeros_like(
                input_buffer) if input_buffer is not None else None

        processed_buffer = self._apply_input_gain(input_buffer, context)
        for plugin in self._inserts:
            if plugin.is_enabled:
                processed_buffer = plugin.process_block(
                    processed_buffer, midi_events, context)

        pre_fader_sends = [
            s for s in self._sends if not s.is_post_fader and s.is_enabled
        ]
        self._process_sends(pre_fader_sends, processed_buffer, context)

        final_output = self._apply_fader(processed_buffer, context)

        post_fader_sends = [
            s for s in self._sends if s.is_post_fader and s.is_enabled
        ]
        self._process_sends(post_fader_sends, final_output, context)

        return final_output

    def _apply_input_gain(self, buffer: Optional[np.ndarray],
                          context: TransportContext) -> Optional[np.ndarray]:
        return buffer

    def _apply_fader(self, buffer: Optional[np.ndarray],
                     context: TransportContext) -> Optional[np.ndarray]:
        return buffer

    def _process_sends(self, sends: List[Send], buffer: Optional[np.ndarray],
                       context: TransportContext):
        pass

    # subscribe 方法被移除

    def add_insert(self, plugin: IPlugin, index: Optional[int] = None):
        if index is None or index >= len(self._inserts):
            self._inserts.append(plugin)
            actual_index = len(self._inserts) - 1
        else:
            self._inserts.insert(index, plugin)
            actual_index = index

        # 发布事件
        self._event_bus.publish(
            InsertAdded(owner_node_id=self._channel_id,
                        plugin=plugin,
                        index=actual_index))

    def remove_insert(self, plugin_instance_id: str) -> bool:
        for i, plugin in enumerate(self._inserts):
            if plugin.node_id == plugin_instance_id:
                self._inserts.pop(i)
                # 发布事件
                self._event_bus.publish(
                    InsertRemoved(owner_node_id=self._channel_id,
                                  plugin_id=plugin_instance_id))
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
            # 确保 new_index 在有效范围内
            if new_index > old_index:
                new_index -= 1
            actual_new_index = max(0, min(new_index, len(self._inserts)))
            self._inserts.insert(actual_new_index, plugin_to_move)

            # 发布事件
            self._event_bus.publish(
                InsertMoved(owner_node_id=self._channel_id,
                            plugin_id=plugin_instance_id,
                            old_index=old_index,
                            new_index=actual_new_index))
            return True
        return False

    def add_send(self,
                 target_bus_node_id: str,
                 is_post_fader: bool = True) -> Send:
        send_level_param = Parameter(owner_node_id=self.channel_id,
                                     name=f"send_to_{target_bus_node_id[:8]}",
                                     default_value=-100.0,
                                     event_bus=self._event_bus)
        new_send = Send(send_id=str(uuid.uuid4()),
                        target_bus_node_id=target_bus_node_id,
                        is_post_fader=is_post_fader,
                        level=send_level_param)
        self._sends.append(new_send)
        # 注意: 尚未为 Send 创建专门的事件，因此这里不发布事件
        return new_send

    def remove_send(self, send_id: str) -> bool:
        for i, send in enumerate(self._sends):
            if send.send_id == send_id:
                self._sends.pop(i)
                # 注意: 尚未为 Send 创建专门的事件，因此这里不发布事件
                return True
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
