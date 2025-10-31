# file: src/MuzaiCore/core/router.py
from typing import List, Dict, Optional
import networkx as nx

from ..interfaces.system import IRouter, INode, IEventBus
from ..models import Connection, Port, PortDirection
from ..models.event_model import NodeAdded, NodeRemoved, ConnectionAdded, ConnectionRemoved
import networkx as nx
from ..models import Port, Connection
from ..interfaces.system.ilifecycle import ILifecycleAware


class Router(IRouter):
    """
    优化后的路由器
    自动管理所有节点的生命周期
    """

    def __init__(self):
        super().__init__()
        self._nodes: Dict[str, 'INode'] = {}
        self._connections: List[Connection] = []
        self._graph = nx.DiGraph()

    def _get_children(self) -> List[ILifecycleAware]:
        """返回所有节点"""
        return list(self._nodes.values())

    def add_node(self, node: 'INode'):
        """添加节点"""
        node_id = node.node_id

        if node_id in self._nodes:
            print(f"Router: Node {node_id[:8]} already exists")
            return

        self._nodes[node_id] = node
        self._graph.add_node(node_id)

        # 如果路由器已挂载，立即挂载节点
        if self.is_mounted:
            node.mount(self._event_bus)
            from ..models.event_model import NodeAdded
            self._event_bus.publish(NodeAdded(node=node))

    def remove_node(self, node_id: str):
        """移除节点"""
        if node_id not in self._nodes:
            return

        # 移除相关连接
        connections_to_remove = [
            c for c in self._connections
            if c.source_port.owner_node_id == node_id
            or c.dest_port.owner_node_id == node_id
        ]

        for conn in connections_to_remove:
            self.disconnect(conn.source_port, conn.dest_port)

        # 移除节点
        node = self._nodes.pop(node_id)
        self._graph.remove_node(node_id)

        # 卸载节点
        node.unmount()

        if self.is_mounted:
            from ..models.event_model import NodeRemoved
            self._event_bus.publish(NodeRemoved(node_id=node_id))

    def get_node_by_id(self, node_id: str) -> Optional['INode']:
        """根据ID获取节点"""
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List['INode']:
        """获取所有节点"""
        return list(self._nodes.values())

    def connect(self, source_port: Port, dest_port: Port) -> bool:
        """创建连接"""
        # 验证节点存在
        if source_port.owner_node_id not in self._nodes:
            print(
                f"Router: Source node {source_port.owner_node_id[:8]} not found"
            )
            return False

        if dest_port.owner_node_id not in self._nodes:
            print(f"Router: Dest node {dest_port.owner_node_id[:8]} not found")
            return False

        # 验证端口方向
        from ..models import PortDirection
        if dest_port.direction != PortDirection.INPUT:
            print("Router: Destination must be an INPUT port")
            return False

        # 防止重复连接
        if any(c.source_port == source_port and c.dest_port == dest_port
               for c in self._connections):
            print("Router: Connection already exists")
            return False

        # 验证端口类型
        if source_port.port_type != dest_port.port_type:
            print(
                f"Router: Port type mismatch: {source_port.port_type} -> {dest_port.port_type}"
            )
            return False

        # 创建连接
        self._graph.add_edge(source_port.owner_node_id,
                             dest_port.owner_node_id)
        connection = Connection(source_port, dest_port)
        self._connections.append(connection)

        if self.is_mounted:
            from ..models.event_model import ConnectionAdded
            self._event_bus.publish(ConnectionAdded(connection=connection))

        return True

    def disconnect(self, source_port: Port, dest_port: Port) -> bool:
        """断开连接"""
        connection = next(
            (c for c in self._connections
             if c.source_port == source_port and c.dest_port == dest_port),
            None)

        if not connection:
            return False

        self._connections.remove(connection)

        # 如果没有其他连接，移除图边
        src_id = source_port.owner_node_id
        dest_id = dest_port.owner_node_id

        if not any(c.source_port.owner_node_id == src_id
                   and c.dest_port.owner_node_id == dest_id
                   for c in self._connections):
            if self._graph.has_edge(src_id, dest_id):
                self._graph.remove_edge(src_id, dest_id)

        if self.is_mounted:
            from ..models.event_model import ConnectionRemoved
            self._event_bus.publish(ConnectionRemoved(connection=connection))

        return True

    def get_all_connections(self) -> List[Connection]:
        """获取所有连接"""
        return self._connections.copy()

    def get_inputs_for_node(self, node_id: str) -> List[Connection]:
        """获取节点的所有输入连接"""
        if node_id not in self._nodes:
            return []
        return [
            c for c in self._connections
            if c.dest_port.owner_node_id == node_id
        ]

    def get_outputs_for_node(self, node_id: str) -> List[Connection]:
        """获取节点的所有输出连接"""
        if node_id not in self._nodes:
            return []
        return [
            c for c in self._connections
            if c.source_port.owner_node_id == node_id
        ]

    def get_processing_order(self) -> List[str]:
        """获取拓扑排序的处理顺序"""
        try:
            return list(nx.topological_sort(self._graph))
        except nx.NetworkXError:
            print(
                "Router: Graph has cycles, cannot determine processing order")
            return []

    def has_cycle(self) -> bool:
        """检测图中是否有环"""
        try:
            nx.find_cycle(self._graph)
            return True
        except nx.NetworkXNoCycle:
            return False

    def __repr__(self) -> str:
        return (f"Router(nodes={len(self._nodes)}, "
                f"connections={len(self._connections)}, "
                f"has_cycle={self.has_cycle()})")
