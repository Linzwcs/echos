# file: src/MuzaiCore/implementations/services/query_service.py
from typing import Optional, List, Dict, Any
from ..interfaces.services import IQueryService
from ..models import ToolResponse
from ..interfaces import IDAWManager, IPluginRegistry


class QueryService(IQueryService):
    """
    查询服务 - 只读操作检查项目状态
    
    特点：
    - 所有操作都是查询
    - 不使用Command
    - 直接访问Domain对象
    - 格式化并返回数据
    """

    def __init__(self, manager: IDAWManager, registry: IPluginRegistry):
        self._manager = manager
        self._registry = registry

    def get_project_overview(self, project_id: str) -> ToolResponse:
        """
        获取项目概览
        
        返回：
        - 基本信息（tempo, time_signature）
        - 节点统计
        - 连接统计
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        nodes = project.get_all_nodes()
        connections = project.router.get_all_connections()

        # 统计不同类型的节点
        node_types = {}
        for node in nodes:
            node_type = type(node).__name__
            node_types[node_type] = node_types.get(node_type, 0) + 1

        return ToolResponse(
            "success", {
                "project_id": project.project_id,
                "name": project.name,
                "tempo": project.tempo,
                "time_signature": project.time_signature,
                "transport_status": project.transport_status.value,
                "node_count": len(nodes),
                "node_types": node_types,
                "connection_count": len(connections)
            }, "Project overview retrieved")

    def get_full_project_tree(self, project_id: str) -> ToolResponse:
        """
        获取完整的项目层次结构
        
        返回每个节点的：
        - 基本信息
        - 参数
        - 插件
        - Clips
        - 连接
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        nodes = project.get_all_nodes()
        tree = []

        for node in nodes:
            node_info = {
                "node_id": node.node_id,
                "name": getattr(node, "name", "Unknown"),
                "type": type(node).__name__,
                "parameters": {}
            }

            # 添加参数信息
            if hasattr(node, "get_parameters"):
                params = node.get_parameters()
                for param_name, param_obj in params.items():
                    node_info["parameters"][param_name] = {
                        "value":
                        param_obj.value,
                        "has_automation":
                        (len(param_obj.automation_lane.points) > 0 if hasattr(
                            param_obj, "automation_lane") else False)
                    }

            # 添加插件信息
            if hasattr(node, "mixer_channel"):
                node_info["inserts"] = [{
                    "plugin_id": plugin.node_id,
                    "name": plugin.descriptor.name,
                    "enabled": plugin.is_enabled
                } for plugin in node.mixer_channel.inserts]

                node_info["sends"] = [{
                    "send_id": send.send_id,
                    "target": send.target_bus_node_id,
                    "level": send.level.value,
                    "post_fader": send.is_post_fader
                } for send in node.mixer_channel.sends]

            # 添加片段信息
            if hasattr(node, "clips"):
                node_info["clips"] = [{
                    "clip_id":
                    clip.clip_id,
                    "name":
                    clip.name,
                    "start_beat":
                    clip.start_beat,
                    "duration_beats":
                    clip.duration_beats,
                    "type":
                    type(clip).__name__,
                    "note_count":
                    (len(clip.notes) if hasattr(clip, "notes") else 0)
                } for clip in node.clips]

            tree.append(node_info)

        return ToolResponse(
            "success", {
                "project_id": project_id,
                "tree": tree,
                "node_count": len(tree)
            }, f"Full project tree retrieved ({len(tree)} nodes)")

    def find_node_by_name(self, project_id: str, name: str) -> ToolResponse:
        """按名称查找节点"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        nodes = project.get_all_nodes()
        matches = [
            {
                "node_id": node.node_id,
                "name": getattr(node, "name", "Unknown"),
                "type": type(node).__name__
            } for node in nodes
            if hasattr(node, "name") and name.lower() in node.name.lower()
        ]

        if not matches:
            return ToolResponse("success", {
                "matches": [],
                "count": 0
            }, f"No nodes found matching '{name}'")

        return ToolResponse("success", {
            "matches": matches,
            "count": len(matches)
        }, f"Found {len(matches)} node(s) matching '{name}'")

    def get_node_details(self, project_id: str, node_id: str) -> ToolResponse:
        """获取节点详细信息"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node {node_id} not found")

        details = {
            "node_id":
            node.node_id,
            "name":
            getattr(node, "name", "Unknown"),
            "type":
            type(node).__name__,
            "ports": [{
                "port_id": port.port_id,
                "type": port.port_type.value,
                "direction": port.direction.value,
                "channels": port.channel_count
            } for port in node.get_ports()]
        }

        # 添加参数
        if hasattr(node, "get_parameters"):
            details["parameters"] = {
                name: {
                    "value": param.value,
                    "type": str(getattr(param, "param_type", "unknown"))
                }
                for name, param in node.get_parameters().items()
            }

        # 添加混音器通道信息
        if hasattr(node, "mixer_channel"):
            mc = node.mixer_channel
            details["mixer_channel"] = {
                "volume": mc.volume.value,
                "pan": mc.pan.value,
                "muted": mc.is_muted,
                "solo": mc.is_solo,
                "insert_count": len(mc.inserts),
                "send_count": len(mc.sends)
            }

        return ToolResponse("success", details, "Node details retrieved")

    def get_connections_for_node(self, project_id: str,
                                 node_id: str) -> ToolResponse:
        """获取节点的所有连接"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        inputs = project.router.get_inputs_for_node(node_id)
        outputs = project.router.get_outputs_for_node(node_id)

        return ToolResponse(
            "success", {
                "node_id":
                node_id,
                "inputs": [{
                    "source":
                    f"{c.source_port.owner_node_id}:{c.source_port.port_id}",
                    "destination":
                    f"{c.dest_port.owner_node_id}:{c.dest_port.port_id}",
                    "type": c.source_port.port_type.value
                } for c in inputs],
                "outputs": [{
                    "source":
                    f"{c.source_port.owner_node_id}:{c.source_port.port_id}",
                    "destination":
                    f"{c.dest_port.owner_node_id}:{c.dest_port.port_id}",
                    "type": c.source_port.port_type.value
                } for c in outputs]
            },
            f"Connections retrieved ({len(inputs)} inputs, {len(outputs)} outputs)"
        )

    def get_parameter_value(self, project_id: str, node_id: str,
                            parameter_path: str) -> ToolResponse:
        """获取参数值"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node {node_id} not found")

        parameters = node.get_parameters()
        if parameter_path not in parameters:
            return ToolResponse("error", None,
                                f"Parameter '{parameter_path}' not found")

        param = parameters[parameter_path]
        return ToolResponse(
            "success", {
                "node_id":
                node_id,
                "parameter":
                parameter_path,
                "value":
                param.value,
                "has_automation":
                (len(param.automation_lane.points) > 0 if hasattr(
                    param, "automation_lane") else False)
            }, f"Parameter value: {param.value}")
