# file: src/MuzaiCore/backends/dawdreamer/manager.py
"""
DawDreamer后端的DAW管理器
这是DawDreamer后端的组合根（Composition Root）
"""
import dawdreamer as daw
from typing import Optional, Dict

from ...interfaces.system import (IDAWManager, IProject, IProjectSerializer,
                                  INodeFactory)
from ...models import ProjectState
from ...core.persistence import ProjectSerializer
from ...core.event_bus import EventBus
from ...core.project import Project
from ...core.router import Router
from ...core.timeline import Timeline
from ...core.history.command_manager import CommandManager

from ..common.message_queue import RealTimeMessageQueue

from .registry import DawDreamerPluginRegistry
from .render_graph import DawDreamerRenderGraph
from .sync_controller import DawDreamerSyncController
from .transport import DawDreamerTransport
from .engine import DawDreamerAudioEngine
from .factory import DawDreamerNodeFactory
from .persistence import DawDreamerProjectSerializer


class DawDreamerDAWManager(IDAWManager):
    """
    DawDreamer后端的DAW管理器
    
    职责：
    1. 管理项目生命周期
    2. 组装所有后端组件
    3. 协调主线程和音频线程
    """

    def __init__(self, node_factory: DawDreamerNodeFactory,
                 registry: DawDreamerPluginRegistry):
        print("=" * 70)
        print("Initializing Definitive DAW Manager...")
        print("=" * 70)

        self._projects: Dict[str, Project] = {}
        self._active_project_id: Optional[str] = None

        self._node_factory: DawDreamerNodeFactory = node_factory
        self._registry = registry
        self._project_serializer = DawDreamerProjectSerializer(
            node_factory, registry)

        print("      ✓ Manager is ready.")
        print("=" * 70 + "\n")

    # ========================================================================
    # 公共属性（后端内部API）
    # ========================================================================

    @property
    def plugin_registry(self) -> DawDreamerPluginRegistry:
        """插件注册表"""
        return self._registry

    @property
    def node_factory(self) -> INodeFactory:
        """节点工厂"""
        return self._node_factory

    # ========================================================================
    # IDAWManager 接口实现
    # ========================================================================
    def _build_project_stack(
        self,
        name: str,
        project_id: Optional[str] = None,
        sample_rate=48000,
        block_size=512,
    ) -> IProject:
        """Factory method to assemble a complete, self-contained IProject instance."""
        print(
            f"  - Building new stack for '{name}' (SR={sample_rate}, BS={block_size})"
        )

        event_bus = EventBus()
        project = Project(name=name,
                          project_id=project_id,
                          sample_rate=sample_rate,
                          block_size=block_size,
                          router=Router(event_bus),
                          timeline=Timeline(event_bus),
                          command_manager=CommandManager(),
                          event_bus=event_bus)

        engine = DawDreamerAudioEngine.create_engine()
        project.set_engine(engine)
        print(f"  ✓ Stack built. Project root: {project.project_id}")
        return project

    def create_project(
        self,
        name: str,
        sample_rate=48000,
        block_size=512,
    ) -> IProject:
        if self._active_project_id:
            self.close_project(self._active_project_id)

        project = self._build_project_stack(name=name,
                                            sample_rate=sample_rate,
                                            block_size=block_size)

        self._projects[project.project_id] = project
        self._active_project_id = project.project_id
        return project

    def load_project_from_state(self, state: ProjectState) -> IProject:
        if self._active_project_id:
            self.close_project(self._active_project_id)

        project = self._project_serializer.deserialize(state)
        self._projects[project.project_id] = project
        self._active_project_id = project.project_id
        return project

    def close_project(self, project_id: str) -> bool:
        if project_id not in self._projects:
            return False

        print(f"\nClosing project and destroying its stack ({project_id})...")
        project = self._projects[project_id]

        project.engine.shutdown()

        del self._projects[project_id]

        if self._active_project_id == project_id:
            self._active_project_id = None

        return True

    def get_project(self, project_id: str) -> Optional[IProject]:
        return self._projects.get(project_id)

    # ========================================================================
    # 调试和监控
    # ========================================================================

    def get_manager_info(self) -> Dict:
        """获取管理器信息（用于调试）"""
        return {
            "backend": "DawDreamer",
            "sample_rate": self._sample_rate,
            "block_size": self._block_size,
            "project_count": len(self._projects),
            "active_project": self._active_project_id,
            "transport_info": self._transport.get_engine_info(),
            "plugin_count": len(self._registry.list_plugins())
        }

    def print_status(self):
        """打印当前状态（用于调试）"""
        info = self.get_manager_info()

        print("\n" + "=" * 70)
        print("DawDreamer Manager Status")
        print("=" * 70)
        print(f"Backend: {info['backend']}")
        print(f"Sample Rate: {info['sample_rate']} Hz")
        print(f"Block Size: {info['block_size']} samples")
        print(
            f"Projects: {info['project_count']} (Active: {info['active_project'] or 'None'})"
        )
        print(f"Available Plugins: {info['plugin_count']}")
        print(f"\nTransport:")
        for key, value in info['transport_info'].items():
            print(f"  {key}: {value}")
        print("=" * 70 + "\n")
