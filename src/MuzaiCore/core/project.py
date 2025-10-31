# file: src/MuzaiCore/core/project.py
"""
修复后的Project - 纯领域模型
移除所有AudioEngine直接调用
"""
import uuid
from typing import Optional, List, Tuple

from ..interfaces.system import (IProject, INode, IRouter, ITimeline,
                                 ICommandManager, IEngine, IEventBus)
from ..interfaces.system.ilifecycle import ILifecycleAware
from ..models.engine_model import TransportStatus
from ..models.event_model import ProjectLoaded, ProjectClosed

from .router import Router
from .timeline import Timeline
from .history.command_manager import CommandManager
from .event_bus import EventBus

from ..models import TransportStatus
from .event_bus import EventBus
from .history.command_manager import CommandManager
from .parameter import Parameter


class Project(IProject):
    """
    优化后的项目类
    作为聚合根管理所有组件
    """

    def __init__(self, name: str, project_id: Optional[str] = None):
        super().__init__()
        self._project_id = project_id or f"project_{uuid.uuid4()}"
        self._name = name

        # 创建核心组件（未挂载）
        self._event_bus_instance = EventBus()
        self._router = Router()
        self._timeline = Timeline()
        self._command_manager = CommandManager()

        # 前端状态
        self._transport_status = TransportStatus.STOPPED
        self._current_beat = 0.0

        # 音频引擎引用（可选）
        self._audio_engine: Optional['IAudioEngine'] = None

    def _get_children(self) -> List[ILifecycleAware]:
        """返回核心组件"""
        return [self._router, self._timeline]

    def _on_mount(self, event_bus):
        """项目使用自己的EventBus"""
        self._event_bus = self._event_bus_instance

    @property
    def project_id(self) -> str:
        return self._project_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def router(self) -> Router:
        return self._router

    @property
    def timeline(self) -> Timeline:
        return self._timeline

    @property
    def command_manager(self) -> CommandManager:
        return self._command_manager

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus_instance

    @property
    def transport_status(self) -> TransportStatus:
        return self._transport_status

    @property
    def current_beat(self) -> float:
        return self._current_beat

    @property
    def tempo(self) -> float:
        return self._timeline.tempo

    @tempo.setter
    def tempo(self, bpm: float):
        self._timeline.set_tempo(bpm)

    @property
    def time_signature(self) -> Tuple[int, int]:
        return self._timeline.time_signature

    @time_signature.setter
    def time_signature(self, value: Tuple[int, int]):
        numerator, denominator = value
        self._timeline.set_time_signature(numerator, denominator)

    def initialize(self):
        """
        初始化项目
        1. 挂载所有组件到EventBus
        2. 启动批量参数更新器
        """
        # 挂载所有组件
        self.mount(self._event_bus_instance)

        # 启动批量参数更新器
        Parameter.initialize_batch_updater(self._event_bus_instance)

        print(f"Project '{self._name}': ✓ Initialized")

    def attach_engine(self, engine: 'IAudioEngine'):
        """
        附加音频引擎
        1. 挂载Engine到EventBus
        2. 触发全量同步
        """

        if not self.is_mounted:
            raise RuntimeError(
                "Project must be initialized before attaching engine")

        if self._audio_engine:
            print("Project: Replacing existing engine")
            self.detach_engine()

        self._audio_engine = engine
        engine.mount(self._event_bus_instance)
        engine.set_timeline(self._timeline)

        # 触发全量同步
        from ..models.event_model import ProjectLoaded
        self._event_bus_instance.publish(ProjectLoaded(project=self))

        print(f"Project '{self._name}': ✓ Engine attached")

    def detach_engine(self):
        """
        分离音频引擎
        1. 通知关闭
        2. 卸载Engine
        """
        if not self._audio_engine:
            return

        # 通知关闭
        from ..models.event_model import ProjectClosed
        self._event_bus_instance.publish(ProjectClosed(project=self))

        self._audio_engine.unmount()
        self._audio_engine = None

        print(f"Project '{self._name}': ✓ Engine detached")

    def add_node(self, node: 'INode'):
        """添加节点（委托给Router）"""
        self._router.add_node(node)

    def remove_node(self, node_id: str):
        """移除节点（委托给Router）"""
        self._router.remove_node(node_id)

    def get_node_by_id(self, node_id: str) -> Optional['INode']:
        """获取节点（委托给Router）"""
        return self._router.get_node_by_id(node_id)

    def get_all_nodes(self) -> List['INode']:
        """获取所有节点（委托给Router）"""
        return self._router.get_all_nodes()

    def cleanup(self):
        """
        清理项目
        1. 分离Engine
        2. 卸载所有组件
        3. 关闭批量更新器
        4. 清理EventBus
        """
        print(f"Project '{self._name}': Cleaning up...")

        # 1. 分离Engine
        if self._audio_engine:
            self.detach_engine()

        # 2. 卸载所有组件
        self.unmount()

        # 3. 关闭批量更新器
        Parameter.shutdown_batch_updater()

        # 4. 清理命令历史
        self._command_manager.clear()

        # 5. 清理EventBus
        self._event_bus_instance.clear()

        print(f"Project '{self._name}': ✓ Cleaned up")

    def validate(self) -> Tuple[bool, List[str]]:
        """验证项目完整性"""
        errors = []

        if self._router.has_cycle():
            errors.append("Graph contains cycles")

        if self.tempo <= 0:
            errors.append(f"Invalid tempo: {self.tempo}")

        for node in self.get_all_nodes():
            if not node.node_id:
                errors.append(f"Node without ID: {type(node).__name__}")

        return len(errors) == 0, errors

    def get_statistics(self) -> dict:
        """获取项目统计信息"""
        nodes = self.get_all_nodes()
        connections = self._router.get_all_connections()

        node_types = {}
        for node in nodes:
            node_type = type(node).__name__
            node_types[node_type] = node_types.get(node_type, 0) + 1

        return {
            "project_id": self._project_id,
            "name": self.name,
            "tempo": self.tempo,
            "time_signature": self.time_signature,
            "transport_status": self._transport_status.value,
            "current_beat": self._current_beat,
            "node_count": len(nodes),
            "node_types": node_types,
            "connection_count": len(connections),
            "has_cycle": self._router.has_cycle(),
            "has_audio_engine": self._audio_engine is not None,
        }

    def __repr__(self) -> str:
        stats = self.get_statistics()
        engine_status = "attached" if self._audio_engine else "no_engine"
        return (f"Project(name='{self.name}', "
                f"nodes={stats['node_count']}, "
                f"tempo={self.tempo}BPM, "
                f"status={self._transport_status.value}, "
                f"engine={engine_status})")
