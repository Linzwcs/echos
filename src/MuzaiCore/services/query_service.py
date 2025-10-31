# file: src/MuzaiCore/services/query_service.py
from ..interfaces import IDAWManager, IQueryService, INode
from ..models import ToolResponse


class QueryService(IQueryService):
    """只读查询服务的实现。"""

    def __init__(self, manager: IDAWManager):
        self._manager = manager

    def get_project_overview(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        stats = project.get_statistics()
        return ToolResponse("success", stats, "Project overview retrieved.")

    def get_full_project_tree(self, project_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        def node_to_dict(node: INode):
            if hasattr(node, 'to_dict'): return node.to_dict()
            return {
                "node_id": node.node_id,
                "name": getattr(node, 'name', 'N/A'),
                "type": node.node_type
            }

        tree = {
            "project_info":
            project.get_statistics(),
            "nodes": [node_to_dict(n) for n in project.get_all_nodes()],
            "connections":
            [c.__dict__ for c in project.router.get_all_connections()]
        }
        return ToolResponse("success", tree, "Full project tree retrieved.")

    def find_node_by_name(self, project_id: str, name: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")

        found_nodes = []
        for node in project.get_all_nodes():
            if hasattr(node, 'name') and node.name == name:
                found_nodes.append({
                    "node_id": node.node_id,
                    "name": node.name,
                    "type": node.node_type
                })

        if not found_nodes:
            return ToolResponse("success", {"nodes": []},
                                f"No node with name '{name}' found.")
        return ToolResponse(
            "success", {"nodes": found_nodes},
            f"Found {len(found_nodes)} node(s) with name '{name}'.")

    def get_node_details(self, project_id: str, node_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node '{node_id}' not found.")
        if hasattr(node, 'to_dict'):
            details = node.to_dict()
            return ToolResponse(
                "success", details,
                f"Details for node '{getattr(node, 'name', node_id)}' retrieved."
            )
        return ToolResponse("error", None,
                            f"Node '{node_id}' cannot be serialized.")

    def get_connections_for_node(self, project_id: str,
                                 node_id: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        if not project.get_node_by_id(node_id):
            return ToolResponse("error", None, f"Node '{node_id}' not found.")

        router = project.router
        inputs = router.get_inputs_for_node(node_id)
        outputs = router.get_outputs_for_node(node_id)

        def format_conn(c):
            return {
                "source": f"{c.source_port.owner_node_id}",
                "dest": f"{c.dest_port.owner_node_id}"
            }

        data = {
            "inputs": [format_conn(c) for c in inputs],
            "outputs": [format_conn(c) for c in outputs]
        }
        return ToolResponse("success", data,
                            f"Connections for node '{node_id}' retrieved.")

    def get_parameter_value(self, project_id: str, node_id: str,
                            parameter_path: str) -> ToolResponse:
        project = self._manager.get_project(project_id)
        if not project:
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        node = project.get_node_by_id(node_id)
        if not node:
            return ToolResponse("error", None, f"Node '{node_id}' not found.")

        params = node.get_parameters() if hasattr(node,
                                                  'get_parameters') else {}
        param = params.get(parameter_path)

        if not param:
            return ToolResponse(
                "error", None,
                f"Parameter '{parameter_path}' not found on node '{node_id}'.")
        data = {"name": param.name, "value": param.value, "unit": param.unit}
        return ToolResponse("success", data, "Parameter value retrieved.")
