import uuid
from ...interfaces.system import IPlugin, ITrack
from ...interfaces.system.ifactory import INodeFactory, IEngineFactory
from ...interfaces.system.iengine import IEngine
from ...models import PluginDescriptor
from ...core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack
from ...core.plugin import Plugin
from ...core.engine import Engine


class MockNodeFactory(INodeFactory):
    """
    Mock节点工厂
    
    创建基础的Track和Plugin实例，用于测试和演示
    不涉及实际音频处理，只提供状态管理
    """

    def create_instrument_track(self, name: str) -> ITrack:
        """
        创建乐器轨道
        
        Args:
            name: 轨道名称
            
        Returns:
            InstrumentTrack实例
        """
        return InstrumentTrack(name=name)

    def create_audio_track(self, name: str) -> ITrack:
        """
        创建音频轨道
        
        Args:
            name: 轨道名称
            
        Returns:
            AudioTrack实例
        """
        return AudioTrack(name=name)

    def create_bus_track(self, name: str) -> ITrack:
        """
        创建总线轨道
        
        Args:
            name: 轨道名称
            
        Returns:
            BusTrack实例
        """
        return BusTrack(name=name)

    def create_vca_track(self, name: str) -> ITrack:
        """
        创建VCA轨道
        
        Args:
            name: 轨道名称
            
        Returns:
            VCATrack实例
        """
        return VCATrack(name=name)

    def create_plugin_instance(self, descriptor: PluginDescriptor) -> IPlugin:
        """
        创建插件实例
        
        Mock实现：只创建状态容器，不进行实际音频处理
        
        Args:
            descriptor: 插件描述符
            
        Returns:
            Plugin实例
        """

        return Plugin(descriptor=descriptor,
                      event_bus=None,
                      node_id=f"plugin_{uuid.uuid4()}")


class MockEngineFactory(IEngineFactory):
    """
    Mock音频引擎工厂
    
    创建用于测试的Mock音频引擎
    不进行实际音频处理，只模拟状态变化
    """

    def create_engine(
        self,
        sample_rate: int = 48000,
        block_size: int = 512,
    ) -> IEngine:
        """
        创建Mock音频引擎
        
        Args:
            sample_rate: 采样率（Hz）
            block_size: 缓冲区大小（samples）
            
        Returns:
            Engine实例（Mock实现）
        """
        # 创建Engine
        engine = Engine(
            sample_rate=sample_rate,
            block_size=block_size,
        )

        print(
            f"MockAudioEngineFactory: Created engine (SR={sample_rate}Hz, BS={block_size})"
        )
        return engine
