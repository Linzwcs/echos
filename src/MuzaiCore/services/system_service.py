from typing import Optional
from .interfaces import ISystemService
from ..interfaces import IDAWManager, IPluginRegistry
from ..models import ToolResponse


class SystemService(ISystemService):
    """
    系统服务 - 与系统级资源交互
    
    特点：
    - 所有操作都是查询或系统配置
    - 不修改项目状态
    - 不需要Command
    """

    def __init__(self, manager: IDAWManager, registry: IPluginRegistry):
        self._manager = manager
        self._registry = registry

    def list_available_plugins(self,
                               category: Optional[str] = None) -> ToolResponse:
        """
        列出所有可用插件
        
        这是查询Registry，不修改任何状态
        """
        plugins = self._registry.list_plugins()

        if category:
            plugins = [
                p for p in plugins if p.category.value == category.lower()
            ]

        plugin_list = [{
            "unique_id": p.unique_plugin_id,
            "name": p.name,
            "vendor": p.vendor,
            "category": p.category.value
        } for p in plugins]

        return ToolResponse("success", {
            "plugins": plugin_list,
            "count": len(plugin_list)
        }, f"Found {len(plugin_list)} plugin(s)")

    def get_plugin_details(self, plugin_unique_id: str) -> ToolResponse:
        """
        获取插件详细信息
        
        查询Registry中的插件描述符
        """
        descriptor = self._registry.get_plugin_descriptor(plugin_unique_id)
        if not descriptor:
            return ToolResponse("error", None,
                                f"Plugin {plugin_unique_id} not found")

        return ToolResponse(
            "success", {
                "unique_id":
                descriptor.unique_plugin_id,
                "name":
                descriptor.name,
                "vendor":
                descriptor.vendor,
                "category":
                descriptor.category.value,
                "parameters":
                list(descriptor.default_parameters.keys()),
                "ports": [{
                    "port_id": p.port_id,
                    "type": p.port_type.value,
                    "direction": p.direction.value,
                    "channels": p.channel_count
                } for p in descriptor.available_ports]
            }, f"Plugin details for '{descriptor.name}'")

    def get_system_info(self) -> ToolResponse:
        """
        获取系统信息
        
        返回DAW版本、可用服务等
        """
        return ToolResponse(
            "success", {
                "daw_version":
                "MuzaiCore v1.0",
                "architecture":
                "Mock Implementation",
                "available_services": [
                    "project", "transport", "nodes", "routing", "editing",
                    "history", "query", "system"
                ],
                "command_system":
                "enabled",
                "undo_redo":
                "enabled"
            }, "System information")

    def list_audio_devices(self) -> ToolResponse:
        """
        列出音频设备
        
        这是查询DeviceManager，不修改状态
        """
        try:
            device_manager = self._manager.device_manager
            audio_devices = device_manager.get_audio_output_devices()

            device_list = [{
                "device_id": device.id,
                "name": device.name,
                "input_channels": len(device.input_channels),
                "output_channels": len(device.output_channels)
            } for device in audio_devices]

            return ToolResponse("success", {
                "devices": device_list,
                "count": len(device_list)
            }, f"Found {len(device_list)} audio device(s)")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to list audio devices: {str(e)}")

    def list_midi_devices(self) -> ToolResponse:
        """
        列出MIDI设备
        
        这是查询DeviceManager，不修改状态
        """
        try:
            device_manager = self._manager.device_manager
            midi_devices = device_manager.get_midi_input_devices()

            device_list = [{
                "device_id": device.id,
                "name": device.name
            } for device in midi_devices]

            return ToolResponse("success", {
                "devices": device_list,
                "count": len(device_list)
            }, f"Found {len(device_list)} MIDI device(s)")
        except Exception as e:
            return ToolResponse("error", None,
                                f"Failed to list MIDI devices: {str(e)}")
