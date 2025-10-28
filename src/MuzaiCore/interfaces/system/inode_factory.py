# file: src/MuzaiCore/interfaces/INodeFactory.py
"""
定义了用于创建所有节点类型（轨道和插件）的抽象工厂接口。
"""
from abc import ABC, abstractmethod
from .inode import IPlugin, ITrack
from ...models import PluginDescriptor


class INodeFactory(ABC):
    """
    一个抽象工厂 (Abstract Factory)，定义了创建所有类型节点的契约。

    该接口将 NodeService 与每个后端（mock, real, dawdreamer）的具体实现细节解耦。
    每个后端都必须提供此工厂的一个具体实现，负责实例化该后端所需的特定
    Track 和 PluginInstance 对象。
    """

    @abstractmethod
    def create_instrument_track(self, name: str) -> ITrack:
        """
        创建一个适用于当前后端的乐器轨道对象。

        Args:
            name: 轨道的名称。

        Returns:
            一个实现了 ITrack 接口的对象。
        """
        pass

    @abstractmethod
    def create_audio_track(self, name: str) -> ITrack:
        """
        创建一个适用于当前后端的音频轨道对象。

        Args:
            name: 轨道的名称。

        Returns:
            一个实现了 ITrack 接口的对象。
        """
        pass

    @abstractmethod
    def create_bus_track(self, name: str) -> ITrack:
        """
        创建一个适用于当前后端的总线轨道对象。

        Args:
            name: 轨道的名称。

        Returns:
            一个实现了 ITrack 接口的对象。
        """
        pass

    @abstractmethod
    def create_vca_track(self, name: str) -> ITrack:
        """
        创建一个适用于当前后端的VCA轨道对象。

        Args:
            name: 轨道的名称。

        Returns:
            一个实现了 ITrack 接口的对象。
        """
        pass

    @abstractmethod
    def create_plugin_instance(self, descriptor: PluginDescriptor) -> IPlugin:
        """
        根据插件描述符创建一个特定于后端的插件实例。

        这是工厂模式的关键。例如：
        - Mock 后端的工厂将返回一个 MockPluginInstance。
        - Real 后端的工厂将返回一个包装了纯Python DSP的 RealPluginAdapter。
        - DawDreamer 后端的工厂将返回一个通用的 PluginInstance 领域对象，
          其状态后续将被 SyncController 同步到 DawDreamer 引擎。

        Args:
            descriptor: 要创建的插件的静态蓝图（元数据）。

        Returns:
            一个实现了 IPlugin 接口的对象，其具体实现由后端决定。
        """
        pass
