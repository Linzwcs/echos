# file: src/MuzaiCore/drivers/real/dawdreamer_manager.py
"""
Integrated DawDreamer Manager
==============================
完全集成DawDreamer的DAW管理器

特性：
- 使用DawDreamer作为核心引擎
- 完整的VST3/AU支持
- 优化的插件管理
- 离线和实时渲染
"""

from typing import Dict, Optional
import os

from .audio_engine import DawDreamerEngineAdapter
from .plugin_registry import RealPluginRegistry
from .device_manager import RealDeviceManager

from ...core.project import Project
from ...core.track import MasterTrack
from ...subsystems.router import Router
from ...subsystems.timeline import Timeline
from ...subsystems.commands.command_manager import CommandManager

from ...interfaces import IDAWManager, IProject, IPluginRegistry, IDeviceManager
from ...models.project_model import ProjectState


class DawDreamerDAWManager(IDAWManager):
    """
    集成DawDreamer的DAW管理器
    
    架构优势：
    1. 利用DawDreamer的音频图处理能力
    2. 保持MuzaiCore的抽象层和服务层
    3. 完整的VST3/AU支持
    4. 实时和离线渲染
    """

    def __init__(self,
                 sample_rate: int = 48000,
                 block_size: int = 512,
                 projects_dir: str = "./projects",
                 use_dawdreamer: bool = True):
        """
        初始化Manager
        
        Args:
            sample_rate: 采样率
            block_size: 缓冲区大小
            projects_dir: 项目目录
            use_dawdreamer: 是否使用DawDreamer（False则回退到基础引擎）
        """
        self._projects: Dict[str, IProject] = {}
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._projects_dir = projects_dir
        self._use_dawdreamer = use_dawdreamer

        os.makedirs(projects_dir, exist_ok=True)

        print("DawDreamerDAWManager: Initializing...")

        # 1. 插件注册表（使用DawDreamer扫描）
        self._plugin_registry: IPluginRegistry = RealPluginRegistry(
            sample_rate=sample_rate)
        print("  Scanning plugins...")
        self._plugin_registry.scan_for_plugins()

        # 2. 设备管理器
        self._device_manager: IDeviceManager = RealDeviceManager()
        print("  Scanning audio devices...")
        self._device_manager.scan_devices()

        # 3. 共享的DawDreamer引擎（用于插件验证等）
        if use_dawdreamer:
            try:
                import dawdreamer as daw
                self._shared_engine = daw.RenderEngine(sample_rate, block_size)
                print("  ✓ DawDreamer engine initialized")
            except ImportError:
                print("  Warning: DawDreamer not available")
                self._shared_engine = None
                self._use_dawdreamer = False
        else:
            self._shared_engine = None

        print(f"DawDreamerDAWManager: ✓ Initialized")
        print(f"  - Sample Rate: {sample_rate}Hz")
        print(f"  - Block Size: {block_size} samples")
        print(
            f"  - DawDreamer: {'Enabled' if self._use_dawdreamer else 'Disabled'}"
        )

    @property
    def plugin_registry(self) -> IPluginRegistry:
        return self._plugin_registry

    @property
    def device_manager(self) -> IDeviceManager:
        return self._device_manager

    @property
    def shared_engine(self):
        """获取共享的DawDreamer引擎（用于插件加载等）"""
        return self._shared_engine

    def create_project(self, name: str) -> IProject:
        """
        创建新项目（使用DawDreamer引擎）
        
        Args:
            name: 项目名称
            
        Returns:
            项目实例
        """
        print(f"DawDreamerDAWManager: Creating project '{name}'...")

        # 1. 创建子系统
        router = Router()
        timeline = Timeline()
        command_manager = CommandManager()

        # 2. 创建引擎（DawDreamer或Fallback）
        if self._use_dawdreamer:
            engine = DawDreamerEngineAdapter(sample_rate=self._sample_rate,
                                             block_size=self._block_size)
            print("  ✓ Using DawDreamer engine")
        else:
            # Fallback到基础引擎
            from .audio_engine import RealAudioEngine
            engine = RealAudioEngine(sample_rate=self._sample_rate,
                                     block_size=self._block_size)
            print("  ✓ Using fallback engine")

        # 3. 创建项目
        project = Project(name=name,
                          router=router,
                          timeline=timeline,
                          command_manager=command_manager,
                          engine=engine)

        # 4. 添加主轨道
        master_track = MasterTrack()
        project.add_node(master_track)
        router.add_node(master_track)

        # 5. 注册项目
        self._projects[project.project_id] = project

        print(f"  ✓ Project created: {project.project_id[:16]}...")
        return project

    def get_project(self, project_id: str) -> Optional[IProject]:
        """获取已加载的项目"""
        return self._projects.get(project_id)

    def close_project(self, project_id: str) -> bool:
        """
        关闭项目并释放资源
        
        重要：停止DawDreamer引擎并清理处理器
        """
        project = self.get_project(project_id)
        if not project:
            return False

        # 1. 停止音频引擎
        if hasattr(project, 'engine') and project.engine:
            try:
                project.engine.stop()
            except Exception as e:
                print(f"Error stopping engine: {e}")

        # 2. 清理DawDreamer资源
        if isinstance(project.engine, DawDreamerEngineAdapter):
            try:
                project.engine._clear_all_processors()
            except Exception as e:
                print(f"Error cleaning up DawDreamer: {e}")

        # 3. 移除项目引用
        del self._projects[project_id]

        print(f"DawDreamerDAWManager: ✓ Closed project {project_id[:16]}...")
        return True

    def load_project_from_state(self, state: ProjectState) -> IProject:
        """
        从状态重建项目
        
        对于DawDreamer，需要：
        1. 重建节点图
        2. 重建DawDreamer处理器图
        3. 恢复所有连接和参数
        """
        print(f"DawDreamerDAWManager: Loading project from state...")

        # 1. 创建基础项目结构
        router = Router()
        timeline = Timeline()
        command_manager = CommandManager()

        if self._use_dawdreamer:
            engine = DawDreamerEngineAdapter(sample_rate=self._sample_rate,
                                             block_size=self._block_size)
        else:
            from .audio_engine import RealAudioEngine
            engine = RealAudioEngine(sample_rate=self._sample_rate,
                                     block_size=self._block_size)

        project = Project(name=state.name,
                          router=router,
                          timeline=timeline,
                          command_manager=command_manager,
                          engine=engine,
                          project_id=state.project_id)

        # 2. 恢复项目设置
        project.tempo = state.tempo
        project.time_signature = (state.time_signature_numerator,
                                  state.time_signature_denominator)
        timeline.set_tempo(state.tempo)
        timeline.set_time_signature(state.time_signature_numerator,
                                    state.time_signature_denominator)

        # 3. 重建节点
        print(f"  Rebuilding {len(state.nodes)} nodes...")
        self._rebuild_nodes(project, state)

        # 4. 重建连接
        print(f"  Rebuilding {len(state.routing_graph)} connections...")
        self._rebuild_connections(project, state)

        # 5. 如果使用DawDreamer，构建处理器图
        if isinstance(engine, DawDreamerEngineAdapter):
            print("  Building DawDreamer processor graph...")
            engine._build_processor_graph()

        # 6. 注册项目
        self._projects[project.project_id] = project

        print(f"  ✓ Project loaded successfully")
        return project

    def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        """序列化项目状态"""
        project = self.get_project(project_id)
        if not project:
            return None

        print(f"DawDreamerDAWManager: Serializing project...")

        # 序列化所有节点
        nodes_state = {}
        for node in project.get_all_nodes():
            node_state = self._serialize_node(node)
            if node_state:
                nodes_state[node.node_id] = node_state

        # 序列化路由图
        routing_graph = project.router.get_all_connections()

        # 创建状态对象
        state = ProjectState(
            project_id=project.project_id,
            name=project.name,
            nodes=nodes_state,
            routing_graph=routing_graph,
            tempo=project.tempo,
            time_signature_numerator=project.time_signature[0],
            time_signature_denominator=project.time_signature[1])

        print(f"  ✓ Serialized {len(nodes_state)} nodes")
        return state

    # ========================================================================
    # 辅助方法（与RealDAWManager相同）
    # ========================================================================

    def _rebuild_nodes(self, project: IProject, state: ProjectState):
        """从状态重建所有节点"""
        from ...core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack, MasterTrack
        from ...models.node_model import TrackState

        for node_id, node_state in state.nodes.items():
            try:
                if isinstance(node_state, TrackState):
                    track = self._rebuild_track(node_state)
                    project.add_node(track)
                    project.router.add_node(track)
            except Exception as e:
                print(f"  Warning: Failed to rebuild node {node_id[:8]}: {e}")

    def _rebuild_track(self, track_state):
        """根据TrackState重建轨道"""
        from ...core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack, MasterTrack

        # 根据类型创建轨道
        if track_state.track_type == 'instrument':
            track = InstrumentTrack(name=track_state.name,
                                    node_id=track_state.node_id)
        elif track_state.track_type == 'audio':
            track = AudioTrack(name=track_state.name,
                               node_id=track_state.node_id)
        elif track_state.track_type == 'bus':
            track = BusTrack(name=track_state.name,
                             node_id=track_state.node_id)
        elif track_state.track_type == 'vca':
            track = VCATrack(name=track_state.name,
                             node_id=track_state.node_id)
        elif track_state.track_type == 'master':
            track = MasterTrack(name=track_state.name,
                                node_id=track_state.node_id)
        else:
            raise ValueError(f"Unknown track type: {track_state.track_type}")

        # 恢复参数值
        if hasattr(track, 'mixer_channel'):
            track.mixer_channel.volume._set_value_internal(
                track_state.volume.value)
            track.mixer_channel.pan._set_value_internal(track_state.pan.value)
            track.mixer_channel.is_muted = track_state.is_muted
            track.mixer_channel.is_solo = track_state.is_solo

        # 恢复插件
        for plugin_state in track_state.plugins:
            plugin_instance = self._rebuild_plugin(plugin_state)
            if plugin_instance:
                track.mixer_channel.add_insert(plugin_instance)

        # 恢复clips
        track.clips = track_state.clips

        return track

    def _rebuild_plugin(self, plugin_state):
        """根据PluginState重建插件实例"""
        from ...core.plugin import InstrumentPluginInstance, EffectPluginInstance
        from ...models.plugin_model import PluginCategory

        descriptor = self._plugin_registry.get_plugin_descriptor(
            plugin_state.unique_plugin_id)

        if not descriptor:
            print(
                f"  Warning: Plugin {plugin_state.unique_plugin_id} not found")
            return None

        # 创建实例
        if descriptor.category == PluginCategory.INSTRUMENT:
            plugin = InstrumentPluginInstance(descriptor,
                                              plugin_state.instance_id)
        elif descriptor.category == PluginCategory.EFFECT:
            plugin = EffectPluginInstance(descriptor, plugin_state.instance_id)
        else:
            return None

        # 恢复参数值
        for param_name, param_state in plugin_state.parameters.items():
            if param_name in plugin._parameters:
                plugin._parameters[param_name]._set_value_internal(
                    param_state.value)

        plugin.is_enabled = plugin_state.is_enabled

        return plugin

    def _rebuild_connections(self, project: IProject, state: ProjectState):
        """从状态重建所有路由连接"""
        for connection in state.routing_graph:
            try:
                project.router.connect(connection.source_port,
                                       connection.dest_port)
            except Exception as e:
                print(f"  Warning: Failed to rebuild connection: {e}")

    def _serialize_node(self, node):
        """将节点序列化为状态对象"""
        from ...core.track import Track
        from ...models.node_model import TrackState, PluginState
        from ...models.parameter_model import ParameterState

        if isinstance(node, Track):
            plugins = []
            if hasattr(node, 'mixer_channel'):
                for plugin in node.mixer_channel.inserts:
                    plugin_params = {}
                    for param_name, param in plugin.get_parameters().items():
                        plugin_params[param_name] = ParameterState(
                            name=param_name,
                            value=param.value,
                            automation_lane=param.automation_lane)

                    plugins.append(
                        PluginState(instance_id=plugin.node_id,
                                    unique_plugin_id=plugin.descriptor.
                                    unique_plugin_id,
                                    is_enabled=plugin.is_enabled,
                                    parameters=plugin_params))

            track_type = type(node).__name__.lower().replace('track', '')

            return TrackState(
                node_id=node.node_id,
                name=node.name,
                track_type=track_type,
                clips=list(node.clips) if hasattr(node, 'clips') else [],
                plugins=plugins,
                volume=ParameterState(
                    name="volume",
                    value=node.mixer_channel.volume.value,
                    automation_lane=node.mixer_channel.volume.automation_lane)
                if hasattr(node, 'mixer_channel') else ParameterState(
                    "volume", -6.0),
                pan=ParameterState(
                    name="pan",
                    value=node.mixer_channel.pan.value,
                    automation_lane=node.mixer_channel.pan.automation_lane) if
                hasattr(node, 'mixer_channel') else ParameterState("pan", 0.0),
                is_muted=node.mixer_channel.is_muted if hasattr(
                    node, 'mixer_channel') else False,
                is_solo=node.mixer_channel.is_solo if hasattr(
                    node, 'mixer_channel') else False)

        return None

    # ========================================================================
    # DawDreamer特定功能
    # ========================================================================

    def offline_render(self, project_id: str, duration_seconds: float,
                       output_file: str) -> bool:
        """
        离线渲染项目到文件
        
        这是DawDreamer的强大功能：高质量离线渲染
        
        Args:
            project_id: 项目ID
            duration_seconds: 渲染时长（秒）
            output_file: 输出文件路径
            
        Returns:
            是否成功
        """
        project = self.get_project(project_id)
        if not project:
            print(f"Project {project_id} not found")
            return False

        if not isinstance(project.engine, DawDreamerEngineAdapter):
            print("Offline render requires DawDreamer engine")
            return False

        print(f"DawDreamerDAWManager: Offline rendering...")
        print(f"  Duration: {duration_seconds}s")
        print(f"  Output: {output_file}")

        try:
            # 1. 确保处理器图是最新的
            project.engine._build_processor_graph()

            # 2. 更新所有MIDI事件
            # TODO: 为整个时长设置MIDI

            # 3. 使用DawDreamer渲染
            engine = project.engine._engine
            engine.render(duration_seconds)

            # 4. 获取音频并保存
            audio = engine.get_audio()

            # 转换格式并保存
            import soundfile as sf
            # audio shape: [channels, samples]
            audio_transposed = audio.T  # -> [samples, channels]

            sf.write(output_file, audio_transposed, self._sample_rate)

            print(f"  ✓ Rendered successfully")
            return True

        except Exception as e:
            print(f"  ✗ Render failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_engine_type(self, project_id: str) -> str:
        """获取项目使用的引擎类型"""
        project = self.get_project(project_id)
        if not project:
            return "unknown"

        if isinstance(project.engine, DawDreamerEngineAdapter):
            return "dawdreamer"
        else:
            return "basic"

    def list_processors(self, project_id: str) -> dict:
        """列出项目的所有DawDreamer处理器"""
        project = self.get_project(project_id)
        if not project or not isinstance(project.engine,
                                         DawDreamerEngineAdapter):
            return {}

        return {
            "node_to_processor": dict(project.engine._node_to_processor),
            "processor_count": len(project.engine._node_to_processor)
        }

    def get_system_info(self) -> dict:
        """获取系统信息"""
        return {
            "manager_type": "DawDreamerDAWManager",
            "dawdreamer_enabled": self._use_dawdreamer,
            "sample_rate": self._sample_rate,
            "block_size": self._block_size,
            "projects_loaded": len(self._projects),
            "plugins_available": len(self._plugin_registry.list_plugins()),
            "audio_devices":
            len(self._device_manager.get_audio_output_devices())
        }
