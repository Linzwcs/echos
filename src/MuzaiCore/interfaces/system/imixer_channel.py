# file: src/MuzaiCore/interfaces/IMixerChannel.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from .iparameter import IParameter
from .inode import IPlugin
from ...models.mixer_model import Send
from .ilifecycle import ILifecycleAware
from .ievent_bus import IEventBus


class IMixerChannel(ILifecycleAware, ABC):
    """
    表示混音器通道条的状态容器。

    职责:
    - 持有混音参数 (音量, 声像)。
    - 管理插件插入链 (Inserts)。
    - 管理效果发送 (Sends)。
    - 提供修改这些状态的方法。
    - (实现类) 在状态变更时，通过EventBus发布领域事件。
    """

    @property
    @abstractmethod
    def channel_id(self) -> str:
        """通道的唯一ID，通常与其所属的Node ID相同。"""
        pass

    @property
    @abstractmethod
    def volume(self) -> IParameter:
        """音量参数。"""
        pass

    @property
    @abstractmethod
    def pan(self) -> IParameter:
        """声像参数。"""
        pass

    @property
    @abstractmethod
    def inserts(self) -> List[IPlugin]:
        """获取此通道上所有插入效果插件的有序列表。"""
        pass

    @property
    @abstractmethod
    def sends(self) -> List[Send]:
        """获取此通道上所有效果发送的列表。"""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, IParameter]:
        """获取此通道的所有参数，包括插件的参数。"""
        pass

    @abstractmethod
    def add_insert(self, plugin: IPlugin, index: Optional[int] = None):
        """在指定位置添加一个插件到插入链。"""
        pass

    @abstractmethod
    def remove_insert(self, plugin_instance_id: str) -> bool:
        """根据实例ID从插入链中移除一个插件。"""
        pass

    @abstractmethod
    def move_insert(self, plugin_instance_id: str, new_index: int) -> bool:
        """在插入链中移动一个插件到新的位置。"""
        pass

    @abstractmethod
    def add_send(self,
                 target_bus_node_id: str,
                 is_post_fader: bool = True) -> Send:
        """创建一个到目标总线的效果发送。"""
        pass

    @abstractmethod
    def remove_send(self, send_id: str) -> bool:
        """根据ID移除一个效果发送。"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """将通道状态序列化为字典。"""
        pass

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self) -> List[ILifecycleAware]:
        """返回所有子组件"""
        children = [self._volume, self._pan, self._input_gain]
        children.extend(self._inserts)
        for send in self._sends:
            children.append(send.level)
        return children
