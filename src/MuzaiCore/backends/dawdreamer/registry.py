# file: src/MuzaiCore/backends/dawdreamer/registry.py
"""
Plugin registry that uses DawDreamer to scan, validate, and extract
metadata from VST3/AU plugins on the filesystem.
"""
import os
import platform
import json
import uuid
from typing import List, Optional, Dict
from pathlib import Path

try:
    import dawdreamer as daw
    DAWDREAMER_AVAILABLE = True
except ImportError:
    DAWDREAMER_AVAILABLE = False

from ...interfaces.system import IPluginRegistry
from ...models import PluginDescriptor, PluginCategory, Port, PortType, PortDirection

from ...interfaces.system import IPluginRegistry
from ...models import PluginDescriptor, PluginCategory, Port, PortType, PortDirection


class DawDreamerPluginRegistry(IPluginRegistry):
    """
    A lightweight registry for discovered plugins.
    It can be populated from a cache or an explicit, heavyweight scanning operation.
    """

    def __init__(self, cache_file: str = "./plugin_cache.json"):
        """
        Initializes a lightweight registry.
        It does NOT create a RenderEngine. It only prepares to load from cache.
        """
        if not DAWDREAMER_AVAILABLE:
            raise ImportError("DawDreamer is required for this registry.")

        self._plugins: Dict[str, PluginDescriptor] = {}
        self._cache_file = Path(cache_file)

        # Attempt to load from cache immediately upon creation.
        self._load_cache()

    # _load_cache and _save_cache methods remain the same.

    def scan_for_plugins(self, force_rescan: bool = False):
        """
        Performs a heavyweight scan for plugins.
        This method temporarily creates and destroys a RenderEngine for discovery.
        """
        if self._plugins and not force_rescan:
            print(
                f"Registry: {len(self._plugins)} plugins already loaded. Use force_rescan=True."
            )
            return

        print("Registry: Starting heavyweight plugin scan...")
        self._plugins.clear()

        # Create a temporary, non-realtime engine ONLY for this scan operation.
        # Use standard defaults, as they rarely affect static plugin properties.
        scan_engine = daw.RenderEngine(44100, 512)

        try:
            scan_paths = self._get_default_scan_paths()
            plugin_files = set()
            for path in scan_paths:
                if os.path.exists(path):
                    for p_file in self._find_plugin_files(path):
                        plugin_files.add(p_file)

            plugin_files_list = list(plugin_files)
            print(
                f"Found {len(plugin_files_list)} potential plugin files. Validating..."
            )
            for i, path in enumerate(plugin_files_list):
                print(
                    f"  [{i+1}/{len(plugin_files_list)}] Scanning: {Path(path).name}"
                )
                # Pass the temporary engine to the validation helper.
                descriptor = self._load_and_validate_plugin(path, scan_engine)
                if descriptor:
                    self._plugins[descriptor.unique_plugin_id] = descriptor

        finally:
            # CRITICAL: Ensure the temporary engine is destroyed no matter what.
            # In Python, simply dereferencing it is enough for GC if no C++-level
            # explicit cleanup is offered.
            print("Registry: Releasing temporary scanning engine.")
            del scan_engine

        self._add_builtin_plugins()
        print(
            f"Registry: Scan complete. Found {len(self._plugins)} valid plugins."
        )
        self._save_cache()

    def get_plugin_descriptor(
            self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        return self._plugins.get(unique_plugin_id)

    def list_plugins(self) -> List[PluginDescriptor]:
        return list(self._plugins.values())

    def _load_cache(self):
        """Loads the plugin cache from a file if it exists."""
        if self._cache_file.exists():
            print(
                f"DawDreamerRegistry: Loading plugins from cache: {self._cache_file}"
            )
            try:
                with self._cache_file.open('r') as f:
                    cached_data = json.load(f)
                    for item in cached_data:
                        # Reconstruct the dataclass from dict
                        # Ensure enums are correctly reconstructed
                        item['category'] = PluginCategory(item['category'])
                        ports = []
                        for p in item.get('available_ports', []):
                            ports.append(
                                Port(owner_node_id=p['owner_node_id'],
                                     port_id=p['port_id'],
                                     port_type=PortType(p['port_type']),
                                     direction=PortDirection(p['direction']),
                                     channel_count=p['channel_count']))
                        item['available_ports'] = ports

                        descriptor = PluginDescriptor(**item)
                        # Optional: Check if the file still exists before adding
                        plugin_path = descriptor.meta.get('path')
                        if plugin_path is None or Path(plugin_path).exists():
                            self._plugins[
                                descriptor.unique_plugin_id] = descriptor
            except Exception as e:
                print(f"DawDreamerRegistry: Failed to load cache: {e}")

        if not self._plugins:
            print("DawDreamerRegistry: No valid cache found.")

    def _save_cache(self):
        """Saves the scanned plugins to a JSON cache file."""
        print(f"DawDreamerRegistry: Saving plugin cache to {self._cache_file}")
        try:
            with self._cache_file.open('w') as f:
                # Convert descriptors to JSON-serializable format
                plugin_list = []
                for desc in self._plugins.values():
                    desc_dict = desc.__dict__.copy()
                    # Convert Enums to their values for JSON serialization
                    desc_dict['category'] = desc.category.value
                    desc_dict['available_ports'] = []
                    for p in desc.available_ports:
                        p_dict = p.__dict__.copy()
                        p_dict['port_type'] = p.port_type.value
                        p_dict['direction'] = p.direction.value
                        desc_dict['available_ports'].append(p_dict)
                    plugin_list.append(desc_dict)
                json.dump(plugin_list, f, indent=2)
        except Exception as e:
            print(f"DawDreamerRegistry: Failed to save cache: {e}")

    def _load_and_validate_plugin(
            self, plugin_path: str) -> Optional[PluginDescriptor]:
        try:
            # Using a unique name for the processor to avoid collisions during scan
            # FIX: 确保导入了 uuid
            processor_name = f"scan_{uuid.uuid4()}"
            processor = self._scan_engine.make_plugin_processor(
                processor_name, plugin_path)
            if not processor:
                return None

            # Extract info
            plugin_name = processor.get_name()
            if not plugin_name:  # Some plugins don't report a name
                plugin_name = Path(plugin_path).stem

            num_inputs = processor.get_num_input_channels()
            num_outputs = processor.get_num_output_channels()

            # DawDreamer's accepts_midi can be unreliable, so we guess based on I/O.
            # An instrument typically has 0 audio inputs but MIDI input and audio outputs.
            accepts_midi = True if hasattr(processor,
                                           'add_midi_note') else False
            is_instrument = accepts_midi and num_inputs == 0 and num_outputs > 0
            is_midi_effect = accepts_midi and num_inputs == 0 and num_outputs == 0

            if is_instrument:
                category = PluginCategory.INSTRUMENT
            elif is_midi_effect:
                category = PluginCategory.MIDI_EFFECT
            else:
                category = PluginCategory.EFFECT

            params = {
                processor.get_parameter_name(i): processor.get_parameter(i)
                for i in range(processor.get_parameter_count())
            }

            ports = []
            if accepts_midi:
                ports.append(
                    Port(owner_node_id="self",
                         port_id="midi_in",
                         port_type=PortType.MIDI,
                         direction=PortDirection.INPUT,
                         channel_count=1))
            if num_inputs > 0:
                ports.append(
                    Port(owner_node_id="self",
                         port_id="audio_in",
                         port_type=PortType.AUDIO,
                         direction=PortDirection.INPUT,
                         channel_count=num_inputs))
            if num_outputs > 0:
                ports.append(
                    Port(owner_node_id="self",
                         port_id="audio_out",
                         port_type=PortType.AUDIO,
                         direction=PortDirection.OUTPUT,
                         channel_count=num_outputs))

            # Create a unique ID that includes the filename to avoid conflicts
            # between VST/VST3 versions of the same plugin.
            unique_id = f"dawdreamer.{plugin_name.lower().replace(' ', '_')}.{Path(plugin_path).name}"

            self._scan_engine.remove_processor(processor_name)  # Cleanup

            return PluginDescriptor(
                unique_plugin_id=unique_id,
                name=plugin_name,
                vendor="Unknown",  # DawDreamer doesn't easily expose this
                category=category,
                available_ports=ports,
                default_parameters=params,
                meta={'path': plugin_path})

        except Exception as e:
            # Catch all to ensure scanning doesn't crash on one bad plugin
            print(f"  - Failed to load {Path(plugin_path).name}: {e}")
            return None

    def _get_default_scan_paths(self) -> List[str]:
        """Returns a list of default VST/AU plugin paths for the current OS."""
        system = platform.system()
        paths = []
        if system == "Windows":
            paths.extend([
                "C:\\Program Files\\Common Files\\VST3",
                "C:\\Program Files\\VSTPlugins",
                "C:\\Program Files\\Steinberg\\VSTPlugins",
            ])
        elif system == "Darwin":  # macOS
            paths.extend([
                "/Library/Audio/Plug-Ins/VST3",
                "/Library/Audio/Plug-Ins/VST",
                "/Library/Audio/Plug-Ins/Components",  # AudioUnits
                "~/Library/Audio/Plug-Ins/VST3",
                "~/Library/Audio/Plug-Ins/VST",
                "~/Library/Audio/Plug-Ins/Components",
            ])
        elif system == "Linux":
            paths.extend([
                "/usr/lib/vst3",
                "/usr/lib/vst",
                "~/.vst3",
                "~/.vst",
            ])
        return [os.path.expanduser(p) for p in paths]

    def _find_plugin_files(self, directory: str) -> List[str]:
        """Recursively finds all files with plugin extensions."""
        plugin_files = []
        # Added .vst3 folder handling if needed, but typically we want the bundle itself.
        # On macOS .vst and .component are directories (bundles).
        # os.walk will go INTO them, which might be wrong depending on how DawDreamer expects paths.
        # Assuming standard file-based for now, but beware of macOS bundles.
        extensions = {'.vst3', '.vst', '.dll', '.so', '.component'}

        if platform.system() == "Darwin":
            # On macOS, we often need to treat .vst/.component/.vst3 bundles as files, not directories to walk into.
            for root, dirs, files in os.walk(directory):
                # Check directories that ARE plugins (bundles)
                for d in dirs:
                    if Path(d).suffix.lower() in extensions:
                        plugin_files.append(os.path.join(root, d))
                # Check individual files (mostly for Linux/Windows .dll/.so)
                for f in files:
                    if Path(f).suffix.lower() in extensions:
                        plugin_files.append(os.path.join(root, f))
        else:
            for root, _, files in os.walk(directory):
                for file in files:
                    if Path(file).suffix.lower() in extensions:
                        plugin_files.append(os.path.join(root, file))

        return plugin_files

    def _add_builtin_plugins(self):
        """Adds built-in DSP as fallback plugins."""
        # This allows the system to function even without external plugins.
        synth_desc = PluginDescriptor(
            unique_plugin_id="muzaicore.builtin.basic_synth",
            name="Basic Synth",
            vendor="MuzaiCore",
            category=PluginCategory.INSTRUMENT,
            available_ports=[
                Port("self", "midi_in", PortType.MIDI, PortDirection.INPUT, 1),
                Port("self", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                     2)
            ],
            default_parameters={
                "attack": 0.01,
                "release": 0.2
            },
            meta={'path': None}  # No path for built-ins
        )
        reverb_desc = PluginDescriptor(
            unique_plugin_id="muzaicore.builtin.simple_reverb",
            name="Simple Reverb",
            vendor="MuzaiCore",
            category=PluginCategory.EFFECT,
            available_ports=[
                Port("self", "audio_in", PortType.AUDIO, PortDirection.INPUT,
                     2),
                Port("self", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                     2)
            ],
            default_parameters={
                "wet": 0.3,
                "dry": 0.7
            },
            meta={'path': None})
        self._plugins[synth_desc.unique_plugin_id] = synth_desc
        self._plugins[reverb_desc.unique_plugin_id] = reverb_desc
