from enum import Enum


class LifecycleState(Enum):

    CREATED = "created"
    MOUNTING = "mounting"
    MOUNTED = "mounted"
    UNMOUNTING = "unmounting"
    DISPOSED = "disposed"
