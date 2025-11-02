import os
import platform
from typing import List, Optional
from pathlib import Path

try:
    import pedalboard as pb
except ImportError:
    pb = None

from ...interfaces.system.iplugin_registry import IPluginRegistry
from ...models import PluginDescriptor, PluginCategory, Port, PortType, PortDirection


class PedalboardPluginRegistry(IPluginRegistry):
    """
    Pedalboard 插件注册表
    
    扫描并注册系统中的 VST3/AU 插件
    """

    def __init__(self):
        self._plugins: List[PluginDescriptor] = []
        self._plugin_paths: dict = {}  # unique_id -> file_path

        # 内置效果器
        self._register_builtin_effects()

    def scan_for_plugins(self):
        """
        扫描系统中的插件
        
        搜索路径：
        - macOS: /Library/Audio/Plug-Ins/VST3/, ~/Library/Audio/Plug-Ins/VST3/
        - Windows: C:\\Program Files\\VSTPlugins\\
        - Linux: ~/.vst3/
        """
        if not pb:
            print("Pedalboard not available, cannot scan plugins")
            return

        self._plugins.clear()
        self._plugin_paths.clear()

        # 重新注册内置效果
        self._register_builtin_effects()

        # 扫描 VST3 插件
        vst3_paths = self._get_vst3_search_paths()
        for search_path in vst3_paths:
            if os.path.exists(search_path):
                self._scan_directory(search_path, ".vst3")

        # macOS: 扫描 Audio Unit 插件
        if platform.system() == "Darwin":
            au_paths = [
                "/Library/Audio/Plug-Ins/Components",
                os.path.expanduser("~/Library/Audio/Plug-Ins/Components")
            ]
            for search_path in au_paths:
                if os.path.exists(search_path):
                    self._scan_directory(search_path, ".component")

        print(f"PedalboardPluginRegistry: Found {len(self._plugins)} plugins")

    def get_plugin_descriptor(
            self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        """根据 ID 获取插件描述符"""
        for plugin in self._plugins:
            if plugin.unique_plugin_id == unique_plugin_id:
                return plugin
        return None

    def list_plugins(self) -> List[PluginDescriptor]:
        """列出所有插件"""
        return self._plugins.copy()

    def get_plugin_path(self, unique_plugin_id: str) -> Optional[str]:
        """获取插件文件路径（用于加载）"""
        return self._plugin_paths.get(unique_plugin_id)

    # ========================================================================
    # 内部方法
    # ========================================================================

    def _register_builtin_effects(self):
        """注册 Pedalboard 内置效果器"""

        # Reverb
        self._plugins.append(
            PluginDescriptor(unique_plugin_id="pedalboard.builtin.reverb",
                             name="Reverb",
                             vendor="Pedalboard",
                             meta="Algorithmic reverb",
                             category=PluginCategory.EFFECT,
                             reports_latency=True,
                             latency_samples=256,
                             available_ports=[
                                 Port("", "audio_in", PortType.AUDIO,
                                      PortDirection.INPUT, 2),
                                 Port("", "audio_out", PortType.AUDIO,
                                      PortDirection.OUTPUT, 2),
                             ],
                             default_parameters={
                                 "room_size": 0.5,
                                 "damping": 0.5,
                                 "wet_level": 0.33,
                                 "dry_level": 0.4,
                                 "width": 1.0,
                             }))

        # Delay
        self._plugins.append(
            PluginDescriptor(unique_plugin_id="pedalboard.builtin.delay",
                             name="Delay",
                             vendor="Pedalboard",
                             meta="Simple delay",
                             category=PluginCategory.EFFECT,
                             reports_latency=False,
                             available_ports=[
                                 Port("", "audio_in", PortType.AUDIO,
                                      PortDirection.INPUT, 2),
                                 Port("", "audio_out", PortType.AUDIO,
                                      PortDirection.OUTPUT, 2),
                             ],
                             default_parameters={
                                 "delay_seconds": 0.5,
                                 "feedback": 0.3,
                                 "mix": 0.5,
                             }))

        # Chorus
        self._plugins.append(
            PluginDescriptor(unique_plugin_id="pedalboard.builtin.chorus",
                             name="Chorus",
                             vendor="Pedalboard",
                             meta="Chorus effect",
                             category=PluginCategory.EFFECT,
                             reports_latency=False,
                             available_ports=[
                                 Port("", "audio_in", PortType.AUDIO,
                                      PortDirection.INPUT, 2),
                                 Port("", "audio_out", PortType.AUDIO,
                                      PortDirection.OUTPUT, 2),
                             ],
                             default_parameters={
                                 "rate_hz": 1.0,
                                 "depth": 0.25,
                                 "centre_delay_ms": 7.0,
                                 "feedback": 0.0,
                                 "mix": 0.5,
                             }))

        # Distortion
        self._plugins.append(
            PluginDescriptor(unique_plugin_id="pedalboard.builtin.distortion",
                             name="Distortion",
                             vendor="Pedalboard",
                             meta="Distortion effect",
                             category=PluginCategory.EFFECT,
                             reports_latency=False,
                             available_ports=[
                                 Port("", "audio_in", PortType.AUDIO,
                                      PortDirection.INPUT, 2),
                                 Port("", "audio_out", PortType.AUDIO,
                                      PortDirection.OUTPUT, 2),
                             ],
                             default_parameters={
                                 "drive_db": 25.0,
                             }))

        # Compressor
        self._plugins.append(
            PluginDescriptor(unique_plugin_id="pedalboard.builtin.compressor",
                             name="Compressor",
                             vendor="Pedalboard",
                             meta="Dynamic range compressor",
                             category=PluginCategory.EFFECT,
                             reports_latency=True,
                             latency_samples=64,
                             available_ports=[
                                 Port("", "audio_in", PortType.AUDIO,
                                      PortDirection.INPUT, 2),
                                 Port("", "audio_out", PortType.AUDIO,
                                      PortDirection.OUTPUT, 2),
                             ],
                             default_parameters={
                                 "threshold_db": -20.0,
                                 "ratio": 4.0,
                                 "attack_ms": 10.0,
                                 "release_ms": 100.0,
                             }))

    def _scan_directory(self, directory: str, extension: str):
        """扫描目录中的插件文件"""
        try:
            for root, dirs, files in os.walk(directory):
                for plugin_dir in dirs:
                    if plugin_dir.endswith(extension):
                        plugin_path = os.path.join(root, plugin_dir)
                        self._try_load_plugin(plugin_path)
        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")

    def _try_load_plugin(self, plugin_path: str):
        """尝试加载插件并提取信息"""
        if not pb:
            return

        try:
            # 尝试加载插件（这可能很慢）
            plugin = pb.load_plugin(plugin_path)

            plugin_name = getattr(plugin, 'name',
                                  os.path.basename(plugin_path))
            plugin_vendor = getattr(plugin, 'manufacturer_name', "unknown")
            category = PluginCategory.EFFECT
            if hasattr(plugin, 'accepts_midi') and plugin.accepts_midi:
                category = PluginCategory.INSTRUMENT

            # 生成唯一 ID
            unique_id = f"vst3.{plugin_vendor}.{plugin_name}".lower().replace(
                " ", "_")

            # 提取参数
            parameters = {}
            if hasattr(plugin, 'parameters'):
                for param_name in plugin.parameters:
                    try:
                        value = getattr(plugin, param_name)
                        parameters[param_name] = value
                    except:
                        pass

            # 创建描述符
            descriptor = PluginDescriptor(
                unique_plugin_id=unique_id,
                name=plugin_name,
                vendor=plugin_vendor,
                meta=f"VST3 Plugin: {plugin_path}",
                category=category,
                reports_latency=True,
                latency_samples=getattr(plugin, 'latency_samples', 0),
                available_ports=[
                    Port("", "audio_in", PortType.AUDIO, PortDirection.INPUT,
                         2),
                    Port("", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                         2),
                ],
                default_parameters=parameters)

            self._plugins.append(descriptor)
            self._plugin_paths[unique_id] = plugin_path

            print(f"Loaded plugin: {plugin_name} ({plugin_vendor})")

        except Exception as e:
            print(f"Could not load plugin {plugin_path}: {e}")
            pass

    def _get_vst3_search_paths(self) -> List[str]:
        """获取 VST3 搜索路径"""
        system = platform.system()

        if system == "Darwin":  # macOS
            return [
                "/Library/Audio/Plug-Ins/VST3",
                os.path.expanduser("~/Library/Audio/Plug-Ins/VST3")
            ]

        elif system == "Windows":
            return [
                "C:\\Program Files\\Common Files\\VST3",
                os.path.expanduser("~\\AppData\\Local\\Programs\\Common\\VST3")
            ]

        elif system == "Linux":
            return [
                os.path.expanduser("~/.vst3"), "/usr/lib/vst3",
                "/usr/local/lib/vst3"
            ]

        return []
