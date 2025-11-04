from enum import Enum


class LifecycleState(Enum):
    """组件生命周期状态"""
    CREATED = "created"
    MOUNTING = "mounting"
    MOUNTED = "mounted"
    UNMOUNTING = "unmounting"
    DISPOSED = "disposed"
