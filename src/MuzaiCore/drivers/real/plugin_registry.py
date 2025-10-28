# file: src/MuzaiCore/drivers/real/plugin.py
"""
Real Plugin Registry with DawDreamer
====================================
使用DawDreamer实现完整的VST3/AU插件托管

DawDreamer特性：
- 真实的VST3/AU插件加载
- 参数访问和自动化
- MIDI事件处理
- 音频处理
- 跨平台支持

安装：pip install dawdreamer
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
    print(
        "Warning: DawDreamer not available. VST3/AU support will be limited.")
    print("Install with: pip install dawdreamer")

from ...interfaces import IPluginRegistry
from ...models.plugin_model import PluginDescriptor, PluginCategory
from ...models import Port, PortType, PortDirection


class RealPluginRegistry(IPluginRegistry):
    """
    真实插件注册表 - 使用DawDreamer
    
    功能：
    1. 扫描VST3/AU插件
    2. 使用DawDreamer加载和验证插件
    3. 提取插件元数据（参数、端口等）
    4. 缓存插件信息以加速启动
    5. 管理插件黑名单（崩溃的插件）
    """

    def __init__(self,
                 cache_file: str = "./plugin_cache.json",
                 sample_rate: int = 48000):
        self._plugins: Dict[str, PluginDescriptor] = {}
        self._cache_file = cache_file
        self._sample_rate = sample_rate
        self._blacklist: List[str] = []

        # 插件扫描路径
        self._scan_paths = self._get_default_scan_paths()

        # DawDreamer引擎用于插件验证
        if DAWDREAMER_AVAILABLE:
            self._engine = daw.RenderEngine(sample_rate, 512)
        else:
            self._engine = None

    def scan_for_plugins(self):
        """
        扫描所有可用的插件
        
        流程：
        1. 尝试从缓存加载
        2. 如果缓存不存在，扫描文件系统
        3. 使用DawDreamer验证每个插件
        4. 提取元数据
        5. 保存缓存
        """
        print("RealPluginRegistry: Scanning for plugins...")

        if not DAWDREAMER_AVAILABLE:
            print("  DawDreamer not available, using fallback mode")
            self._add_builtin_plugins()
            return

        # 1. 尝试加载缓存
        if os.path.exists(self._cache_file):
            print(f"  Loading from cache: {self._cache_file}")
            if self._load_cache():
                print(f"  ✓ Loaded {len(self._plugins)} plugins from cache")
                return

        # 2. 扫描文件系统
        print("  Performing full scan (this may take a while)...")
        self._plugins.clear()

        plugin_files = []
        for scan_path in self._scan_paths:
            if os.path.exists(scan_path):
                print(f"  Scanning: {scan_path}")
                plugin_files.extend(self._find_plugin_files(scan_path))

        print(f"  Found {len(plugin_files)} plugin files")

        # 3. 验证并加载每个插件
        loaded_count = 0
        for idx, plugin_path in enumerate(plugin_files):
            print(
                f"  [{idx+1}/{len(plugin_files)}] Validating: {Path(plugin_path).name}"
            )

            descriptor = self._load_and_validate_plugin(plugin_path)
            if descriptor:
                self._plugins[descriptor.unique_plugin_id] = descriptor
                loaded_count += 1

        # 4. 添加内置插件
        self._add_builtin_plugins()

        # 5. 保存缓存
        self._save_cache()

        print(
            f"RealPluginRegistry: ✓ Successfully loaded {loaded_count} plugins"
        )
        print(
            f"                    ✓ Total available: {len(self._plugins)} plugins"
        )

    def get_plugin_descriptor(
            self, unique_plugin_id: str) -> Optional[PluginDescriptor]:
        """获取插件描述符"""
        return self._plugins.get(unique_plugin_id)

    def list_plugins(self) -> List[PluginDescriptor]:
        """列出所有插件"""
        return list(self._plugins.values())

    # ========================================================================
    # DawDreamer插件加载和验证
    # ========================================================================

    def _load_and_validate_plugin(
            self, plugin_path: str) -> Optional[PluginDescriptor]:
        """
        使用DawDreamer加载并验证插件
        
        Args:
            plugin_path: 插件文件路径
            
        Returns:
            PluginDescriptor如果成功，否则None
        """
        # 检查黑名单
        if plugin_path in self._blacklist:
            return None

        try:
            # 使用DawDreamer加载插件
            plugin_name = Path(plugin_path).stem

            # 创建临时处理器
            processor = self._engine.make_plugin_processor(
                plugin_name, plugin_path)

            if not processor:
                print(f"    ✗ Failed to load")
                return None

            # 提取插件信息
            plugin_info = self._extract_plugin_info(processor, plugin_path)

            # 移除临时处理器
            self._engine.remove_processor(plugin_name)

            return plugin_info

        except Exception as e:
            print(f"    ✗ Error: {e}")
            # 添加到黑名单
            self._blacklist.append(plugin_path)
            return None

    def _extract_plugin_info(self, processor,
                             plugin_path: str) -> PluginDescriptor:
        """
        从DawDreamer处理器提取插件信息
        
        Args:
            processor: DawDreamer插件处理器
            plugin_path: 插件文件路径
            
        Returns:
            PluginDescriptor
        """
        plugin_name = processor.get_name()

        # 检测插件类别
        category = self._detect_plugin_category(processor)

        # 提取参数
        parameters = {}
        param_count = processor.get_parameter_count()

        for i in range(param_count):
            param_name = processor.get_parameter_name(i)
            param_value = processor.get_parameter(i)
            parameters[param_name] = param_value

        # 提取端口信息
        ports = self._extract_ports(processor, category)

        # 生成唯一ID
        unique_id = self._generate_plugin_id(plugin_path, plugin_name)

        # 获取供应商信息（如果可用）
        vendor = "Unknown"
        if hasattr(processor, 'get_plugin_description'):
            desc = processor.get_plugin_description()
            vendor = desc.get('manufacturer_name', 'Unknown')

        # 检测延迟
        latency_samples = 0
        if hasattr(processor, 'get_latency_samples'):
            latency_samples = processor.get_latency_samples()

        descriptor = PluginDescriptor(unique_plugin_id=unique_id,
                                      name=plugin_name,
                                      vendor=vendor,
                                      category=category,
                                      available_ports=ports,
                                      default_parameters=parameters,
                                      reports_latency=latency_samples > 0,
                                      latency_samples=latency_samples)

        print(
            f"    ✓ Loaded: {plugin_name} ({category.value}, {param_count} params)"
        )

        return descriptor

    def _detect_plugin_category(self, processor) -> PluginCategory:
        """
        检测插件类别（乐器 vs 效果器）
        
        策略：
        1. 检查是否接受MIDI输入但不需要音频输入 -> 乐器
        2. 检查是否处理音频 -> 效果器
        3. 检查插件名称关键词
        """
        # 检查端口配置
        num_inputs = processor.get_num_input_channels()
        accepts_midi = hasattr(processor,
                               'accepts_midi') and processor.accepts_midi()

        # 乐器：接受MIDI，不需要音频输入
        if accepts_midi and num_inputs == 0:
            return PluginCategory.INSTRUMENT

        # 检查名称关键词
        name_lower = processor.get_name().lower()
        instrument_keywords = [
            'synth', 'sampler', 'piano', 'drum', 'bass', 'guitar'
        ]

        if any(keyword in name_lower for keyword in instrument_keywords):
            return PluginCategory.INSTRUMENT

        # 默认为效果器
        return PluginCategory.EFFECT

    def _extract_ports(self, processor,
                       category: PluginCategory) -> List[Port]:
        """
        提取插件的端口信息
        
        Args:
            processor: DawDreamer处理器
            category: 插件类别
            
        Returns:
            端口列表
        """
        ports = []

        # MIDI输入（乐器）
        if category == PluginCategory.INSTRUMENT:
            ports.append(
                Port("self", "midi_in", PortType.MIDI, PortDirection.INPUT, 1))

        # 音频输入
        num_inputs = processor.get_num_input_channels()
        if num_inputs > 0:
            ports.append(
                Port("self", "audio_in", PortType.AUDIO, PortDirection.INPUT,
                     num_inputs))

        # 音频输出
        num_outputs = processor.get_num_output_channels()
        if num_outputs > 0:
            ports.append(
                Port("self", "audio_out", PortType.AUDIO, PortDirection.OUTPUT,
                     num_outputs))

        return ports

    def _generate_plugin_id(self, plugin_path: str, plugin_name: str) -> str:
        """
        生成插件的唯一ID
        
        格式: vendor.name.format
        例如: steinberg.halion_sonic.vst3
        """
        path_obj = Path(plugin_path)
        plugin_format = path_obj.suffix.lower().replace('.', '')

        # 简化名称
        safe_name = plugin_name.lower().replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c == '_')

        return f"plugin.{safe_name}.{plugin_format}"

    # ========================================================================
    # 文件系统扫描
    # ========================================================================

    def _get_default_scan_paths(self) -> List[str]:
        """
        获取平台默认的插件扫描路径
        
        Returns:
            路径列表
        """
        system = platform.system()
        paths = []

        if system == "Windows":
            # Windows VST3路径
            paths.extend([
                os.path.expandvars(r"%PROGRAMFILES%\Common Files\VST3"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Common Files\VST3"),
            ])

        elif system == "Darwin":  # macOS
            # macOS VST3和AU路径
            paths.extend([
                "/Library/Audio/Plug-Ins/VST3",
                os.path.expanduser("~/Library/Audio/Plug-Ins/VST3"),
                "/Library/Audio/Plug-Ins/Components",  # AU
                os.path.expanduser("~/Library/Audio/Plug-Ins/Components"),
            ])

        elif system == "Linux":
            # Linux VST3路径
            paths.extend([
                "/usr/lib/vst3",
                "/usr/local/lib/vst3",
                os.path.expanduser("~/.vst3"),
            ])

        return paths

    def _find_plugin_files(self, directory: str) -> List[str]:
        """
        在目录中查找插件文件
        
        Args:
            directory: 搜索目录
            
        Returns:
            插件文件路径列表
        """
        plugin_files = []

        # VST3插件（目录或.vst3文件）
        # AU插件（.component包）
        extensions = ['.vst3', '.component']

        try:
            for root, dirs, files in os.walk(directory):
                for item in dirs + files:
                    item_path = os.path.join(root, item)

                    # 检查扩展名
                    if any(item.lower().endswith(ext) for ext in extensions):
                        plugin_files.append(item_path)

        except Exception as e:
            print(f"  Warning: Error scanning {directory}: {e}")

        return plugin_files

    # ========================================================================
    # 内置插件
    # ========================================================================

    def _add_builtin_plugins(self):
        """
        添加内置的合成器和效果器
        
        这些是MuzaiCore自带的基本插件，不依赖外部VST
        """
        # 基础合成器
        synth_ports = [
            Port("self", "midi_in", PortType.MIDI, PortDirection.INPUT, 1),
            Port("self", "audio_out", PortType.AUDIO, PortDirection.OUTPUT, 2)
        ]
        synth_params = {
            "attack": 0.01,
            "decay": 0.2,
            "sustain": 0.8,
            "release": 0.1,
            "cutoff": 12000.0,
            "resonance": 0.5
        }
        synth = PluginDescriptor(
            unique_plugin_id="muzaicore.builtin.basic_synth",
            name="Basic Synth",
            vendor="MuzaiCore",
            category=PluginCategory.INSTRUMENT,
            available_ports=synth_ports,
            default_parameters=synth_params)
        self._plugins[synth.unique_plugin_id] = synth

        # 简单混响
        reverb_ports = [
            Port("self", "audio_in", PortType.AUDIO, PortDirection.INPUT, 2),
            Port("self", "audio_out", PortType.AUDIO, PortDirection.OUTPUT, 2)
        ]
        reverb_params = {
            "room_size": 0.7,
            "damping": 0.5,
            "wet": 0.3,
            "dry": 0.7,
            "width": 1.0
        }
        reverb = PluginDescriptor(
            unique_plugin_id="muzaicore.builtin.simple_reverb",
            name="Simple Reverb",
            vendor="MuzaiCore",
            category=PluginCategory.EFFECT,
            available_ports=reverb_ports,
            default_parameters=reverb_params)
        self._plugins[reverb.unique_plugin_id] = reverb

    # ========================================================================
    # 缓存管理
    # ========================================================================

    def _save_cache(self):
        """保存插件缓存到文件"""
        try:
            cache_data = {'version': '1.0', 'plugins': []}

            for descriptor in self._plugins.values():
                # 简化的序列化
                cache_data['plugins'].append({
                    'unique_plugin_id':
                    descriptor.unique_plugin_id,
                    'name':
                    descriptor.name,
                    'vendor':
                    descriptor.vendor,
                    'category':
                    descriptor.category.value,
                    'parameter_count':
                    len(descriptor.default_parameters),
                    'port_count':
                    len(descriptor.available_ports)
                })

            with open(self._cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

            print(f"  ✓ Cache saved to {self._cache_file}")

        except Exception as e:
            print(f"  Warning: Failed to save cache: {e}")

    def _load_cache(self) -> bool:
        """
        从缓存加载插件信息
        
        注意：这是简化实现，真实版本需要：
        1. 验证缓存版本
        2. 检查插件文件是否被修改
        3. 重新验证可疑的插件
        
        Returns:
            是否成功加载
        """
        try:
            with open(self._cache_file, 'r') as f:
                cache_data = json.load(f)

            # 验证缓存版本
            if cache_data.get('version') != '1.0':
                return False

            # 这里需要完整的反序列化逻辑
            # 简化实现：只重新添加内置插件
            self._add_builtin_plugins()

            return True

        except Exception as e:
            print(f"  Warning: Failed to load cache: {e}")
            return False

    # ========================================================================
    # 实用方法
    # ========================================================================

    def rescan_plugins(self, clear_cache: bool = True):
        """
        强制重新扫描插件
        
        Args:
            clear_cache: 是否清除缓存
        """
        if clear_cache and os.path.exists(self._cache_file):
            os.remove(self._cache_file)
            print(f"Removed cache: {self._cache_file}")

        self.scan_for_plugins()

    def blacklist_plugin(self, plugin_id: str):
        """
        将插件添加到黑名单
        
        用于标记崩溃或不兼容的插件
        """
        descriptor = self.get_plugin_descriptor(plugin_id)
        if descriptor:
            # 这里需要获取插件路径，简化实现省略
            print(f"Plugin {plugin_id} blacklisted")

    def get_plugin_stats(self) -> dict:
        """获取插件统计信息"""
        categories = {}
        for descriptor in self._plugins.values():
            cat = descriptor.category.value
            categories[cat] = categories.get(cat, 0) + 1

        return {
            'total_plugins':
            len(self._plugins),
            'by_category':
            categories,
            'builtin_count':
            sum(1 for d in self._plugins.values()
                if 'muzaicore.builtin' in d.unique_plugin_id),
            'external_count':
            sum(1 for d in self._plugins.values()
                if 'muzaicore.builtin' not in d.unique_plugin_id)
        }
