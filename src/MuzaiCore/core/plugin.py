# file: src/MuzaiCore/core/plugin_adapter.py
"""
Unified Plugin System
=====================
统一的插件系统，适配所有三种引擎

架构：
┌─────────────────────────────────┐
│   PluginInstance (抽象基类)      │
├─────────────────────────────────┤
│ - MockPluginInstance            │  ← Mock引擎
│ - RealPluginInstance            │  ← Real引擎  
│ - DawDreamerPluginInstance      │  ← DawDreamer引擎
└─────────────────────────────────┘

关键：
1. 所有插件实例实现相同的接口
2. 根据引擎类型自动选择实现
3. 参数同步在基类中统一处理
4. DSP处理委托给具体实现
"""

import numpy as np
from typing import Optional, Dict, List
from abc import ABC, abstractmethod

from ..models.plugin_model import PluginDescriptor, PluginCategory
from ..models.engine_model import TransportContext, MIDIEvent
from ..interfaces.IPlugin import IPlugin


class UnifiedPluginInstance(IPlugin, ABC):
    """
    统一插件实例基类
    
    提供所有插件共享的功能：
    - 参数管理
    - 端口管理
    - 启用/禁用
    - 状态序列化
    
    具体DSP处理由子类实现
    """

    def __init__(self,
                 descriptor: PluginDescriptor,
                 instance_id: Optional[str] = None):
        """
        初始化插件实例
        
        Args:
            descriptor: 插件描述符
            instance_id: 实例ID（可选）
        """
        from ..core.parameter import Parameter
        import uuid

        self._node_id = instance_id or str(uuid.uuid4())
        self.descriptor = descriptor
        self.is_enabled = True

        # 创建参数
        self._parameters: Dict[str, Parameter] = {}
        self._create_parameters_from_descriptor()

    @property
    def node_id(self) -> str:
        return self._node_id

    def get_parameters(self) -> Dict[str, 'Parameter']:
        return self._parameters

    def get_ports(self,
                  port_type: Optional['PortType'] = None) -> List['Port']:
        from ..models import Port

        # 更新端口的owner_node_id
        ports = [
            Port(self.node_id, p.port_id, p.port_type, p.direction,
                 p.channel_count) for p in self.descriptor.available_ports
        ]

        if port_type:
            return [p for p in ports if p.port_type == port_type]
        return ports

    def _create_parameters_from_descriptor(self):
        """从描述符创建参数"""
        from ..core.parameter import Parameter

        for name, default_value in self.descriptor.default_parameters.items():
            self._parameters[name] = Parameter(name, default_value)

    def process_block(self, input_buffer, midi_events, context):
        """
        处理音频块（统一入口）
        
        流程：
        1. 检查是否启用
        2. 调用具体实现
        """
        print(midi_events)
        if not self.is_enabled:
            return input_buffer

        return self._process_internal(input_buffer, midi_events, context)

    @abstractmethod
    def _process_internal(self, input_buffer, midi_events, context):
        """
        具体的DSP处理（由子类实现）
        
        Args:
            input_buffer: 输入音频
            midi_events: MIDI事件列表
            context: 传输上下文
            
        Returns:
            输出音频
        """
        pass

    def get_latency_samples(self) -> int:
        """获取插件延迟"""
        if self.is_enabled and self.descriptor.reports_latency:
            return self.descriptor.latency_samples
        return 0

    def get_state(self) -> Dict:
        """
        获取插件状态（用于保存）
        
        Returns:
            状态字典
        """
        return {
            'instance_id': self.node_id,
            'plugin_id': self.descriptor.unique_plugin_id,
            'is_enabled': self.is_enabled,
            'parameters': {
                name: param.value
                for name, param in self._parameters.items()
            }
        }

    def set_state(self, state: Dict):
        """
        恢复插件状态
        
        Args:
            state: 状态字典
        """
        self.is_enabled = state.get('is_enabled', True)

        params = state.get('parameters', {})
        for name, value in params.items():
            if name in self._parameters:
                self._parameters[name]._set_value_internal(value)


# ============================================================================
# Mock引擎插件实现
# ============================================================================


class MockPluginInstance(UnifiedPluginInstance):
    """
    Mock插件实例
    
    特点：
    - 只打印日志
    - 不做实际DSP处理
    - 用于测试和开发
    """

    def _process_internal(self, input_buffer, midi_events, context):
        """Mock处理：只打印日志"""

        if self.descriptor.category == PluginCategory.INSTRUMENT and midi_events:
            print(f"      -> [MOCK] Instrument '{self.descriptor.name}' "
                  f"received {len(midi_events)} MIDI events")

        elif self.descriptor.category == PluginCategory.EFFECT:
            if input_buffer is not None:
                print(f"      -> [MOCK] Effect '{self.descriptor.name}' "
                      f"processing signal")

        # 返回输入（直通）
        return input_buffer if input_buffer is not None else "mock_audio"


# ============================================================================
# Real引擎插件实现（Python DSP）
# ============================================================================


