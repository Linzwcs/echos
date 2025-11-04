# file: src/MuzaiCore/backends/pedalboard/message_handler.py
from typing import Dict, Callable, Any

from .messages import (
    AnyMessage,
    AddNode,
    RemoveNode,
    AddConnection,
    RemoveConnection,
    SetParameter,
    AddPlugin,
    RemovePlugin,
    SetBypass,
    ClearProject,
    UpdateTrackClips,
    AddTrackClip,
    MovePlugin,
    SetNodeParameter,
    SetPluginParameter,
    SetPluginBypass,
    AddNotesToClip,
    RemoveNotesFromClip,
    SetTempos,
    SetTimeSignatures,
)
from .render_graph import PedalboardRenderGraph


def _handle_clear_project(msg: ClearProject, graph: PedalboardRenderGraph):
    """清空整个项目"""
    graph.clear()


def _handle_add_node(msg: AddNode, graph: PedalboardRenderGraph):
    """添加节点"""
    graph.add_node(msg.node_id, msg.node_type)


def _handle_remove_node(msg: RemoveNode, graph: PedalboardRenderGraph):
    """移除节点"""
    graph.remove_node(msg.node_id)


def _handle_add_connection(msg: AddConnection, graph: PedalboardRenderGraph):
    """添加音频连接"""
    graph.add_connection(msg.source_node_id, msg.dest_node_id)


def _handle_remove_connection(msg: RemoveConnection,
                              graph: PedalboardRenderGraph):
    """移除音频连接"""
    graph.remove_connection(msg.source_node_id, msg.dest_node_id)


def _handle_add_plugin(msg: AddPlugin, graph: PedalboardRenderGraph):
    """添加插件到节点"""
    graph.add_plugin_to_node(msg.owner_node_id, msg.plugin_unique_id,
                             msg.index)


def _handle_remove_plugin(msg: RemovePlugin, graph: PedalboardRenderGraph):
    """从节点移除插件"""
    graph.remove_plugin_from_node(msg.owner_node_id, msg.plugin_instance_id)


def _handle_move_plugin(msg: MovePlugin, graph: PedalboardRenderGraph):
    """移动插件位置"""
    node = graph._nodes.get(msg.owner_node_id)
    if not node:
        print(
            f"[Handler] Error: Node {msg.owner_node_id[:8]}... not found for plugin move"
        )
        return

    plugin_instance = node.plugin_instance_map.get(msg.plugin_id)
    if not plugin_instance:
        print(
            f"[Handler] Error: Plugin {msg.plugin_id[:8]}... not found in node"
        )
        return

    try:
        # 从旧位置移除
        old_index = msg.old_index - int(bool(node.instrutment)) if hasattr(
            node, 'instrutment') else msg.old_index
        new_index = msg.new_index - int(bool(node.instrutment)) if hasattr(
            node, 'instrutment') else msg.new_index

        if 0 <= old_index < len(node.pedalboard):
            node.pedalboard.pop(old_index)
            # 插入到新位置
            if new_index >= len(node.pedalboard):
                node.pedalboard.append(plugin_instance)
            else:
                node.pedalboard.insert(new_index, plugin_instance)

            print(
                f"[Handler] ✓ Moved plugin {msg.plugin_id[:8]}... from {msg.old_index} to {msg.new_index}"
            )
        else:
            print(
                f"[Handler] Error: Invalid old_index {old_index} for plugin move"
            )
    except Exception as e:
        print(f"[Handler] Error moving plugin: {e}")


def _handle_set_node_parameter(msg: SetNodeParameter,
                               graph: PedalboardRenderGraph):
    """设置节点参数（mixer参数）"""
    node = graph._nodes.get(msg.node_id)
    if not node:
        print(f"[Handler] Warning: Node {msg.node_id[:8]}... not found")
        return

    try:
        node.set_mix_parameter(msg.parameter_name, msg.value)
    except Exception as e:
        print(
            f"[Handler] Error setting node parameter {msg.parameter_name}: {e}"
        )


def _handle_set_plugin_parameter(msg: SetPluginParameter,
                                 graph: PedalboardRenderGraph):

    node_id = graph.find_node_by_plugin_instance(msg.plugin_instance_id)
    if not node_id:
        print(
            f"[Handler] Warning: Plugin {msg.plugin_instance_id[:8]}... not found in any node"
        )
        return

    node = graph._nodes.get(node_id)
    if not node:
        return

    try:
        node.set_plugin_parameter(msg.plugin_instance_id, msg.parameter_name,
                                  msg.value)
    except Exception as e:
        print(
            f"[Handler] Error setting plugin parameter {msg.parameter_name}: {e}"
        )


def _handle_set_plugin_bypass(msg: SetPluginBypass,
                              graph: PedalboardRenderGraph):

    node_id = graph.find_node_by_plugin_instance(msg.plugin_instance_id)
    if not node_id:
        print(
            f"[Handler] Warning: Plugin {msg.plugin_instance_id[:8]}... not found"
        )
        return

    node = graph._nodes.get(node_id)
    if not node:
        return

    try:
        node.set_plugin_parameter(msg.plugin_instance_id, 'bypass',
                                  msg.is_bypassed)
    except Exception as e:
        print(f"[Handler] Error setting plugin bypass: {e}")


def _handle_set_parameter(msg: SetParameter, graph: PedalboardRenderGraph):

    graph.set_parameter(msg.node_id, msg.parameter_path, msg.value)


def _handle_set_bypass(msg: SetBypass, graph: PedalboardRenderGraph):
    """设置bypass（通用，向后兼容）"""
    param_path = f"plugin.{msg.plugin_instance_id}.bypass"
    graph.set_parameter(msg.node_id, param_path, msg.is_bypassed)


