import uuid
from typing import List, Optional, Dict
import dataclasses
from .mixer import MixerChannel
from ..interfaces.system import ITrack
from ..models import AnyClip, PortType, PortDirection, Port
from ..models.state_model import TrackState
from ..interfaces.system.ilifecycle import ILifecycleAware, IEventBus
from ..interfaces.system.iparameter import IParameter


class Track(ITrack):

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__()
        self._node_id = node_id or f"track_{uuid.uuid4()}"
        self._name = name
        self._clips: Dict[str, AnyClip] = {}
        self._mixer_channel = MixerChannel(self._node_id)
        self._color: Optional[str] = None
        self._icon: Optional[str] = None
        self._ports: dict[str, Port] = {
            "main_in":
            Port(port_id="main_in",
                 port_type=PortType.AUDIO,
                 direction=PortDirection.INPUT,
                 channels=2),
            "main_out":
            Port(port_id="main_out",
                 port_type=PortType.AUDIO,
                 direction=PortDirection.OUTPUT,
                 channels=2)
        }

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def node_type(self) -> str:
        return "track"

    @property
    def name(self) -> str:
        return self._name

    @property
    def clips(self) -> List[AnyClip]:
        return sorted(list(self._clips.values()), key=lambda c: c.start_beat)

    @property
    def mixer_channel(self) -> MixerChannel:
        return self._mixer_channel

    @property
    def color(self) -> Optional[str]:
        return self._color

    @color.setter
    def color(self, value: Optional[str]):
        self._color = value

    def set_name(self, value: str):
        if self._name == value:
            return
        old_name = self._name
        self._name = value
        return old_name

    def add_clip(self, clip: AnyClip):

        self._clips[clip.clip_id] = clip

        if self.is_mounted:
            from ..models.event_model import ClipAdded
            self._event_bus.publish(
                ClipAdded(owner_track_id=self._node_id, clip=clip))

    def remove_clip(self, clip_id: str) -> bool:

        clip = self._clips.pop(clip_id, None)
        if clip:
            if self.is_mounted:
                from ..models.event_model import ClipRemoved
                self._event_bus.publish(
                    ClipRemoved(owner_track_id=self._node_id, clip_id=clip_id))
            return True
        return False

    def get_parameters(self) -> Dict[str, IParameter]:
        return self._mixer_channel.get_parameters()

    def to_state(self) -> TrackState:
        return TrackState(
            node_id=self._node_id,
            node_type=self.node_type,
            name=self._name,
            clips=self.clips,
            mixer_state=self.mixer_channel.to_state(),
        )

    @classmethod
    def from_state(cls, state: TrackState, **kwargs) -> 'Track':
        track = cls(name=state.name, node_id=state.node_id)
        track._clips = {c.clip_id: c for c in state.clips}
        track._mixer_channel = MixerChannel.from_state(state.mixer_state,
                                                       **kwargs)
        return track

    def to_dict(self) -> dict:

        return {
            "node_id": self._node_id,
            "name": self._name,
            "color": self._color,
            "clips": [dataclasses.asdict(c) for c in self.clips],
            "mixer_channel": self._mixer_channel.to_dict()
        }

    def get_ports(self) -> dict[str, Port]:
        return self._ports

    def get_port_by_id(self, port_id: str) -> Optional[Port]:
        return self._ports.get(port_id, None)

    def _on_mount(self, event_bus: IEventBus):
        self._event_bus = event_bus

    def _on_unmount(self):
        self._event_bus = None

    def _get_children(self) -> List[ILifecycleAware]:
        return [self._mixer_channel]


class InstrumentTrack(Track):

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "InstrumentTrack"


class AudioTrack(Track):

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "AudioTrack"


class BusTrack(Track):

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "BusTrack"


class MasterTrack(BusTrack):

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "MasterTrack"


class VCATrack(ITrack):

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "VCATrack"
