# file: src/MuzaiCore/backends/dawdreamer/engine.py
"""
DawDreamer音频引擎适配器
将IAudioEngine接口适配到DawDreamer的Transport和RenderGraph
"""
from typing import Optional

from ...core.engine import AudioEngine
from ...core.project import Project
from .render_graph import DawDreamerRenderGraph
from .sync_controller import DawDreamerSyncController
from .transport import DawDreamerTransport
from ..common.message_queue import RealTimeMessageQueue
import dawdreamer as daw


class DawDreamerAudioEngine(AudioEngine):
    """
    IAudioEngine的DawDreamer实现
    
    这个类主要是一个包装器，将IAudioEngine的接口委托给
    DawDreamerTransport和DawDreamerRenderGraph
    
    职责：
    - 提供统一的引擎接口
    - 协调Transport和RenderGraph
    - 管理项目引用
    """

    def __init__(
        self,
        transport: DawDreamerTransport,
        sync_controller: DawDreamerSyncController,
    ):
        self._transport = transport
        self._sync_controller = sync_controller
        print("DawDreamerAudioEngine: Initialized")

    @staticmethod
    def create_engine(sample_rate, block_size) -> "DawDreamerAudioEngine":
        """
        静态工厂方法，为给定的项目构建并组装一个完整的音频引擎堆栈。
        """
        print(
            f"    - Building DawDreamer engine stack for (SR={sample_rate}, BS={block_size})..."
        )
        message_queue = RealTimeMessageQueue()
        daw_engine_instance = daw.RenderEngine(sample_rate, block_size)

        render_graph = DawDreamerRenderGraph(message_queue)
        sync_controller = DawDreamerSyncController(render_graph)
        transport = DawDreamerTransport(daw_engine_instance, message_queue,
                                        sample_rate, block_size)
        audio_engine = DawDreamerAudioEngine(transport, sync_controller)

        print("    ✓ Engine stack built.")
        return audio_engine

    def set_project(self, project: Project):
        self._transport.set_project_timeline(project.timeline)
        self._sync_controller.register_event_handlers(project.event_bus)

    def play(self):
        """开始播放"""
        if not self._project:
            print("DawDreamerAudioEngine Warning: No project set")
            return
        self._transport.play()

    def stop(self):
        """停止播放"""
        self._transport.stop()

    def report_latency(self) -> float:
        """
        报告总延迟
        
        包括：
        - 硬件延迟（音频接口）
        - 插件延迟（VST/AU处理）
        - 缓冲延迟（block size）
        """
        # 基础缓冲延迟
        if not self._project:
            return 0.0

        # 从Transport获取配置
        transport_info = self._transport.get_engine_info()
        sample_rate = transport_info['sample_rate']
        block_size = transport_info['block_size']

        # 计算缓冲延迟（秒）
        buffer_latency = block_size / sample_rate

        # TODO: 添加插件延迟
        # 需要遍历所有激活的插件并累加其报告的延迟
        plugin_latency = 0.0

        # TODO: 添加硬件延迟
        # 从音频设备查询
        hardware_latency = 0.0

        total_latency = buffer_latency + plugin_latency + hardware_latency

        return total_latency

    @property
    def is_playing(self) -> bool:
        """返回引擎是否正在播放"""
        return self._transport.is_playing

    @property
    def current_beat(self) -> float:
        """返回当前播放头的节拍位置"""
        return self._transport.get_playback_position_beats()

    # ========================================================================
    # Backend-specific methods
    # ========================================================================

    def get_engine_info(self) -> dict:
        """获取引擎信息（用于调试）"""
        return {
            "type":
            "DawDreamer",
            "is_playing":
            self.is_playing,
            "current_beat":
            self.current_beat,
            "latency_seconds":
            self.report_latency(),
            "has_project":
            self._project is not None,
            "transport":
            self._transport.get_engine_info() if hasattr(
                self._transport, 'get_engine_info') else None
        }

    def __repr__(self) -> str:
        status = "playing" if self.is_playing else "stopped"
        project_name = self._project.name if self._project else "None"
        return f"DawDreamerAudioEngine(project='{project_name}', status={status})"
