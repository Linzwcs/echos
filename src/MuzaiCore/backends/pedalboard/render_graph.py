import numpy as np
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import threading

try:
    import pedalboard as pb
    from pedalboard import Pedalboard
except ImportError:
    pb = None
    Pedalboard = None

from ...models import TransportContext, NotePlaybackInfo, MIDIClip, Note


@dataclass
class AudioNodeState:
    """音频节点状态（在音频线程中）"""
    node_id: str
    node_type: str  # "track", "plugin", "bus"

    # Pedalboard 处理链
    pedalboard: Optional[Pedalboard] = None

    # 音频缓冲
    input_buffer: np.ndarray = field(
        default_factory=lambda: np.zeros((2, 512)))
    output_buffer: np.ndarray = field(
        default_factory=lambda: np.zeros((2, 512)))

    # MIDI 数据（仅用于乐器轨道）
    pending_notes: List[NotePlaybackInfo] = field(default_factory=list)
    active_notes: Set[int] = field(default_factory=set)  # 正在播放的音符音高

    # 参数
    volume: float = 1.0  # 线性增益
    pan: float = 0.0  # -1 (左) 到 +1 (右)
    muted: bool = False
    soloed: bool = False

    # 延迟补偿
    latency_samples: int = 0
    delay_buffer: Optional[np.ndarray] = None


@dataclass
class AudioConnection:
    """音频连接"""
    source_id: str
    dest_id: str
    gain: float = 1.0  # 连接增益（用于发送）


