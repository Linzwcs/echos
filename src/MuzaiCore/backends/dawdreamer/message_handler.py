# file: src/MuzaiCore/backends/dawdreamer/message_handler.py
"""
完整的音频线程消息处理器
处理所有从主线程发送到音频线程的消息
"""
from typing import Dict, Callable, Optional, Type
import dawdreamer as daw

from .messages import (AnyMessage, AddNode, RemoveNode, AddConnection,
                       RemoveConnection, SetParameter, AddNotes,
                       SetPluginBypass, SetTempo, SetTimeSignature, RemoveClip,
                       UpdateAutomation)
from ...interfaces.system import ITimeline
from ...models import AutomationLane


class AudioThreadStateHandler:
    """音频线程状态管理器"""

    def __init__(self):
        # 节点ID到处理器名称的映射
        self.node_id_to_processor_name: Dict[str, str] = {}

        # 时间线引用（用于节拍/秒转换）
        self.timeline: Optional[ITimeline] = None

        # 自动化数据
        # 结构: { node_id: { param_name: AutomationLane } }
        self.automation_data: Dict[str, Dict[str, AutomationLane]] = {}

        # 插件路径缓存（用于重新加载）
        self.plugin_paths: Dict[str, str] = {}

        # --- 修正: 新增图结构表示 ---
        # 维护整个音频图的连接。
        # 结构: { "dest_processor_name": ["source_processor_name_1", ...], ... }
        self.graph: Dict[str, List[str]] = {}


# ============================================================================
# 辅助函数 (新)
# ============================================================================


def _rebuild_and_load_graph(engine: daw.RenderEngine,
                            state: AudioThreadStateHandler):
    """
    根据 state.graph 重建DawDreamer图并加载。
    这是处理动态连接的核心。
    """
    try:
        graph_to_load: List[Tuple[daw.Processor, List[str]]] = []

        # 确保所有在图中的节点都存在于引擎中
        all_processors_in_graph = set(state.graph.keys())
        for sources in state.graph.values():
            all_processors_in_graph.update(sources)

        for proc_name in all_processors_in_graph:
            # 检查节点是否仍然由 state 管理
            if proc_name in state.node_id_to_processor_name.values():
                processor = engine.get_processor(proc_name)
                if processor:
                    inputs = state.graph.get(proc_name, [])
                    graph_to_load.append((processor, inputs))

        if graph_to_load:
            engine.load_graph(graph_to_load)
            print("  Audio Thread: Graph reloaded successfully.")
        else:
            # 如果图为空，则清空
            engine.load_graph([])
            print("  Audio Thread: Graph is empty, cleared engine graph.")

    except Exception as e:
        print(f"  Audio Thread Error: Failed to rebuild and load graph: {e}")


# ============================================================================
# 消息处理函数 (已修改)
# ============================================================================


def _handle_add_node(engine: daw.RenderEngine, state: AudioThreadStateHandler,
                     msg: AddNode):
    """添加节点到引擎"""
    processor_name = f"proc_{msg.node_id}"
    state.node_id_to_processor_name[msg.node_id] = processor_name

    try:
        if msg.node_type == 'plugin' and msg.plugin_path:
            engine.make_plugin_processor(processor_name, msg.plugin_path)
            state.plugin_paths[msg.node_id] = msg.plugin_path
            print(
                f"  Audio Thread: Created plugin processor '{processor_name}'")

        elif msg.node_type == 'sum':
            engine.make_add_processor(
                processor_name)  # DawDreamer v0.6+不需要输入列表
            print(f"  Audio Thread: Created sum processor '{processor_name}'")

        else:
            print(
                f"  Audio Thread Warning: Unknown node type '{msg.node_type}'")
            return

        # --- 修正: 将新节点添加到图状态中 ---
        state.graph[processor_name] = []

    except Exception as e:
        print(f"  Audio Thread Error: Failed to add node '{msg.node_id}': {e}")


