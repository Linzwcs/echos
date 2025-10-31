# file: src/MuzaiCore/core/track.py
from enum import Flag, auto, Enum
import uuid
from typing import List, Optional, Dict, Set, Tuple, Any
import numpy as np

from ..interfaces.system import ITrack, IMixerChannel, IEventBus
from ..models import (Port, PortType, PortDirection, AnyClip, MIDIClip,
                      AudioClip, Note, TransportContext, NotePlaybackInfo)
from ..models.event_model import ClipAdded, ClipRemoved, NodeRemoved, NodeRenamed
from .mixer import MixerChannel
from .parameter import VCAParameter
from ..interfaces.system.ilifecycle import ILifecycleAware
from ..interfaces.system.iparameter import IParameter


# (VCAControlMode and TrackRecordMode enums remain unchanged)
class VCAControlMode(Flag):
    NONE = 0
    VOLUME = auto()
    PAN = auto()
    MUTE = auto()
    ALL = VOLUME | PAN | MUTE

    def controls_volume(self) -> bool:
        return bool(self & VCAControlMode.VOLUME)

    def controls_pan(self) -> bool:
        return bool(self & VCAControlMode.PAN)

    def controls_mute(self) -> bool:
        return bool(self & VCAControlMode.MUTE)


class TrackRecordMode(Enum):
    NORMAL = "normal"
    OVERDUB = "overdub"
    REPLACE = "replace"
    LOOP = "loop"


class Track(ITrack):
    """
    优化后的轨道基类
    自动管理混音器通道的生命周期
    """

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__()
        self._node_id = node_id or f"track_{uuid.uuid4()}"
        self._name = name
        self._clips: Dict[str, AnyClip] = {}
        self._mixer_channel = MixerChannel(self._node_id)
        self._color: Optional[str] = None
        self._icon: Optional[str] = None

    def _get_children(self) -> List[ILifecycleAware]:
        """返回混音器通道"""
        return [self._mixer_channel]

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def node_type(self) -> str:
        return "track"

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        """设置轨道名称"""
        if self._name == value:
            return

        old_name = self._name
        self._name = value

        if self.is_mounted:
            from ..models.event_model import NodeRenamed
            self._event_bus.publish(
                NodeRenamed(node_id=self._node_id,
                            old_name=old_name,
                            new_name=value))

    @property
    def clips(self) -> List[AnyClip]:
        """获取所有片段"""
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

    def add_clip(self, clip: AnyClip):
        """添加片段"""
        self._clips[clip.clip_id] = clip

        if self.is_mounted:
            from ..models.event_model import ClipAdded
            self._event_bus.publish(
                ClipAdded(owner_track_id=self._node_id, clip=clip))

    def remove_clip(self, clip_id: str) -> bool:
        """移除片段"""
        clip = self._clips.pop(clip_id, None)
        if clip:
            if self.is_mounted:
                from ..models.event_model import ClipRemoved
                self._event_bus.publish(
                    ClipRemoved(owner_track_id=self._node_id, clip_id=clip_id))
            return True
        return False

    def get_parameters(self) -> Dict[str, IParameter]:
        """获取所有参数"""
        return self._mixer_channel.get_parameters()

    def to_dict(self) -> dict:
        """序列化为字典"""
        import dataclasses
        return {
            "node_id": self._node_id,
            "name": self._name,
            "color": self._color,
            "clips": [dataclasses.asdict(c) for c in self.clips],
            "mixer_channel": self._mixer_channel.to_dict()
        }


class InstrumentTrack(Track):
    """乐器轨道"""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "InstrumentTrack"


class AudioTrack(Track):
    """音频轨道"""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "AudioTrack"


class BusTrack(Track):
    """总线轨道"""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "BusTrack"


class MasterTrack(BusTrack):
    """The final output track in the signal chain."""

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "MasterTrack"


class VCATrack(ITrack):
    """
    VCA轨道 - 纯控制层实现
    """

    def __init__(self, name: str, node_id: Optional[str] = None):
        super().__init__(name, node_id)

    @property
    def node_type(self) -> str:
        return "VCATrack"
