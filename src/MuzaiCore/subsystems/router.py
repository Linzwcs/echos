# file: src/MuzaiCore/subsystems/routing/router.py
from typing import List, Dict, Set, Optional, Tuple
import networkx as nx

from ..interfaces import IRouter, INode
from ..models import Connection, Port, PortType, PortDirection


class Router(IRouter):
    """
    管理节点的信号流图，使用有向图
    支持复杂路由：发送、并联处理、侧链等
    """

    def __init__(self):
        self._graph = nx.DiGraph()
        self._connections: List[Connection] = []

        # 延迟补偿缓存
        self._latency_cache: Dict[str, int] = {}
        self._needs_latency_recalculation = True

        # 节点元数据
        self._node_metadata: Dict[str, Dict] = {}

    def add_node(self, node: INode):
        """添加节点到路由图"""
        if self._graph.has_node(node.node_id):
            print(f"Router: Node {node.node_id[:8]} already exists, skipping")
            return

        self._graph.add_node(node.node_id)
        self._node_metadata[node.node_id] = {
            "type": type(node).__name__,
            "name": getattr(node, "name", "Unknown"),
            "latency": 0
        }
        self._needs_latency_recalculation = True
        print(
            f"Router: Added node {node.node_id[:8]} ({self._node_metadata[node.node_id]['type']})"
        )

    def remove_node(self, node_id: str):
        """从路由图移除节点"""
        if not self._graph.has_node(node_id):
            print(f"Router: Node {node_id[:8]} not found")
            return

        # 移除与此节点相关的所有连接
        self._connections = [
            c for c in self._connections
            if c.source_port.owner_node_id != node_id
            and c.dest_port.owner_node_id != node_id
        ]

        self._graph.remove_node(node_id)
        if node_id in self._node_metadata:
            del self._node_metadata[node_id]

        self._needs_latency_recalculation = True
        print(f"Router: Removed node {node_id[:8]}")

    def connect(self, source_port: Port, dest_port: Port) -> bool:
        """创建两个端口之间的连接"""
        # 验证连接
        validation_result = self._validate_connection(source_port, dest_port)
        if not validation_result[0]:
            print(f"Router: Connection failed - {validation_result[1]}")
            return False

        src_node_id = source_port.owner_node_id
        dest_node_id = dest_port.owner_node_id

        # 确保节点存在
        if not self._graph.has_node(src_node_id) or not self._graph.has_node(
                dest_node_id):
            print(f"Router: Cannot connect non-existent nodes")
            return False

        # 检查是否会创建循环
        if self._would_create_cycle(src_node_id, dest_node_id):
            print(f"Router: Connection would create a cycle")
            return False

        # 添加边和连接
        self._graph.add_edge(src_node_id, dest_node_id)
        connection = Connection(source_port, dest_port)
        self._connections.append(connection)

        self._needs_latency_recalculation = True
        print(
            f"Router: Connected {src_node_id[:8]}:{source_port.port_id} -> {dest_node_id[:8]}:{dest_port.port_id}"
        )
        return True

    def disconnect(self, source_node_id: str, dest_node_id: str) -> bool:
        """断开两个节点之间的连接"""
        # 移除所有匹配的连接
        removed = False
        self._connections = [
            c for c in self._connections
            if not (c.source_port.owner_node_id == source_node_id
                    and c.dest_port.owner_node_id == dest_node_id)
        ]

        # 如果没有更多连接，移除图中的边
        if not any(c.source_port.owner_node_id == source_node_id
                   and c.dest_port.owner_node_id == dest_node_id
                   for c in self._connections):
            if self._graph.has_edge(source_node_id, dest_node_id):
                self._graph.remove_edge(source_node_id, dest_node_id)
                removed = True

        if removed:
            self._needs_latency_recalculation = True
            print(
                f"Router: Disconnected {source_node_id[:8]} -> {dest_node_id[:8]}"
            )

        return removed

    def get_processing_order(self) -> List[str]:
        """
        返回拓扑排序的节点ID列表用于渲染
        处理断开的子图和延迟补偿
        """
        if not nx.is_directed_acyclic_graph(self._graph):
            raise Exception(
                "Routing graph contains a cycle! Cannot determine processing order."
            )

        # 获取所有连接的组件
        if self._graph.number_of_nodes() == 0:
            return []

        # 拓扑排序处理断开的节点
        try:
            order = list(nx.topological_sort(self._graph))
        except nx.NetworkXError as e:
            raise Exception(f"Failed to determine processing order: {e}")

        # 如果需要，计算延迟补偿
        if self._needs_latency_recalculation:
            self._calculate_latency_compensation()
            self._needs_latency_recalculation = False

        return order

    def get_inputs_for_node(self, node_id: str) -> List[Connection]:
        """获取节点的所有输入连接"""
        return [
            c for c in self._connections
            if c.dest_port.owner_node_id == node_id
        ]

    def get_outputs_for_node(self, node_id: str) -> List[Connection]:
        """获取节点的所有输出连接"""
        return [
            c for c in self._connections
            if c.source_port.owner_node_id == node_id
        ]

    def get_all_connections(self) -> List[Connection]:
        """获取所有连接"""
        return self._connections.copy()

    def find_path(self, source_node_id: str,
                  dest_node_id: str) -> Optional[List[str]]:
        """查找两个节点之间的路径"""
        try:
            if nx.has_path(self._graph, source_node_id, dest_node_id):
                return nx.shortest_path(self._graph, source_node_id,
                                        dest_node_id)
        except nx.NodeNotFound:
            pass
        return None

    def get_node_latency(self, node_id: str) -> int:
        """获取节点的延迟补偿值（以样本为单位）"""
        return self._latency_cache.get(node_id, 0)

    def report_node_latency(self, node_id: str, latency_samples: int):
        """节点报告其处理延迟"""
        if node_id in self._node_metadata:
            self._node_metadata[node_id]["latency"] = latency_samples
            self._needs_latency_recalculation = True
            print(
                f"Router: Node {node_id[:8]} reported latency: {latency_samples} samples"
            )

    def _validate_connection(self, source_port: Port,
                             dest_port: Port) -> Tuple[bool, str]:
        """验证连接是否有效"""
        # 检查端口类型匹配
        if source_port.port_type != dest_port.port_type:
            return False, f"Port types must match (source: {source_port.port_type.value}, dest: {dest_port.port_type.value})"

        # 检查端口方向
        if source_port.direction != PortDirection.OUTPUT:
            return False, "Source port must be an output"
        if dest_port.direction != PortDirection.INPUT:
            return False, "Destination port must be an input"

        # 检查不能连接到自己
        if source_port.owner_node_id == dest_port.owner_node_id:
            return False, "Cannot connect node to itself"

        # 检查通道数兼容性
        if dest_port.channel_count < source_port.channel_count:
            return False, f"Destination has fewer channels ({dest_port.channel_count}) than source ({source_port.channel_count})"

        # 检查连接是否已存在
        for conn in self._connections:
            if (conn.source_port.owner_node_id == source_port.owner_node_id
                    and conn.source_port.port_id == source_port.port_id
                    and conn.dest_port.owner_node_id == dest_port.owner_node_id
                    and conn.dest_port.port_id == dest_port.port_id):
                return False, "Connection already exists"

        return True, "Valid"

    def _would_create_cycle(self, source_node_id: str,
                            dest_node_id: str) -> bool:
        """检查添加边是否会创建循环"""
        # 临时添加边
        self._graph.add_edge(source_node_id, dest_node_id)
        has_cycle = not nx.is_directed_acyclic_graph(self._graph)
        # 移除临时边
        self._graph.remove_edge(source_node_id, dest_node_id)
        return has_cycle

    def _calculate_latency_compensation(self):
        """
        计算整个图的延迟补偿
        这确保所有信号通路正确对齐，即使插件引入延迟
        """
        self._latency_cache.clear()

        # 对于每个节点，计算其最大输入延迟
        for node_id in nx.topological_sort(self._graph):
            node_latency = self._node_metadata.get(node_id,
                                                   {}).get("latency", 0)

            # 获取所有前驱节点
            predecessors = list(self._graph.predecessors(node_id))
            if predecessors:
                max_input_latency = max(
                    self._latency_cache.get(pred, 0) for pred in predecessors)
            else:
                max_input_latency = 0

            # 此节点的总延迟是其自身延迟加上最大输入延迟
            self._latency_cache[node_id] = max_input_latency + node_latency

        # 找到最大延迟
        if self._latency_cache:
            max_latency = max(self._latency_cache.values())
            print(f"Router: Maximum graph latency: {max_latency} samples")

            # 计算每个节点需要的延迟补偿
            # (最大延迟 - 节点延迟 = 需要添加的延迟)
            for node_id in self._latency_cache:
                compensation = max_latency - self._latency_cache[node_id]
                self._latency_cache[node_id] = compensation

    def get_graph_statistics(self) -> Dict:
        """返回路由图的统计信息"""
        return {
            "node_count":
            self._graph.number_of_nodes(),
            "connection_count":
            len(self._connections),
            "has_cycles":
            not nx.is_directed_acyclic_graph(self._graph),
            "weakly_connected_components":
            nx.number_weakly_connected_components(self._graph),
            "max_latency":
            max(self._latency_cache.values()) if self._latency_cache else 0
        }

    def export_graph_dot(self) -> str:
        """导出图为DOT格式（用于可视化）"""
        import io
        from networkx.drawing.nx_pydot import write_dot

        output = io.StringIO()
        write_dot(self._graph, output)
        return output.getvalue()

    def __repr__(self) -> str:
        stats = self.get_graph_statistics()
        return f"Router(nodes={stats['node_count']}, connections={stats['connection_count']})"
