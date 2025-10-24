from typing import Optional
from .interfaces import INodeService
from ..models import ToolResponse
from ..interfaces import IDAWManager, IPluginRegistry

# 导入所有需要的Command
from ..subsystems.commands.all_commands import (
    CreateNodeCommand,
    DeleteNodeCommand,
    RenameNodeCommand,
    AddInsertPluginCommand,
    RemoveInsertPluginCommand,
)

from ..core.track import InstrumentTrack, AudioTrack, BusTrack, VCATrack
from ..core.plugin import InstrumentPluginInstance, EffectPluginInstance
from ..models.plugin_model import PluginCategory


class NodeService(INodeService):
    """
    重构后的节点管理服务
    
    关键改变：
    - 所有修改操作都创建并执行Command
    - 查询操作直接访问（不需要Command）
    - 服务只是"翻译器"：将Agent请求转换为Command
    """

    def __init__(self, manager: IDAWManager, registry: IPluginRegistry):
        self._manager = manager
        self._registry = registry

    # ========================================================================
    # 修改操作：创建Command → 执行 → 返回结果
    # ========================================================================

    def create_instrument_track(self, project_id: str,
                                name: str) -> ToolResponse:
        """
        创建乐器轨道（重构后 - 使用Command）
        
        旧方式：
            track = InstrumentTrack(name)
            project.add_node(track)  # ✗ 直接操作
            project.router.add_node(track)  # ✗ 无法撤销
        
        新方式：
            创建Command → 通过CommandManager执行 → 可撤销
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        # 1. 准备数据（创建轨道对象）
        track = InstrumentTrack(name=name)

        # 2. 创建Command
        command = CreateNodeCommand(project, track)

        # 3. 通过CommandManager执行（这样就可以撤销！）
        project.command_manager.execute_command(command)

        # 4. 返回结果
        return ToolResponse("success", {
            "node_id": track.node_id,
            "name": name,
            "type": "instrument_track"
        }, f"Instrument track '{name}' created (undoable)")

    def create_audio_track(self, project_id: str, name: str) -> ToolResponse:
        """创建音频轨道（Command驱动）"""
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
        """创建总线轨道（Command驱动）"""
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
        """创建VCA轨道（Command驱动）"""
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

    def delete_node(self, project_id: str, node_id: str) -> ToolResponse:
        """
        删除节点（Command驱动）
        
        关键优势：
        - 自动保存节点状态
        - 自动保存所有连接
        - 可以完整撤销（节点+连接都恢复）
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        # 检查节点是否存在
        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node {node_id} not found")

        # 创建并执行删除命令
        command = DeleteNodeCommand(project, node_id)
        project.command_manager.execute_command(command)

        return ToolResponse("success", None,
                            f"Node {node_id[:8]}... deleted (undoable)")

    def rename_node(self, project_id: str, node_id: str,
                    new_name: str) -> ToolResponse:
        """
        重命名节点（Command驱动）
        
        支持Command合并：
        - 连续重命名会被合并成单个撤销步骤
        """
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

    def add_insert_plugin(self,
                          project_id: str,
                          target_node_id: str,
                          plugin_unique_id: str,
                          index: Optional[int] = None) -> ToolResponse:
        """
        添加插入效果（Command驱动）
        
        流程：
        1. 从Registry获取插件描述符
        2. 实例化插件
        3. 创建AddInsertPluginCommand
        4. 执行（可撤销）
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        target_node = project.get_node_by_id(target_node_id)
        if not hasattr(target_node, "mixer_channel"):
            return ToolResponse("error", None,
                                f"Node {target_node_id} cannot host plugins")

        # 获取插件描述符
        descriptor = self._registry.get_plugin_descriptor(plugin_unique_id)
        if not descriptor:
            return ToolResponse("error", None,
                                f"Plugin {plugin_unique_id} not found")

        # 实例化插件
        if descriptor.category == PluginCategory.INSTRUMENT:
            plugin_instance = InstrumentPluginInstance(descriptor)
        elif descriptor.category == PluginCategory.EFFECT:
            plugin_instance = EffectPluginInstance(descriptor)
        else:
            return ToolResponse(
                "error", None,
                f"Unsupported plugin category: {descriptor.category}")

        # 创建并执行Command
        command = AddInsertPluginCommand(project, target_node_id,
                                         plugin_instance, index)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "plugin_instance_id": plugin_instance.node_id,
                "plugin_name": descriptor.name,
                "target_node_id": target_node_id
            }, f"Plugin '{descriptor.name}' added (undoable)")

    def remove_insert_plugin(self, project_id: str, target_node_id: str,
                             plugin_instance_id: str) -> ToolResponse:
        """
        移除插入效果（Command驱动）
        
        Command会自动保存：
        - 插件实例
        - 插件在链中的位置
        - 所有参数值
        - 撤销时完整恢复
        """
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
    # 查询操作：直接访问，不需要Command
    # ========================================================================

    def list_nodes(self,
                   project_id: str,
                   node_type: Optional[str] = None) -> ToolResponse:
        """
        列出节点（查询操作，不需要Command）
        
        原则：
        - 只读操作不经过Command系统
        - 直接访问Domain对象
        - 更快，更简单
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        nodes = project.get_all_nodes()

        # 过滤节点类型
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
