# file: src/MuzaiCore/drivers/real/dawdreamer_engine.py
"""
DawDreamer Engine Adapter
==========================
将DawDreamer引擎深度集成到MuzaiCore架构中

DawDreamer特性：
- 完整的音频图处理
- VST3/AU插件托管
- MIDI序列处理
- 离线和实时渲染
- Python友好的API

集成策略：
1. 使用DawDreamer的RenderEngine作为底层引擎
2. 将MuzaiCore的节点图映射到DawDreamer的处理器图
3. 实现双向同步（参数、状态、连接）
4. 支持实时和离线两种模式
"""

import numpy as np
import threading
import time
from typing import Optional, Dict, List, Set
from collections import defaultdict

try:
    import dawdreamer as daw
    DAWDREAMER_AVAILABLE = True
except ImportError:
    DAWDREAMER_AVAILABLE = False
    print("Warning: DawDreamer not available")

from ...interfaces import IAudioEngine, IProject, INode
from ...models.engine_model import TransportStatus, TransportContext, MIDIEvent
from ...models.clip_model import MIDIClip


class DawDreamerEngineAdapter(IAudioEngine):
    """
    DawDreamer引擎适配器
    
    核心功能：
    1. 管理DawDreamer RenderEngine
    2. 同步MuzaiCore节点图到DawDreamer
    3. 处理实时音频回调
    4. MIDI事件转换和路由
    5. 参数自动化
    
    架构：
    - MuzaiCore Project → DawDreamer RenderEngine
    - MuzaiCore Node → DawDreamer Processor
    - MuzaiCore Connection → DawDreamer Audio Routing
    - MuzaiCore Parameter → DawDreamer Parameter
    """

    def __init__(self, sample_rate: int = 48000, block_size: int = 512):
        """
        初始化DawDreamer引擎适配器
        
        Args:
            sample_rate: 采样率
            block_size: 缓冲区大小
        """
        if not DAWDREAMER_AVAILABLE:
            raise ImportError("DawDreamer is required for this engine")

        self._sample_rate = sample_rate
        self._block_size = block_size
        self._project: Optional[IProject] = None

        # DawDreamer引擎
        self._engine = daw.RenderEngine(sample_rate, block_size)

        # 播放状态
        self._is_playing = False
        self._current_sample = 0
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._state_lock = threading.Lock()

        # 节点到处理器的映射
        self._node_to_processor: Dict[str,
                                      str] = {}  # node_id -> processor_name
        self._processor_to_node: Dict[str,
                                      str] = {}  # processor_name -> node_id

        # 性能统计
        self._render_time_history: List[float] = []
        self._max_history_length = 100

        print(
            f"DawDreamerEngine initialized: {sample_rate}Hz, {block_size} samples"
        )

    def set_project(self, project: IProject):
        """
        关联项目并构建DawDreamer处理器图
        
        流程：
        1. 保存项目引用
        2. 分析项目节点图
        3. 创建对应的DawDreamer处理器
        4. 建立音频路由
        5. 同步参数
        """
        with self._state_lock:
            self._project = project

        print(
            f"DawDreamerEngine: Building processor graph for '{project.name}'")
        self._build_processor_graph()

    def _build_processor_graph(self):
        """
        构建DawDreamer处理器图
        
        这是最关键的方法：将MuzaiCore的抽象节点图
        转换为DawDreamer的具体处理器图
        """
        if not self._project:
            return

        # 1. 清理现有处理器
        self._clear_all_processors()

        # 2. 获取拓扑排序的节点顺序
        try:
            processing_order = self._project.router.get_processing_order()
        except Exception as e:
            print(f"Error getting processing order: {e}")
            return

        # 3. 为每个节点创建处理器
        print(f"  Creating {len(processing_order)} processors...")

        for node_id in processing_order:
            node = self._project.get_node_by_id(node_id)
            if node:
                self._create_processor_for_node(node)

        # 4. 建立音频路由
        print("  Establishing audio routing...")
        self._setup_audio_routing()

        # 5. 配置MIDI路由
        print("  Configuring MIDI routing...")
        self._setup_midi_routing()

        print("  ✓ Processor graph built successfully")

    def _create_processor_for_node(self, node: INode):
        """
        为MuzaiCore节点创建对应的DawDreamer处理器
        
        处理器类型：
        - Track → PlaybackWarp或Sampler（用于播放clips）
        - Plugin → PluginProcessor（VST3/AU）
        - Bus → AddProcessor（混音）
        - Master → 输出
        """
        node_id = node.node_id
        processor_name = f"node_{node_id[:8]}"

        try:
            from ...core.track import Track, InstrumentTrack, AudioTrack
            from ...core.plugin import PluginInstance

            if isinstance(node, Track):
                # 轨道处理器
                self._create_track_processor(node, processor_name)

            elif isinstance(node, PluginInstance):
                # 插件处理器
                self._create_plugin_processor(node, processor_name)

            # 记录映射
            self._node_to_processor[node_id] = processor_name
            self._processor_to_node[processor_name] = node_id

        except Exception as e:
            print(
                f"  Warning: Failed to create processor for {node_id[:8]}: {e}"
            )

    def _create_track_processor(self, track: 'Track', processor_name: str):
        """
        为轨道创建处理器
        
        策略：
        - 使用PlaybackWarp处理器播放音频clips
        - 使用自定义MIDI生成器处理MIDI clips
        - 链接mixer channel的插件
        """
        from ...core.track import InstrumentTrack, AudioTrack

        if isinstance(track, InstrumentTrack):
            # 乐器轨道：需要MIDI输入
            # DawDreamer没有直接的"MIDI轨道"，我们使用插件处理器

            # 检查是否有插件
            if hasattr(track, 'mixer_channel') and track.mixer_channel.inserts:
                first_plugin = track.mixer_channel.inserts[0]
                # 插件会在_create_plugin_processor中单独处理
                pass
            else:
                # 没有插件，创建一个空的AddProcessor作为占位
                processor = self._engine.make_add_processor(processor_name, [])

        elif isinstance(track, AudioTrack):
            # 音频轨道：播放音频clips
            # TODO: 实现音频clip播放
            processor = self._engine.make_add_processor(processor_name, [])

        else:
            # Bus/Master轨道：混音器
            processor = self._engine.make_add_processor(processor_name, [])

    def _create_plugin_processor(self, plugin: 'PluginInstance',
                                 processor_name: str):
        """
        为插件创建DawDreamer处理器
        
        Args:
            plugin: MuzaiCore插件实例
            processor_name: 处理器名称
        """
        # 检查是否是内置插件
        if 'builtin' in plugin.descriptor.unique_plugin_id:
            # 内置插件：使用自定义处理器或直通
            processor = self._engine.make_add_processor(processor_name, [])
            return

        # 外部VST3/AU插件
        # 需要插件路径 - 这里需要从注册表获取
        plugin_path = self._get_plugin_path(plugin.descriptor.unique_plugin_id)

        if plugin_path:
            try:
                processor = self._engine.make_plugin_processor(
                    processor_name, plugin_path)

                # 同步参数值
                self._sync_parameters_to_dawdreamer(plugin, processor)

            except Exception as e:
                print(
                    f"  Warning: Failed to load plugin {plugin.descriptor.name}: {e}"
                )
                # Fallback到空处理器
                processor = self._engine.make_add_processor(processor_name, [])

    def _setup_audio_routing(self):
        """
        建立音频路由
        
        根据MuzaiCore的连接图设置DawDreamer的音频路由
        """
        if not self._project:
            return

        connections = self._project.router.get_all_connections()

        for conn in connections:
            source_node_id = conn.source_port.owner_node_id
            dest_node_id = conn.dest_port.owner_node_id

            # 获取处理器名称
            source_proc = self._node_to_processor.get(source_node_id)
            dest_proc = self._node_to_processor.get(dest_node_id)

            if source_proc and dest_proc:
                try:
                    # 在DawDreamer中建立连接
                    # 注意：DawDreamer使用不同的路由方式
                    # 这里需要使用graph.add_edge()或类似方法

                    # DawDreamer的路由是通过设置处理器的输入来完成的
                    dest_processor = self._engine.get_processor(dest_proc)
                    if dest_processor:
                        # 某些处理器有input属性
                        if hasattr(dest_processor, 'set_input'):
                            source_processor = self._engine.get_processor(
                                source_proc)
                            dest_processor.set_input(source_processor)

                except Exception as e:
                    print(
                        f"  Warning: Failed to route {source_proc} -> {dest_proc}: {e}"
                    )

    def _setup_midi_routing(self):
        """
        配置MIDI路由
        
        DawDreamer的MIDI处理：
        1. 创建MIDI序列
        2. 将序列分配给处理器
        3. 在render时处理
        """
        # MIDI路由在实时模式下动态处理
        pass

    def _get_plugin_path(self, unique_plugin_id: str) -> Optional[str]:
        """
        从插件ID获取插件文件路径
        
        这需要访问PluginRegistry
        """
        # TODO: 实现从Registry获取路径的机制
        # 暂时返回None
        return None

    def _sync_parameters_to_dawdreamer(self, plugin: 'PluginInstance',
                                       processor):
        """将MuzaiCore参数同步到DawDreamer处理器"""
        try:
            param_count = processor.get_parameter_count()

            for i in range(param_count):
                param_name = processor.get_parameter_name(i)

                if param_name in plugin._parameters:
                    param_value = plugin._parameters[param_name].value
                    processor.set_parameter(i, param_value)

        except Exception as e:
            print(f"  Warning: Parameter sync failed: {e}")

    def _clear_all_processors(self):
        """清除所有DawDreamer处理器"""
        # 移除所有处理器
        for proc_name in list(self._node_to_processor.values()):
            try:
                self._engine.remove_processor(proc_name)
            except:
                pass

        self._node_to_processor.clear()
        self._processor_to_node.clear()

    # ========================================================================
    # 播放控制
    # ========================================================================

    def play(self):
        """
        开始播放
        
        实时模式：使用线程循环调用render
        """
        with self._state_lock:
            if self._is_playing:
                return

            if not self._project:
                print("DawDreamerEngine: No project loaded")
                return

            self._is_playing = True
            self._current_sample = 0

        # 更新项目状态
        self._project.set_transport_status(TransportStatus.PLAYING)

        # 启动播放线程
        self._stop_event.clear()
        self._playback_thread = threading.Thread(target=self._playback_loop,
                                                 daemon=True)
        self._playback_thread.start()

        print("DawDreamerEngine: Playback started")

    def stop(self):
        """停止播放"""
        with self._state_lock:
            if not self._is_playing:
                return

            self._is_playing = False
            self._current_sample = 0

        # 停止线程
        if self._playback_thread:
            self._stop_event.set()
            self._playback_thread.join(timeout=2.0)
            self._playback_thread = None

        # 更新项目状态
        if self._project:
            self._project.set_transport_status(TransportStatus.STOPPED)

        print("DawDreamerEngine: Playback stopped")

    def _playback_loop(self):
        """
        播放循环线程
        
        策略：
        1. 使用DawDreamer的render()方法
        2. 批量渲染音频块
        3. 使用sounddevice播放
        """
        import sounddevice as sd

        print("DawDreamerEngine: Starting playback loop")

        try:
            # 创建音频流
            stream = sd.OutputStream(samplerate=self._sample_rate,
                                     blocksize=self._block_size,
                                     channels=2,
                                     dtype=np.float32,
                                     callback=self._audio_callback,
                                     latency='low')

            with stream:
                # 等待停止信号
                while not self._stop_event.is_set():
                    time.sleep(0.1)

        except Exception as e:
            print(f"DawDreamerEngine: Playback error: {e}")
            with self._state_lock:
                self._is_playing = False

        print("DawDreamerEngine: Playback loop ended")

    def _audio_callback(self, outdata, frames, time_info, status):
        """
        Sounddevice音频回调
        
        在这里调用DawDreamer进行渲染
        """
        if status:
            print(f"Audio callback status: {status}")

        try:
            with self._state_lock:
                if not self._is_playing or not self._project:
                    outdata.fill(0)
                    return

                current_sample = self._current_sample

            # 使用DawDreamer渲染
            start_time = time.time()
            audio = self._render_with_dawdreamer(current_sample, frames)
            render_time = time.time() - start_time

            # 记录渲染时间
            self._render_time_history.append(render_time)
            if len(self._render_time_history) > self._max_history_length:
                self._render_time_history.pop(0)

            # 输出音频
            if audio is not None and audio.shape[0] >= frames:
                outdata[:] = audio[:frames]
            else:
                outdata.fill(0)

            # 更新播放位置
            with self._state_lock:
                self._current_sample += frames

        except Exception as e:
            print(f"DawDreamerEngine: Render error: {e}")
            outdata.fill(0)

    def _render_with_dawdreamer(self, start_sample: int,
                                num_frames: int) -> np.ndarray:
        """
        使用DawDreamer渲染音频块
        
        Args:
            start_sample: 起始样本位置
            num_frames: 要渲染的帧数
            
        Returns:
            [frames, 2] 立体声音频
        """
        try:
            # 1. 更新MIDI事件
            self._update_midi_for_block(start_sample, num_frames)

            # 2. 更新自动化参数
            self._update_automation_for_block(start_sample, num_frames)

            # 3. 使用DawDreamer渲染
            # 设置渲染长度
            duration_seconds = num_frames / self._sample_rate

            # 渲染
            self._engine.render(duration_seconds)

            # 获取输出音频
            audio = self._engine.get_audio()

            # 转换格式 [channels, frames] -> [frames, channels]
            if audio.ndim == 2:
                audio = audio.T

            return audio

        except Exception as e:
            print(f"DawDreamer render error: {e}")
            return np.zeros((num_frames, 2), dtype=np.float32)

    def _update_midi_for_block(self, start_sample: int, num_frames: int):
        """
        更新当前块的MIDI事件
        
        遍历所有乐器轨道，收集MIDI clips中的音符
        """
        if not self._project:
            return

        from ...core.track import InstrumentTrack

        # 计算时间范围
        start_seconds = start_sample / self._sample_rate
        end_seconds = (start_sample + num_frames) / self._sample_rate

        start_beat = self._project.timeline.seconds_to_beats(start_seconds)
        end_beat = self._project.timeline.seconds_to_beats(end_seconds)

        # 遍历所有节点
        for node in self._project.get_all_nodes():
            if not isinstance(node, InstrumentTrack):
                continue

            processor_name = self._node_to_processor.get(node.node_id)
            if not processor_name:
                continue

            processor = self._engine.get_processor(processor_name)
            if not processor:
                continue

            # 收集MIDI事件
            midi_events = self._collect_midi_events(node, start_beat, end_beat,
                                                    start_sample)

            # 发送到处理器
            self._send_midi_to_processor(processor, midi_events)

    def _collect_midi_events(self, track: 'InstrumentTrack', start_beat: float,
                             end_beat: float,
                             start_sample: int) -> List[MIDIEvent]:
        """收集轨道在指定范围内的MIDI事件"""
        events = []

        for clip in track.clips:
            if not isinstance(clip, MIDIClip):
                continue

            clip_end = clip.start_beat + clip.duration_beats

            if clip_end < start_beat or clip.start_beat > end_beat:
                continue

            # 遍历音符
            for note in clip.notes:
                note_beat = clip.start_beat + note.start_beat

                if start_beat <= note_beat < end_beat:
                    # 计算样本偏移
                    note_seconds = self._project.timeline.beats_to_seconds(
                        note_beat)
                    note_sample = int(note_seconds * self._sample_rate)
                    sample_offset = note_sample - start_sample

                    if sample_offset >= 0:
                        events.append(
                            MIDIEvent(note_pitch=note.pitch,
                                      velocity=note.velocity,
                                      start_sample=sample_offset))

        return events

    def _send_midi_to_processor(self, processor, midi_events: List[MIDIEvent]):
        """将MIDI事件发送到DawDreamer处理器"""
        try:
            for event in midi_events:
                if hasattr(processor, 'add_midi_note'):
                    # DawDreamer的add_midi_note方法
                    processor.add_midi_note(
                        event.note_pitch,
                        event.velocity,
                        event.start_sample,
                        duration=4410  # 默认100ms @ 44.1kHz
                    )
        except Exception as e:
            print(f"Warning: Failed to send MIDI: {e}")

    def _update_automation_for_block(self, start_sample: int, num_frames: int):
        """更新自动化参数"""
        # TODO: 实现参数自动化更新
        pass

    def render_next_block(self):
        """Mock compatibility"""
        pass

    def report_latency(self) -> float:
        """报告延迟"""
        return self._block_size / self._sample_rate

    @property
    def is_playing(self) -> bool:
        with self._state_lock:
            return self._is_playing

    @property
    def current_beat(self) -> float:
        if not self._project:
            return 0.0

        with self._state_lock:
            current_seconds = self._current_sample / self._sample_rate

        return self._project.timeline.seconds_to_beats(current_seconds)

    # ========================================================================
    # 性能统计
    # ========================================================================

    def get_performance_stats(self) -> dict:
        """获取性能统计"""
        avg_render_time = (sum(self._render_time_history) /
                           len(self._render_time_history)
                           if self._render_time_history else 0)

        max_render_time = max(
            self._render_time_history) if self._render_time_history else 0

        # CPU负载估算
        available_time = self._block_size / self._sample_rate
        cpu_load = (avg_render_time / available_time *
                    100) if available_time > 0 else 0

        return {
            "is_playing": self.is_playing,
            "sample_rate": self._sample_rate,
            "block_size": self._block_size,
            "current_beat": self.current_beat,
            "latency_ms": self.report_latency() * 1000,
            "avg_render_time_ms": avg_render_time * 1000,
            "max_render_time_ms": max_render_time * 1000,
            "cpu_load_percent": cpu_load,
            "processor_count": len(self._node_to_processor),
            "underruns": 0,  # TODO: 实现
            "overruns": 0
        }