def _handle_update_track_clips(msg: UpdateTrackClips,
                               graph: PedalboardRenderGraph):
    """更新轨道的所有clips"""
    graph.update_clips_for_track(msg.track_id, msg.clips)


def _handle_add_track_clip(msg: AddTrackClip, graph: PedalboardRenderGraph):
    """添加单个clip到轨道"""
    node = graph._nodes.get(msg.track_id)
    if not node:
        print(f"[Handler] Warning: Track {msg.track_id[:8]}... not found")
        return

    if not hasattr(node, 'clips'):
        print(
            f"[Handler] Warning: Node {msg.track_id[:8]}... does not support clips"
        )
        return

    # 添加clip到现有clips列表
    node.clips.append(msg.clip)
    print(
        f"[Handler] ✓ Added clip {msg.clip.clip_id[:8]}... to track {msg.track_id[:8]}..."
    )


def _handle_add_notes_to_clip(msg: AddNotesToClip,
                              graph: PedalboardRenderGraph):
    """添加音符到clip"""
    # 遍历所有节点查找包含该clip的节点
    for node in graph._nodes.values():
        if not hasattr(node, 'clips'):
            continue

        for clip in node.clips:
            if clip.clip_id == msg.clip_id:
                if hasattr(clip, 'notes'):
                    # 添加音符到clip
                    clip.notes.extend(msg.notes)
                    print(
                        f"[Handler] ✓ Added {len(msg.notes)} notes to clip {msg.clip_id[:8]}..."
                    )
                    return

    print(
        f"[Handler] Warning: Clip {msg.clip_id[:8]}... not found in any track")


def _handle_remove_notes_from_clip(msg: RemoveNotesFromClip,
                                   graph: PedalboardRenderGraph):
    """从clip移除音符"""
    # 遍历所有节点查找包含该clip的节点
    for node in graph._nodes.values():
        if not hasattr(node, 'clips'):
            continue

        for clip in node.clips:
            if clip.clip_id == msg.clip_id:
                if hasattr(clip, 'notes'):
                    # 移除指定ID的音符
                    note_ids_set = set(msg.note_ids)
                    clip.notes = [
                        note for note in clip.notes
                        if note.note_id not in note_ids_set
                    ]
                    print(
                        f"[Handler] ✓ Removed {len(msg.note_ids)} notes from clip {msg.clip_id[:8]}..."
                    )
                    return

    print(
        f"[Handler] Warning: Clip {msg.clip_id[:8]}... not found in any track")


def _handle_set_tempos(msg: SetTempos, graph: PedalboardRenderGraph):
    """设置tempo变化"""
    # 这个消息应该由Engine的timeline处理，而不是RenderGraph
    # 这里只是占位，实际实现在Engine中
    print(f"[Handler] Info: Tempo change message received (handled by Engine)")


def _handle_set_time_signatures(msg: SetTimeSignatures,
                                graph: PedalboardRenderGraph):
    """设置拍号变化"""
    # 这个消息应该由Engine的timeline处理，而不是RenderGraph
    # 这里只是占位，实际实现在Engine中
    print(
        f"[Handler] Info: Time signature change message received (handled by Engine)"
    )


# 消息处理器映射表
_MESSAGE_HANDLERS: Dict[Any, Callable] = {
    # 项目管理
    ClearProject: _handle_clear_project,

    # 节点管理
    AddNode: _handle_add_node,
    RemoveNode: _handle_remove_node,

    # 连接管理
    AddConnection: _handle_add_connection,
    RemoveConnection: _handle_remove_connection,

    # 插件管理
    AddPlugin: _handle_add_plugin,
    RemovePlugin: _handle_remove_plugin,
    MovePlugin: _handle_move_plugin,

    # 参数设置（新消息类型）
    SetNodeParameter: _handle_set_node_parameter,
    SetPluginParameter: _handle_set_plugin_parameter,
    SetPluginBypass: _handle_set_plugin_bypass,

    # 参数设置（向后兼容）
    SetParameter: _handle_set_parameter,
    SetBypass: _handle_set_bypass,

    # Clip管理
    UpdateTrackClips: _handle_update_track_clips,
    AddTrackClip: _handle_add_track_clip,
    AddNotesToClip: _handle_add_notes_to_clip,
    RemoveNotesFromClip: _handle_remove_notes_from_clip,

    # Timeline管理
    SetTempos: _handle_set_tempos,
    SetTimeSignatures: _handle_set_time_signatures,
}


def process_message(msg: AnyMessage, graph: PedalboardRenderGraph):

    handler = _MESSAGE_HANDLERS.get(type(msg))
    if handler:
        try:
            handler(msg, graph)
        except Exception as e:
            print(
                f"[Audio Thread Handler] CRITICAL: Error handling {type(msg).__name__}: {e}"
            )
            import traceback
            traceback.print_exc()
    else:
        print(
            f"[Audio Thread Handler] WARNING: No handler for '{type(msg).__name__}'"
        )


def register_custom_handler(message_type: type, handler: Callable):
    _MESSAGE_HANDLERS[message_type] = handler
    print(f"[Handler] Registered custom handler for {message_type.__name__}")


def unregister_handler(message_type: type):
    if message_type in _MESSAGE_HANDLERS:
        del _MESSAGE_HANDLERS[message_type]
        print(f"[Handler] Unregistered handler for {message_type.__name__}")


def get_supported_message_types() -> list:
    return list(_MESSAGE_HANDLERS.keys())