class PedalboardRenderGraph:
    """
    Pedalboard 渲染图
    
    这是实时音频线程的核心，必须是实时安全的：
    - 无内存分配
    - 无锁等待
    - 确定性时间
    """

    def __init__(self, sample_rate: int, block_size: int):
        self._sample_rate = sample_rate
        self._block_size = block_size

        # 图结构（仅在非实时线程修改）
        self._nodes: Dict[str, AudioNodeState] = {}
        self._connections: List[AudioConnection] = []
        self._processing_order: List[str] = []

        # 主输出混音
        self._master_output = np.zeros((2, block_size), dtype=np.float32)

        # 线程安全
        self._graph_lock = threading.RLock()

        print(
            f"PedalboardRenderGraph: Created ({sample_rate}Hz, {block_size} samples)"
        )

    # ========================================================================
    # 图结构管理（非实时线程）
    # ========================================================================

    def add_node(self, node_id: str, node_type: str):
        """添加音频节点"""
        with self._graph_lock:
            if node_id in self._nodes:
                print(f"RenderGraph: Node {node_id[:8]} already exists")
                return

            # 创建 Pedalboard 实例
            pedalboard_instance = Pedalboard([])

            self._nodes[node_id] = AudioNodeState(
                node_id=node_id,
                node_type=node_type,
                pedalboard=pedalboard_instance,
                input_buffer=np.zeros((2, self._block_size), dtype=np.float32),
                output_buffer=np.zeros((2, self._block_size),
                                       dtype=np.float32),
            )

            self._update_processing_order()
            print(f"RenderGraph: Added {node_type} node {node_id[:8]}")

    def remove_node(self, node_id: str):
        """移除音频节点"""
        with self._graph_lock:
            if node_id not in self._nodes:
                return

            # 移除相关连接
            self._connections = [
                c for c in self._connections
                if c.source_id != node_id and c.dest_id != node_id
            ]

            del self._nodes[node_id]
            self._update_processing_order()
            print(f"RenderGraph: Removed node {node_id[:8]}")

    def add_connection(self, source_id: str, dest_id: str, gain: float = 1.0):
        """添加音频连接"""
        with self._graph_lock:
            if source_id not in self._nodes or dest_id not in self._nodes:
                print(f"RenderGraph: Cannot connect - nodes not found")
                return

            self._connections.append(AudioConnection(source_id, dest_id, gain))
            self._update_processing_order()
            print(f"RenderGraph: Connected {source_id[:8]} -> {dest_id[:8]}")

    def remove_connection(self, source_id: str, dest_id: str):
        """移除音频连接"""
        with self._graph_lock:
            self._connections = [
                c for c in self._connections
                if not (c.source_id == source_id and c.dest_id == dest_id)
            ]
            self._update_processing_order()

    def add_plugin_to_node(self,
                           node_id: str,
                           plugin_path: str,
                           index: Optional[int] = None):
        """
        添加插件到节点
        
        Args:
            node_id: 节点ID
            plugin_path: 插件文件路径（VST3/AU）
            index: 插入位置（None = 末尾）
        """
        with self._graph_lock:
            node = self._nodes.get(node_id)
            if not node or not node.pedalboard:
                return

            try:
                # 加载插件（这会分配内存，所以在非实时线程）
                if plugin_path.endswith('.vst3'):
                    plugin = pb.load_plugin(plugin_path)
                elif plugin_path.endswith('.component'):  # macOS AU
                    plugin = pb.load_plugin(plugin_path)
                else:
                    print(
                        f"RenderGraph: Unsupported plugin format: {plugin_path}"
                    )
                    return

                # 添加到 Pedalboard 链
                if index is None:
                    node.pedalboard.append(plugin)
                else:
                    node.pedalboard.insert(index, plugin)

                # 更新延迟
                self._update_node_latency(node_id)

                print(f"RenderGraph: Added plugin to {node_id[:8]}")

            except Exception as e:
                print(f"RenderGraph: Failed to load plugin: {e}")

    def remove_plugin_from_node(self, node_id: str, plugin_index: int):
        """从节点移除插件"""
        with self._graph_lock:
            node = self._nodes.get(node_id)
            if not node or not node.pedalboard:
                return

            if 0 <= plugin_index < len(node.pedalboard):
                del node.pedalboard[plugin_index]
                self._update_node_latency(node_id)
                print(f"RenderGraph: Removed plugin from {node_id[:8]}")

    def set_parameter(self, node_id: str, param_name: str, value: float):
        """
        设置节点参数（实时安全）
        
        支持的参数：
        - volume: 音量（dB）
        - pan: 声像（-1 到 1）
        - muted: 静音
        - plugin.X.param: 插件参数
        """
        node = self._nodes.get(node_id)
        if not node:
            return

        if param_name == "volume":
            # dB 转线性增益
            node.volume = 10**(value / 20.0)

        elif param_name == "pan":
            node.pan = np.clip(value, -1.0, 1.0)

        elif param_name == "muted":
            node.muted = bool(value)

        elif param_name.startswith("plugin."):
            # 格式: "plugin.0.cutoff"
            parts = param_name.split(".")
            if len(parts) >= 3:
                plugin_idx = int(parts[1])
                plugin_param = ".".join(parts[2:])

                if 0 <= plugin_idx < len(node.pedalboard):
                    plugin = node.pedalboard[plugin_idx]
                    # Pedalboard 插件参数设置
                    if hasattr(plugin, plugin_param):
                        setattr(plugin, plugin_param, value)

    def schedule_notes(self, track_id: str, notes: List[NotePlaybackInfo]):
        """
        调度 MIDI 音符（用于乐器轨道）
        
        这些音符将在下一个音频块中播放
        """
        node = self._nodes.get(track_id)
        if node:
            node.pending_notes.extend(notes)

    # ========================================================================
    # 实时音频处理
    # ========================================================================

    def process_block(self, context: TransportContext) -> np.ndarray:
        """
        处理单个音频块（实时线程）
        
        这是最关键的方法，必须在严格的时间约束内完成
        
        Args:
            context: 传输上下文（当前节拍、采样率等）
            
        Returns:
            立体声音频输出 (2, block_size)
        """
        # 清空主输出
        self._master_output.fill(0.0)

        # 按拓扑顺序处理所有节点
        for node_id in self._processing_order:
            node = self._nodes.get(node_id)
            if not node:
                continue

            # 1. 收集输入
            node.input_buffer.fill(0.0)
            for conn in self._connections:
                if conn.dest_id == node_id:
                    source = self._nodes.get(conn.source_id)
                    if source:
                        node.input_buffer += source.output_buffer * conn.gain

            # 2. 处理音频
            self._process_node(node, context)

            # 3. 应用音量和声像
            self._apply_mix_controls(node)

        # 收集所有输出到主混音
        for node in self._nodes.values():
            if self._is_output_node(node):
                self._master_output += node.output_buffer

        return self._master_output

    def _process_node(self, node: AudioNodeState, context: TransportContext):
        """
        处理单个节点
        
        Args:
            node: 节点状态
            context: 传输上下文
        """
        # 如果静音，输出静音
        if node.muted:
            node.output_buffer.fill(0.0)
            return

        # 如果是乐器轨道且有待处理的音符
        if node.node_type == "InstrumentTrack" and node.pending_notes:
            # 生成 MIDI 事件
            # 注意：Pedalboard 的 MIDI 处理方式取决于插件
            # 这里需要将 pending_notes 转换为插件可理解的格式
            pass

        # 通过 Pedalboard 处理音频
        if node.pedalboard and len(node.pedalboard) > 0:
            try:
                # Pedalboard 处理（这是 C++ 加速的）
                node.output_buffer = node.pedalboard(
                    node.input_buffer, sample_rate=self._sample_rate)
            except Exception as e:
                # 错误时输出静音（避免崩溃）
                print(f"Error processing node {node.node_id}: {e}")
                node.output_buffer.fill(0.0)
        else:
            # 无插件时直通
            node.output_buffer[:] = node.input_buffer

        # 清空已处理的音符
        node.pending_notes.clear()

    def _apply_mix_controls(self, node: AudioNodeState):
        """
        应用混音控制（音量、声像）
        
        这些是基本的DSP操作，非常快
        """
        # 音量
        node.output_buffer *= node.volume

        # 声像（恒功率声像法则）
        if node.pan != 0.0:
            # 计算左右增益
            angle = (node.pan + 1.0) * np.pi / 4.0  # 0 到 π/2
            left_gain = np.cos(angle)
            right_gain = np.sin(angle)

            node.output_buffer[0] *= left_gain
            node.output_buffer[1] *= right_gain

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _update_processing_order(self):
        """
        更新处理顺序（拓扑排序）
        
        使用 Kahn 算法进行拓扑排序
        """
        # 计算入度
        in_degree = {node_id: 0 for node_id in self._nodes}

        for conn in self._connections:
            if conn.dest_id in in_degree:
                in_degree[conn.dest_id] += 1

        # 找到所有入度为0的节点
        queue = [
            node_id for node_id, degree in in_degree.items() if degree == 0
        ]
        order = []

        while queue:
            node_id = queue.pop(0)
            order.append(node_id)

            # 减少相邻节点的入度
            for conn in self._connections:
                if conn.source_id == node_id and conn.dest_id in in_degree:
                    in_degree[conn.dest_id] -= 1
                    if in_degree[conn.dest_id] == 0:
                        queue.append(conn.dest_id)

        # 检测循环
        if len(order) != len(self._nodes):
            print("Warning: Graph contains cycles!")
            # 使用原有顺序
            order = list(self._nodes.keys())

        self._processing_order = order

    def _update_node_latency(self, node_id: str):
        """更新节点的总延迟"""
        node = self._nodes.get(node_id)
        if not node or not node.pedalboard:
            return

        # 计算所有插件的总延迟
        total_latency = 0
        for plugin in node.pedalboard:
            if hasattr(plugin, 'latency_samples'):
                total_latency += plugin.latency_samples

        node.latency_samples = total_latency

        # 如果需要，创建延迟补偿缓冲
        if total_latency > 0:
            node.delay_buffer = np.zeros((2, total_latency), dtype=np.float32)

    def _is_output_node(self, node: AudioNodeState) -> bool:
        """判断节点是否为输出节点（无输出连接）"""
        for conn in self._connections:
            if conn.source_id == node.node_id:
                return False
        return True

    def get_total_latency(self) -> int:
        """获取整个图的总延迟"""
        max_latency = 0
        for node in self._nodes.values():
            max_latency = max(max_latency, node.latency_samples)
        return max_latency

    def get_node_count(self) -> int:
        """获取节点数量"""
        return len(self._nodes)

    def get_statistics(self) -> dict:
        """获取渲染图统计信息"""
        return {
            "node_count": len(self._nodes),
            "connection_count": len(self._connections),
            "total_latency_samples": self.get_total_latency(),
            "sample_rate": self._sample_rate,
            "block_size": self._block_size,
        }
