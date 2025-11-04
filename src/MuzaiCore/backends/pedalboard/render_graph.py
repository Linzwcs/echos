import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from .nodes import BusNode, InstrumentTrackNode, AudioTrackNode, IAudioNode, BaseEffectNode
from ...models import AnyClip, TransportContext
from ...interfaces.system import IPluginInstanceManager

PEDALBOARD_AVAILABLE = True


@dataclass
class AudioConnection:
    source_id: str
    dest_id: str

    def __hash__(self):
        return hash((self.source_id, self.dest_id))

    def __eq__(self, other):
        if not isinstance(other, AudioConnection):
            return False
        return self.source_id == other.source_id and self.dest_id == other.dest_id


class PedalboardRenderGraph:

    def __init__(self, sample_rate: int, block_size: int,
                 plugin_instance_manager: IPluginInstanceManager):

        self._sample_rate = sample_rate
        self._block_size = block_size
        self._plugin_instance_manager = plugin_instance_manager

        self._nodes: Dict[str, BaseEffectNode] = {}
        self._connections: List[AudioConnection] = []
        self._processing_order: List[str] = []

        self._plugin_to_node_map: Dict[str, str] = {}

        self._stats = {
            'total_blocks_processed': 0,
            'total_samples_processed': 0,
            'nodes_added': 0,
            'nodes_removed': 0,
            'plugins_added': 0,
            'plugins_removed': 0,
        }

        print(
            f"PedalboardRenderGraph: Initialized ({sample_rate}Hz, {block_size} samples)"
        )

    def add_node(self, node_id: str, node_type: str):
        if node_id in self._nodes: return

        node: Optional[IAudioNode] = None
        if node_type == "InstrumentTrack":
            node = InstrumentTrackNode(node_id, node_type, self._sample_rate,
                                       self._block_size)
        elif node_type == "AudioTrack":
            node = AudioTrackNode(node_id, node_type, self._sample_rate,
                                  self._block_size)
        elif node_type == "BusTrack":
            node = BusNode(node_id, node_type, self._sample_rate,
                           self._block_size)
        else:
            node = BaseEffectNode(node_id, node_type, self._sample_rate,
                                  self._block_size)
        if node:
            self._nodes[node_id] = node
            self._update_processing_order()
            print(f"RenderGraph: Added {node_type} node object {node_id[:8]}")

    def remove_node(self, node_id: str):
        if node_id not in self._nodes: return

        self._connections = [
            c for c in self._connections
            if c.source_id != node_id and c.dest_id != node_id
        ]

        node_to_remove = self._nodes[node_id]
        for instance_id in list(node_to_remove.plugin_instance_map.keys()):
            self._plugin_instance_manager.release_instance(instance_id)
            self._plugin_to_node_map.pop(instance_id, None)
            self._stats['plugins_removed'] += 1

        del self._nodes[node_id]
        self._update_processing_order()
        print(f"RenderGraph: Removed node object {node_id[:8]}")

    def add_connection(self, source_id: str, dest_id: str):

        if source_id not in self._nodes or dest_id not in self._nodes:
            print(f"RenderGraph: Error - Cannot connect {source_id[:8]}... -> "
                  f"{dest_id[:8]}...: node not found")
            return

        new_conn = AudioConnection(source_id, dest_id)
        if new_conn in self._connections:
            print(f"RenderGraph: Warning - Connection {source_id[:8]}... -> "
                  f"{dest_id[:8]}... already exists")
            return

        if self._would_create_cycle(source_id, dest_id):
            print(f"RenderGraph: Error - Connection {source_id[:8]}... -> "
                  f"{dest_id[:8]}... would create a cycle!")
            return

        self._connections.append(new_conn)
        self._update_processing_order()

        print(
            f"RenderGraph: ✓ Connected {source_id[:8]}... -> {dest_id[:8]}... "
            f"(total: {len(self._connections)})")

    def remove_connection(self, source_id: str, dest_id: str):
        original_count = len(self._connections)
        conn_to_remove = AudioConnection(source_id, dest_id)

        if conn_to_remove in self._connections:
            self._connections.remove(conn_to_remove)
            self._update_processing_order()
            print(
                f"RenderGraph: ✓ Disconnected {source_id[:8]}... -> {dest_id[:8]}..."
            )
        else:
            print(f"RenderGraph: Warning - Connection {source_id[:8]}... -> "
                  f"{dest_id[:8]}... not found")

    def _would_create_cycle(self, source_id: str, dest_id: str) -> bool:
        adj = {node_id: [] for node_id in self._nodes}
        for conn in self._connections:
            adj[conn.source_id].append(conn.dest_id)
        adj[source_id].append(dest_id)

        # DFS 检测环
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        return has_cycle(dest_id)

    def add_plugin_to_node(self, node_id: str, unique_plugin_id: str,
                           index: int):

        node = self._nodes.get(node_id)
        if not node:
            print(f"RenderGraph: Error - Node {node_id[:8]}... not found")
            return
        print("8" * 50)
        result = self._plugin_instance_manager.create_instance(
            unique_plugin_id)
        print(result)
        print("8" * 50)
        if not result:
            print(
                f"RenderGraph: CRITICAL - Failed to create instance for {unique_plugin_id}"
            )
            return

        cache_instance_id, instance = result

        node.add_plugin(plugin_instance=instance,
                        instance_id=cache_instance_id,
                        index=index)

        self._plugin_to_node_map[cache_instance_id] = node_id

        self._update_node_latency(node)
        self._stats['plugins_added'] += 1

        print(f"RenderGraph: ✓ Added plugin '{cache_instance_id[:8]}...' "
              f"to node '{node_id[:8]}...' at index {index}")

    def remove_plugin_from_node(self, node_id: str, plugin_instance_id: str):
        node = self._nodes.get(node_id)
        if not node:
            print(f"RenderGraph: Warning - Node {node_id[:8]}... not found")
            return

        if plugin_instance_id not in node.plugin_instance_map:
            print(f"RenderGraph: Warning - Plugin {plugin_instance_id[:8]}... "
                  f"not found in node {node_id[:8]}...")
            return

        node.remove_plugin(plugin_instance_id)
        self._plugin_instance_manager.release_instance(plugin_instance_id)
        self._plugin_to_node_map.pop(plugin_instance_id, None)

        self._update_node_latency(node)
        self._stats['plugins_removed'] += 1
        print(f"RenderGraph: ✓ Removed plugin '{plugin_instance_id[:8]}...' "
              f"from node '{node_id[:8]}...'")

    def set_parameter(self, node_id: str, parameter_path: str, value: Any):
        node = self._nodes.get(node_id)
        if not node:
            print(
                f"RenderGraph: Warning - Node {node_id[:8]}... not found for parameter set"
            )
            return

        parts = parameter_path.split('.', 1)
        if len(parts) < 2:
            print(
                f"RenderGraph: Warning - Invalid parameter path: {parameter_path}"
            )
            return

        domain, path = parts[0], parts[1]

        try:
            if domain == "mixer":
                node.set_parameter(path, value)
            elif domain == "plugin":
                instance_id, param_name = path.split('.', 1)
                node.set_plugin_parameter(instance_id, param_name, value)
            else:
                print(
                    f"RenderGraph: Warning - Unknown parameter domain: {domain}"
                )
        except Exception as e:
            print(
                f"RenderGraph: Error setting parameter {parameter_path}: {e}")

    def update_clips_for_track(self, node_id: str, clips: List[AnyClip]):
        node = self._nodes.get(node_id)
        if node and node.node_type in ["InstrumentTrack", "AudioTrack"]:
            node.update_clips(clips)
        else:
            print(
                f"RenderGraph: Warning - Cannot update clips for node {node_id[:8]}..."
            )

    def find_node_by_plugin_instance(
        self,
        plugin_instance_id: str,
    ) -> BaseEffectNode:
        instance_id = self._plugin_to_node_map.get(plugin_instance_id)
        return self._nodes[instance_id]

    def get_total_latency(self) -> int:
        max_latency = 0

        for node in self._nodes.values():
            if node.latency_samples > max_latency:
                max_latency = node.latency_samples
        return max_latency

    def get_node_count(self) -> int:
        return len(self._nodes)

    def get_connection_count(self) -> int:

        return len(self._connections)

    def get_plugin_count(self) -> int:
        total = 0
        for node in self._nodes.values():
            total += len(node.plugin_instance_map)
        return total

    def clear(self):

        for node in self._nodes.values():
            for instance_id in list(node.plugin_instance_map.keys()):
                self._plugin_instance_manager.release_instance(instance_id)

        self._nodes.clear()
        self._connections.clear()
        self._processing_order.clear()
        self._plugin_to_node_map.clear()

        print("RenderGraph: ✓ Cleared all nodes and connections")

    def _update_node_latency(self, node: BaseEffectNode):

        total_latency = sum(
            getattr(p, 'latency_samples', 0) for p in node.pedalboard)
        node.latency_samples = total_latency

    def _update_processing_order(self):
        in_degree = {node_id: 0 for node_id in self._nodes}
        for conn in self._connections:
            if conn.dest_id in in_degree:
                in_degree[conn.dest_id] += 1

        queue = [
            node_id for node_id, degree in in_degree.items() if degree == 0
        ]
        order = []

        while queue:
            node_id = queue.pop(0)
            order.append(node_id)

            for conn in self._connections:
                if conn.source_id == node_id and conn.dest_id in in_degree:
                    in_degree[conn.dest_id] -= 1
                    if in_degree[conn.dest_id] == 0:
                        queue.append(conn.dest_id)

        if len(order) != len(self._nodes):
            print(
                "RenderGraph: WARNING - Graph contains cycles! Using fallback order."
            )
            self._processing_order = list(self._nodes.keys())
        else:
            self._processing_order = order

    def process_block(self, context: TransportContext) -> np.ndarray:

        master_output = np.zeros((2, self._block_size), dtype=np.float32)
        processed_outputs: Dict[str, np.ndarray] = {}

        for node_id in self._processing_order:

            node = self._nodes.get(node_id)
            if not node: continue

            inputs: Dict[str, np.ndarray] = {}
            for conn in self._connections:
                if conn.dest_id == node_id and conn.source_id in processed_outputs:
                    inputs[conn.source_id] = processed_outputs[conn.source_id]

            output_audio = node.process(context, inputs)
            processed_outputs[node_id] = output_audio

        for node_id, final_output in processed_outputs.items():

            is_output_node = not any(c.source_id == node_id
                                     for c in self._connections)
            if is_output_node:
                master_output += final_output

        self._stats['total_blocks_processed'] += 1
        self._stats['total_samples_processed'] += self._block_size

        return master_output

    def get_stats(self) -> Dict:

        return {
            **self._stats,
            'current_nodes':
            len(self._nodes),
            'current_connections':
            len(self._connections),
            'current_plugins':
            self.get_plugin_count(),
            'total_latency_samples':
            self.get_total_latency(),
            'total_latency_ms':
            self.get_total_latency() / self._sample_rate * 1000,
        }

    def print_stats(self):

        stats = self.get_stats()
        print("=" * 70)
        print("RenderGraph Statistics")
        print("=" * 70)
        print(f"Nodes:              {stats['current_nodes']} "
              f"(+{stats['nodes_added']} -{stats['nodes_removed']})")
        print(f"Connections:        {stats['current_connections']}")
        print(f"Plugins:            {stats['current_plugins']} "
              f"(+{stats['plugins_added']} -{stats['plugins_removed']})")
        print(f"Total Latency:      {stats['total_latency_samples']} samples "
              f"({stats['total_latency_ms']:.2f} ms)")
        print(f"Blocks Processed:   {stats['total_blocks_processed']}")
        print(f"Samples Processed:  {stats['total_samples_processed']}")
        print("=" * 70)

    def print_graph_structure(self):

        print("\n" + "=" * 70)
        print("Graph Structure")
        print("=" * 70)

        print(f"\nNodes ({len(self._nodes)}):")
        for node_id, node in self._nodes.items():
            plugin_count = len(node.plugin_instance_map)
            print(
                f"  [{node.node_type}] {node_id[:16]}... "
                f"({plugin_count} plugins, {node.latency_samples}ms latency)")
            if node.muted:
                print(f"    ⚠ MUTED")
            if node.soloed:
                print(f"    ⭐ SOLOED")

        print(f"\nConnections ({len(self._connections)}):")
        for conn in self._connections:
            print(f"  {conn.source_id[:16]}... → {conn.dest_id[:16]}...")

        print(f"\nProcessing Order:")
        for i, node_id in enumerate(self._processing_order):
            print(f"  {i+1}. {node_id[:16]}...")

        print("=" * 70 + "\n")

    def validate_graph(self) -> Tuple[bool, List[str]]:
        issues = []

        for conn in self._connections:
            if conn.source_id not in self._nodes:
                issues.append(
                    f"Connection references non-existent source: {conn.source_id}"
                )
            if conn.dest_id not in self._nodes:
                issues.append(
                    f"Connection references non-existent dest: {conn.dest_id}")

        for node_id, node in self._nodes.items():
            for plugin_instance_id in node.plugin_instance_map.keys():

                if plugin_instance_id not in self._plugin_to_node_map:
                    issues.append(
                        f"Plugin {plugin_instance_id} in node {node_id} "
                        f"missing from reverse map")
                elif self._plugin_to_node_map[plugin_instance_id] != node_id:
                    issues.append(
                        f"Plugin {plugin_instance_id} reverse map mismatch")

        for plugin_instance_id, node_id in self._plugin_to_node_map.items():
            if node_id not in self._nodes:
                issues.append(
                    f"Reverse map references non-existent node: {node_id}")
            elif plugin_instance_id not in self._nodes[
                    node_id].plugin_instance_map:
                issues.append(f"Reverse map plugin {plugin_instance_id} "
                              f"not in node {node_id}")

        if len(self._processing_order) != len(self._nodes):
            issues.append("Graph contains cycles")

        is_valid = len(issues) == 0
        return is_valid, issues

    def get_node_graph_info(self, node_id: str) -> Optional[Dict]:

        node = self._nodes.get(node_id)
        if not node:
            return None

        inputs = [
            c.source_id for c in self._connections if c.dest_id == node_id
        ]
        outputs = [
            c.dest_id for c in self._connections if c.source_id == node_id
        ]

        return {
            'node_id': node_id,
            'node_type': node.node_type,
            'plugin_count': len(node.plugin_instance_map),
            'plugins': list(node.plugin_instance_map.keys()),
            'volume_db':
            20 * np.log10(node.volume) if node.volume > 0 else -96.0,
            'pan': node.pan,
            'muted': node.muted,
            'soloed': node.soloed,
            'latency_samples': node.latency_samples,
            'latency_ms': node.latency_samples / self._sample_rate * 1000,
            'input_connections': inputs,
            'output_connections': outputs,
            'is_output_node': len(outputs) == 0,
            'clip_count': len(node.clips),
        }

    def export_graph_as_dot(self) -> str:
        lines = ['digraph AudioGraph {']
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, style=rounded];')

        for node_id, node in self._nodes.items():
            plugin_count = len(node.plugin_instance_map)
            label = f"{node.node_type}\\n{node_id[:8]}...\\n{plugin_count} plugins"

            if node.muted:
                color = 'gray'
            elif node.soloed:
                color = 'gold'
            else:
                color = 'lightblue'

            lines.append(
                f'  "{node_id}" [label="{label}", fillcolor={color}, style="filled,rounded"];'
            )

        for conn in self._connections:
            lines.append(f'  "{conn.source_id}" -> "{conn.dest_id}";')

        lines.append('}')
        return '\n'.join(lines)

    def start_profiling(self):

        self._profiling_enabled = True
        self._node_process_times = {node_id: [] for node_id in self._nodes}
        print("RenderGraph: Profiling started")

    def stop_profiling(self) -> Dict:

        self._profiling_enabled = False

        results = {}
        for node_id, times in self._node_process_times.items():
            if times:
                results[node_id] = {
                    'avg_ms': np.mean(times) * 1000,
                    'max_ms': np.max(times) * 1000,
                    'min_ms': np.min(times) * 1000,
                    'count': len(times),
                }

        print("RenderGraph: Profiling stopped")
        return results

    def get_cpu_usage_estimate(self) -> float:
        """
        估算 CPU 使用率
        
        基于处理时间和可用时间的比率
        
        Returns:
            CPU 使用率百分比 (0-100)
        """
        if self._stats['total_blocks_processed'] == 0:
            return 0.0

        # 可用时间 = block_size / sample_rate
        available_time_per_block = self._block_size / self._sample_rate

        estimated_process_time = len(self._nodes) * 0.0001  # 秒

        cpu_usage = (estimated_process_time / available_time_per_block) * 100
        return min(cpu_usage, 100.0)

    def get_buffer_usage(self) -> Dict:

        total_buffer_memory = 0

        for node in self._nodes.values():

            total_buffer_memory += node.input_buffer.nbytes
            total_buffer_memory += node.output_buffer.nbytes

        total_buffer_memory += self._master_output.nbytes

        return {
            'total_buffers': len(self._nodes) * 2 + 1,
            'total_memory_bytes': total_buffer_memory,
            'total_memory_mb': total_buffer_memory / (1024 * 1024),
            'buffer_size_samples': self._block_size,
            'channels': 2,
        }

    def freeze_node(self, node_id: str) -> bool:
        """
        冻结节点（将其输出缓存为静态缓冲）
        
        用于 CPU 优化：如果节点输出不变，可以跳过处理
        
        Args:
            node_id: 要冻结的节点ID
            
        Returns:
            是否成功冻结
        """
        # TODO: 实现节点冻结逻辑
        print(f"RenderGraph: Node freezing not yet implemented")
        return False

    def create_parallel_processing_groups(self) -> List[List[str]]:
        """
        创建可并行处理的节点组
        
        返回多个节点列表，每个列表中的节点可以并行处理
        （它们之间没有依赖关系）
        
        Returns:
            节点组列表
        """
        groups = []
        processed = set()

        # 按拓扑层级分组
        while len(processed) < len(self._nodes):
            current_group = []

            for node_id in self._nodes:
                if node_id in processed:
                    continue

                # 检查所有依赖是否已处理
                dependencies = [
                    c.source_id for c in self._connections
                    if c.dest_id == node_id
                ]

                if all(dep in processed for dep in dependencies):
                    current_group.append(node_id)

            if current_group:
                groups.append(current_group)
                processed.update(current_group)
            else:
                # 防止死循环（不应该发生）
                break

        return groups

    def optimize_processing_order(self):
        """
        优化处理顺序以提高缓存局部性
        
        这是一个启发式优化，尝试将相关节点放在一起处理
        """
        # TODO: 实现基于缓存局部性的优化
        print("RenderGraph: Processing order optimization not yet implemented")
        pass
