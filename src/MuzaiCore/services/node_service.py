# file: src/MuzaiCore/services/node_service_v2.py
"""
Updated NodeService with Unified Plugin System
===============================================
使用统一插件系统的NodeService

关键改进：
1. 自动检测引擎类型
2. 根据引擎类型创建合适的插件实例
3. 统一的插件管理接口
"""

from typing import Optional
from ..interfaces.services import INodeService
from ..models import ToolResponse
from ..interfaces import IDAWManager, IPluginRegistry

# 导入Command
from ..core.history.commands.all_commands import (
    CreateNodeCommand,
    DeleteNodeCommand,
    RenameNodeCommand,
    AddInsertPluginCommand,
    RemoveInsertPluginCommand,
)

from ..core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack
from ..core.plugin import PluginFactory
from ..models.plugin_model import PluginCategory


class NodeService(INodeService):
    """
    更新的节点服务
    
    特点：
    - 自动适配所有引擎类型
    - 使用统一的插件工厂
    - 透明的插件创建
    """

    def __init__(self, manager: IDAWManager, registry: IPluginRegistry):
        self._manager = manager
        self._registry = registry

    def _detect_engine_type(self, project_id: str) -> str:
        """
        检测项目使用的引擎类型
        
        Returns:
            "mock", "real", "dawdreamer"
        """
        project = self._manager.get_project(project_id)
        if not project:
            return "mock"

        engine = project.engine
        engine_class_name = type(engine).__name__

        if "Mock" in engine_class_name:
            return "mock"
        elif "DawDreamer" in engine_class_name:
            return "dawdreamer"
        else:
            return "real"

    def _get_dawdreamer_engine(self, project_id: str):
        """获取DawDreamer引擎（如果可用）"""
        project = self._manager.get_project(project_id)
        if not project:
            return None

        from ..drivers.dawdreamer_driver.audio_engine import DawDreamerEngineAdapter

        if isinstance(project.engine, DawDreamerEngineAdapter):
            return project.engine._engine

        return None

    def _get_plugin_path(self, plugin_id: str) -> Optional[str]:
        """从插件ID获取文件路径（用于DawDreamer）"""
        # TODO: 实现从注册表获取路径
        # 暂时返回None，使用内置插件
        return None

    # ========================================================================
    # 创建轨道（与之前相同）
    # ========================================================================

    def create_instrument_track(self, project_id: str,
                                name: str) -> ToolResponse:
        """创建乐器轨道"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        track = InstrumentTrack(name=name)
        command = CreateNodeCommand(project, track)
        project.command_manager.execute_command(command)

        return ToolResponse("success", {
            "node_id": track.node_id,
            "name": name,
            "type": "instrument_track"
        }, f"Instrument track '{name}' created (undoable)")

    def create_audio_track(self, project_id: str, name: str) -> ToolResponse:
        """创建音频轨道"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        track = AudioTrack(name=name)
        command = CreateNodeCommand(project, track)
        project.command_manager.execute_command(command)

        return ToolResponse("success", {
            "node_id": track.node_id,
            "name": name,
            "type": "audio_track"
        }, f"Audio track '{name}' created (undoable)")

    def create_bus_track(self, project_id: str, name: str) -> ToolResponse:
        """创建总线轨道"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        bus = BusTrack(name=name)
        command = CreateNodeCommand(project, bus)
        project.command_manager.execute_command(command)

        return ToolResponse("success", {
            "node_id": bus.node_id,
            "name": name,
            "type": "bus_track"
        }, f"Bus track '{name}' created (undoable)")

    def create_vca_track(self, project_id: str, name: str) -> ToolResponse:
        """创建VCA轨道"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        vca = VCATrack(name=name)
        command = CreateNodeCommand(project, vca)
        project.command_manager.execute_command(command)

        return ToolResponse("success", {
            "node_id": vca.node_id,
            "name": name,
            "type": "vca_track"
        }, f"VCA track '{name}' created (undoable)")

    # ========================================================================
    # 插件管理（使用统一插件系统）
    # ========================================================================

    def add_insert_plugin(self,
                          project_id: str,
                          target_node_id: str,
                          plugin_unique_id: str,
                          index: Optional[int] = None) -> ToolResponse:
        """
        添加插件（自动适配引擎类型）
        
        这是关键方法：根据引擎类型创建合适的插件实例
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        target_node = project.get_node_by_id(target_node_id)
        if not hasattr(target_node, "mixer_channel"):
            return ToolResponse("error", None,
                                f"Node {target_node_id} cannot host plugins")

        # 1. 获取插件描述符
        descriptor = self._registry.get_plugin_descriptor(plugin_unique_id)
        if not descriptor:
            return ToolResponse("error", None,
                                f"Plugin {plugin_unique_id} not found")

        # 2. 检测引擎类型
        engine_type = self._detect_engine_type(project_id)

        # 3. 准备引擎特定的参数
        plugin_kwargs = {}

        if engine_type == "dawdreamer":
            # DawDreamer需要额外参数
            dawdreamer_engine = self._get_dawdreamer_engine(project_id)
            plugin_path = self._get_plugin_path(plugin_unique_id)

            if dawdreamer_engine and plugin_path:
                plugin_kwargs['dawdreamer_engine'] = dawdreamer_engine
                plugin_kwargs['plugin_path'] = plugin_path
            else:
                # 如果是内置插件或找不到路径，降级到real
                engine_type = "real"
                print(f"  Note: Using Real plugin for {descriptor.name}")

        # 4. 使用工厂创建插件实例
        try:
            plugin_instance = PluginFactory.create_plugin_instance(
                descriptor, engine_type, **plugin_kwargs)
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to create plugin instance: {str(e)}")

        # 5. 创建并执行Command
        command = AddInsertPluginCommand(project, target_node_id,
                                         plugin_instance, index)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "plugin_instance_id": plugin_instance.node_id,
                "plugin_name": descriptor.name,
                "plugin_category": descriptor.category.value,
                "engine_type": engine_type,
                "target_node_id": target_node_id
            },
            f"Plugin '{descriptor.name}' added using {engine_type} engine (undoable)"
        )

    def remove_insert_plugin(self, project_id: str, target_node_id: str,
                             plugin_instance_id: str) -> ToolResponse:
        """移除插件"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        target_node = project.get_node_by_id(target_node_id)
        if not hasattr(target_node, "mixer_channel"):
            return ToolResponse(
                "error", None,
                f"Node {target_node_id} does not have mixer channel")

        # 创建并执行Command
        command = RemoveInsertPluginCommand(project, target_node_id,
                                            plugin_instance_id)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", None,
            f"Plugin {plugin_instance_id[:8]}... removed (undoable)")

    # ========================================================================
    # 节点管理（与之前相同）
    # ========================================================================

    def delete_node(self, project_id: str, node_id: str) -> ToolResponse:
        """删除节点"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node {node_id} not found")

        command = DeleteNodeCommand(project, node_id)
        project.command_manager.execute_command(command)

        return ToolResponse("success", None,
                            f"Node {node_id[:8]}... deleted (undoable)")

    def rename_node(self, project_id: str, node_id: str,
                    new_name: str) -> ToolResponse:
        """重命名节点"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node {node_id} not found")

        old_name = getattr(node, "name", "Unknown")
        command = RenameNodeCommand(project, node_id, new_name)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "node_id": node_id,
                "old_name": old_name,
                "new_name": new_name
            }, f"Node renamed: '{old_name}' → '{new_name}' (undoable)")

    def list_nodes(self,
                   project_id: str,
                   node_type: Optional[str] = None) -> ToolResponse:
        """列出所有节点（查询操作）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        nodes = project.get_all_nodes()

        if node_type:
            nodes = [
                n for n in nodes
                if type(n).__name__.lower().startswith(node_type.lower())
            ]

        node_list = [{
            "node_id": node.node_id,
            "name": getattr(node, "name", "Unknown"),
            "type": type(node).__name__
        } for node in nodes]

        return ToolResponse("success", {
            "nodes": node_list,
            "count": len(node_list)
        }, f"Found {len(node_list)} nodes")

    # ========================================================================
    # 插件信息查询
    # ========================================================================

    def get_node_plugins(self, project_id: str, node_id: str) -> ToolResponse:
        """
        获取节点上的所有插件
        
        返回插件列表及其引擎类型
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        node = project.get_node_by_id(node_id)
        if not node or not hasattr(node, "mixer_channel"):
            return ToolResponse(
                "error", None,
                f"Node {node_id} not found or has no mixer channel")

        plugins_info = []
        for plugin in node.mixer_channel.inserts:
            # 检测插件类型
            plugin_type = type(plugin).__name__

            if "Mock" in plugin_type:
                engine_type = "mock"
            elif "DawDreamer" in plugin_type:
                engine_type = "dawdreamer"
            else:
                engine_type = "real"

            plugins_info.append({
                "instance_id": plugin.node_id,
                "name": plugin.descriptor.name,
                "vendor": plugin.descriptor.vendor,
                "category": plugin.descriptor.category.value,
                "is_enabled": plugin.is_enabled,
                "engine_type": engine_type,
                "parameter_count": len(plugin.get_parameters())
            })

        return ToolResponse(
            "success", {
                "node_id": node_id,
                "plugins": plugins_info,
                "count": len(plugins_info)
            }, f"Found {len(plugins_info)} plugins on node")