def _handle_remove_node(engine: daw.RenderEngine,
                        state: AudioThreadStateHandler, msg: RemoveNode):
    """从引擎移除节点"""
    if msg.node_id not in state.node_id_to_processor_name:
        return

    processor_name = state.node_id_to_processor_name.pop(msg.node_id)

    try:
        # --- 修正: 从图状态中移除节点及其所有连接 ---
        # 1. 移除以该节点为目标的所有连接
        state.graph.pop(processor_name, None)
        # 2. 移除以该节点为来源的所有连接
        for dest_name in list(state.graph.keys()):
            if processor_name in state.graph[dest_name]:
                state.graph[dest_name].remove(processor_name)

        # 重建图以应用断开的连接
        _rebuild_and_load_graph(engine, state)

        # 从引擎中移除处理器
        engine.remove_processor(processor_name)

        # 清理其他状态
        if msg.node_id in state.automation_data:
            del state.automation_data[msg.node_id]
        if msg.node_id in state.plugin_paths:
            del state.plugin_paths[msg.node_id]

        print(f"  Audio Thread: Removed processor '{processor_name}'")

    except Exception as e:
        print(
            f"  Audio Thread Error: Failed to remove node '{msg.node_id}': {e}"
        )


def _handle_add_connection(engine: daw.RenderEngine,
                           state: AudioThreadStateHandler, msg: AddConnection):
    """创建连接（通过更新图并重新加载）"""
    source_name = state.node_id_to_processor_name.get(msg.source_node_id)
    dest_name = state.node_id_to_processor_name.get(msg.dest_node_id)

    if not (source_name and dest_name):
        print(f"  Audio Thread Warning: Cannot connect - processor not found")
        return

    # --- 修正: 更新内部图表示 ---
    try:
        # 确保目标节点在图中
        if dest_name not in state.graph:
            state.graph[dest_name] = []

        # 添加源到目标的输入列表
        if source_name not in state.graph[dest_name]:
            state.graph[dest_name].append(source_name)
            print(
                f"  Audio Thread: Added connection '{source_name}' -> '{dest_name}' to internal graph."
            )
            # 应用更改
            _rebuild_and_load_graph(engine, state)
        else:
            print(
                f"  Audio Thread Info: Connection '{source_name}' -> '{dest_name}' already exists."
            )

    except Exception as e:
        print(f"  Audio Thread Error: Failed to add connection: {e}")


def _handle_remove_connection(engine: daw.RenderEngine,
                              state: AudioThreadStateHandler,
                              msg: RemoveConnection):
    """移除连接（通过更新图并重新加载）"""
    source_name = state.node_id_to_processor_name.get(msg.source_node_id)
    dest_name = state.node_id_to_processor_name.get(msg.dest_node_id)

    if not (source_name and dest_name):
        return

    # --- 修正: 更新内部图表示 ---
    try:
        if dest_name in state.graph and source_name in state.graph[dest_name]:
            state.graph[dest_name].remove(source_name)
            print(
                f"  Audio Thread: Removed connection '{source_name}' -X-> '{dest_name}' from internal graph."
            )
            # 应用更改
            _rebuild_and_load_graph(engine, state)
        else:
            print(
                f"  Audio Thread Warning: Connection '{source_name}' -> '{dest_name}' not found to remove."
            )

    except Exception as e:
        print(f"  Audio Thread Error: Failed to remove connection: {e}")


# ... (其余的处理函数 _handle_set_parameter, _handle_add_notes 等保持不变)


def _handle_set_parameter(engine: daw.RenderEngine,
                          state: AudioThreadStateHandler, msg: SetParameter):
    """设置参数值"""
    proc_name = state.node_id_to_processor_name.get(msg.node_id)
    if not proc_name:
        return

    try:
        processor = engine.get_processor(proc_name)

        # 使用名称设置参数（更可靠）
        if hasattr(processor, 'set_parameter_by_name'):
            processor.set_parameter_by_name(msg.param_name, msg.value)
        else:
            # 回退：通过索引查找
            for i in range(processor.get_parameter_count()):
                if processor.get_parameter_name(i) == msg.param_name:
                    processor.set_parameter(i, msg.value)
                    break

    except Exception as e:
        print(f"  Audio Thread Error: Failed to set parameter: {e}")


def _handle_add_notes(engine: daw.RenderEngine, state: AudioThreadStateHandler,
                      msg: AddNotes):
    """添加MIDI音符"""
    proc_name = state.node_id_to_processor_name.get(msg.node_id)
    timeline = state.timeline

    if not (proc_name and timeline):
        return

    try:
        processor = engine.get_processor(proc_name)
        if hasattr(processor, 'add_midi_note'):
            for note in msg.notes:
                # 转换节拍到秒
                start_sec = timeline.beats_to_seconds(note.start_beat)
                duration_sec = timeline.beats_to_seconds(note.duration_beats)

                # 添加MIDI音符
                processor.add_midi_note(note.pitch, note.velocity, start_sec,
                                        duration_sec)

            print(
                f"  Audio Thread: Added {len(msg.notes)} notes to '{proc_name}'"
            )

    except Exception as e:
        print(f"  Audio Thread Error: Failed to add notes: {e}")