class RealPluginInstance(UnifiedPluginInstance):
    """
    Real插件实例（纯Python DSP）
    
    特点：
    - 实现简单的内置DSP算法
    - 不依赖外部插件
    - 适合自定义音频处理
    """

    def _process_internal(self, input_buffer, midi_events, context):
        """Real处理：Python DSP实现"""

        # 乐器插件：生成音频
        print(midi_events)
        if self.descriptor.category == PluginCategory.INSTRUMENT:
            return self._generate_instrument_audio(midi_events, context)

        # 效果插件：处理音频
        elif self.descriptor.category == PluginCategory.EFFECT:
            return self._process_effect_audio(input_buffer, context)

        return input_buffer

    def _generate_instrument_audio(self, midi_events: List[MIDIEvent],
                                   context: TransportContext) -> np.ndarray:
        """
        生成乐器音频（简单合成器）
        
        实现一个基础的正弦波合成器
        """
        output = np.zeros((context.block_size, 2), dtype=np.float32)

        # 获取参数
        attack = self._parameters.get('attack', None)
        attack_time = attack.value if attack else 0.01

        for event in midi_events:
            # 计算频率
            freq = 440.0 * (2**((event.note_pitch - 69) / 12.0))

            # 生成样本
            start_sample = event.start_sample
            duration = context.block_size - start_sample

            if duration > 0:
                t = np.arange(duration) / context.sample_rate
                amplitude = event.velocity / 127.0

                # 简单包络
                envelope = np.ones(duration)
                attack_samples = int(attack_time * context.sample_rate)
                if duration > attack_samples:
                    envelope[:attack_samples] = np.linspace(
                        0, 1, attack_samples)

                # 生成正弦波
                wave = amplitude * envelope * np.sin(2 * np.pi * freq * t)

                # 添加到输出（立体声）
                output[start_sample:, 0] += wave
                output[start_sample:, 1] += wave

        return output

    def _process_effect_audio(self, input_buffer: np.ndarray,
                              context: TransportContext) -> np.ndarray:
        """
        处理效果音频
        
        根据插件类型应用不同的效果
        """
        if input_buffer is None or input_buffer.size == 0:
            return np.zeros((context.block_size, 2), dtype=np.float32)

        # 简单混响实现
        if 'reverb' in self.descriptor.name.lower():
            return self._apply_simple_reverb(input_buffer, context)

        # 其他效果：直通
        return input_buffer

    def _apply_simple_reverb(self, audio: np.ndarray,
                             context: TransportContext) -> np.ndarray:
        """
        简单混响效果（全通滤波器）
        
        这是一个教育性的示例实现
        """
        # 获取参数
        wet_param = self._parameters.get('wet', None)
        dry_param = self._parameters.get('dry', None)

        wet = wet_param.value if wet_param else 0.3
        dry = dry_param.value if dry_param else 0.7

        # 简化：只返回混合
        return audio * dry


# ============================================================================
# DawDreamer引擎插件实现
# ============================================================================


