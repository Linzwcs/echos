from typing import Dict, List, Optional
from pathlib import Path
import json
from dataclasses import asdict
from ..interfaces.system import IPluginCache
from ..models import CachedPluginInfo, PluginDescriptor


class PluginCache(IPluginCache):

    def __init__(self,
                 cache_file_path: Path = Path.home() / ".muzaicache.json"):
        self._cache_file = cache_file_path
        self._cache: Dict[str, CachedPluginInfo] = {}
        print(f"Cache file will be stored at: {self._cache_file}")

    def load(self) -> None:
        if not self._cache_file.exists():
            self._cache = {}
            return
        try:
            with open(self._cache_file, 'r') as f:
                data = json.load(f)
                self._cache = {
                    path:
                    CachedPluginInfo(
                        descriptor=PluginDescriptor(**info['descriptor']),
                        file_modification_time=info['file_modification_time'])
                    for path, info in data.items()
                }
        except (json.JSONDecodeError, KeyError) as e:
            print(
                f"Warning: Could not load cache file, it might be corrupt. Error: {e}"
            )
            self._cache = {}

    def persist(self) -> None:
        try:
            data_to_persist = {
                path: {
                    'descriptor': asdict(info.descriptor),
                    'file_modification_time': info.file_modification_time
                }
                for path, info in self._cache.items()
            }
            with open(self._cache_file, 'w') as f:
                json.dump(data_to_persist, f, indent=4)
        except Exception as e:
            print(f"Error: Could not persist cache. Reason: {e}")

    def get_valid_entry(self, path: Path) -> Optional[CachedPluginInfo]:
        path_str = str(path.resolve())
        cached_info = self._cache.get(path_str)

        if not cached_info:
            return None

        if not path.exists():
            return None  # 插件文件已被删除

        # 验证文件修改时间是否一致
        current_mtime = path.stat().st_mtime
        if cached_info.file_modification_time == current_mtime:
            return cached_info

        return None  # 文件已更改，缓存无效

    def store_entry(self, path: Path, info: CachedPluginInfo) -> None:
        self._cache[str(path.resolve())] = info

    def get_all_cached_paths(self) -> List[Path]:
        return [Path(p) for p in self._cache.keys()]

    def remove_entry(self, path: Path) -> None:
        path_str = str(path.resolve())
        if path_str in self._cache:
            del self._cache[path_str]
