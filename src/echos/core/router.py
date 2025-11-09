from typing import List, Dict, Optional
import networkx as nx

from ..interfaces.system import IRouter, IPlugin, IEventBus, INode
from ..models.router_model import Port, Connection, PortDirection
from ..interfaces.system.ilifecycle import ILifecycleAware
from ..models.state_model import RouterState


class Router(IRouter):

    def __init__(self):
        super().__init__()
        self._nodes: Dict[str, INode] = {}
        self._connections: List[Connection] = []
        self._graph = nx.DiGraph()

    @property
    def nodes(self):
        return self._nodes

    def add_node(self, node: 'INode'):
        if isinstance(node, IPlugin):
            raise ValueError(
                "can not add plugin to graph, you should add to mixer")

        node_id = node.node_id
        if node_id in self._nodes:
            print(f"Router: Node {node_id[:8]} already exists")
            return
        self._nodes[node_id] = node
        self._graph.add_node(node_id)

        if self.is_mounted:
            node.mount(self._event_bus)
            from ..models.event_model import NodeAdded
            self._event_bus.publish(
                NodeAdded(
                    node_id=node.node_id,
                    node_type=node.node_type,
                ))

    def remove_node(self, node_id: str):

        if node_id not in self._nodes:
            return

        connections_to_remove = [
            c for c in self._connections
            if c.source_port.owner_node_id == node_id
            or c.dest_port.owner_node_id == node_id
        ]

        for conn in connections_to_remove:
            self.disconnect(conn.source_port, conn.dest_port)

        node = self._nodes.pop(node_id)
        self._graph.remove_node(node_id)
        node.unmount()

        if self.is_mounted:
            from ..models.event_model import NodeRemoved
            self._event_bus.publish(NodeRemoved(node_id=node_id))

    def get_node_by_id(self, node_id: str) -> Optional['INode']:

        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List['INode']:

        return list(self._nodes.values())

    def connect(self,
                source_node_id: str,
                dest_node_id: str,
                source_port_id: str = "main_out",
                dest_port_id: str = "main_in") -> bool:

        source_node = self.get_node_by_id(source_node_id)
        dest_node = self.get_node_by_id(dest_node_id)
        if not source_node or not dest_node:
            print(f"Router: Source or destination node not found.")
            return False

        source_port: Optional[Port] = source_node.get_port_by_id(
            source_port_id)
        dest_port: Optional[Port] = dest_node.get_port_by_id(dest_port_id)
        if not source_port or not dest_port:
            print(
                f"Router: Source or destination port not found on the respective nodes."
            )
            return False

        if source_port.direction != PortDirection.OUTPUT or dest_port.direction != PortDirection.INPUT:
            print(
                f"Router: Port direction mismatch (must be OUTPUT -> INPUT).")
            return False

        if source_port.port_type != dest_port.port_type:
            print(
                f"Router: Port type mismatch ({source_port.port_type} -> {dest_port.port_type})."
            )
            return False

        new_connection = Connection(source_node_id, dest_node_id,
                                    source_port_id, dest_port_id)

        if new_connection in self._connections:
            print("Router: Connection already exists.")
            return False

        if self._would_create_cycle(source_node_id, dest_node_id):
            print(
                f"Router: Connection from {source_node_id[:6]} to {dest_node_id[:6]} would create a cycle."
            )
            return False

        self._graph.add_edge(source_node_id, dest_node_id)
        self._connections.append(new_connection)

        if self.is_mounted:
            from ..models.event_model import ConnectionAdded
            self._event_bus.publish(ConnectionAdded(connection=new_connection))

        return True

    def disconnect(self,
                   source_node_id: str,
                   dest_node_id: str,
                   source_port_id: str = "main_out",
                   dest_port_id: str = "main_in") -> bool:

        connection_to_remove = Connection(source_node_id, dest_node_id,
                                          source_port_id, dest_port_id)

        if connection_to_remove not in self._connections:
            return False

        self._connections.remove(connection_to_remove)

        if not any(c.source_node_id == source_node_id
                   and c.dest_node_id == dest_node_id
                   for c in self._connections):
            if self._graph.has_edge(source_node_id, dest_node_id):
                self._graph.remove_edge(source_node_id, dest_node_id)

        if self.is_mounted:
            from ..models.event_model import ConnectionRemoved
            self._event_bus.publish(
                ConnectionRemoved(connection=connection_to_remove))

        return True

    def get_all_connections(self) -> List[Connection]:

        return self._connections.copy()

    def get_inputs_for_node(self, node_id: str) -> List[Connection]:

        if node_id not in self._nodes:
            return []
        return [
            c for c in self._connections
            if c.dest_port.owner_node_id == node_id
        ]

    def get_outputs_for_node(self, node_id: str) -> List[Connection]:

        if node_id not in self._nodes:
            return []
        return [
            c for c in self._connections
            if c.source_port.owner_node_id == node_id
        ]

    def get_processing_order(self) -> List[str]:

        try:
            return list(nx.topological_sort(self._graph))
        except nx.NetworkXError:
            print(
                "Router: Graph has cycles, cannot determine processing order")
            return []

    def has_cycle(self) -> bool:

        try:
            nx.find_cycle(self._graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def to_state(self) -> RouterState:
        return RouterState(
            nodes=[node.to_state() for node in self._nodes.values()],
            connections=self._connections[:],
        )

    @classmethod
    def from_state(cls, state: RouterState) -> 'Router':
        pass

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self) -> List[ILifecycleAware]:
        return list(self._nodes.values())

    def __repr__(self) -> str:
        return (f"Router(nodes={len(self._nodes)}, "
                f"connections={len(self._connections)}, "
                f"has_cycle={self.has_cycle()})")
