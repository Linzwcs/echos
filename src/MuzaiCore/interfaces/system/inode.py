from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .ilifecycle import ILifecycleAware
from .ievent_bus import IEventBus
from ...models import AnyClip, Port


class INode(ILifecycleAware, ABC):
    """
    纯前端节点接口
    
    职责：
    - 元数据（ID, name, type）
    - 端口定义（仅描述）
    - 参数定义（仅数据）
    
    不负责：
    ❌ 音频处理
    ❌ MIDI处理
    ❌ DSP计算
    """

    @property
    @abstractmethod
    def node_id(self) -> str:
        """节点唯一标识"""
        pass

    @property
    @abstractmethod
    def node_type(self) -> str:
        """节点类型：'track', 'plugin', 'bus', 'vca'"""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        获取参数定义
        
        Returns:
            {param_name: param_descriptor}
        """
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        """
        序列化为字典
        
        前端对象必须可序列化
        """
        pass

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None


class ITrack(INode):
    """
    纯前端轨道接口
    
    改变：
    - ❌ 删除 mixer_channel 属性（音频相关）
    - ✓ 保留 clips（纯数据）
    - ✓ 保留元数据
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """轨道名称"""
        pass

    @name.setter
    @abstractmethod
    def name(self, value: str):
        """设置轨道名称"""
        pass

    @property
    @abstractmethod
    def clips(self) -> List[AnyClip]:
        """此轨道的所有片段（纯数据）"""
        pass


class IPlugin(INode):
    """
    纯前端插件接口
    
    改变：
    - ❌ 删除所有音频处理方法
    - ✓ 只保留描述符和状态
    """

    @property
    @abstractmethod
    def descriptor(self) -> 'PluginDescriptor':
        """插件静态描述符"""
        pass

    @property
    @abstractmethod
    def is_enabled(self) -> bool:
        """是否启用（前端状态）"""
        pass

    @abstractmethod
    def get_parameter_values(self) -> Dict[str, Any]:
        """
        获取所有参数的当前值
        
        注意：这是前端存储的值，非实时音频线程的值
        """
        pass

    @abstractmethod
    def set_parameter_value(self, name: str, value: Any):
        """
        设置参数值（前端）
        
        这只更新前端状态，实际音频变化由SyncController处理
        """
        pass
