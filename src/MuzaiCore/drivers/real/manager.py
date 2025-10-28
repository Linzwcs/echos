# file: src/MuzaiCore/drivers/real/manager.py
"""
Real DAW Manager Implementation
================================
管理真实DAW环境的项目生命周期

与Mock版本的区别：
- 使用真实音频引擎
- 真实的VST/AU插件托管
- 真实的音频设备管理
- 文件系统持久化
"""

from typing import Dict, Optional
import json
import os

from ...core.project import Project
from ...core.track import MasterTrack
from ...subsystems.router import Router
from ...subsystems.timeline import Timeline
from ...subsystems.commands.command_manager import CommandManager

from .audio_engine import RealAudioEngine
from .plugin_registry import RealPluginRegistry
from .device_manager import RealDeviceManager

from ...interfaces import (IDAWManager, IProject, IPluginRegistry,
                           IDeviceManager)
from ...models.project_model import ProjectState


class RealDAWManager(IDAWManager):
    """
    真实DAW管理器
    
    功能：
    1. 项目生命周期管理
    2. 音频设备初始化和配置
    3. 插件注册表管理
    4. 项目序列化/反序列化
    """

    def __init__(self,
                 sample_rate: int = 48000,
                 block_size: int = 512,
                 projects_dir: str = "./projects"):
        """
        初始化Real DAW Manager
        
        Args:
            sample_rate: 全局采样率
            block_size: 音频块大小
            projects_dir: 项目保存目录
        """
        self._projects: Dict[str, IProject] = {}
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._projects_dir = projects_dir

        # 创建项目目录
        os.makedirs(projects_dir, exist_ok=True)

        # 初始化系统级单例
        print("RealDAWManager: Initializing system components...")

        # 1. 插件注册表
        self._plugin_registry: IPluginRegistry = RealPluginRegistry()
        self._plugin_registry.scan_for_plugins()

        # 2. 设备管理器
        self._device_manager: IDeviceManager = RealDeviceManager()
        self._device_manager.scan_devices()

        print(f"RealDAWManager: Initialized")
        print(f"  - Sample Rate: {sample_rate}Hz")
        print(f"  - Block Size: {block_size} samples")
        print(f"  - Projects Directory: {projects_dir}")

    @property
    def plugin_registry(self) -> IPluginRegistry:
        return self._plugin_registry

    @property
    def device_manager(self) -> IDeviceManager:
        return self._device_manager

    def create_project(self, name: str) -> IProject:
        """
        创建新项目
        
        创建顺序：
        1. 实例化所有子系统
        2. 创建音频引擎
        3. 创建项目对象
        4. 添加主轨道
        5. 注册到管理器
        
        Args:
            name: 项目名称
            
        Returns:
            创建的项目实例
        """
        print(f"RealDAWManager: Creating project '{name}'...")

        # 1. 创建子系统
        router = Router()
        timeline = Timeline()
        command_manager = CommandManager()

        # 2. 创建Real音频引擎
        engine = RealAudioEngine(sample_rate=self._sample_rate,
                                 block_size=self._block_size)

        # 3. 创建项目
        new_project = Project(name=name,
                              router=router,
                              timeline=timeline,
                              command_manager=command_manager,
                              engine=engine)

        # 4. 添加主轨道
        master_track = MasterTrack()
        new_project.add_node(master_track)
        router.add_node(master_track)

        # 5. 注册项目
        self._projects[new_project.project_id] = new_project

        print(f"RealDAWManager: Project '{name}' created")
        print(f"  - Project ID: {new_project.project_id}")
        print(f"  - Master track added")

        return new_project

    def get_project(self, project_id: str) -> Optional[IProject]:
        """获取已加载的项目"""
        return self._projects.get(project_id)

    def close_project(self, project_id: str) -> bool:
        """
        关闭项目并释放资源
        
        重要：必须停止音频引擎！
        """
        project = self.get_project(project_id)
        if not project:
            return False

        # 1. 停止音频引擎
        if hasattr(project, 'engine') and project.engine:
            try:
                project.engine.stop()
            except Exception as e:
                print(f"RealDAWManager: Error stopping engine: {e}")

        # 2. 清理资源
        del self._projects[project_id]

        print(f"RealDAWManager: Closed project {project_id}")
        return True

    def load_project_from_state(self, state: ProjectState) -> IProject:
        """
        从序列化状态重建项目
        
        这是一个复杂的过程：
        1. 创建空项目
        2. 重建所有节点
        3. 重建所有连接
        4. 恢复参数值
        5. 恢复clips和自动化
        
        Args:
            state: 项目状态DTO
            
        Returns:
            重建的项目
        """
        print(f"RealDAWManager: Loading project from state...")

        # 1. 创建基础项目结构
        router = Router()
        timeline = Timeline()
        command_manager = CommandManager()
        engine = RealAudioEngine(sample_rate=self._sample_rate,
                                 block_size=self._block_size)

        project = Project(name=state.name,
                          router=router,
                          timeline=timeline,
                          command_manager=command_manager,
                          engine=engine,
                          project_id=state.project_id)

        # 2. 恢复tempo和time signature
        project.tempo = state.tempo
        project.time_signature = (state.time_signature_numerator,
                                  state.time_signature_denominator)
        timeline.set_tempo(state.tempo)
        timeline.set_time_signature(state.time_signature_numerator,
                                    state.time_signature_denominator)

        # 3. 重建所有节点
        print(f"  - Rebuilding {len(state.nodes)} nodes...")
        self._rebuild_nodes(project, state)

        # 4. 重建所有连接
        print(f"  - Rebuilding {len(state.routing_graph)} connections...")
        self._rebuild_connections(project, state)

        # 5. 注册项目
        self._projects[project.project_id] = project

        print(f"RealDAWManager: Project loaded successfully")
        return project

    def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        """
        序列化项目状态
        
        将完整的项目状态转换为可序列化的DTO
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目状态DTO，如果项目不存在则返回None
        """
        project = self.get_project(project_id)
        if not project:
            return None

        print(f"RealDAWManager: Serializing project {project_id}...")

        # 1. 序列化所有节点
        nodes_state = {}
        for node in project.get_all_nodes():
            node_state = self._serialize_node(node)
            if node_state:
                nodes_state[node.node_id] = node_state

        # 2. 序列化路由图
        routing_graph = project.router.get_all_connections()

        # 3. 创建状态对象
        state = ProjectState(
            project_id=project.project_id,
            name=project.name,
            nodes=nodes_state,
            routing_graph=routing_graph,
            tempo=project.tempo,
            time_signature_numerator=project.time_signature[0],
            time_signature_denominator=project.time_signature[1])

        print(f"  - Serialized {len(nodes_state)} nodes")
        print(f"  - Serialized {len(routing_graph)} connections")

        return state

    # ========================================================================
    # 私有辅助方法
    # ========================================================================

    def _rebuild_nodes(self, project: IProject, state: ProjectState):
        """
        从状态重建所有节点
        
        这需要：
        1. 根据类型实例化节点
        2. 恢复参数值
        3. 重新加载插件
        4. 恢复clips
        """
        from ...core.track import (InstrumentTrack, AudioTrack, BusTrack,
                                   VCATrack, MasterTrack)
        from ...core.plugin import InstrumentPluginInstance, EffectPluginInstance
        from ...models.node_model import TrackState, PluginState

        for node_id, node_state in state.nodes.items():
            try:
                if isinstance(node_state, TrackState):
                    # 重建轨道
                    track = self._rebuild_track(node_state)
                    project.add_node(track)
                    project.router.add_node(track)

            except Exception as e:
                print(
                    f"  - Warning: Failed to rebuild node {node_id[:8]}: {e}")

    def _rebuild_track(self, track_state):
        """根据TrackState重建轨道"""
        from ...core.track import (InstrumentTrack, AudioTrack, BusTrack,
                                   VCATrack, MasterTrack)

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

        # 从注册表获取描述符
        descriptor = self._plugin_registry.get_plugin_descriptor(
            plugin_state.unique_plugin_id)

        if not descriptor:
            print(
                f"  - Warning: Plugin {plugin_state.unique_plugin_id} not found"
            )
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
                print(f"  - Warning: Failed to rebuild connection: {e}")

    def _serialize_node(self, node):
        """将节点序列化为状态对象"""
        from ...core.track import Track
        from ...models.node_model import TrackState, PluginState
        from ...models.parameter_model import ParameterState

        if isinstance(node, Track):
            # 序列化插件
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

            # 创建TrackState
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
    # 文件系统持久化
    # ========================================================================

    def save_project_to_file(self, project_id: str, filename: str) -> bool:
        """
        保存项目到文件
        
        格式：JSON
        
        Args:
            project_id: 项目ID
            filename: 文件名（相对于projects_dir）
            
        Returns:
            是否成功
        """
        state = self.get_project_state(project_id)
        if not state:
            return False

        filepath = os.path.join(self._projects_dir, filename)

        try:
            # 转换为可序列化的字典
            state_dict = self._state_to_dict(state)

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2)

            print(f"RealDAWManager: Project saved to {filepath}")
            return True

        except Exception as e:
            print(f"RealDAWManager: Failed to save project: {e}")
            return False

    def load_project_from_file(self, filename: str) -> Optional[IProject]:
        """
        从文件加载项目
        
        Args:
            filename: 文件名（相对于projects_dir）
            
        Returns:
            加载的项目，失败则返回None
        """
        filepath = os.path.join(self._projects_dir, filename)

        if not os.path.exists(filepath):
            print(f"RealDAWManager: File not found: {filepath}")
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)

            state = self._dict_to_state(state_dict)
            project = self.load_project_from_state(state)

            print(f"RealDAWManager: Project loaded from {filepath}")
            return project

        except Exception as e:
            print(f"RealDAWManager: Failed to load project: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _state_to_dict(self, state: ProjectState) -> dict:
        """将ProjectState转换为可序列化的字典"""
        # 简化实现 - 真实版本需要处理所有嵌套对象
        return {
            'project_id': state.project_id,
            'name': state.name,
            'tempo': state.tempo,
            'time_signature_numerator': state.time_signature_numerator,
            'time_signature_denominator': state.time_signature_denominator,
            # nodes和routing_graph需要递归序列化
            'nodes': {},  # TODO: 实现完整序列化
            'routing_graph': []  # TODO: 实现完整序列化
        }

    def _dict_to_state(self, state_dict: dict) -> ProjectState:
        """从字典重建ProjectState"""
        return ProjectState(project_id=state_dict['project_id'],
                            name=state_dict['name'],
                            tempo=state_dict.get('tempo', 120.0),
                            time_signature_numerator=state_dict.get(
                                'time_signature_numerator', 4),
                            time_signature_denominator=state_dict.get(
                                'time_signature_denominator', 4),
                            nodes=state_dict.get('nodes', {}),
                            routing_graph=state_dict.get('routing_graph', []))
