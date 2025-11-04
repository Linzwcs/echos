from typing import List, Dict, Optional, Any
import uuid
from .parameter import Parameter
from ..interfaces import IMixerChannel, IPlugin, IParameter, IEventBus
from ..interfaces.system.ilifecycle import ILifecycleAware
from ..interfaces.system.inode import IPlugin
from ..models.mixer_model import Send


class MixerChannel(IMixerChannel):

    def __init__(self, channel_id: Optional[str] = None):
        super().__init__()
        self._channel_id = channel_id or f"channel_{uuid.uuid4()}"

        # 核心参数
        self._volume = Parameter(self._channel_id, "volume", 0.0, -100.0, 12.0,
                                 "dB")
        self._pan = Parameter(self._channel_id, "pan", 0.0, -1.0, 1.0)
        self._input_gain = Parameter(self._channel_id, "input_gain", 0.0,
                                     -100.0, 12.0, "dB")

        # 状态
        self.is_muted = False
        self.is_solo = False

        # 插件链
        self._inserts: List[IPlugin] = []

        # 发送
        self._sends: List[Send] = []

    @property
    def channel_id(self) -> str:
        return self._channel_id

    @property
    def volume(self) -> Parameter:
        return self._volume

    @property
    def pan(self) -> Parameter:
        return self._pan

    @property
    def inserts(self) -> List[IPlugin]:
        return list(self._inserts)

    @property
    def sends(self) -> List[Send]:
        return list(self._sends)

    def get_parameters(self) -> Dict[str, Parameter]:

        params = {
            "volume": self._volume,
            "pan": self._pan,
            "input_gain": self._input_gain
        }

        for i, plugin in enumerate(self._inserts):
            for name, param in plugin.get_parameters().items():
                params[f"insert_{i}_{name}"] = param

        for i, send in enumerate(self._sends):
            params[f"send_{i}_level"] = send.level

        return params

    def set_parameter(self, name: str, value: Any):
        parameters = self.get_parameters()
        parameters[name].set_value(value)

    def add_insert(self, plugin: IPlugin, index: Optional[int] = None):

        if index is None:
            self._inserts.append(plugin)
            actual_index = len(self._inserts) - 1
        else:
            self._inserts.insert(index, plugin)
            actual_index = index

        # 如果通道已挂载，立即挂载插件
        if self.is_mounted:
            plugin.mount(self._event_bus)

            from ..models.event_model import InsertAdded
            self._event_bus.publish(
                InsertAdded(owner_node_id=self._channel_id,
                            plugin=plugin,
                            index=actual_index))

    def remove_insert(self, plugin_id: str) -> bool:

        for i, plugin in enumerate(self._inserts):
            if plugin.node_id == plugin_id:
                removed = self._inserts.pop(i)
                removed.unmount()

                if self.is_mounted:
                    from ..models.event_model import InsertRemoved
                    self._event_bus.publish(
                        InsertRemoved(owner_node_id=self._channel_id,
                                      plugin_id=plugin_id))
                return True
        return False

    def move_insert(self, plugin_id: str, new_index: int) -> bool:

        old_index = -1
        plugin_to_move = None

        for i, plugin in enumerate(self._inserts):
            if plugin.node_id == plugin_id:
                plugin_to_move = plugin
                old_index = i
                break

        if plugin_to_move:
            self._inserts.pop(old_index)
            actual_new_index = max(0, min(new_index, len(self._inserts)))
            self._inserts.insert(actual_new_index, plugin_to_move)

            if self.is_mounted:
                from ..models.event_model import InsertMoved
                self._event_bus.publish(
                    InsertMoved(owner_node_id=self._channel_id,
                                plugin_id=plugin_id,
                                old_index=old_index,
                                new_index=actual_new_index))
            return True
        return False

    def add_send(self, target_bus_id: str, is_post_fader: bool = True) -> Send:

        send_level = Parameter(owner_node_id=self._channel_id,
                               name=f"send_to_{target_bus_id[:8]}",
                               default_value=-100.0,
                               min_value=-100.0,
                               max_value=12.0,
                               unit="dB")

        send = Send(send_id=f"send_{uuid.uuid4()}",
                    target_bus_node_id=target_bus_id,
                    level=send_level,
                    is_post_fader=is_post_fader)

        self._sends.append(send)

        if self.is_mounted:
            send_level.mount(self._event_bus)

            from ..models.event_model import SendAdded
            self._event_bus.publish(
                SendAdded(owner_node_id=self._channel_id, send=send))

        return send

    def remove_send(self, send_id: str) -> bool:

        for i, send in enumerate(self._sends):
            if send.send_id == send_id:
                removed = self._sends.pop(i)
                removed.level.unmount()

                if self.is_mounted:
                    from ..models.event_model import SendRemoved
                    self._event_bus.publish(
                        SendRemoved(owner_node_id=self._channel_id,
                                    send_id=send_id))
                return True
        return False

    def to_dict(self) -> dict:

        return {
            "channel_id":
            self._channel_id,
            "volume":
            self._volume.value,
            "pan":
            self._pan.value,
            "is_muted":
            self.is_muted,
            "is_solo":
            self.is_solo,
            "inserts": [plugin.to_dict() for plugin in self._inserts],
            "sends": [{
                "send_id": send.send_id,
                "target": send.target_bus_node_id,
                "level": send.level.value,
                "post_fader": send.is_post_fader
            } for send in self._sends]
        }

    def _get_children(self) -> List[ILifecycleAware]:

        children = [self._volume, self._pan, self._input_gain]
        children.extend(self._inserts)
        for send in self._sends:
            children.append(send.level)
        return children
