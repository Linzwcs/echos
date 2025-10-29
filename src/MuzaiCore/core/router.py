# file: src/MuzaiCore/core/router.py
from typing import List, Dict, Optional
import networkx as nx

from ..interfaces.system import IRouter, INode, IEventBus
from ..models import Connection, Port, PortDirection
from ..models.event_model import NodeAdded, NodeRemoved, ConnectionAdded, ConnectionRemoved


class Router(IRouter):
    """
    Manages the project's entire graph structure, including nodes and connections.
    It is the Single Source of Truth for all nodes in the project.
    """

    def __init__(self, event_bus: IEventBus):
        self._graph = nx.DiGraph()
        self._nodes: Dict[str, INode] = {
        }  # <-- The single source of truth for nodes
        self._connections: List[Connection] = []
        self._event_bus = event_bus

    # --- Node Management ---

    def add_node(self, node: INode):
        """Adds a node to the graph and publishes a NodeAdded event."""
        if node.node_id in self._nodes:
            return

        self._nodes[node.node_id] = node
        self._graph.add_node(node.node_id)

        self._event_bus.publish(NodeAdded(node=node))
        print(
            f"Router: Added node {node.node_id[:8]} ({node.name}) and published NodeAdded event."
        )

    def remove_node(self, node_id: str):
        """Removes a node and its connections, publishing all necessary events."""
        if node_id not in self._nodes:
            return

        # Connections must be removed first to fire ConnectionRemoved events
        conns_to_remove = [
            c for c in self._connections
            if c.source_port.owner_node_id == node_id
            or c.dest_port.owner_node_id == node_id
        ]
        for conn in conns_to_remove:
            self.disconnect(conn.source_port, conn.dest_port)

        removed_node = self._nodes.pop(node_id)
        self._graph.remove_node(node_id)

        self._event_bus.publish(NodeRemoved(node_id=node_id))
        print(
            f"Router: Removed node {node_id[:8]} ({removed_node.name}) and published NodeRemoved event."
        )

    def get_node_by_id(self, node_id: str) -> Optional[INode]:
        """Retrieves a node by its ID."""
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[INode]:
        """Returns a list of all nodes in the project."""
        return list(self._nodes.values())

    # --- Connection Management ---

    def connect(self, source_port: Port, dest_port: Port) -> bool:
        """Creates a connection and publishes a ConnectionAdded event."""
        if (source_port.owner_node_id not in self._nodes
                or dest_port.owner_node_id not in self._nodes):
            print("Router Error: One or both nodes do not exist.")
            return False

        if dest_port.direction != PortDirection.INPUT:
            print("Router Error: Destination port must be an input.")
            return False

        if any(c.source_port == source_port and c.dest_port == dest_port
               for c in self._connections):
            return False

        self._graph.add_edge(source_port.owner_node_id,
                             dest_port.owner_node_id)
        connection = Connection(source_port, dest_port)
        self._connections.append(connection)

        self._event_bus.publish(ConnectionAdded(connection=connection))
        print(
            f"Router: Connected {source_port.owner_node_id[:8]} -> {dest_port.owner_node_id[:8]} and published ConnectionAdded event."
        )
        return True

    def disconnect(self, source_port: Port, dest_port: Port) -> bool:
        """Removes a connection and publishes a ConnectionRemoved event."""
        connection_to_remove = next(
            (c for c in self._connections
             if c.source_port == source_port and c.dest_port == dest_port),
            None)

        if not connection_to_remove:
            return False

        self._connections.remove(connection_to_remove)
        src_node_id = source_port.owner_node_id
        dest_node_id = dest_port.owner_node_id

        if not any(c.source_port.owner_node_id == src_node_id
                   and c.dest_port.owner_node_id == dest_node_id
                   for c in self._connections):
            if self._graph.has_edge(src_node_id, dest_node_id):
                self._graph.remove_edge(src_node_id, dest_node_id)

        self._event_bus.publish(
            ConnectionRemoved(connection=connection_to_remove))
        print(
            f"Router: Disconnected {src_node_id[:8]} -> {dest_node_id[:8]} and published ConnectionRemoved event."
        )
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

    # --- Graph Calculation ---

    def get_processing_order(self) -> List[str]:
        """Calculates the order in which nodes should be processed."""
        try:
            return list(nx.topological_sort(self._graph))
        except nx.NetworkXUnfeasible:
            print(
                "Router Warning: A cycle was detected in the graph. Cannot determine processing order."
            )
            return []
