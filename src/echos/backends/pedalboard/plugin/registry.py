import os
import platform
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import asdict
from uuid import uuid4
import pedalboard as pb
import gc
from ....core.plugin import PluginCache
from ....interfaces.system import IPluginRegistry
from ....models import PluginDescriptor, CachedPluginInfo


class PedalboardPluginRegistry(IPluginRegistry):

    def __init__(self, cache: PluginCache):
        self._cache = cache
        self._registry_by_id: Dict[str, PluginDescriptor] = {}
        self._registry_by_path: Dict[str, PluginDescriptor] = {}

    def load(self) -> None:

        self._cache.load()
        search_paths = self._get_plugin_search_paths()

        if not search_paths:
            print("Warning: No plugin search paths found or configured.")
            return

        print(f"Scanning for plugins in: {search_paths}")

        found_paths_on_disk = set()
        plugin_extensions = {".vst3", ".component"}

        max_count = 0

        for folder in search_paths:
            if max_count == 3:
                break

            for root, dirs, _ in os.walk(folder):
                if max_count == 3:
                    break

                for d in list(dirs):
                    if max_count == 3:
                        break
                    path = Path(root) / d

                    if path.suffix.lower() in plugin_extensions:
                        found_paths_on_disk.add(path)

                        if str(path.resolve()) in self._registry_by_path:
                            continue

                        cached_info = self._cache.get_valid_entry(path)
                        if cached_info:
                            print(f"  [CACHE] Loading {path.name}")
                            descriptor = cached_info.descriptor
                        else:
                            print(f"  [SCAN]  Scanning {path.name}...")
                            try:

                                plugin = pb.load_plugin(str(path.resolve()))
                                unique_id = f"{plugin.manufacturer_name}::{plugin.name}::{path.suffix}"
                                descriptor = PluginDescriptor(
                                    unique_plugin_id=unique_id,
                                    name=plugin.name,
                                    vendor=plugin.manufacturer_name,
                                    path=str(path.resolve()),
                                    is_instrument=plugin.is_instrument,
                                    plugin_format=path.suffix,
                                    default_parameters={
                                        p_name: {
                                            "min": p.range[0],
                                            "max": p.range[1],
                                            "default": p.raw_value
                                        }
                                        for p_name, p in
                                        plugin.parameters.items()
                                    })

                                new_cache_info = CachedPluginInfo(
                                    descriptor=descriptor,
                                    file_mod_time=path.stat().st_mtime)
                                self._cache.store_entry(
                                    path.resolve(), new_cache_info)

                                del plugin
                                gc.collect()

                            except Exception as e:
                                print(
                                    f"    -> Failed to load plugin {path.name}: {e}"
                                )
                                continue

                        if descriptor.unique_plugin_id not in self._registry_by_id:
                            self._registry_by_id[
                                descriptor.unique_plugin_id] = descriptor
                            self._registry_by_path[str(
                                path.resolve())] = descriptor

                        max_count += 1

        cached_paths = set(self._cache.get_all_cached_paths())
        removed_paths = cached_paths - found_paths_on_disk
        for path in removed_paths:
            print(
                f"  [CLEAN] Removing uninstalled plugin from cache: {path.name}"
            )
            self._cache.remove_entry(path)

        self._cache.persist()
        print(f"Registry loaded. Total plugins: {len(self._registry_by_id)}")

    def list_all(self) -> List[PluginDescriptor]:
        return list(self._registry_by_id.values())

    def find_by_id(self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        return self._registry_by_id.get(unique_plugin_id)

    def find_by_path(self, path: str) -> Optional[PluginDescriptor]:
        return self._registry_by_path.get(str(Path(path).resolve()))

    def _get_plugin_search_paths(self) -> List[Path]:

        system = platform.system()
        paths = []

        if system == "Windows":
            common_paths = [
                Path(
                    os.environ.get("COMMONPROGRAMFILES",
                                   "C:/Program Files/Common Files")) / "VST3"
            ]
            paths.extend(common_paths)
        elif system == "Darwin":  # macOS
            paths.extend([
                Path("/Library/Audio/Plug-Ins/VST3"),
                Path.home() / "Library/Audio/Plug-Ins/VST3",
                Path("/Library/Audio/Plug-Ins/Components"),
                Path.home() / "Library/Audio/Plug-Ins/Components",
            ])
        else:  # Linux
            paths.extend([
                Path("/usr/lib/vst3"),
                Path.home() / ".vst3",
            ])

        return [p for p in paths if p.exists()]
