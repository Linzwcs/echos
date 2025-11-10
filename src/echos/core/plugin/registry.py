import time
from pathlib import Path
from typing import Dict, List, Optional
from .scanner import PluginScanner
from .cache import PluginCache
from ...interfaces.system import IPluginRegistry
from ...models import PluginDescriptor, CachedPluginInfo


class PluginRegistry(IPluginRegistry):

    def __init__(self, scanner: PluginScanner, cache: PluginCache):
        self._scanner = scanner
        self._cache = cache

        self._registry_by_id: Dict[str, PluginDescriptor] = {}
        self._registry_by_path: Dict[Path, PluginDescriptor] = {}

    def load(self) -> None:
        print("Loading registry from cache...")
        self._cache.load()
        self.clear()

        for path in self._cache.get_all_cached_paths():
            cached_info = self._cache.get_valid_entry(path)
            if cached_info:
                self._add_to_memory(cached_info.descriptor)

        print(f"Registry loaded with {len(self._registry_by_id)} plugins.")

    def update(self, force_rescan: bool = False) -> None:
        print("\n--- Starting Registry Update ---")
        start_time = time.time()

        search_paths = self._scanner.get_default_search_paths()
        paths_on_disk = set(self._scanner.scan_plugin_paths(search_paths))
        cached_paths = set(self._cache.get_all_cached_paths())

        for path in (cached_paths - paths_on_disk):
            print(f"  [REMOVED] Forgetting '{path.name}'")
            self._remove_plugin(path)

        for path in paths_on_disk:
            try:
                current_mod_time = path.stat().st_mtime
                cached_entry = self._cache.get_valid_entry(path)

                is_new = cached_entry is None
                is_updated = not is_new and cached_entry.file_mod_time != current_mod_time

                if force_rescan or is_new or is_updated:
                    status = "NEW" if is_new else "UPDATED"
                    print(f"  [{status}] Scanning '{path.name}'...")
                    self._scan_and_update_plugin(path, current_mod_time)
            except FileNotFoundError:
                if path in cached_paths:
                    self._remove_plugin(path)

        self._cache.persist()
        end_time = time.time()
        print(
            f"--- Registry Update Complete in {end_time - start_time:.2f}s ---"
        )

    def clear(self):
        self._registry_by_id.clear()
        self._registry_by_path.clear()

    def list_all(self) -> List[PluginDescriptor]:
        return list(self._registry_by_id.values())

    def find_by_id(self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        return self._registry_by_id.get(unique_plugin_id)

    def find_by_path(self, path: Path) -> Optional[PluginDescriptor]:
        return self._registry_by_path.get(path.resolve())

    def _scan_and_update_plugin(self, path: Path, mod_time: float):

        scan_result = self._scanner.scan_plugin_safe(path)

        if scan_result.success:
            try:
                descriptor = PluginDescriptor(**scan_result.plugin_info)
                cached_info = CachedPluginInfo(descriptor=descriptor,
                                               file_mod_time=mod_time)

                self._cache.store_entry(path, cached_info)

                self._remove_from_memory(path)
                self._add_to_memory(descriptor)

                print(f"    -> Success: Registered '{descriptor.name}'")
            except (TypeError, KeyError) as e:
                print(
                    f"    -> Error: Scan data for '{path.name}' is malformed. {e}"
                )
        else:
            print(f"    -> Failed: {scan_result.error}")

            self._remove_plugin(path)

    def _add_to_memory(self, descriptor: PluginDescriptor):
        path = Path(descriptor.path).resolve()
        self._registry_by_id[descriptor.unique_plugin_id] = descriptor
        self._registry_by_path[path] = descriptor

    def _remove_from_memory(self, path: Path):
        resolved_path = path.resolve()
        descriptor = self._registry_by_path.pop(resolved_path, None)
        if descriptor:
            self._registry_by_id.pop(descriptor.unique_plugin_id, None)

    def _remove_plugin(self, path: Path):
        self._remove_from_memory(path)
        self._cache.remove_entry(path)
