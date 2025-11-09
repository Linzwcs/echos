from dataclasses import dataclass
from .router_state import RouterState
from .timeline_state import TimelineState
from .base_state import BaseState


@dataclass(frozen=True)
class ProjectState(BaseState):

    project_id: str
    name: str

    router: RouterState
    timeline: TimelineState

    sample_rate: int = 48000
    block_size: int = 512
    output_channels: int = 2
