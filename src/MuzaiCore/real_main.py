# file: examples/real_daw_demo.py
"""
Real DAW Core 完整演示
======================
展示使用真实音频引擎、VST3插件和实时音频处理的完整工作流程

依赖：
    pip install sounddevice numpy dawdreamer

运行前确保：
1. 已安装sounddevice和dawdreamer
2. 系统有可用的音频输出设备
3. （可选）已安装VST3插件
"""

import sys
import time
import numpy as np
from pathlib import Path

# 添加项目到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from MuzaiCore.drivers.real.manager import RealDAWManager
from MuzaiCore.drivers.real.audio_engine import RealAudioEngine
from MuzaiCore.facade import DAWFacade
from MuzaiCore.services import (NodeService, EditingService, ProjectService,
                                RoutingService, HistoryService,
                                TransportService, QueryService, SystemService)


def print_banner():
    """打印启动横幅"""
    banner = """
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║         🎵  MuzaiCore Real DAW Engine Demo  🎵                ║
    ║                                                                ║
    ║            Professional Real-Time Audio Processing             ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('=' * 70)


def demo_audio_devices(manager: RealDAWManager):
    """演示音频设备扫描"""
    print_section("PART 1: 音频设备配置")

    print("\n[1.1] 扫描音频设备")
    audio_devices = manager.device_manager.get_audio_output_devices()

    print(f"\n✓ 发现 {len(audio_devices)} 个音频输出设备:\n")
    for i, device in enumerate(audio_devices):
        print(f"  [{i}] {device.name}")
        print(f"      输出通道: {len(device.output_channels)}")

    # 显示默认设备
    default_device = manager.device_manager.get_active_device_info()
    print(f"\n✓ 当前活动设备:")
    print(f"  - 名称: {default_device['device_name']}")
    print(f"  - 采样率: {default_device['sample_rate']}Hz")
    print(f"  - 缓冲区大小: {default_device['block_size']} samples")
    print(
        f"  - 理论延迟: {(default_device['block_size'] / default_device['sample_rate']) * 1000:.2f}ms"
    )


def demo_plugin_scanning(manager: RealDAWManager):
    """演示插件扫描"""
    print_section("PART 2: VST3插件扫描")

    print("\n[2.1] 插件统计")
    stats = manager.plugin_registry.get_plugin_stats()

    print(f"✓ 插件总数: {stats['total_plugins']}")
    print(f"  - 内置插件: {stats['builtin_count']}")
    print(f"  - 外部插件: {stats['external_count']}")

    print(f"\n✓ 按类别分类:")
    for category, count in stats['by_category'].items():
        print(f"  - {category}: {count}")

    print("\n[2.2] 可用插件列表")
    plugins = manager.plugin_registry.list_plugins()

    for plugin in plugins[:10]:  # 只显示前10个
        print(f"  • {plugin.name} ({plugin.category.value})")
        print(f"    来自: {plugin.vendor}")
        if plugin.reports_latency:
            print(f"    延迟: {plugin.latency_samples} samples")


def create_simple_project(daw: DAWFacade) -> dict:
    """创建一个简单的项目"""
    print_section("PART 3: 创建项目")

    print("\n[3.1] 创建项目和轨道")

    # 创建项目
    resp = daw.project.create_project("Real Audio Test")
    project_id = resp.data['project_id']
    print(f"✓ 项目创建: {resp.data['name']}")

    # 创建乐器轨道
    resp = daw.nodes.create_instrument_track(project_id, "Synth Lead")
    synth_track_id = resp.data['node_id']
    print(f"✓ 创建乐器轨道: Synth Lead")

    # 添加内置合成器
    resp = daw.nodes.add_insert_plugin(project_id, synth_track_id,
                                       "muzaicore.builtin.basic_synth")
    print(f"✓ 添加内置合成器")

    return {'project_id': project_id, 'synth_track_id': synth_track_id}


def create_musical_content(daw: DAWFacade, context: dict):
    """创建音乐内容"""
    print_section("PART 4: 创建音乐内容")

    project_id = context['project_id']
    synth_track_id = context['synth_track_id']

    print("\n[4.1] 创建MIDI片段")

    # 创建MIDI片段
    resp = daw.editing.create_midi_clip(project_id,
                                        synth_track_id,
                                        start_beat=0.0,
                                        duration_beats=8.0,
                                        name="Test Pattern")
    clip_id = resp.data['clip_id']
    print(f"✓ 创建片段: Test Pattern")

    # 创建简单的旋律（C大调音阶）
    print("\n[4.2] 添加音符")
    notes = []
    scale = [60, 62, 64, 65, 67, 69, 71, 72]  # C大调音阶

    for i, pitch in enumerate(scale):
        notes.append({
            "pitch": pitch,
            "velocity": 100,
            "start_beat": float(i),
            "duration_beats": 0.8
        })

    resp = daw.editing.add_notes_to_clip(project_id, clip_id, notes)
    print(f"✓ 添加了 {len(notes)} 个音符")

    context['clip_id'] = clip_id


def setup_mixing(daw: DAWFacade, context: dict):
    """设置混音参数"""
    print_section("PART 5: 混音设置")

    project_id = context['project_id']
    synth_track_id = context['synth_track_id']

    print("\n[5.1] 设置音量和声像")

    # 设置音量
    resp = daw.editing.set_parameter_value(
        project_id,
        synth_track_id,
        "volume",
        -6.0  # -6dB
    )
    print(f"✓ 设置音量: -6.0 dB")

    # 设置声像
    resp = daw.editing.set_parameter_value(
        project_id,
        synth_track_id,
        "pan",
        0.0  # 居中
    )
    print(f"✓ 设置声像: 居中")


def demo_real_time_playback(daw: DAWFacade, context: dict):
    """演示实时播放"""
    print_section("PART 6: 实时音频播放")

    project_id = context['project_id']

    print("\n[6.1] 配置播放参数")

    # 设置速度
    resp = daw.transport.set_tempo(project_id, 120.0)
    print(f"✓ 速度: 120 BPM")

    # 设置拍号
    resp = daw.transport.set_time_signature(project_id, 4, 4)
    print(f"✓ 拍号: 4/4")

    print("\n[6.2] 开始播放")
    print("=" * 70)

    # 开始播放
    resp = daw.transport.play(project_id)
    if resp.status == "success":
        print("✓ 音频引擎已启动")
        print("\n♪ 播放中... (按 Ctrl+C 停止)")
        print("=" * 70)

        try:
            # 监控播放
            for i in range(10):  # 播放10秒
                time.sleep(1)

                # 获取性能统计
                manager = context.get('manager')
                if manager:
                    project = manager.get_project(project_id)
                    if project and hasattr(project.engine,
                                           'get_performance_stats'):
                        stats = project.engine.get_performance_stats()
                        print(f"  ♪ 播放进度: {stats['current_beat']:.1f} beats | "
                              f"延迟: {stats['latency_ms']:.2f}ms | "
                              f"Underruns: {stats['underruns']}")

        except KeyboardInterrupt:
            print("\n\n⚠️  播放被中断")

        # 停止播放
        print("\n" + "=" * 70)
        resp = daw.transport.stop(project_id)
        print("✓ 播放已停止")

        # 显示最终统计
        if hasattr(project.engine, 'get_performance_stats'):
            stats = project.engine.get_performance_stats()
            print(f"\n播放统计:")
            print(f"  - 总Underruns: {stats['underruns']}")
            print(f"  - 总Overruns: {stats['overruns']}")
            print(f"  - 平均延迟: {stats['latency_ms']:.2f}ms")


def demo_advanced_features(daw: DAWFacade, context: dict):
    """演示高级特性"""
    print_section("PART 7: 高级特性")

    project_id = context['project_id']

    print("\n[7.1] 项目状态查询")
    resp = daw.query.get_project_overview(project_id)
    if resp.status == "success":
        data = resp.data
        print(f"✓ 项目概览:")
        print(f"  - 节点数: {data['node_count']}")
        print(f"  - 连接数: {data['connection_count']}")
        print(f"  - 速度: {data['tempo']} BPM")

    print("\n[7.2] 历史管理")
    resp = daw.history.get_undo_history(project_id)
    print(f"✓ 撤销栈: {resp.data['count']} 个命令")

    if resp.data['count'] > 0:
        print(f"  最近的命令:")
        for cmd in resp.data['history'][-3:]:
            print(f"    - {cmd}")


def demo_save_project(daw: DAWFacade, context: dict):
    """演示项目保存"""
    print_section("PART 8: 保存项目")

    project_id = context['project_id']

    print("\n[8.1] 保存到文件")
    resp = daw.project.save_project(project_id, "real_audio_test.mzc")

    if resp.status == "success":
        print(f"✓ 项目已保存")
        print(f"  文件: {resp.data['file_path']}")


def print_summary():
    """打印总结"""
    print_section("演示完成")

    summary = """
    🎉 Real DAW Core 演示成功完成！
    
    本演示展示了：
    
    ✓ 真实音频设备集成     - sounddevice实时音频I/O
    ✓ VST3插件扫描         - DawDreamer插件托管
    ✓ 实时音频处理         - 真实的DSP处理流程
    ✓ MIDI事件处理         - 准确的时间同步
    ✓ 延迟补偿             - 专业级延迟管理
    ✓ 性能监控             - CPU负载和缓冲区统计
    
    与Mock版本的对比：
    • Mock: 模拟播放（线程sleep）→ Real: 真实音频回调
    • Mock: 虚拟插件        → Real: VST3/AU插件
    • Mock: 打印日志        → Real: 实际音频输出
    • Mock: 无延迟问题      → Real: 专业延迟补偿
    
    架构优势：
    • 相同的Facade API      - Mock和Real可以互换
    • 清晰的接口分离        - 易于测试和扩展
    • 完整的Command系统     - 支持撤销/重做
    • 专业的信号流图        - 拓扑排序处理
    
    下一步：
    1. 集成更多VST3插件
    2. 实现音频录制
    3. 添加实时MIDI输入
    4. 实现多轨并行处理
    5. 优化性能和延迟
    """

    print(summary)
    print("  " + "═" * 66)
    print("  🎵 Ready for Professional Music Production 🎵")
    print("  " + "═" * 66 + "\n")


def main():
    """主程序"""
    try:
        print_banner()

        # 初始化Real DAW系统
        print_section("系统初始化")
        print("\n正在初始化 Real DAW Core...")

        # 创建Manager（48kHz, 512 samples）
        manager = RealDAWManager(sample_rate=48000, block_size=512)

        # 创建Services
        services = {
            "project": ProjectService(manager),
            "transport": TransportService(manager),
            "nodes": NodeService(manager, manager.plugin_registry),
            "routing": RoutingService(manager),
            "editing": EditingService(manager),
            "history": HistoryService(manager),
            "query": QueryService(manager, manager.plugin_registry),
            "system": SystemService(manager, manager.plugin_registry)
        }
        print(manager.plugin_registry.list_plugins())
        # 创建Facade
        daw = DAWFacade(manager, services)

        print("✓ Real DAW Manager 初始化完成")
        print("✓ 音频引擎就绪")
        print("✓ 插件注册表已扫描")
        print("✓ DAW Facade 已创建")

        # 运行演示
        demo_audio_devices(manager)
        demo_plugin_scanning(manager)

        context = create_simple_project(daw)
        context['manager'] = manager  # 保存引用

        create_musical_content(daw, context)
        setup_mixing(daw, context)
        demo_real_time_playback(daw, context)
        demo_advanced_features(daw, context)
        demo_save_project(daw, context)

        # 清理
        print_section("清理资源")
        resp = daw.project.close_project(context['project_id'])
        print("✓ 项目已关闭")
        print("✓ 音频引擎已停止")

        print_summary()

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  演示被用户中断")
        return 1

    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
