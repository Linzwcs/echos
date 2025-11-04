from typing import Dict, List, Optional, Tuple
import pedalboard as pb
from ....interfaces.system import IPluginRegistry, IPluginInstanceManager


class PedalboardPluginInstanceManager(IPluginInstanceManager):

    def __init__(self, registry: IPluginRegistry):
        self._registry = registry
        self._active_instances: Dict[str, pb.Plugin] = {}
        print("PluginInstanceManager: Initialized")

    def create_instance(
            self, instance_id: str,
            unique_plugin_id: str) -> Optional[Tuple[str, pb.Plugin]]:
        descriptor = self._registry.find_by_id(unique_plugin_id)
        if not descriptor:
            print(
                f"Error: Plugin with ID '{unique_plugin_id}' not found in registry."
            )
            return None

        try:
            print(f"Creating instance for: {descriptor.name}")
            plugin_instance = pb.load_plugin(descriptor.path)
            self._active_instances[instance_id] = plugin_instance
            return instance_id, plugin_instance
        except Exception as e:
            print(
                f"Error: Failed to create instance of {descriptor.name}. Reason: {e}"
            )
            return None

    def get_instance(self, instance_id: str) -> Optional[pb.Plugin]:
        return self._active_instances.get(instance_id)

    def release_instance(self, instance_id: str) -> bool:

        if instance_id in self._active_instances:
            print(f"Releasing instance: {instance_id}")
            del self._active_instances[instance_id]
            return True
        print(f"Warning: Instance ID '{instance_id}' not found.")
        return False

    def release_all(self) -> None:

        print("Releasing all active instances.")
        self._active_instances.clear()
