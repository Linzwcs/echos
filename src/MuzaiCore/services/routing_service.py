from ..interfaces.services import IRoutingService
from ..models import ToolResponse
from ..interfaces import IDAWManager
from ..core.history.commands.all_commands import (
    CreateConnectionCommand,
    CreateSendCommand,
)


class RoutingService(IRoutingService):
    """重构后的路由服务（Command驱动）"""

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def connect(self, project_id: str, source_node_id: str,
                source_port_id: str, dest_node_id: str,
                dest_port_id: str) -> ToolResponse:
        """
        连接节点（改为Command驱动）
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        # 获取端口
        source_node = project.get_node_by_id(source_node_id)
        dest_node = project.get_node_by_id(dest_node_id)

        if not source_node or not dest_node:
            return ToolResponse("error", None,
                                "Source or destination node not found")

        source_ports = source_node.get_ports()
        dest_ports = dest_node.get_ports()

        source_port = next(
            (p for p in source_ports if p.port_id == source_port_id), None)
        dest_port = next((p for p in dest_ports if p.port_id == dest_port_id),
                         None)

        if not source_port or not dest_port:
            return ToolResponse("error", None,
                                "Source or destination port not found")

        # 创建并执行Command
        command = CreateConnectionCommand(project, source_port, dest_port)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "source": f"{source_node_id}:{source_port_id}",
                "destination": f"{dest_node_id}:{dest_port_id}"
            }, "Connection created (undoable)")

    def disconnect(self, project_id: str, source_node_id: str,
                   dest_node_id: str) -> ToolResponse:
        """
        断开连接（需要DisconnectCommand）
        """
        # 实现类似，创建DisconnectCommand
        pass

    def create_send(self,
                    project_id: str,
                    source_track_id: str,
                    dest_bus_id: str,
                    is_post_fader: bool = True) -> ToolResponse:
        """
        创建发送（改为Command驱动）
        """
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        # 创建并执行Command
        command = CreateSendCommand(project, source_track_id, dest_bus_id,
                                    is_post_fader)
        project.command_manager.execute_command(command)

        return ToolResponse(
            "success", {
                "source_track_id": source_track_id,
                "dest_bus_id": dest_bus_id,
                "is_post_fader": is_post_fader
            }, "Send created (undoable)")

    # 查询方法保持不变...
    def list_connections(self, project_id: str) -> ToolResponse:
        """列出连接（查询操作，不需要Command）"""
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project {project_id} not found")

        connections = project.router.get_all_connections()
        conn_list = [{
            "source": f"{c.source_port.owner_node_id}:{c.source_port.port_id}",
            "destination":
            f"{c.dest_port.owner_node_id}:{c.dest_port.port_id}",
            "type": c.source_port.port_type.value
        } for c in connections]

        return ToolResponse("success", {
            "connections": conn_list,
            "count": len(conn_list)
        }, f"Found {len(conn_list)} connections")
