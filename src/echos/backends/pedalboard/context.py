from dataclasses import dataclass
from .render_graph import PedalboardRenderGraph
from .timeline import RealTimeTimeline


@dataclass
class AudioEngineContext:
    graph: PedalboardRenderGraph
    timeline: RealTimeTimeline
