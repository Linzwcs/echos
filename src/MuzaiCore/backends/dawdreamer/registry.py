# file: src/MuzaiCore/backends/dawdreamer/registry.py
"""
Plugin registry that uses DawDreamer to scan, validate, and extract
metadata from VST3/AU plugins on the filesystem.
"""
import os
import platform
import json
from typing import List, Optional, Dict
from pathlib import Path

try:
    import dawdreamer as daw
    DAWDREAMER_AVAILABLE = True
except ImportError:
    DAWDREAMER_AVAILABLE = False

from ...interfaces.system import IPluginRegistry
from ...models import PluginDescriptor, PluginCategory, Port, PortType, PortDirection


class DawDreamerPluginRegistry(IPluginRegistry):
    """
    Discovers plugins using a temporary DawDreamer engine.
    This implementation is very similar to the original RealPluginRegistry.
    """

    def __init__(self,
                 sample_rate: int = 48000,
                 block_size: int = 512,
                 cache_file: str = "./plugin_cache.json"):
        if not DAWDREAMER_AVAILABLE:
            raise ImportError("DawDreamer is required for this registry.")

        self._plugins: Dict[str, PluginDescriptor] = {}
        self._cache_file = cache_file
        # A temporary, non-realtime engine just for scanning plugins
        self._scan_engine = daw.RenderEngine(sample_rate, block_size)
        self._scan_paths = self._get_default_scan_paths()

    def scan_for_plugins(self):
        print("DawDreamerRegistry: Scanning for plugins...")
        # In a real app, you would implement caching logic here.
        # For simplicity, we perform a full scan every time.
        self._plugins.clear()
        plugin_files = []
        for path in self._scan_paths:
            if os.path.exists(path):
                plugin_files.extend(self._find_plugin_files(path))

        for path in plugin_files:
            descriptor = self._load_and_validate_plugin(path)
            if descriptor:
                self._plugins[descriptor.unique_plugin_id] = descriptor

        # Add built-in fallbacks
        self._add_builtin_plugins()
        print(
            f"DawDreamerRegistry: Scan complete. Found {len(self._plugins)} plugins."
        )

    def get_plugin_descriptor(
            self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        return self._plugins.get(unique_plugin_id)

    def list_plugins(self) -> List[PluginDescriptor]:
        return list(self._plugins.values())

    def _load_and_validate_plugin(
            self, plugin_path: str) -> Optional[PluginDescriptor]:
        try:
            name = Path(plugin_path).stem
            processor = self._scan_engine.make_plugin_processor(
                name, plugin_path)
            if not processor:
                return None

            # Extract info
            plugin_name = processor.get_name()
            num_inputs = processor.get_num_input_channels()
            num_outputs = processor.get_num_output_channels()
            accepts_midi = hasattr(
                processor, 'accepts_midi') and processor.accepts_midi()
            category = PluginCategory.INSTRUMENT if accepts_midi and num_inputs == 0 else PluginCategory.EFFECT

            params = {
                processor.get_parameter_name(i): processor.get_parameter(i)
                for i in range(processor.get_parameter_count())
            }

            ports = []
            if accepts_midi:
                ports.append(
                    Port("self", "midi_in", PortType.MIDI, PortDirection.INPUT,
                         1))
            if num_inputs > 0:
                ports.append(
                    Port("self", "audio_in", PortType.AUDIO,
                         PortDirection.INPUT, num_inputs))
            if num_outputs > 0:
                ports.append(
                    Port("self", "audio_out", PortType.AUDIO,
                         PortDirection.OUTPUT, num_outputs))

            unique_id = f"dawdreamer.{plugin_name.lower().replace(' ', '_')}.{Path(plugin_path).suffix[1:]}"

            self._scan_engine.remove_processor(name)  # Cleanup

            return PluginDescriptor(
                unique_plugin_id=unique_id,
                name=plugin_name,
                vendor="Unknown",  # DawDreamer doesn't easily expose this
                category=category,
                available_ports=ports,
                default_parameters=params,
                meta={'path': plugin_path})
        except Exception as e:
            print(f"  - Failed to load {plugin_path}: {e}")
            return None

    # (Helper methods like _get_default_scan_paths, _find_plugin_files, _add_builtin_plugins would be here)
    # ...
