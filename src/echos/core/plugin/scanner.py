import uuid
from pathlib import Path
import json
import os
import platform
import sys
import subprocess
from typing import List
from ...models import PluginScanResult


class PluginScanner:

    def __init__(self, worker_path: Path, timeout: int = 10):
        self.timeout = timeout
        self.plugin_extensions = {".vst3", ".component"}

        self._script_path = worker_path.resolve()
        if not self._script_path.is_file():
            raise FileNotFoundError(
                f"Scan worker script not found at the specified path: {self._script_path}"
            )

    def scan_plugin_paths(self, paths: List[Path]) -> List[Path]:

        found_plugins = []

        for folder in paths:
            if not folder.exists():
                continue

            try:
                for root, dirs, _ in os.walk(folder):
                    for d in dirs:
                        path = Path(root) / d
                        if path.suffix.lower() in self.plugin_extensions:
                            found_plugins.append(path)
            except Exception as e:
                print(f"Warning: Error scanning {folder}: {e}")

        return found_plugins

    def scan_plugin_safe(self, plugin_path: Path) -> PluginScanResult:
        try:
            script_path = self._script_path

            if not script_path.exists():
                return PluginScanResult(
                    success=False,
                    error=f"Scan worker script not found: {script_path}")

            result = subprocess.run(
                [sys.executable,
                 str(script_path),
                 str(plugin_path.resolve())],
                capture_output=True,
                text=True,
                timeout=self.timeout)

            if result.returncode == 0:
                plugin_info = json.loads(result.stdout)
                return PluginScanResult(success=True, plugin_info=plugin_info)
            else:
                error_msg = result.stderr or "Unknown error"
                return PluginScanResult(success=False, error=error_msg)

        except subprocess.TimeoutExpired:
            return PluginScanResult(success=False,
                                    error=f"Timeout after {self.timeout}s")
        except Exception as e:
            return PluginScanResult(success=False, error=str(e))

    def _get_scan_script(self) -> str:
        script_path = Path(__file__).parent / "scan_worker.py"
        return f"import sys; exec(open('{script_path}').read())"

    def get_default_search_paths(self) -> List[Path]:
        system = platform.system()
        paths = []

        if system == "Windows":
            common_paths = [
                Path(
                    os.environ.get("COMMONPROGRAMFILES",
                                   "C:/Program Files/Common Files")) / "VST3"
            ]
            paths.extend(common_paths)
        elif system == "Darwin":
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


class BackgroundScanner:

    def __init__(self, scanner: PluginScanner, scan_interval: int = 300):

        self.scanner = scanner
        self.scan_interval = scan_interval
        self._scanning = False
        self._last_scan_time = 0
        self._known_plugins: Set[Path] = set()

    def start_scan(self, search_paths: List[Path], on_plugin_found: callable,
                   on_plugin_removed: callable):

        if self._scanning:
            print("Scan already in progress")
            return

        self._scanning = True
        current_time = time.time()

        if current_time - self._last_scan_time < self.scan_interval:
            print(
                f"Skipping scan, last scan was {int(current_time - self._last_scan_time)}s ago"
            )
            self._scanning = False
            return

        print("Starting background plugin scan...")
        found_plugins = self.scanner.scan_plugin_paths(search_paths)
        current_plugins = set(found_plugins)

        new_plugins = current_plugins - self._known_plugins
        for plugin_path in new_plugins:
            print(f"  [NEW] Scanning {plugin_path.name}...")
            result = self.scanner.scan_plugin_safe(plugin_path)

            if result.success:
                on_plugin_found(plugin_path, result.plugin_info)
            else:
                print(f"    -> Failed: {result.error}")

        removed_plugins = self._known_plugins - current_plugins
        for plugin_path in removed_plugins:
            print(f"  [REMOVED] {plugin_path.name}")
            on_plugin_removed(plugin_path)

        self._known_plugins = current_plugins
        self._last_scan_time = current_time
        self._scanning = False
        print(f"Scan complete. Total plugins: {len(self._known_plugins)}")
