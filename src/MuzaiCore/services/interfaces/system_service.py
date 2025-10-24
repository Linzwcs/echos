# file: src/MuzaiCore/services/ISystemService.py
from abc import ABC, abstractmethod
from typing import Optional
from MuzaiCore.models import ToolResponse
from .base_service import IService


class ISystemService(IService):
    """A service for interacting with system-level resources like plugins and devices."""

    @abstractmethod
    def list_available_plugins(self,
                               category: Optional[str] = None) -> ToolResponse:
        """
        Lists all discovered plugins, optionally filtered by category
        ('instrument', 'effect').
        """
        pass

    @abstractmethod
    def get_plugin_details(self, plugin_unique_id: str) -> ToolResponse:
        """Returns the descriptor of a specific plugin (its parameters, ports, etc.)."""
        pass

    @abstractmethod
    def get_system_info(self) -> ToolResponse:
        pass

    @abstractmethod
    def list_audio_devices(self) -> ToolResponse:
        """Lists available audio input and output devices."""
        pass

    @abstractmethod
    def list_midi_devices(self) -> ToolResponse:
        """Lists available MIDI input devices."""
        pass