def _handle_set_plugin_bypass(engine: daw.RenderEngine,
                              state: AudioThreadStateHandler,
                              msg: SetPluginBypass):
    """设置插件旁路状态"""
    proc_name = state.node_id_to_processor_name.get(msg.node_id)
    if not proc_name:
        return

    try:
        processor = engine.get_processor(proc_name)

        if hasattr(processor, 'set_bypass'):
            processor.set_bypass(msg.bypass)
            status = "bypassed" if msg.bypass else "active"
            print(f"  Audio Thread: Plugin '{proc_name}' {status}")

    except Exception as e:
        print(f"  Audio Thread Error: Failed to set bypass: {e}")


def _handle_set_tempo(engine: daw.RenderEngine, state: AudioThreadStateHandler,
                      msg: SetTempo):
    """设置速度"""
    try:
        engine.set_bpm(msg.bpm)
        print(f"  Audio Thread: Tempo set to {msg.bpm} BPM at beat {msg.beat}")

    except Exception as e:
        print(f"  Audio Thread Error: Failed to set tempo: {e}")


def _handle_set_time_signature(engine: daw.RenderEngine,
                               state: AudioThreadStateHandler,
                               msg: SetTimeSignature):
    """设置拍号"""
    # DawDreamer可能不直接支持拍号
    # 这里只是记录日志
    print(
        f"  Audio Thread: Time signature set to {msg.numerator}/{msg.denominator} at beat {msg.beat}"
    )


def _handle_remove_clip(engine: daw.RenderEngine,
                        state: AudioThreadStateHandler, msg: RemoveClip):
    """移除clip"""
    # 对于DawDreamer，移除clip意味着清除MIDI数据
    proc_name = state.node_id_to_processor_name.get(msg.track_id)
    if not proc_name:
        return

    try:
        processor = engine.get_processor(proc_name)

        if hasattr(processor, 'clear_midi'):
            processor.clear_midi()
            print(f"  Audio Thread: Cleared MIDI from '{proc_name}'")

    except Exception as e:
        print(f"  Audio Thread Error: Failed to remove clip: {e}")


def _handle_update_automation(engine: daw.RenderEngine,
                              state: AudioThreadStateHandler,
                              msg: UpdateAutomation):
    """更新自动化数据"""
    # 存储自动化数据到状态
    if msg.node_id not in state.automation_data:
        state.automation_data[msg.node_id] = {}

    # 创建自动化lane
    lane = AutomationLane(is_enabled=msg.is_enabled, points=msg.points)
    state.automation_data[msg.node_id][msg.param_name] = lane

    print(
        f"  Audio Thread: Updated automation for '{msg.node_id}.{msg.param_name}' "
        f"({len(msg.points)} points)")


# ============================================================================
# 消息处理器
# ============================================================================


class MessageHandler:
    """消息分发器 - 将消息路由到对应的处理函数"""

    def __init__(self):
        self._handlers: Dict[Type[AnyMessage], Callable] = {
            AddNode: _handle_add_node,
            RemoveNode: _handle_remove_node,
            AddConnection: _handle_add_connection,
            RemoveConnection: _handle_remove_connection,
            SetParameter: _handle_set_parameter,
            AddNotes: _handle_add_notes,
            SetPluginBypass: _handle_set_plugin_bypass,
            SetTempo: _handle_set_tempo,
            SetTimeSignature: _handle_set_time_signature,
            RemoveClip: _handle_remove_clip,
            UpdateAutomation: _handle_update_automation,
        }

    def handle(self, msg: AnyMessage, engine: daw.RenderEngine,
               state: AudioThreadStateHandler):
        """
        处理单个消息
        
        在音频线程中调用，必须保证实时安全
        """
        handler = self._handlers.get(type(msg))

        if handler:
            try:
                handler(engine, state, msg)
            except Exception as e:
                # 在实时线程中绝不能崩溃
                print(
                    f"Audio Thread Error: Failed to handle {type(msg).__name__}: {e}"
                )
        else:
            print(
                f"Audio Thread Warning: No handler for message type '{type(msg).__name__}'"
            )
