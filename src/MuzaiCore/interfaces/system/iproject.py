# file: src/MuzaiCore/interfaces/IProject.py
from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING, Tuple
from .inode import INode
from .irouter import IRouter
from .itimeline import ITimeline
from .icommand import ICommandManager
from .ievent_bus import IEventBus
from .ilifecycle import ILifecycleAware
from ...models import TransportStatus


class IProject(ILifecycleAware, ABC):
    """
    纯前端Project接口
    
    改变：
    - ❌ 删除 play/stop 方法（音频控制交给Engine）
    - ✓ 保留所有领域逻辑
    - ✓ 保留事件发布
    """

    @property
    @abstractmethod
    def project_id(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def router(self) -> IRouter:
        """逻辑图管理"""
        pass

    @property
    @abstractmethod
    def timeline(self) -> ITimeline:
        """时间线数据"""
        pass

    @property
    @abstractmethod
    def command_manager(self) -> ICommandManager:
        """命令管理（撤销/重做）"""
        pass

    @property
    @abstractmethod
    def transport_status(self) -> TransportStatus:
        """传输状态（仅前端显示）"""
        pass

    # ✓ 保留：生命周期
    @abstractmethod
    def cleanup(self):
        """清理资源"""
        pass

    def _on_mount(self, event_bus: IEventBus):
        pass

    def _on_unmount(self):
        pass
