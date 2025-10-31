from typing import Optional, Dict
from .project import Project
from ..interfaces import (IDAWManager, IProject, IProjectSerializer,
                          IPluginRegistry)

from ..interfaces.system.ifactory import IEngineFactory, INodeFactory
from ..models import ProjectState


class DAWManager(IDAWManager):
    """
    MuzaiCore的通用DAW管理器。
    
    这是系统的主要“组合根”。它不包含任何特定于后端的逻辑，
    而是通过依赖注入接收所有特定于后端的工厂和服务。
    
    职责:
    1. 管理所有活动项目的生命周期。
    2. 使用注入的工厂来创建和反序列化项目。
    3. 为服务层提供一个统一、稳定的入口点。
    """

    def __init__(
        self,
        project_serializer: IProjectSerializer,
        plugin_registry: IPluginRegistry,
        engine_factory: IEngineFactory,
        node_factory: INodeFactory,
    ):
        print("=" * 70)
        print("Initializing Generic Core DAW Manager...")
        print("=" * 70)

        self._projects: Dict[str, IProject] = {}
        self._engine_factory = engine_factory
        self._project_serializer = project_serializer
        self._plugin_registry = plugin_registry
        self._node_factory = node_factory

        print(
            "      ✓ Core Manager is ready. Backend is determined by injected factories."
        )
        print("=" * 70 + "\n")

    # --- 公共属性，以便 Facade 可以访问它们来初始化服务 ---
    @property
    def plugin_registry(self) -> IPluginRegistry:
        return self._plugin_registry

    @property
    def node_factory(self) -> INodeFactory:
        return self._node_factory

    # ========================================================================
    # IDAWManager 接口实现
    # ========================================================================

    def create_project(
        self,
        name: str,
        sample_rate: int = 48000,
        block_size: int = 512,
    ) -> IProject:
        """使用注入的ProjectFactory创建一个新项目。"""
        # 委托给工厂
        project = Project(name=name)
        project.initialize()
        engine = self._engine_factory.create_engine(sample_rate=sample_rate,
                                                    block_size=block_size)
        project.attach_engine(engine)
        self._projects[project.project_id] = project
        return project

    def load_project_from_state(self, state: ProjectState) -> IProject:
        """使用注入的ProjectSerializer反序列化一个项目。"""
        # 委托给序列化器
        project = self._project_serializer.deserialize(state)
        # 假设反序列化后需要附加引擎，这部分逻辑可以在deserialize内部或这里处理
        self._projects[project.project_id] = project
        return project

    def close_project(self, project_id: str) -> bool:
        """关闭一个项目并清理其资源。"""
        if project_id not in self._projects:
            return False

        print(f"\nClosing project and destroying its stack ({project_id})...")
        project = self._projects[project_id]

        # 项目自身负责清理（包括其引擎）
        project.cleanup()

        del self._projects[project_id]
        return True

    def get_project(self, project_id: str) -> Optional[IProject]:
        return self._projects.get(project_id)

    def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        """使用注入的ProjectSerializer序列化一个项目。"""
        project = self.get_project(project_id)
        if not project:
            return None
        # 委托给序列化器
        return self._project_serializer.serialize(project)
