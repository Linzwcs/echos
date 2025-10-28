# file: src/MuzaiCore/core/plugin_instance.py
from typing import Dict, List, Optional
#from uuid import uuid4
import uuid
import numpy as np

from ..interfaces.system import IPlugin, IParameter
from ..models import PluginDescriptor, TransportContext, NotePlaybackInfo, Port
from .parameter import Parameter


class Plugin(IPlugin):
    """
    The backend-agnostic domain model for a plugin instance.

    This class represents a plugin in the project's data model. It holds all
    stateful information, such as parameter values and enabled status, but
    contains NO audio processing logic itself.

    The actual DSP is handled by a backend-specific adapter or engine that
    mirrors the state of this object.
    """

    def __init__(self,
                 descriptor: PluginDescriptor,
                 node_id: Optional[str] = None):
        self._node_id = node_id or f"plugin_{uuid.uuid4()}"
        self.descriptor = descriptor
        self._is_enabled = True

        # Instantiate parameters from the descriptor's defaults
        self._parameters: Dict[str, IParameter] = {
            name: Parameter(self._node_id, name, default_value)
            for name, default_value in descriptor.default_parameters.items()
        }

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    def set_enabled(self, enabled: bool):
        self._is_enabled = enabled

    def get_parameters(self) -> Dict[str, IParameter]:
        return self._parameters

    def get_ports(self, port_type: Optional[str] = None) -> List[Port]:
        return self.descriptor.available_ports

    def get_latency_samples(self) -> int:
        """Returns the static latency reported by the plugin descriptor."""
        if self.is_enabled and self.descriptor.reports_latency:
            return self.descriptor.latency_samples
        return 0

    def process_block(self, input_buffer: np.ndarray,
                      notes: List[NotePlaybackInfo],
                      context: TransportContext) -> np.ndarray:
        """
        In the core domain model, a plugin does not process audio itself.
        It acts as a placeholder in the signal chain. The actual processing
        is delegated to a backend-specific implementation.
        This method simply passes the audio through.
        """
        return input_buffer
