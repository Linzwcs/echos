from abc import ABC, abstractmethod
from typing import List, Optional
from .ievent_bus import IEventBus
from ...models.lifecycle_model import LifecycleState


class ILifecycleAware(ABC):
    """
    统一的生命周期接口
    所有需要挂载到EventBus的组件都应继承此类
    """

    def __init__(self):
        self._lifecycle_state = LifecycleState.CREATED
        self._event_bus: Optional['IEventBus'] = None

    @property
    def lifecycle_state(self) -> LifecycleState:
        """当前生命周期状态"""
        return self._lifecycle_state

    @property
    def is_mounted(self) -> bool:
        """是否已挂载"""
        return self._lifecycle_state == LifecycleState.MOUNTED

    @property
    def event_bus(self) -> Optional['IEventBus']:
        """获取EventBus引用"""
        return self._event_bus

    def mount(self, event_bus: 'IEventBus'):
        """挂载到EventBus"""
        if self._lifecycle_state == LifecycleState.MOUNTED:
            return

        if self._lifecycle_state == LifecycleState.DISPOSED:
            raise RuntimeError(
                f"{self.__class__.__name__}: Cannot mount disposed component")

        try:
            self._lifecycle_state = LifecycleState.MOUNTING
            self._event_bus = event_bus

            # 子类实现的挂载逻辑
            self._on_mount(event_bus)

            # 递归挂载子组件
            for child in self._get_children():
                if isinstance(child, ILifecycleAware):
                    child.mount(event_bus)

            self._lifecycle_state = LifecycleState.MOUNTED

        except Exception as e:
            self._lifecycle_state = LifecycleState.CREATED
            self._event_bus = None
            raise RuntimeError(
                f"{self.__class__.__name__}: Mount failed: {e}") from e

    def unmount(self):
        """从EventBus卸载"""
        if self._lifecycle_state != LifecycleState.MOUNTED:
            return
        try:
            self._lifecycle_state = LifecycleState.UNMOUNTING

            # 先卸载子组件
            for child in reversed(self._get_children()):
                if isinstance(child, ILifecycleAware):
                    child.unmount()

            # 子类实现的卸载逻辑
            self._on_unmount()

            self._event_bus = None
            self._lifecycle_state = LifecycleState.CREATED

        except Exception as e:
            self._event_bus = None
            self._lifecycle_state = LifecycleState.CREATED
            print(f"{self.__class__.__name__}: Unmount error: {e}")

    def dispose(self):
        """销毁组件（不可逆）"""
        self.unmount()
        self._lifecycle_state = LifecycleState.DISPOSED

    @abstractmethod
    def _on_mount(self, event_bus: 'IEventBus'):
        """挂载时的钩子（子类重写）"""
        pass

    @abstractmethod
    def _on_unmount(self):
        """卸载时的钩子（子类重写）"""
        pass

    @abstractmethod
    def _get_children(self) -> List['ILifecycleAware']:
        """返回所有子组件（子类必须实现）"""
        return []
