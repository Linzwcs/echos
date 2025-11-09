from enum import Flag, auto, Enum


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
