from typing import Dict, Callable, Any

from .messages import (AnyMessage, AddNode, RemoveNode, AddConnection,
                       RemoveConnection, SetParameter, AddPlugin, RemovePlugin,
                       SetBypass, ClearProject, UpdateTrackClips, AddTrackClip,
                       MovePlugin, SetPluginBypass, AddNotesToClip,
                       RemoveNotesFromClip, SetTimelineState, GraphMessage,
                       TimelineMessage)

from .render_graph import PedalboardRenderGraph
from .timeline import RealTimeTimeline
from .context import AudioEngineContext


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
    graph.add_plugin_to_node(msg.owner_node_id, msg.plugin_instance_id,
                             msg.plugin_unique_id, msg.index)


def _handle_remove_plugin(msg: RemovePlugin, graph: PedalboardRenderGraph):
    graph.remove_plugin_from_node(msg.owner_node_id, msg.plugin_instance_id)


def _handle_move_plugin(msg: MovePlugin, graph: PedalboardRenderGraph):
    graph.move_plugin_in_node(msg.owner_node_id, msg.plugin_instance_id,
                              msg.new_index)


def _handle_set_parameter(msg: SetParameter, graph: PedalboardRenderGraph):

    graph.set_parameter(msg.node_id, msg.parameter_path, msg.value)


def _handle_update_track_clips(msg: UpdateTrackClips,
                               graph: PedalboardRenderGraph):
    graph.update_clips_for_track(msg.track_id, msg.clips)


def _handle_add_track_clip(msg: AddTrackClip, graph: PedalboardRenderGraph):
    graph.add_clip_for_track(msg.track_id, msg.clip)


def _handle_timeline_state_changed(msg: SetTimelineState,
                                   timeline: RealTimeTimeline):
    """设置tempo变化"""
    timeline.set_state(msg.timeline_state)
    print(f"[Handler] Info: Tempo change message received (handled by Engine)")


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
    SetParameter: _handle_set_parameter,

    # Clip管理
    UpdateTrackClips: _handle_update_track_clips,
    AddTrackClip: _handle_add_track_clip,
    #AddNotesToClip: _handle_add_notes_to_clip,
    #RemoveNotesFromClip: _handle_remove_notes_from_clip,

    # Timeline管理
    SetTimelineState: _handle_timeline_state_changed
}


def process_message(msg: AnyMessage, context: AudioEngineContext):

    handler = _MESSAGE_HANDLERS.get(type(msg))

    if handler:
        try:
            if isinstance(msg, GraphMessage):
                handler(msg, context.graph)
            elif isinstance(msg, TimelineMessage):
                handler(msg, context.timeline)
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
