# file: src/MuzaiCore/core/router.py
from typing import List, Dict, Set, Optional, Tuple
import networkx as nx

from ..interfaces.system import IRouter, INode
from ..interfaces.system.isync import IGraphSync  # <-- IMPORT THE NEW INTERFACE
from ..models import Connection, Port, PortDirection


class Router(IRouter):
    """
    Manages the logical signal flow graph and emits events upon modification.
    """

    def __init__(self):
        self._graph = nx.DiGraph()
        self._connections: List[Connection] = []
        # ... other properties
        self._subscribers: List[IGraphSync] = [
        ]  # <-- NEW: List of subscribers

    # --- NEW: Subscription Management ---
    def subscribe(self, listener: IGraphSync):
        """Registers a listener for graph change events."""
        if listener not in self._subscribers:
            self._subscribers.append(listener)

    def unsubscribe(self, listener: IGraphSync):
        """Unregisters a listener."""
        if listener in self._subscribers:
            self._subscribers.remove(listener)

    # --- Modified Methods to Emit Events ---

    def add_node(self, node: INode):
        if self._graph.has_node(node.node_id):
            return

        self._graph.add_node(node.node_id)

        for sub in self._subscribers:
            sub.on_node_added(node)
        print(
            f"Router: Added node {node.node_id[:8]} and notified {len(self._subscribers)} listeners."
        )

    def remove_node(self, node_id: str):
        if not self._graph.has_node(node_id):
            return

        # Important: Remove connections first and notify about them
        conns_to_remove = [
            c for c in self._connections
            if c.source_port.owner_node_id == node_id
            or c.dest_port.owner_node_id == node_id
        ]
        for conn in conns_to_remove:
            self.disconnect(
                conn.source_port,
                conn.dest_port)  # This will trigger its own notification

        self._graph.remove_node(node_id)
        # ... (rest of the method)

        for sub in self._subscribers:
            sub.on_node_removed(node_id)  # <-- NOTIFY

        print(f"Router: Removed node {node_id[:8]} and notified listeners.")

    def connect(self, source_port: Port, dest_port: Port) -> bool:
        # ... (validation logic)
        if not validation_result[0]:
            return False

        self._graph.add_edge(source_port.owner_node_id,
                             dest_port.owner_node_id)
        connection = Connection(source_port, dest_port)
        self._connections.append(connection)

        # ... (rest of the method)

        for sub in self._subscribers:
            sub.on_connection_added(connection)  # <-- NOTIFY

        print(
            f"Router: Connected {source_port.owner_node_id[:8]} -> {dest_port.owner_node_id[:8]} and notified listeners."
        )
        return True

    def disconnect(self, source_port: Port,
                   dest_port: Port) -> bool:  # Updated signature
        """Disconnects a specific port-to-port connection."""
        connection_to_remove = None
        for c in self._connections:
            if c.source_port == source_port and c.dest_port == dest_port:
                connection_to_remove = c
                break

        if not connection_to_remove:
            return False

        self._connections.remove(connection_to_remove)

        src_node_id = source_port.owner_node_id
        dest_node_id = dest_port.owner_node_id

        # If no other connections exist between these two nodes, remove the graph edge
        if not any(c.source_port.owner_node_id == src_node_id
                   and c.dest_port.owner_node_id == dest_node_id
                   for c in self._connections):
            if self._graph.has_edge(src_node_id, dest_node_id):
                self._graph.remove_edge(src_node_id, dest_node_id)

        for sub in self._subscribers:
            sub.on_connection_removed(connection_to_remove)  # <-- NOTIFY

        print(
            f"Router: Disconnected {src_node_id[:8]} -> {dest_node_id[:8]} and notified listeners."
        )
        return True
