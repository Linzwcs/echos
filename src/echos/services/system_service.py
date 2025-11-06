# file: src/MuzaiCore/services/system_service.py
from typing import Optional
import dataclasses
from ..interfaces import IDAWManager, ISystemService, IPluginRegistry
from ..models import ToolResponse


class SystemService(ISystemService):

    def __init__(self, manager: IDAWManager):
        self._manager = manager
        self._plugin_registry: IPluginRegistry = manager.plugin_registry

    def list_available_plugins(self,
                               category: Optional[str] = None) -> ToolResponse:
        plugins = self._plugin_registry.list_plugins()
        if category:
            plugins = [p for p in plugins if p.category.value == category]
        data = [{
            "id": p.unique_plugin_id,
            "name": p.name,
            "vendor": p.vendor,
            "category": p.category.value
        } for p in plugins]
        return ToolResponse("success", {"plugins": data},
                            f"Found {len(data)} available plugins.")

    def get_plugin_details(self, plugin_unique_id: str) -> ToolResponse:
        descriptor = self._plugin_registry.get_plugin_descriptor(
            plugin_unique_id)
        if not descriptor:
            return ToolResponse("error", None,
                                f"Plugin '{plugin_unique_id}' not found.")

        # Dataclasses.asdict is useful for serialization
        data = dataclasses.asdict(descriptor)
        # Convert enum to string for clean JSON output
        data['category'] = descriptor.category.value
        return ToolResponse(
            "success", data,
            f"Details for plugin '{descriptor.name}' retrieved.")

    def get_system_info(self) -> ToolResponse:
        info = {
            "core_version":
            "0.1.0-alpha",
            "status":
            "Operational",
            "active_projects":
            len(getattr(self._manager, '_projects', {})),
            "backend":
            self._manager.node_factory.__class__.__name__.replace(
                "NodeFactory", "")
        }
        return ToolResponse("success", info, "System information retrieved.")

    def list_audio_devices(self) -> ToolResponse:
        # In a real app, this would use a DeviceManager. Here we mock it.
        mock_devices = [{
            "id": "0",
            "name": "Built-in Microphone",
            "inputs": 2,
            "outputs": 0
        }, {
            "id": "1",
            "name": "Built-in Output",
            "inputs": 0,
            "outputs": 2
        }, {
            "id": "2",
            "name": "Focusrite Scarlett 2i2",
            "inputs": 2,
            "outputs": 2
        }]
        return ToolResponse("success", {"devices": mock_devices},
                            "Mock audio devices listed.")

    def list_midi_devices(self) -> ToolResponse:
        # Mocked response
        mock_devices = [{
            "id": "midi_in_0",
            "name": "Keystation Mini 32"
        }, {
            "id": "midi_in_1",
            "name": "IAC Driver Bus 1"
        }]
        return ToolResponse("success", {"devices": mock_devices},
                            "Mock MIDI devices listed.")
