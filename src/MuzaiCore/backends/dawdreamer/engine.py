# file: src/MuzaiCore/backends/dawdreamer/engine.py
from typing import Optional
from ...interfaces.system import IAudioEngine, IProject, ITransport
from .render_graph import DawDreamerRenderGraph


class DawDreamerAudioEngine(IAudioEngine):
    """
    IAudioEngine 的 DawDreamer 实现。
    这个类主要是一个包装器，将 IAudioEngine 的接口委托给
    DawDreamerTransport 和 DawDreamerRenderGraph。
    """

    def __init__(self, transport: ITransport,
                 render_graph: Optional[DawDreamerRenderGraph]):
        self._transport = transport
        self._render_graph = render_graph  # RenderGraph可能在之后设置
        self._project: Optional[IProject] = None
        self._current_beat = 0.0  # 模拟播放头

    def set_project(self, project: IProject):
        self._project = project
        self._transport.set_project_timeline(project.timeline)

    def play(self):
        self._transport.play()

    def stop(self):
        self._transport.stop()

    def render_next_block(self):
        # 在 DawDreamer 后端，这是由 sounddevice 的回调自动处理的，
        # 所以这个方法可以留空或用于非实时渲染。
        pass

    def report_latency(self) -> float:
        # 实际实现将查询硬件和插件延迟
        return 0.0

    @property
    def is_playing(self) -> bool:
        return self._transport.is_playing

    @property
    def current_beat(self) -> float:
        # 真实的播放头位置应由 transport 提供
        return self._transport.get_playback_position_beats()

    # --- Backend-specific methods ---
    def set_render_graph(self, render_graph: DawDreamerRenderGraph):
        """Allows deferred setting of the render graph."""
        self._render_graph = render_graph
