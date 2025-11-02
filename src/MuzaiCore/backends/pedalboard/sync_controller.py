from typing import Dict, Optional, List
from .render_graph import PedalboardRenderGraph
from ...interfaces.system.isync import ISyncController
from ...models import event_model


class PedalboardSyncController(ISyncController):

    def __init__(self):
        super().__init__()
        self._render_graph: Optional[PedalboardRenderGraph] = None
        self._node_mapping: Dict[str, str] = {}
        self._plugin_mapping: Dict[str, tuple] = {}
        print("PedalboardSyncController: Created")

    def set_render_graph(self, render_graph: PedalboardRenderGraph):
        self._render_graph = render_graph
        print("PedalboardSyncController: Render graph connected")

    def _get_children(self):
        return []

    def _on_mount(self, event_bus):
        self._event_bus = event_bus

        event_bus.subscribe(event_model.ProjectLoaded, self.on_project_loaded)
        event_bus.subscribe(event_model.ProjectClosed, self.on_project_closed)

        event_bus.subscribe(event_model.NodeAdded, self.on_node_added)
        event_bus.subscribe(event_model.NodeRemoved, self.on_node_removed)
        event_bus.subscribe(event_model.ConnectionAdded,
                            self.on_connection_added)
        event_bus.subscribe(event_model.ConnectionRemoved,
                            self.on_connection_removed)

        event_bus.subscribe(event_model.InsertAdded, self.on_insert_added)
        event_bus.subscribe(event_model.InsertRemoved, self.on_insert_removed)
        event_bus.subscribe(event_model.InsertMoved, self.on_insert_moved)
        event_bus.subscribe(event_model.PluginEnabledChanged,
                            self.on_plugin_enabled_changed)
        event_bus.subscribe(event_model.ParameterChanged,
                            self.on_parameter_changed)

        event_bus.subscribe(event_model.TempoChanged, self.on_tempo_changed)
        event_bus.subscribe(event_model.TimeSignatureChanged,
                            self.on_time_signature_changed)

        event_bus.subscribe(event_model.ClipAdded, self.on_clip_added)
        event_bus.subscribe(event_model.ClipRemoved, self.on_clip_removed)

        event_bus.subscribe(event_model.NoteAdded, self.on_notes_added)
        event_bus.subscribe(event_model.NoteRemoved, self.on_notes_removed)

        print("PedalboardSyncController: Mounted - all events subscribed")

    def _on_unmount(self):

        if not self._event_bus:
            return

        event_bus = self._event_bus
        event_bus.unsubscribe(event_model.ProjectLoaded,
                              self.on_project_loaded)
        event_bus.unsubscribe(event_model.ProjectClosed,
                              self.on_project_closed)
        event_bus.unsubscribe(event_model.NodeAdded, self.on_node_added)
        event_bus.unsubscribe(event_model.NodeRemoved, self.on_node_removed)
        event_bus.unsubscribe(event_model.ConnectionAdded,
                              self.on_connection_added)
        event_bus.unsubscribe(event_model.ConnectionRemoved,
                              self.on_connection_removed)
        event_bus.unsubscribe(event_model.InsertAdded, self.on_insert_added)
        event_bus.unsubscribe(event_model.InsertRemoved,
                              self.on_insert_removed)
        event_bus.unsubscribe(event_model.InsertMoved, self.on_insert_moved)
        event_bus.unsubscribe(event_model.PluginEnabledChanged,
                              self.on_plugin_enabled_changed)
        event_bus.unsubscribe(event_model.ParameterChanged,
                              self.on_parameter_changed)
        event_bus.unsubscribe(event_model.TempoChanged, self.on_tempo_changed)
        event_bus.unsubscribe(event_model.TimeSignatureChanged,
                              self.on_time_signature_changed)
        event_bus.unsubscribe(event_model.ClipAdded, self.on_clip_added)
        event_bus.unsubscribe(event_model.ClipRemoved, self.on_clip_removed)
        event_bus.unsubscribe(event_model.NoteAdded, self.on_notes_added)
        event_bus.unsubscribe(event_model.NoteRemoved, self.on_notes_removed)

        self._event_bus = None
        print("PedalboardSyncController: Unmounted")

    def on_project_loaded(self, event: event_model.ProjectLoaded):
        """
        项目加载 - 全量同步
        
        这是最重要的同步点，需要：
        1. 清空现有图
        2. 重建所有节点
        3. 重建所有连接
        4. 恢复所有参数
        """
        print(f"Sync: Project loaded - '{event.project.name}'")

        if not self._render_graph:
            print("Sync: No render graph available")
            return

        project = event.project

        # 1. 构建所有节点
        for node in project.get_all_nodes():
            self._sync_node_full(node)

        # 2. 构建所有连接
        for connection in project.router.get_all_connections():
            self._sync_connection(connection)

        print(
            f"Sync: Project fully synchronized - {len(project.get_all_nodes())} nodes"
        )

    def on_project_closed(self, event: event_model.ProjectClosed):
        """项目关闭 - 清理所有资源"""
        print(f"Sync: Project closing - '{event.project.name}'")

        # 清空映射
        self._node_mapping.clear()
        self._plugin_mapping.clear()

        # TODO: 清空渲染图
        # self._render_graph.clear()

    # ========================================================================
    # IGraphSync - 图结构事件
    # ========================================================================

    def on_node_added(self, event: event_model.NodeAdded):
        """节点添加"""
        node = event.node
        print(f"Sync: Node added - {node.name} ({node.node_type})")

        if not self._render_graph:
            return

        # 在渲染图中创建对应节点
        self._render_graph.add_node(node.node_id, node.node_type)
        self._node_mapping[node.node_id] = node.node_id

        # 如果是轨道，同步混音器参数
        if hasattr(node, 'mixer_channel'):
            mixer = node.mixer_channel
            self._sync_mixer_parameters(node.node_id, mixer)

    def on_node_removed(self, event: event_model.NodeRemoved):
        """节点移除"""
        print(f"Sync: Node removed - {event.node_id[:8]}")

        if not self._render_graph:
            return

        # 从渲染图移除
        self._render_graph.remove_node(event.node_id)

        # 清理映射
        self._node_mapping.pop(event.node_id, None)

        # 清理相关插件映射
        to_remove = [
            pid for pid, (nid, _) in self._plugin_mapping.items()
            if nid == event.node_id
        ]
        for pid in to_remove:
            self._plugin_mapping.pop(pid)

    def on_connection_added(self, event: event_model.ConnectionAdded):
        """连接添加"""
        conn = event.connection
        print(
            f"Sync: Connection added - {conn.source_port.owner_node_id[:8]} -> {conn.dest_port.owner_node_id[:8]}"
        )

        if not self._render_graph:
            return

        self._render_graph.add_connection(conn.source_port.owner_node_id,
                                          conn.dest_port.owner_node_id)

    def on_connection_removed(self, event: event_model.ConnectionRemoved):
        """连接移除"""
        conn = event.connection
        print(
            f"Sync: Connection removed - {conn.source_port.owner_node_id[:8]} -> {conn.dest_port.owner_node_id[:8]}"
        )

        if not self._render_graph:
            return

        self._render_graph.remove_connection(conn.source_port.owner_node_id,
                                             conn.dest_port.owner_node_id)

    # ========================================================================
    # IMixerSync - 混音器事件
    # ========================================================================

    def on_insert_added(self, event: event_model.InsertAdded):
        """插件插入添加"""
        print(
            f"Sync: Insert added - {event.plugin.descriptor.name} to {event.owner_node_id[:8]}"
        )

        if not self._render_graph:
            return

        # 获取插件文件路径（从描述符）
        # 注意：这需要从 PluginRegistry 获取实际文件路径
        plugin_path = self._get_plugin_path(
            event.plugin.descriptor.unique_plugin_id)

        if plugin_path:
            self._render_graph.add_plugin_to_node(event.owner_node_id,
                                                  plugin_path, event.index)

            # 记录映射
            self._plugin_mapping[event.plugin.node_id] = (event.owner_node_id,
                                                          event.index)

    def on_insert_removed(self, event: event_model.InsertRemoved):
        """插件插入移除"""
        print(
            f"Sync: Insert removed - {event.plugin_id[:8]} from {event.owner_node_id[:8]}"
        )

        if not self._render_graph:
            return

        # 获取插件位置
        mapping = self._plugin_mapping.get(event.plugin_id)
        if mapping:
            node_id, index = mapping
            self._render_graph.remove_plugin_from_node(node_id, index)
            self._plugin_mapping.pop(event.plugin_id)

    def on_insert_moved(self, event: event_model.InsertMoved):
        """插件位置移动"""
        print(
            f"Sync: Insert moved - {event.plugin_id[:8]} from {event.old_index} to {event.new_index}"
        )

        # Pedalboard 不支持直接移动，需要先移除再添加
        # TODO: 实现插件移动

    def on_plugin_enabled_changed(self,
                                  event: event_model.PluginEnabledChanged):
        """插件启用状态改变"""
        print(
            f"Sync: Plugin enabled changed - {event.plugin_id[:8]} -> {event.is_enabled}"
        )

        # Pedalboard 可以通过旁路实现
        # TODO: 实现插件旁路

    def on_parameter_changed(self, event: event_model.ParameterChanged):
        """参数改变"""
        if not self._render_graph:
            return

        # 将参数变化发送到渲染图
        self._render_graph.set_parameter(event.owner_node_id, event.param_name,
                                         event.new_value)

    # ========================================================================
    # ITransportSync - 传输事件
    # ========================================================================

    def on_tempo_changed(self, event: event_model.TempoChanged):
        """速度改变"""
        print(f"Sync: Tempo changed - {event.new_bpm} BPM")
        # Tempo 由 Timeline 管理，引擎会在处理时读取

    def on_time_signature_changed(self,
                                  event: event_model.TimeSignatureChanged):
        """拍号改变"""
        print(
            f"Sync: Time signature changed - {event.numerator}/{event.denominator}"
        )
        # 拍号改变通常不影响音频处理

    # ========================================================================
    # ITrackSync - 轨道事件
    # ========================================================================

    def on_clip_added(self, event: event_model.ClipAdded):
        """片段添加"""
        print(
            f"Sync: Clip added - {event.clip.name} to track {event.owner_track_id[:8]}"
        )
        # 片段数据由 Timeline 管理，在播放时读取

    def on_clip_removed(self, event: event_model.ClipRemoved):
        """片段移除"""
        print(f"Sync: Clip removed - {event.clip_id[:8]}")

    # ========================================================================
    # IClipSync - 片段事件
    # ========================================================================

    def on_notes_added(self, event: event_model.NoteAdded):
        """音符添加"""
        print(
            f"Sync: {len(event.notes)} notes added to clip {event.owner_clip_id[:8]}"
        )
        # 音符数据存储在前端，播放时调度

    def on_notes_removed(self, event: event_model.NoteRemoved):
        """音符移除"""
        print(
            f"Sync: {len(event.notes)} notes removed from clip {event.owner_clip_id[:8]}"
        )

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _sync_node_full(self, node):
        """完整同步单个节点"""
        # 添加节点
        if self._render_graph:
            self._render_graph.add_node(node.node_id, node.node_type)
            self._node_mapping[node.node_id] = node.node_id

        # 如果有混音器，同步参数
        if hasattr(node, 'mixer_channel'):
            self._sync_mixer_parameters(node.node_id, node.mixer_channel)

            # 同步插件
            for i, plugin in enumerate(node.mixer_channel.inserts):
                plugin_path = self._get_plugin_path(
                    plugin.descriptor.unique_plugin_id)
                if plugin_path and self._render_graph:
                    self._render_graph.add_plugin_to_node(
                        node.node_id, plugin_path, i)
                    self._plugin_mapping[plugin.node_id] = (node.node_id, i)

    def _sync_mixer_parameters(self, node_id: str, mixer):
        """同步混音器参数"""
        if not self._render_graph:
            return

        # 音量
        volume_db = mixer.volume.value
        self._render_graph.set_parameter(node_id, "volume", volume_db)

        # 声像
        pan = mixer.pan.value
        self._render_graph.set_parameter(node_id, "pan", pan)

        # 静音/独奏
        self._render_graph.set_parameter(node_id, "muted", mixer.is_muted)

    def _sync_connection(self, connection):
        """同步单个连接"""
        if self._render_graph:
            self._render_graph.add_connection(
                connection.source_port.owner_node_id,
                connection.dest_port.owner_node_id)

    def _get_plugin_path(self, plugin_id: str) -> Optional[str]:
        """
        获取插件文件路径
        
        在实际实现中，这应该：
        1. 查询 PluginRegistry
        2. 返回 VST3/AU 文件的完整路径
        
        示例：
        - macOS: "/Library/Audio/Plug-Ins/VST3/Serum.vst3"
        - Windows: "C:\\Program Files\\VSTPlugins\\Serum.vst3"
        """
        # Mock 实现
        if "basic_synth" in plugin_id:
            # 这里应该返回实际的插件路径
            return None  # Pedalboard 内置效果器

        return None