class DawDreamerPluginInstance(UnifiedPluginInstance):
    """
    DawDreamer插件实例（真实VST3/AU）
    
    特点：
    - 使用DawDreamer托管真实插件
    - 完整的VST3/AU支持
    - 专业音质
    """

    def __init__(self,
                 descriptor: PluginDescriptor,
                 dawdreamer_engine: 'daw.RenderEngine',
                 plugin_path: str,
                 instance_id: Optional[str] = None):
        """
        初始化DawDreamer插件实例
        
        Args:
            descriptor: 插件描述符
            dawdreamer_engine: DawDreamer引擎实例
            plugin_path: 插件文件路径
            instance_id: 实例ID
        """
        super().__init__(descriptor, instance_id)

        self._engine = dawdreamer_engine
        self._plugin_path = plugin_path
        self._processor_name = f"plugin_{self._node_id[:8]}"
        self._processor = None

        # 初始化DawDreamer处理器
        self._initialize_dawdreamer_processor()

    def _initialize_dawdreamer_processor(self):
        """初始化DawDreamer插件处理器"""
        try:
            import dawdreamer as daw

            # 创建处理器
            self._processor = self._engine.make_plugin_processor(
                self._processor_name, self._plugin_path)

            if not self._processor:
                raise Exception("Failed to create processor")

            # 同步参数值
            self._sync_parameters_to_dawdreamer()

            print(f"DawDreamerPlugin: Initialized {self.descriptor.name}")

        except Exception as e:
            print(f"DawDreamerPlugin: Failed to initialize: {e}")
            self._processor = None

    def _sync_parameters_to_dawdreamer(self):
        """将参数同步到DawDreamer"""
        if not self._processor:
            return

        try:
            param_count = self._processor.get_parameter_count()

            for i in range(param_count):
                param_name = self._processor.get_parameter_name(i)

                if param_name in self._parameters:
                    value = self._parameters[param_name].value
                    self._processor.set_parameter(i, value)

        except Exception as e:
            print(f"Warning: Parameter sync failed: {e}")

    def _process_internal(self, input_buffer, midi_events, context):
        """DawDreamer处理：使用真实插件"""

        if not self._processor:
            # Fallback：直通
            return input_buffer if input_buffer is not None else np.zeros(
                (context.block_size, 2), dtype=np.float32)

        try:
            # 1. 更新参数（考虑自动化）
            self._update_automated_parameters(context)

            # 2. 发送MIDI事件
            if midi_events and self.descriptor.category == PluginCategory.INSTRUMENT:
                self._send_midi_to_dawdreamer(midi_events)

            # 3. 处理音频
            # 注意：实际的处理由DawDreamer引擎统一管理
            # 这里只是接口层

            return input_buffer if input_buffer is not None else np.zeros(
                (context.block_size, 2), dtype=np.float32)

        except Exception as e:
            print(f"DawDreamerPlugin: Processing error: {e}")
            return np.zeros((context.block_size, 2), dtype=np.float32)

    def _update_automated_parameters(self, context: TransportContext):
        """更新自动化参数"""
        if not self._processor:
            return

        try:
            param_count = self._processor.get_parameter_count()

            for i in range(param_count):
                param_name = self._processor.get_parameter_name(i)

                if param_name in self._parameters:
                    # 获取当前值（考虑自动化）
                    current_value = self._parameters[param_name].get_value_at(
                        context)

                    # 更新插件参数
                    self._processor.set_parameter(i, current_value)

        except Exception as e:
            print(f"Warning: Automation update failed: {e}")

    def _send_midi_to_dawdreamer(self, midi_events: List[MIDIEvent]):
        """发送MIDI事件到DawDreamer"""
        if not self._processor:
            return

        try:
            for event in midi_events:
                if hasattr(self._processor, 'add_midi_note'):
                    self._processor.add_midi_note(
                        event.note_pitch,
                        event.velocity,
                        event.start_sample,
                        duration=4410  # 默认100ms @ 44.1kHz
                    )
        except Exception as e:
            print(f"Warning: MIDI send failed: {e}")

    def get_latency_samples(self) -> int:
        """获取真实插件延迟"""
        if not self._processor or not self.is_enabled:
            return 0

        try:
            if hasattr(self._processor, 'get_latency_samples'):
                return self._processor.get_latency_samples()
        except:
            pass

        return self.descriptor.latency_samples

    def cleanup(self):
        """清理DawDreamer资源"""
        if self._processor and self._engine:
            try:
                self._engine.remove_processor(self._processor_name)
            except:
                pass

        self._processor = None

    def __del__(self):
        """析构函数"""
        self.cleanup()


# ============================================================================
# 插件工厂
# ============================================================================


class PluginFactory:
    """
    插件工厂
    
    根据引擎类型自动创建合适的插件实例
    """

    @staticmethod
    def create_plugin_instance(descriptor: PluginDescriptor,
                               engine_type: str,
                               instance_id: Optional[str] = None,
                               **kwargs) -> UnifiedPluginInstance:
        """
        创建插件实例
        
        Args:
            descriptor: 插件描述符
            engine_type: 引擎类型（"mock", "real", "dawdreamer"）
            instance_id: 实例ID
            **kwargs: 引擎特定的参数
            
        Returns:
            插件实例
        """
        if engine_type == "mock":
            return MockPluginInstance(descriptor, instance_id)

        elif engine_type == "real":
            return RealPluginInstance(descriptor, instance_id)

        elif engine_type == "dawdreamer":
            # 需要额外的参数
            dawdreamer_engine = kwargs.get('dawdreamer_engine')
            plugin_path = kwargs.get('plugin_path')

            if not dawdreamer_engine or not plugin_path:
                # Fallback到Real实现
                print(
                    "Warning: Missing DawDreamer parameters, using Real plugin"
                )
                return RealPluginInstance(descriptor, instance_id)

            return DawDreamerPluginInstance(descriptor, dawdreamer_engine,
                                            plugin_path, instance_id)

        else:
            raise ValueError(f"Unknown engine type: {engine_type}")

    @staticmethod
    def create_instrument_plugin(descriptor: PluginDescriptor,
                                 engine_type: str,
                                 instance_id: Optional[str] = None,
                                 **kwargs) -> UnifiedPluginInstance:
        """创建乐器插件（便捷方法）"""
        if descriptor.category != PluginCategory.INSTRUMENT:
            raise ValueError(f"Descriptor is not for an instrument plugin")

        return PluginFactory.create_plugin_instance(descriptor, engine_type,
                                                    instance_id, **kwargs)

    @staticmethod
    def create_effect_plugin(descriptor: PluginDescriptor,
                             engine_type: str,
                             instance_id: Optional[str] = None,
                             **kwargs) -> UnifiedPluginInstance:
        """创建效果插件（便捷方法）"""
        if descriptor.category != PluginCategory.EFFECT:
            raise ValueError(f"Descriptor is not for an effect plugin")

        return PluginFactory.create_plugin_instance(descriptor, engine_type,
                                                    instance_id, **kwargs)


# ============================================================================
# 向后兼容的别名
# ============================================================================

# 为了向后兼容，保留旧的类名
InstrumentPluginInstance = UnifiedPluginInstance
EffectPluginInstance = UnifiedPluginInstance
