# file: src/MuzaiCore/drivers/real/audio_engine.py
"""
Real Audio Engine Implementation
================================
使用sounddevice进行真实音频I/O，实现专业级音频处理流程。

关键特性：
- 真实的OS音频驱动接口
- 精确的样本级时间控制
- 延迟补偿
- 缓冲区管理
- 线程安全的状态管理
"""

import sounddevice as sd
import numpy as np
import threading
from typing import Optional, List
from queue import Queue, Empty

from ...interfaces import IAudioEngine, IProject
from ...models.engine_model import TransportStatus, TransportContext, MIDIEvent


class RealAudioEngine(IAudioEngine):
    """
    真实音频引擎 - 与操作系统音频驱动交互
    
    架构：
    1. 音频回调（硬件驱动的实时线程）
    2. DSP处理（渲染音频图）
    3. 缓冲区管理（平滑音频流）
    4. 延迟补偿（保持信号对齐）
    """

    def __init__(self,
                 sample_rate: int = 48000,
                 block_size: int = 512,
                 device_id: Optional[int] = None):
        """
        初始化音频引擎
        
        Args:
            sample_rate: 采样率 (Hz)，推荐48000
            block_size: 缓冲区大小（样本数），越小延迟越低但CPU负载越高
            device_id: 音频设备ID，None表示使用默认设备
        """
        self._project: Optional[IProject] = None
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._device_id = device_id

        # 播放状态
        self._is_playing = False
        self._current_sample_pos = 0
        self._stream: Optional[sd.OutputStream] = None

        # 线程安全
        self._state_lock = threading.Lock()
        self._underrun_count = 0
        self._overrun_count = 0

        # 性能监控
        self._cpu_load = 0.0
        self._last_callback_time = 0.0

        print(
            f"RealAudioEngine initialized: {sample_rate}Hz, {block_size} samples"
        )
        print(
            f"Theoretical latency: {(block_size / sample_rate) * 1000:.2f}ms")

    def set_project(self, project: IProject):
        """关联项目"""
        with self._state_lock:
            self._project = project
            print(f"RealAudioEngine: Project '{project.name}' loaded")

    def play(self):
        """开始播放"""
        with self._state_lock:
            if self._is_playing:
                print("RealAudioEngine: Already playing")
                return

            if not self._project:
                print("RealAudioEngine: No project loaded")
                return

            self._is_playing = True
            self._underrun_count = 0
            self._overrun_count = 0

        # 创建并启动音频流
        try:
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                blocksize=self._block_size,
                channels=2,  # 立体声
                dtype=np.float32,
                callback=self._audio_callback,
                device=self._device_id,
                latency='low'  # 请求低延迟模式
            )
            self._stream.start()

            # 更新项目状态
            self._project.set_transport_status(TransportStatus.PLAYING)

            print("RealAudioEngine: Playback started")
            print(
                f"  - Device: {sd.query_devices(self._device_id or sd.default.device[1])['name']}"
            )
            print(f"  - Actual latency: {self._stream.latency * 1000:.2f}ms")

        except Exception as e:
            with self._state_lock:
                self._is_playing = False
            print(f"RealAudioEngine: Failed to start playback: {e}")
            raise

    def stop(self):
        """停止播放"""
        with self._state_lock:
            if not self._is_playing:
                return

            self._is_playing = False
            self._current_sample_pos = 0

        # 停止并关闭音频流
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                print(f"RealAudioEngine: Error stopping stream: {e}")
            finally:
                self._stream = None

        # 更新项目状态
        if self._project:
            self._project.set_transport_status(TransportStatus.STOPPED)

        print("RealAudioEngine: Playback stopped")
        if self._underrun_count > 0 or self._overrun_count > 0:
            print(
                f"  - Underruns: {self._underrun_count}, Overruns: {self._overrun_count}"
            )

    def render_next_block(self):
        """
        这个方法在Real引擎中不直接使用
        实际渲染由_audio_callback完成
        """
        pass

    def report_latency(self) -> float:
        """报告总延迟（秒）"""
        if self._stream and self._stream.active:
            # 硬件延迟
            hw_latency = self._stream.latency
            # 缓冲区延迟
            buffer_latency = self._block_size / self._sample_rate
            return hw_latency + buffer_latency
        return 0.0

    @property
    def is_playing(self) -> bool:
        with self._state_lock:
            return self._is_playing

    @property
    def current_beat(self) -> float:
        """当前播放头的节拍位置"""
        if not self._project:
            return 0.0

        with self._state_lock:
            current_sample = self._current_sample_pos

        return self._project.timeline.samples_to_beats(current_sample,
                                                       self._sample_rate)

    # ========================================================================
    # 核心DSP方法 - 实时音频回调
    # ========================================================================

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info,
                        status):
        """
        音频回调函数 - 由sounddevice在实时线程中调用
        
        这是整个引擎最关键的方法：
        1. 必须非常快（不能阻塞）
        2. 必须线程安全
        3. 必须无异常（异常会中断音频流）
        
        Args:
            outdata: 输出缓冲区 [frames, channels]
            frames: 要填充的帧数
            time_info: 时间信息（未使用）
            status: 流状态标志
        """
        # 检查状态标志
        if status.output_underflow:
            self._underrun_count += 1
        if status.output_overflow:
            self._overrun_count += 1

        try:
            # 1. 渲染音频块
            with self._state_lock:
                if not self._is_playing or not self._project:
                    outdata.fill(0)
                    return

                current_sample = self._current_sample_pos
                project = self._project

            # 2. 实际DSP处理（在锁外进行，避免阻塞）
            audio_buffer = self._render_audio_block(project, current_sample,
                                                    frames)

            # 3. 复制到输出缓冲区
            outdata[:] = audio_buffer

            # 4. 推进播放头
            with self._state_lock:
                self._current_sample_pos += frames

        except Exception as e:
            # 在实时线程中不能抛出异常
            print(f"RealAudioEngine: Error in audio callback: {e}")
            outdata.fill(0)  # 输出静音以避免噪音

    def _render_audio_block(self, project: IProject, start_sample: int,
                            num_frames: int) -> np.ndarray:
        """
        渲染音频块的核心DSP方法
        
        这个方法实现了完整的音频图处理流程：
        1. 获取处理顺序（拓扑排序）
        2. 为每个节点分配输入缓冲区
        3. 收集MIDI事件
        4. 调用节点的process_block
        5. 路由输出到连接的节点
        6. 混合到主输出
        
        Args:
            project: 项目实例
            start_sample: 起始样本位置
            num_frames: 要渲染的帧数
            
        Returns:
            [num_frames, 2] 的立体声音频缓冲区
        """
        # 1. 创建TransportContext
        current_beat = project.timeline.samples_to_beats(
            start_sample, self._sample_rate)

        context = TransportContext(current_beat=current_beat,
                                   sample_rate=self._sample_rate,
                                   block_size=num_frames,
                                   tempo=project.tempo)

        # 2. 获取拓扑排序的处理顺序
        try:
            processing_order = project.router.get_processing_order()
        except Exception as e:
            print(f"RealAudioEngine: Failed to get processing order: {e}")
            return np.zeros((num_frames, 2), dtype=np.float32)

        # 3. 初始化节点输出缓冲区字典
        node_outputs = {}

        # 4. 按顺序处理每个节点
        for node_id in processing_order:
            node = project.get_node_by_id(node_id)
            if not node:
                continue

            # a. 收集此节点的输入
            input_buffer = self._gather_node_inputs(project, node_id,
                                                    node_outputs, num_frames)

            # b. 收集此节点的MIDI事件
            midi_events = self._gather_midi_events(project, node_id, context,
                                                   start_sample, num_frames)

            # c. 处理节点
            try:
                print("=========")
                print((midi_events))
                print(node)
                output_buffer = node.process_block(input_buffer, midi_events,
                                                   context)

                if output_buffer is not None:

                    if output_buffer.ndim == 1:

                        output_buffer = np.column_stack(
                            [output_buffer, output_buffer])

                    node_outputs[node_id] = output_buffer

            except Exception as e:
                print(
                    f"RealAudioEngine: Error processing node {node_id[:8]} {node}: {e}"
                )
                node_outputs[node_id] = np.zeros((num_frames, 2),
                                                 dtype=np.float32)

        # 5. 混合所有输出到主输出
        master_output = self._mix_to_master(project, node_outputs, num_frames)

        # 6. 应用主限制器（防止削波）
        master_output = self._apply_master_limiter(master_output)

        return master_output

    def _gather_node_inputs(self, project: IProject, node_id: str,
                            node_outputs: dict, num_frames: int) -> np.ndarray:
        """
        收集节点的所有输入连接并混合
        
        Args:
            project: 项目实例
            node_id: 目标节点ID
            node_outputs: 已处理节点的输出缓冲区
            num_frames: 缓冲区大小
            
        Returns:
            混合后的输入缓冲区
        """
        input_connections = project.router.get_inputs_for_node(node_id)

        if not input_connections:
            # 没有输入，返回静音
            return np.zeros((num_frames, 2), dtype=np.float32)

        # 混合所有输入
        mixed_input = np.zeros((num_frames, 2), dtype=np.float32)

        for conn in input_connections:
            source_node_id = conn.source_port.owner_node_id

            if source_node_id in node_outputs:
                source_buffer = node_outputs[source_node_id]

                # 处理通道数不匹配
                if source_buffer.shape[1] == 1 and mixed_input.shape[1] == 2:
                    # 单声道 -> 立体声
                    mixed_input += np.column_stack(
                        [source_buffer, source_buffer])
                elif source_buffer.shape[1] == 2:
                    mixed_input += source_buffer

        return mixed_input

    def _gather_midi_events(self, project: IProject, node_id: str,
                            context: TransportContext, start_sample: int,
                            num_frames: int) -> List[MIDIEvent]:
        """
        收集节点当前块中的所有MIDI事件
        
        这个方法需要：
        1. 查找节点的所有MIDI片段
        2. 找到当前时间范围内的音符
        3. 转换为MIDIEvent对象
        
        Args:
            project: 项目实例
            node_id: 目标节点ID
            context: 运输上下文
            start_sample: 块起始样本
            num_frames: 块大小
            
        Returns:
            MIDIEvent列表
        """
        node = project.get_node_by_id(node_id)
        if not node or not hasattr(node, 'clips'):
            return []

        midi_events = []
        start_beat = context.current_beat
        end_beat = project.timeline.samples_to_beats(start_sample + num_frames,
                                                     self._sample_rate)

        # 遍历所有MIDI片段
        from ...models.clip_model import MIDIClip

        for clip in node.clips:
            if not isinstance(clip, MIDIClip):
                continue

            # 检查片段是否在当前时间范围内
            clip_end_beat = clip.start_beat + clip.duration_beats

            if clip_end_beat < start_beat or clip.start_beat > end_beat:
                continue

            # 收集片段中的音符
            for note in clip.notes:
                note_abs_beat = clip.start_beat + note.start_beat

                # 音符是否在当前块中开始？
                if start_beat <= note_abs_beat < end_beat:
                    # 计算音符在块中的样本偏移
                    note_sample = project.timeline.beats_to_samples(
                        note_abs_beat, self._sample_rate)
                    sample_offset = note_sample - start_sample

                    if 0 <= sample_offset < num_frames:
                        midi_events.append(
                            MIDIEvent(note_pitch=note.pitch,
                                      velocity=note.velocity,
                                      start_sample=sample_offset))

        return midi_events

    def _mix_to_master(self, project: IProject, node_outputs: dict,
                       num_frames: int) -> np.ndarray:
        """
        将所有轨道输出混合到主输出
        
        在真实DAW中，这会：
        1. 识别主轨道
        2. 只混合路由到主轨道的信号
        3. 应用主轨道的处理
        
        Args:
            project: 项目实例
            node_outputs: 节点输出字典
            num_frames: 缓冲区大小
            
        Returns:
            主输出缓冲区
        """
        # 简化实现：混合所有输出
        # 真实实现应该只混合路由到master的信号
        master_output = np.zeros((num_frames, 2), dtype=np.float32)

        for node_id, buffer in node_outputs.items():
            if buffer is not None and buffer.size > 0:
                master_output += buffer

        return master_output

    def _apply_master_limiter(self, audio: np.ndarray) -> np.ndarray:
        """
        应用主限制器防止削波
        
        简单的软削波算法：
        - 线性直到0.8
        - 0.8-1.0之间软饱和
        
        Args:
            audio: 输入音频
            
        Returns:
            限制后的音频
        """
        threshold = 0.8

        # 查找超过阈值的样本
        mask = np.abs(audio) > threshold

        if np.any(mask):
            # 软饱和公式
            sign = np.sign(audio[mask])
            magnitude = np.abs(audio[mask])

            # 双曲正切软饱和
            audio[mask] = sign * (threshold + (1 - threshold) * np.tanh(
                (magnitude - threshold) / (1 - threshold)))

        return audio

    # ========================================================================
    # 性能监控
    # ========================================================================

    def get_performance_stats(self) -> dict:
        """获取性能统计"""
        return {
            "is_playing": self.is_playing,
            "sample_rate": self._sample_rate,
            "block_size": self._block_size,
            "current_beat": self.current_beat,
            "latency_ms": self.report_latency() * 1000,
            "underruns": self._underrun_count,
            "overruns": self._overrun_count,
            "cpu_load": self._cpu_load
        }
