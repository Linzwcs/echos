# file: src/MuzaiCore/services/node_service.py
from typing import Optional
from ..interfaces import IDAWManager, INodeService
from ..models import ToolResponse
from ..core.history.commands.node_commands import CreateTrackCommand, RenameNodeCommand


class NodeService(INodeService):
    """节点管理服务的实现。"""

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def _create_track(
        self,
        project_id: str,
        name: str,
        track_type: str,
    ) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        node_factory = self._manager._node_factory
        command = CreateTrackCommand(
            router=project.router,
            node_factory=node_factory,
            track_type=track_type,
            name=name,
        )
        project.command_manager.execute_command(command)

        if command.is_executed:
            track = command._created_track
            return ToolResponse(
                "success", {
                    "node_id": track.node_id,
                    "name": track.name,
                    "type": track.node_type
                }, command.description)
        return ToolResponse("error", None, command.error)

    def create_instrument_track(self, project_id: str,
                                name: str) -> ToolResponse:
        return self._create_track(project_id, name, "InstrumentTrack")

    def create_audio_track(self, project_id: str, name: str) -> ToolResponse:
        return self._create_track(project_id, name, "AudioTrack")

    def create_bus_track(self, project_id: str, name: str) -> ToolResponse:
        return self._create_track(project_id, name, "BusTrack")

    def list_nodes(self,
                   project_id: str,
                   node_type: Optional[str] = None) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        nodes = project.get_all_nodes()
        if node_type:
            nodes = [n for n in nodes if n.node_type == node_type]

        data = [{
            "node_id": n.node_id,
            "name": n.name,
            "type": n.node_type
        } for n in nodes]
        return ToolResponse("success", {"nodes": data},
                            f"Found {len(data)} nodes.")

    # 其他方法的实现...
    def create_vca_track(self, project_id: str, name: str) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")

    def delete_node(self, project_id: str, node_id: str) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")

    def rename_node(self, project_id: str, node_id: str,
                    new_name: str) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")

    def add_insert_plugin(self,
                          project_id: str,
                          target_node_id: str,
                          plugin_unique_id: str,
                          index: Optional[int] = None) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")

    def remove_insert_plugin(self, project_id: str, target_node_id: str,
                             plugin_instance_id: str) -> ToolResponse:
        return ToolResponse("error", None, "Not implemented")
