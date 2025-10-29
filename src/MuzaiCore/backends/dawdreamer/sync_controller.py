# file: src/MuzaiCore/backends/dawdreamer/sync_controller.py
from typing import List, Optional

from ...interfaces.system import IProject, INode, IPlugin, ITrack
from ...models import Connection, Note, PluginDescriptor
from ...interfaces.system.isync import ISyncController
from .render_graph import DawDreamerRenderGraph


class DawDreamerSyncController(ISyncController):
    """
    DawDreamer 后端的完整同步控制器。
    
    这个类实现了所有 ISync 接口，作为领域模型和渲染图之间的适配器。
    它将高级的领域事件转换为对 RenderGraph 的低级操作。
    """

    def __init__(self, render_graph: DawDreamerRenderGraph):
        self._render_graph = render_graph
        print(
            "DawDreamerSyncController: Initialized with all sync interfaces.")

    # ========================================================================
    # IProjectSync - 项目级别的事件
    # ========================================================================

    def on_project_loaded(self, project: IProject):
        """当项目加载时，执行完整同步"""
        print(
            f"SyncController: Project '{project.name}' loaded, performing full sync."
        )

        # 订阅项目的各个组件
        project.router.subscribe(self)
        project.timeline.subscribe(self)

        # 订阅所有轨道和插件
        for node in project.get_all_nodes():
            if isinstance(node, ITrack):
                node.subscribe_clip_events(self)
                node.mixer_channel.subscribe(self)
                # 订阅所有参数
                for param in node.mixer_channel.get_parameters().values():
                    param.subscribe(self)
            elif isinstance(node, IPlugin):
                node.subscribe(self)
                for param in node.get_parameters().values():
                    param.subscribe(self)

        # 执行完整的图同步
        self._render_graph.full_sync_from_project(project)

    def on_project_closed(self, project: IProject):
        """当项目关闭时，清理所有资源"""
        print(
            f"SyncController: Project '{project.project_id}' closing, cleaning up."
        )

        # 取消所有订阅
        project.router.unsubscribe(self)
        project.timeline.unsubscribe(self)

        # 清空渲染图
        self._render_graph.clear()

    # ========================================================================
    # IGraphSync - 图结构事件
    # ========================================================================

    def on_node_added(self, node: INode):
        """当节点添加到图时"""
        descriptor = getattr(node, 'descriptor', None)

        # 如果是轨道，订阅其事件
        if isinstance(node, ITrack):
            node.subscribe_clip_events(self)
            node.mixer_channel.subscribe(self)
            # 订阅混音器参数
            for param in node.mixer_channel.get_parameters().values():
                param.set_owner(node.node_id)
                param.subscribe(self)

        # 如果是插件，订阅其事件
        elif isinstance(node, IPlugin):
            node.subscribe(self)
            for param in node.get_parameters().values():
                param.set_owner(node.node_id)
                param.subscribe(self)

        # 添加到渲染图
        self._render_graph.add_node(node, descriptor)
        print(f"SyncController: Node {node.node_id[:8]} added and subscribed.")

    def on_node_removed(self, node_id: str):
        """当节点从图中移除时"""
        self._render_graph.remove_node(node_id)
        print(f"SyncController: Node {node_id[:8]} removed.")

    def on_connection_added(self, connection: Connection):
        """当连接被创建时"""
        self._render_graph.add_connection(connection)
        print(f"SyncController: Connection added: "
              f"{connection.source_port.owner_node_id[:8]} -> "
              f"{connection.dest_port.owner_node_id[:8]}")

    def on_connection_removed(self, connection: Connection):
        """当连接被移除时"""
        self._render_graph.remove_connection(connection)
        print(f"SyncController: Connection removed: "
              f"{connection.source_port.owner_node_id[:8]} -X-> "
              f"{connection.dest_port.owner_node_id[:8]}")

    # ========================================================================
    # IMixerSync - 混音器事件
    # ========================================================================

    def on_insert_added(self, owner_node_id: str, plugin: IPlugin, index: int):
        """当插件被添加到轨道的插入链时"""
        # 确保插件节点已经添加到图中
        self.on_node_added(plugin)

        # 更新轨道的插入链
        self._render_graph.add_insert_to_track(owner_node_id, plugin, index)
        print(f"SyncController: Plugin {plugin.descriptor.name} added to "
              f"track {owner_node_id[:8]} at index {index}")

    def on_insert_removed(self, owner_node_id: str, plugin_id: str):
        """当插件从轨道的插入链中移除时"""
        self._render_graph.remove_insert_from_track(owner_node_id, plugin_id)
        print(f"SyncController: Plugin {plugin_id[:8]} removed from "
              f"track {owner_node_id[:8]}")

    def on_insert_moved(self, owner_node_id: str, plugin_id: str,
                        old_index: int, new_index: int):
        """当插件在插入链中移动位置时"""
        # 通过先移除再添加来实现移动
        # 这会触发渲染图的重新连接
        print(f"SyncController: Plugin {plugin_id[:8]} moved in "
              f"track {owner_node_id[:8]} from {old_index} to {new_index}")
        # RenderGraph 会在内部处理这个逻辑
        self._render_graph.move_insert_in_track(owner_node_id, plugin_id,
                                                new_index)

    def on_plugin_enabled_changed(self, plugin_id: str, is_enabled: bool):
        """当插件的启用状态改变时"""
        # 在 DawDreamer 中，可能需要更新插件的旁路状态
        status = "enabled" if is_enabled else "bypassed"
        print(f"SyncController: Plugin {plugin_id[:8]} {status}")
        self._render_graph.set_plugin_bypass(plugin_id, not is_enabled)

    def on_parameter_changed(self, owner_node_id: str, param_name: str,
                             value: Any):
        """当参数值改变时"""
        self._render_graph.set_parameter(owner_node_id, param_name, value)
        # 为了避免日志过多，只在调试模式下打印
        # print(f"SyncController: Parameter '{param_name}' of {owner_node_id[:8]} = {value}")

    # ========================================================================
    # ITransportSync - 传输/时间线事件
    # ========================================================================

    def on_tempo_changed(self, beat: float, new_bpm: float):
        """当速度改变时"""
        print(f"SyncController: Tempo changed at beat {beat} to {new_bpm} BPM")
        self._render_graph.set_tempo_at_beat(beat, new_bpm)

    def on_time_signature_changed(self, beat: float, numerator: int,
                                  denominator: int):
        """当拍号改变时"""
        print(f"SyncController: Time signature changed at beat {beat} "
              f"to {numerator}/{denominator}")
        self._render_graph.set_time_signature_at_beat(beat, numerator,
                                                      denominator)

    # ========================================================================
    # ITrackSync - 轨道内容事件
    # ========================================================================

    def on_clip_added(self, owner_track_id: str, clip: AnyClip):
        """当 clip 添加到轨道时"""
        from ...models import MIDIClip

        print(
            f"SyncController: Clip '{clip.name}' added to track {owner_track_id[:8]}"
        )

        # 如果是 MIDI clip，需要将音符发送到渲染图
        if isinstance(clip, MIDIClip):
            self._render_graph.add_notes_to_instrument(owner_track_id,
                                                       list(clip.notes))

    def on_clip_removed(self, owner_track_id: str, clip_id: str):
        """当 clip 从轨道移除时"""
        print(
            f"SyncController: Clip {clip_id[:8]} removed from track {owner_track_id[:8]}"
        )
        self._render_graph.remove_clip(owner_track_id, clip_id)

    # ========================================================================
    # IClipSync - Clip 内容事件
    # ========================================================================

    def on_notes_added(self, owner_clip_id: str, notes: List[Note]):
        """当音符添加到 MIDI clip 时"""
        print(
            f"SyncController: {len(notes)} notes added to clip {owner_clip_id[:8]}"
        )
        # 需要从 clip_id 找到对应的轨道
        # 这里简化处理，实际需要维护 clip -> track 的映射
        # self._render_graph.update_clip_notes(owner_clip_id, notes)

    def on_notes_removed(self, owner_clip_id: str, notes: List[Note]):
        """当音符从 MIDI clip 移除时"""
        print(
            f"SyncController: {len(notes)} notes removed from clip {owner_clip_id[:8]}"
        )
        # self._render_graph.remove_clip_notes(owner_clip_id, notes)
