# file: src/MuzaiCore/persistence/project_serializer.py
from typing import Optional, Dict, List

from .factory import DawDreamerNodeFactory
from .registry import DawDreamerPluginRegistry
from ...core.timeline import Timeline
from ...core.persistence import ProjectSerializer


class DawDreamerProjectSerializer(ProjectSerializer):

    def __init__(
        self,
        node_factory: DawDreamerNodeFactory,
        plugin_registry: DawDreamerPluginRegistry,
    ):
        self._node_factory = node_factory
        self._registry = plugin_registry
