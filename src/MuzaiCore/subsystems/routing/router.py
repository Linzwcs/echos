# file: src/MuzaiCore/subsystems/routing/router.py
from typing import List
import networkx as nx

from ...interfaces import IRouter, INode  # <-- ADD INode
from .routing_types import Connection, Port


class Router(IRouter):
    """Manages the signal flow graph of nodes using a directed graph."""

    def __init__(self):
        self._graph = nx.DiGraph()
        self._connections: List[Connection] = []

    # +++ NEW IMPLEMENTATION +++
    def add_node(self, node: INode):
        if not self._graph.has_node(node.node_id):
            self._graph.add_node(node.node_id)
            print(f"Router: Added node {node.node_id}")

    # +++ NEW IMPLEMENTATION +++
    def remove_node(self, node_id: str):
        if self._graph.has_node(node_id):
            # Also remove any connections associated with this node
            self._connections = [
                c for c in self._connections
                if c.source_port.owner_node_id != node_id
                and c.dest_port.owner_node_id != node_id
            ]
            self._graph.remove_node(node_id)
            print(f"Router: Removed node {node_id}")

    def connect(self, source_port: Port, dest_port: Port) -> bool:
        if source_port.port_type != dest_port.port_type:
            print("Error: Port types must match.")
            return False

        src_node_id = source_port.owner_node_id
        dest_node_id = dest_port.owner_node_id

        # Ensure nodes exist before connecting
        if not self._graph.has_node(src_node_id) or not self._graph.has_node(
                dest_node_id):
            print(
                f"Error: Cannot connect non-existent nodes {src_node_id} -> {dest_node_id}"
            )
            return False

        # In a real router, you'd check for cycles and other invalid connections.
        self._graph.add_edge(src_node_id, dest_node_id)
        self._connections.append(Connection(source_port, dest_port))
        print(f"Router: Connected {src_node_id} -> {dest_node_id}")
        return True

    def get_processing_order(self) -> List[str]:
        """Returns a topologically sorted list of node IDs for rendering."""
        # A professional DAW must handle disconnected nodes. Topological sort only works
        # on connected components. We need to process all nodes.
        # Here we process independent subgraphs one by one.

        # For simplicity in V1, let's assume we can get all nodes and sort them.
        # nx.topological_sort handles disconnected nodes correctly by returning
        # an iterator over all nodes in a valid order.
        if not nx.is_directed_acyclic_graph(self._graph):
            # This check is crucial for preventing infinite loops in audio processing
            raise Exception("Routing graph contains a cycle!")

        return list(nx.topological_sort(self._graph))

    def get_inputs_for_node(self, node_id: str) -> List[Connection]:
        return [
            c for c in self._connections
            if c.dest_port.owner_node_id == node_id
        ]
