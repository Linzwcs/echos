# file: src/MuzaiCore/main_demo.py
"""
MuzaiCore 完整功能演示
展示专业DAW核心的所有主要功能
"""
import time
import sys
import os

# 添加项目根目录到路径
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from MuzaiCore.drivers.mock.manager import MockDAWManager
from MuzaiCore.drivers.mock.plugin import MockPluginRegistry
from MuzaiCore.facade import DAWFacade
from MuzaiCore.services import (
    NodeService,
    EditingService,
    ProjectService,
    RoutingService,
    HistoryService,
    TransportService,
    QueryService,
    SystemService,
)


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('=' * 70)


def print_response(response, verbose=True):
    """打印工具响应"""
    status_symbol = "✓" if response.status == "success" else "✗"
    status_color = "\033[92m" if response.status == "success" else "\033[91m"
    reset_color = "\033[0m"

    print(f"{status_color}{status_symbol}{reset_color} {response.message}")

    if verbose and response.data:
        for key, value in response.data.items():
            if isinstance(value, dict):
                print(f"  - {key}:")
                for k, v in value.items():
                    print(f"      {k}: {v}")
            elif isinstance(value, list) and len(value) > 3:
                print(f"  - {key}: [{len(value)} items]")
            else:
                print(f"  - {key}: {value}")


def print_banner():
    """打印启动横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║              🎵  MuzaiCore DAW Engine v1.0  🎵              ║
    ║                                                              ║
    ║         Professional Headless DAW for AI Agents              ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def demo_basic_workflow(daw: DAWFacade):
    """演示基础工作流"""
    print_section("PART 1: 基础项目设置")

    # 创建项目
    print("\n[1.1] 创建新项目")
    resp = daw.project.create_project("AI音乐创作演示项目")
    print_response(resp)
    project_id = resp.data['project_id']

    # 创建基础轨道
    print("\n[1.2] 创建基础轨道结构")

    print("  → 创建主乐器轨道...")
    resp = daw.nodes.create_instrument_track(project_id, "Lead Synth")
    print_response(resp, verbose=False)
    lead_track_id = resp.data['node_id']

    resp = daw.nodes.create_instrument_track(project_id, "Bass")
    print_response(resp, verbose=False)
    bass_track_id = resp.data['node_id']

    resp = daw.nodes.create_instrument_track(project_id, "Pad")
    print_response(resp, verbose=False)
    pad_track_id = resp.data['node_id']

    print("  → 创建音频轨道...")
    resp = daw.nodes.create_audio_track(project_id, "Vocals")
    print_response(resp, verbose=False)
    vocal_track_id = resp.data['node_id']

    resp = daw.nodes.create_audio_track(project_id, "Drums")
    print_response(resp, verbose=False)
    drums_track_id = resp.data['node_id']

    print("  → 创建效果总线...")
    resp = daw.nodes.create_bus_track(project_id, "Reverb Bus")
    print_response(resp, verbose=False)
    reverb_bus_id = resp.data['node_id']

    resp = daw.nodes.create_bus_track(project_id, "Delay Bus")
    print_response(resp, verbose=False)
    delay_bus_id = resp.data['node_id']

    print("  → 创建主控制...")
    resp = daw.nodes.create_vca_track(project_id, "Master VCA")
    print_response(resp, verbose=False)
    vca_id = resp.data['node_id']

    # 列出所有节点
    print("\n[1.3] 项目结构概览")
    resp = daw.nodes.list_nodes(project_id)
    print(f"✓ 已创建 {resp.data['count']} 个节点:")
    for node in resp.data['nodes']:
        print(f"  - {node['type']:20s} : {node['name']}")

    return {
        'project_id': project_id,
        'lead_track_id': lead_track_id,
        'bass_track_id': bass_track_id,
        'pad_track_id': pad_track_id,
        'vocal_track_id': vocal_track_id,
        'drums_track_id': drums_track_id,
        'reverb_bus_id': reverb_bus_id,
        'delay_bus_id': delay_bus_id,
        'vca_id': vca_id
    }


def demo_plugin_management(daw: DAWFacade, context: dict):
    """演示插件管理"""
    print_section("PART 2: 插件管理")

    project_id = context['project_id']

    # 列出可用插件
    print("\n[2.1] 扫描可用插件")
    resp = daw.system.list_available_plugins()
    print(f"✓ 发现 {resp.data['count']} 个插件:")
    for plugin in resp.data['plugins']:
        print(f"  - {plugin['name']:20s} ({plugin['category']})")

    # 为轨道添加插件
    print("\n[2.2] 为轨道添加插件")

    print("  → Lead Synth: 添加乐器 + 混响")
    resp = daw.nodes.add_insert_plugin(project_id, context['lead_track_id'],
                                       "muzaicore.mock.basic_synth")
    print_response(resp, verbose=False)

    resp = daw.nodes.add_insert_plugin(project_id, context['lead_track_id'],
                                       "muzaicore.mock.simple_reverb")
    print_response(resp, verbose=False)

    print("  → Bass: 添加乐器")
    resp = daw.nodes.add_insert_plugin(project_id, context['bass_track_id'],
                                       "muzaicore.mock.basic_synth")
    print_response(resp, verbose=False)

    print("  → Pad: 添加乐器 + 混响")
    resp = daw.nodes.add_insert_plugin(project_id, context['pad_track_id'],
                                       "muzaicore.mock.basic_synth")
    print_response(resp, verbose=False)

    resp = daw.nodes.add_insert_plugin(project_id, context['pad_track_id'],
                                       "muzaicore.mock.simple_reverb")
    print_response(resp, verbose=False)

    # 获取插件详情
    print("\n[2.3] 查询插件详细信息")
    resp = daw.system.get_plugin_details("muzaicore.mock.basic_synth")
    print_response(resp)


def demo_signal_routing(daw: DAWFacade, context: dict):
    """演示信号路由"""
    print_section("PART 3: 信号路由设置")

    project_id = context['project_id']

    # 创建发送
    print("\n[3.1] 创建效果发送")

    print("  → Lead Synth -> Reverb Bus (Post-Fader)")
    resp = daw.routing.create_send(project_id,
                                   context['lead_track_id'],
                                   context['reverb_bus_id'],
                                   is_post_fader=True)
    print_response(resp, verbose=False)

    print("  → Vocals -> Reverb Bus (Post-Fader)")
    resp = daw.routing.create_send(project_id,
                                   context['vocal_track_id'],
                                   context['reverb_bus_id'],
                                   is_post_fader=True)
    print_response(resp, verbose=False)

    print("  → Lead Synth -> Delay Bus (Pre-Fader)")
    resp = daw.routing.create_send(project_id,
                                   context['lead_track_id'],
                                   context['delay_bus_id'],
                                   is_post_fader=False)
    print_response(resp, verbose=False)

    print("  → Pad -> Delay Bus (Post-Fader)")
    resp = daw.routing.create_send(project_id,
                                   context['pad_track_id'],
                                   context['delay_bus_id'],
                                   is_post_fader=True)
    print_response(resp, verbose=False)

    # 列出所有连接
    print("\n[3.2] 路由总览")
    resp = daw.routing.list_connections(project_id)
    if resp.data['count'] > 0:
        print(f"✓ 已建立 {resp.data['count']} 个发送连接")
    else:
        print("✓ 路由系统就绪 (无外部连接)")


def demo_content_creation(daw: DAWFacade, context: dict):
    """演示内容创建"""
    print_section("PART 4: 创建音乐内容")

    project_id = context['project_id']

    # 创建主旋律
    print("\n[4.1] 创建主旋律 (Lead Synth)")
    resp = daw.editing.create_midi_clip(project_id,
                                        context['lead_track_id'],
                                        start_beat=0.0,
                                        duration_beats=16.0,
                                        name="Main Melody")
    print_response(resp, verbose=False)
    lead_clip_id = resp.data['clip_id']

    # C大调旋律线
    lead_notes = [
        # 第一乐句 (0-4拍)
        {
            "pitch": 72,
            "velocity": 100,
            "start_beat": 0.0,
            "duration_beats": 0.5
        },  # C5
        {
            "pitch": 74,
            "velocity": 95,
            "start_beat": 0.5,
            "duration_beats": 0.5
        },  # D5
        {
            "pitch": 76,
            "velocity": 100,
            "start_beat": 1.0,
            "duration_beats": 1.0
        },  # E5
        {
            "pitch": 74,
            "velocity": 90,
            "start_beat": 2.0,
            "duration_beats": 0.5
        },  # D5
        {
            "pitch": 72,
            "velocity": 95,
            "start_beat": 2.5,
            "duration_beats": 1.5
        },  # C5

        # 第二乐句 (4-8拍)
        {
            "pitch": 69,
            "velocity": 100,
            "start_beat": 4.0,
            "duration_beats": 0.5
        },  # A4
        {
            "pitch": 71,
            "velocity": 95,
            "start_beat": 4.5,
            "duration_beats": 0.5
        },  # B4
        {
            "pitch": 72,
            "velocity": 100,
            "start_beat": 5.0,
            "duration_beats": 1.0
        },  # C5
        {
            "pitch": 74,
            "velocity": 90,
            "start_beat": 6.0,
            "duration_beats": 0.5
        },  # D5
        {
            "pitch": 76,
            "velocity": 95,
            "start_beat": 6.5,
            "duration_beats": 1.5
        },  # E5

        # 第三乐句 (8-12拍)
        {
            "pitch": 77,
            "velocity": 105,
            "start_beat": 8.0,
            "duration_beats": 1.0
        },  # F5
        {
            "pitch": 76,
            "velocity": 100,
            "start_beat": 9.0,
            "duration_beats": 0.5
        },  # E5
        {
            "pitch": 74,
            "velocity": 95,
            "start_beat": 9.5,
            "duration_beats": 0.5
        },  # D5
        {
            "pitch": 72,
            "velocity": 100,
            "start_beat": 10.0,
            "duration_beats": 2.0
        },  # C5 (长音)

        # 第四乐句 (12-16拍)
        {
            "pitch": 71,
            "velocity": 90,
            "start_beat": 12.0,
            "duration_beats": 1.0
        },  # B4
        {
            "pitch": 69,
            "velocity": 95,
            "start_beat": 13.0,
            "duration_beats": 1.0
        },  # A4
        {
            "pitch": 67,
            "velocity": 100,
            "start_beat": 14.0,
            "duration_beats": 2.0
        },  # G4 (结束)
    ]

    resp = daw.editing.add_notes_to_clip(project_id, lead_clip_id, lead_notes)
    print(f"  ✓ 添加了 {len(lead_notes)} 个音符")

    # 创建贝斯线
    print("\n[4.2] 创建贝斯线 (Bass)")
    resp = daw.editing.create_midi_clip(project_id,
                                        context['bass_track_id'],
                                        start_beat=0.0,
                                        duration_beats=16.0,
                                        name="Bass Line")
    print_response(resp, verbose=False)
    bass_clip_id = resp.data['clip_id']

    # 简单的4小节贝斯模式
    bass_notes = [
        # C根音模式 (0-4拍)
        {
            "pitch": 36,
            "velocity": 110,
            "start_beat": 0.0,
            "duration_beats": 1.0
        },  # C2
        {
            "pitch": 36,
            "velocity": 90,
            "start_beat": 1.0,
            "duration_beats": 0.5
        },
        {
            "pitch": 43,
            "velocity": 85,
            "start_beat": 1.5,
            "duration_beats": 0.5
        },  # G2
        {
            "pitch": 36,
            "velocity": 100,
            "start_beat": 2.0,
            "duration_beats": 1.0
        },
        {
            "pitch": 40,
            "velocity": 85,
            "start_beat": 3.0,
            "duration_beats": 1.0
        },  # E2

        # Am模式 (4-8拍)
        {
            "pitch": 33,
            "velocity": 110,
            "start_beat": 4.0,
            "duration_beats": 1.0
        },  # A1
        {
            "pitch": 33,
            "velocity": 90,
            "start_beat": 5.0,
            "duration_beats": 0.5
        },
        {
            "pitch": 40,
            "velocity": 85,
            "start_beat": 5.5,
            "duration_beats": 0.5
        },  # E2
        {
            "pitch": 33,
            "velocity": 100,
            "start_beat": 6.0,
            "duration_beats": 1.0
        },
        {
            "pitch": 36,
            "velocity": 85,
            "start_beat": 7.0,
            "duration_beats": 1.0
        },  # C2

        # F模式 (8-12拍)
        {
            "pitch": 29,
            "velocity": 110,
            "start_beat": 8.0,
            "duration_beats": 1.0
        },  # F1
        {
            "pitch": 29,
            "velocity": 90,
            "start_beat": 9.0,
            "duration_beats": 0.5
        },
        {
            "pitch": 36,
            "velocity": 85,
            "start_beat": 9.5,
            "duration_beats": 0.5
        },  # C2
        {
            "pitch": 29,
            "velocity": 100,
            "start_beat": 10.0,
            "duration_beats": 1.0
        },
        {
            "pitch": 33,
            "velocity": 85,
            "start_beat": 11.0,
            "duration_beats": 1.0
        },  # A1

        # G模式 (12-16拍)
        {
            "pitch": 31,
            "velocity": 110,
            "start_beat": 12.0,
            "duration_beats": 1.0
        },  # G1
        {
            "pitch": 31,
            "velocity": 90,
            "start_beat": 13.0,
            "duration_beats": 0.5
        },
        {
            "pitch": 38,
            "velocity": 85,
            "start_beat": 13.5,
            "duration_beats": 0.5
        },  # D2
        {
            "pitch": 31,
            "velocity": 100,
            "start_beat": 14.0,
            "duration_beats": 1.0
        },
        {
            "pitch": 35,
            "velocity": 85,
            "start_beat": 15.0,
            "duration_beats": 1.0
        },  # B1
    ]

    resp = daw.editing.add_notes_to_clip(project_id, bass_clip_id, bass_notes)
    print(f"  ✓ 添加了 {len(bass_notes)} 个音符")

    # 创建和弦垫音
    print("\n[4.3] 创建和弦垫音 (Pad)")
    resp = daw.editing.create_midi_clip(project_id,
                                        context['pad_track_id'],
                                        start_beat=0.0,
                                        duration_beats=16.0,
                                        name="Chord Pad")
    print_response(resp, verbose=False)
    pad_clip_id = resp.data['clip_id']

    # 和弦进行: C - Am - F - G
    pad_notes = [
        # C和弦 (0-4拍)
        {
            "pitch": 48,
            "velocity": 70,
            "start_beat": 0.0,
            "duration_beats": 4.0
        },  # C3
        {
            "pitch": 52,
            "velocity": 65,
            "start_beat": 0.0,
            "duration_beats": 4.0
        },  # E3
        {
            "pitch": 55,
            "velocity": 65,
            "start_beat": 0.0,
            "duration_beats": 4.0
        },  # G3
        {
            "pitch": 60,
            "velocity": 60,
            "start_beat": 0.0,
            "duration_beats": 4.0
        },  # C4

        # Am和弦 (4-8拍)
        {
            "pitch": 45,
            "velocity": 70,
            "start_beat": 4.0,
            "duration_beats": 4.0
        },  # A2
        {
            "pitch": 48,
            "velocity": 65,
            "start_beat": 4.0,
            "duration_beats": 4.0
        },  # C3
        {
            "pitch": 52,
            "velocity": 65,
            "start_beat": 4.0,
            "duration_beats": 4.0
        },  # E3
        {
            "pitch": 57,
            "velocity": 60,
            "start_beat": 4.0,
            "duration_beats": 4.0
        },  # A3

        # F和弦 (8-12拍)
        {
            "pitch": 41,
            "velocity": 70,
            "start_beat": 8.0,
            "duration_beats": 4.0
        },  # F2
        {
            "pitch": 45,
            "velocity": 65,
            "start_beat": 8.0,
            "duration_beats": 4.0
        },  # A2
        {
            "pitch": 48,
            "velocity": 65,
            "start_beat": 8.0,
            "duration_beats": 4.0
        },  # C3
        {
            "pitch": 53,
            "velocity": 60,
            "start_beat": 8.0,
            "duration_beats": 4.0
        },  # F3

        # G和弦 (12-16拍)
        {
            "pitch": 43,
            "velocity": 70,
            "start_beat": 12.0,
            "duration_beats": 4.0
        },  # G2
        {
            "pitch": 47,
            "velocity": 65,
            "start_beat": 12.0,
            "duration_beats": 4.0
        },  # B2
        {
            "pitch": 50,
            "velocity": 65,
            "start_beat": 12.0,
            "duration_beats": 4.0
        },  # D3
        {
            "pitch": 55,
            "velocity": 60,
            "start_beat": 12.0,
            "duration_beats": 4.0
        },  # G3
    ]

    resp = daw.editing.add_notes_to_clip(project_id, pad_clip_id, pad_notes)
    print(f"  ✓ 添加了 {len(pad_notes)} 个音符")

    print(f"\n✓ 总计创建:")
    print(f"  - 3个MIDI片段")
    print(f"  - {len(lead_notes) + len(bass_notes) + len(pad_notes)} 个音符")

    return {
        'lead_clip_id': lead_clip_id,
        'bass_clip_id': bass_clip_id,
        'pad_clip_id': pad_clip_id
    }


def demo_mixing_automation(daw: DAWFacade, context: dict):
    """演示混音和自动化"""
    print_section("PART 5: 混音和自动化")

    project_id = context['project_id']

    # 使用宏命令组合混音操作
    print("\n[5.1] 开始混音操作 (使用宏命令)")
    resp = daw.history.begin_macro(project_id, "Initial Mix Setup")
    print_response(resp, verbose=False)

    # 设置各轨道音量
    print("\n  → 设置轨道音量")
    volumes = {
        'lead_track_id': -3.0,
        'bass_track_id': -6.0,
        'pad_track_id': -12.0,
        'vocal_track_id': -9.0,
        'drums_track_id': -4.5,
        'reverb_bus_id': -10.0,
        'delay_bus_id': -12.0
    }

    for track_key, volume in volumes.items():
        track_id = context[track_key]
        resp = daw.editing.set_parameter_value(project_id, track_id, "volume",
                                               volume)
        if resp.status == "success":
            print(f"    {track_key:20s}: {volume:+.1f} dB")

    # 设置声像
    print("\n  → 设置立体声声像")
    pans = {
        'lead_track_id': 0.0,  # 居中
        'bass_track_id': 0.0,  # 居中
        'pad_track_id': 0.0,  # 居中
        'vocal_track_id': 0.0,  # 居中
        'drums_track_id': 0.0  # 居中
    }

    for track_key, pan in pans.items():
        track_id = context[track_key]
        resp = daw.editing.set_parameter_value(project_id, track_id, "pan",
                                               pan)
        if resp.status == "success":
            pan_str = "Center" if pan == 0.0 else f"{pan:+.2f}"
            print(f"    {track_key:20s}: {pan_str}")

    # 结束宏命令
    resp = daw.history.end_macro(project_id)
    print(f"\n✓ 混音宏命令完成")

    # 添加动态自动化
    print("\n[5.2] 添加音量自动化 (渐强效果)")

    print("  → Lead Synth: 从 -12dB 渐强到 -3dB")
    for beat in range(0, 17, 2):
        value = -12.0 + (beat / 16.0) * 9.0
        resp = daw.editing.add_automation_point(project_id,
                                                context['lead_track_id'],
                                                "volume", float(beat), value)
    print(f"    ✓ 添加了 9 个自动化点")

    print("  → Pad: 反向渐弱效果 (-8dB 到 -14dB)")
    for beat in range(0, 17, 2):
        value = -8.0 - (beat / 16.0) * 6.0
        resp = daw.editing.add_automation_point(project_id,
                                                context['pad_track_id'],
                                                "volume", float(beat), value)
    print(f"    ✓ 添加了 9 个自动化点")


def demo_project_query(daw: DAWFacade, context: dict):
    """演示项目查询"""
    print_section("PART 6: 项目状态查询")

    project_id = context['project_id']

    # 项目概览
    print("\n[6.1] 项目概览")
    resp = daw.query.get_project_overview(project_id)
    if resp.status == "success":
        data = resp.data
        print(f"✓ 项目: {data['name']}")
        print(f"  - 节点总数: {data['node_count']}")
        print(f"  - 连接数: {data['connection_count']}")
        print(f"  - 速度: {data['tempo']} BPM")
        print(
            f"  - 拍号: {data['time_signature'][0]}/{data['time_signature'][1]}")
        print(f"  - 状态: {data['transport_status']}")
        print(f"\n  节点类型分布:")
        for node_type, count in data['node_types'].items():
            print(f"    - {node_type:25s}: {count}")

    # 节点详情
    print("\n[6.2] Lead Synth 轨道详细信息")
    resp = daw.query.get_node_details(project_id, context['lead_track_id'])
    if resp.status == "success":
        data = resp.data
        print(f"✓ {data['name']} ({data['type']})")
        print(f"  - Node ID: {data['node_id'][:16]}...")
        print(f"  - 端口数: {len(data['ports'])}")

        if 'mixer_channel' in data:
            mc = data['mixer_channel']
            print(f"\n  混音器通道:")
            print(f"    - 音量: {mc['volume']:.2f} dB")
            print(f"    - 声像: {mc['pan']:.2f}")
            print(f"    - 静音: {mc['muted']}")
            print(f"    - 独奏: {mc['solo']}")
            print(f"    - 插入效果: {mc['insert_count']}")
            print(f"    - 发送: {mc['send_count']}")

    # 查找节点
    print("\n[6.3] 按名称搜索节点")
    resp = daw.query.find_node_by_name(project_id, "bus")
    if resp.status == "success":
        print(f"✓ 找到 {resp.data['count']} 个匹配节点:")
        for match in resp.data['matches']:
            print(f"  - {match['name']:20s} ({match['type']})")

    # 获取完整项目树
    print("\n[6.4] 完整项目结构")
    resp = daw.query.get_full_project_tree(project_id)
    if resp.status == "success":
        print(f"✓ 项目结构包含 {len(resp.data['tree'])} 个节点:\n")
        for node in resp.data['tree']:
            node_type = node['type']
            node_name = node['name']

            info_parts = []
            if 'parameters' in node:
                param_count = len(node['parameters'])
                if param_count > 0:
                    info_parts.append(f"{param_count} params")
            if 'clips' in node:
                clip_count = len(node['clips'])
                if clip_count > 0:
                    info_parts.append(f"{clip_count} clips")
            if 'inserts' in node:
                insert_count = len(node['inserts'])
                if insert_count > 0:
                    info_parts.append(f"{insert_count} inserts")

            info_str = ", ".join(info_parts) if info_parts else "empty"
            print(f"  [{node_type:15s}] {node_name:20s} ({info_str})")


def demo_history_management(daw: DAWFacade, context: dict):
    """演示历史管理"""
    print_section("PART 7: 撤销/重做系统")

    project_id = context['project_id']

    # 查看历史
    print("\n[7.1] 命令历史")
    resp = daw.history.get_undo_history(project_id)
    if resp.status == "success":
        print(f"✓ 撤销栈: {resp.data['count']} 项")
        for i, cmd in enumerate(resp.data['history'][-8:], 1):
            print(f"  {i}. {cmd}")

    # 测试撤销
    print("\n[7.2] 撤销操作演示")

    print("  → 撤销最后一个操作...")
    resp = daw.history.undo(project_id)
    print_response(resp, verbose=False)

    print("  → 再撤销一次...")
    resp = daw.history.undo(project_id)
    print_response(resp, verbose=False)

    # 查看更新后的历史
    resp = daw.history.get_undo_history(project_id)
    print(f"  ✓ 当前撤销栈: {resp.data['count']} 项")

    # 测试重做
    print("\n[7.3] 重做操作演示")

    resp = daw.history.can_redo(project_id)
    if resp.data['can_redo']:
        print("  → 重做撤销的操作...")
        resp = daw.history.redo(project_id)
        print_response(resp, verbose=False)

        resp = daw.history.redo(project_id)
        print_response(resp, verbose=False)

    resp = daw.history.get_redo_history(project_id)
    print(f"  ✓ 当前重做栈: {resp.data['count']} 项")


def demo_transport_control(daw: DAWFacade, context: dict):
    """演示走带控制"""
    print_section("PART 8: 走带控制和播放")

    project_id = context['project_id']

    # 设置播放参数
    print("\n[8.1] 设置播放参数")

    print("  → 设置速度: 128 BPM")
    resp = daw.transport.set_tempo(project_id, 128.0)
    print_response(resp, verbose=False)

    print("  → 设置拍号: 4/4")
    resp = daw.transport.set_time_signature(project_id, 4, 4)
    print_response(resp, verbose=False)

    # 获取走带状态
    print("\n[8.2] 当前走带状态")
    resp = daw.transport.get_transport_state(project_id)
    if resp.status == "success":
        data = resp.data
        print(f"✓ 走带信息:")
        print(f"  - 状态: {data['status']}")
        print(f"  - 速度: {data['tempo']} BPM")
        print(
            f"  - 拍号: {data['time_signature']['numerator']}/{data['time_signature']['denominator']}"
        )

    # 播放演示
    print("\n[8.3] 开始播放演示")
    print("  → 启动音频引擎...")
    resp = daw.transport.play(project_id)
    print_response(resp, verbose=False)

    print("\n  ♪ 播放中...")
    print("  " + "─" * 50)

    # 模拟播放3秒
    for i in range(3):
        time.sleep(1)
        print(f"  ♪ 播放进度: {i+1}/3 秒")

    print("  " + "─" * 50)

    # 停止播放
    print("\n  → 停止播放...")
    resp = daw.transport.stop(project_id)
    print_response(resp, verbose=False)


def demo_advanced_features(daw: DAWFacade, context: dict):
    """演示高级功能"""
    print_section("PART 9: 高级功能演示")

    project_id = context['project_id']

    # 参数查询
    print("\n[9.1] 查询特定参数值")
    resp = daw.query.get_parameter_value(project_id, context['lead_track_id'],
                                         "volume")
    print_response(resp)

    # 节点连接信息
    print("\n[9.2] 查询节点连接")
    resp = daw.query.get_connections_for_node(project_id,
                                              context['lead_track_id'])
    if resp.status == "success":
        data = resp.data
        print(f"✓ {data['node_id'][:16]}... 的连接:")
        print(f"  - 输入连接: {len(data['inputs'])}")
        print(f"  - 输出连接: {len(data['outputs'])}")

        if data['outputs']:
            print(f"\n  输出到:")
            for conn in data['outputs']:
                print(f"    → {conn['destination']} ({conn['type']})")

    # 系统信息
    print("\n[9.3] 系统信息")
    resp = daw.system.get_system_info()
    print_response(resp)


def demo_help_system(daw: DAWFacade):
    """演示帮助系统"""
    print_section("PART 10: 内置帮助系统")

    # 获取服务列表
    print("\n[10.1] 可用服务类别")
    resp = daw.get_help()
    if resp.status == "success":
        print("✓ MuzaiCore 提供以下服务:\n")
        for category, description in resp.data['categories'].items():
            print(f"  [{category:10s}] {description}")

    # 获取特定服务的方法
    print("\n[10.2] 'editing' 服务的可用方法")
    resp = daw.get_help(category='editing')
    if resp.status == "success":
        print(f"✓ {len(resp.data['methods'])} 个可用方法:\n")
        for method in resp.data['methods']:
            print(f"  - {method}")

    # 获取特定方法的文档
    print("\n[10.3] 方法详细文档")
    resp = daw.get_help(category='editing', method='set_parameter_value')
    if resp.status == "success":
        print(f"✓ 方法签名:")
        print(f"  {resp.data['signature']}\n")
        print(f"  文档:")
        print(f"  {resp.data['documentation']}")


def demo_project_statistics(daw: DAWFacade, context: dict):
    """显示最终统计"""
    print_section("项目统计摘要")

    project_id = context['project_id']

    # 项目信息
    resp = daw.query.get_project_overview(project_id)
    if resp.status == "success":
        data = resp.data
        print(f"\n✓ 项目: {data['name']}")
        print(f"  {'─' * 60}")
        print(f"  配置:")
        print(f"    • 速度: {data['tempo']} BPM")
        print(
            f"    • 拍号: {data['time_signature'][0]}/{data['time_signature'][1]}"
        )
        print(f"    • 状态: {data['transport_status']}")
        print(f"\n  内容统计:")
        print(f"    • 总节点数: {data['node_count']}")
        print(f"    • 信号连接: {data['connection_count']}")

        print(f"\n  节点类型:")
        for node_type, count in sorted(data['node_types'].items()):
            print(f"    • {node_type:20s}: {count}")

    # 从manager获取底层统计
    from MuzaiCore.drivers.mock.manager import MockDAWManager
    manager = context.get('manager')
    if manager:
        project = manager.get_project(project_id)
        if project:
            # 命令历史统计
            stats = project.command_manager.get_statistics()
            print(f"\n  命令历史:")
            print(f"    • 总命令数: {stats['total_commands']}")
            print(f"    • 合并命令: {stats['merged_commands']}")
            print(f"    • 撤销栈: {stats['undo_stack_size']}")
            print(f"    • 重做栈: {stats['redo_stack_size']}")

            # 路由图统计
            router_stats = project.router.get_graph_statistics()
            print(f"\n  路由图:")
            print(f"    • 图节点: {router_stats['node_count']}")
            print(f"    • 图边数: {router_stats['connection_count']}")
            print(f"    • 有循环: {router_stats['has_cycles']}")
            print(f"    • 连通分量: {router_stats['weakly_connected_components']}")
            print(f"    • 最大延迟: {router_stats['max_latency']} samples")


def demo_save_close(daw: DAWFacade, context: dict):
    """保存和关闭项目"""
    print_section("PART 11: 保存和关闭")

    project_id = context['project_id']

    print("\n[11.1] 保存项目")
    resp = daw.project.save_project(project_id, "./tmp/ai_music_demo.mzc")
    print_response(resp)

    print("\n[11.2] 关闭项目")
    resp = daw.project.close_project(project_id)
    print_response(resp)


def print_final_summary():
    """打印最终总结"""
    print_section("演示完成")

    summary = """
    🎉 MuzaiCore 完整演示成功完成！
    
    本演示展示了以下核心功能:
    
    ✓ 项目管理        - 创建、保存、加载、关闭
    ✓ 轨道系统        - 乐器、音频、总线、VCA轨道
    ✓ 插件管理        - 扫描、加载、配置虚拟乐器和效果
    ✓ 信号路由        - 发送/返回、推子前/后路由
    ✓ 内容创建        - MIDI片段、音符编辑
    ✓ 混音自动化      - 音量、声像、参数自动化曲线
    ✓ 历史管理        - 撤销/重做、宏命令
    ✓ 走带控制        - 播放、停止、速度和拍号
    ✓ 查询系统        - 项目状态、节点详情、连接信息
    ✓ 帮助系统        - API文档、方法签名
    
    这是一个完全功能的、专业级的DAW核心引擎，
    专为AI Agent设计，通过统一的Facade API提供访问。
    
    架构特点:
    • 清晰的分层架构 (Core → Services → Facade)
    • 命令模式支持完整撤销/重做
    • 信号流图 (DAG) 路由系统
    • 延迟补偿和拓扑排序
    • 可扩展的插件系统
    • Mock和Real实现分离
    
    下一步:
    1. 替换Mock实现为Real音频引擎
    2. 集成VST3/AU插件托管
    3. 添加音频录制和文件处理
    4. 实现高级调制矩阵
    5. 连接到AI Agent进行自动化音乐创作
    """

    print(summary)
    print("  " + "═" * 66)
    print("  🎵 Ready for AI-Driven Music Production 🎵")
    print("  " + "═" * 66 + "\n")


def main():
    """主演示程序"""
    try:
        # 打印启动横幅
        print_banner()

        # 初始化系统
        print_section("系统初始化")
        print("\n正在初始化 MuzaiCore...")

        manager = MockDAWManager()
        registry = MockPluginRegistry()
        registry.scan_for_plugins()
        services = {
            "project": ProjectService(manager),
            "transport": TransportService(manager),
            "nodes": NodeService(manager, registry),
            "routing": RoutingService(manager),
            "editing": EditingService(manager),
            "history": HistoryService(manager),
            "query": QueryService(manager, registry),
            "system": SystemService(manager, registry)
        }

        daw = DAWFacade(manager, services)

        print("✓ DAW Manager 已初始化")
        print("✓ Plugin Registry 已初始化")
        print("✓ DAW Facade 已创建")
        print(f"\n可用服务: {', '.join(daw.list_tools().keys())}")

        # 执行演示
        context = {}

        # Part 1-4: 基础设置和内容创建
        project_context = demo_basic_workflow(daw)
        context.update(project_context)
        context['manager'] = manager  # 保存manager引用用于统计

        demo_plugin_management(daw, context)
        demo_signal_routing(daw, context)

        clip_context = demo_content_creation(daw, context)
        context.update(clip_context)

        # Part 5-8: 混音、查询、历史和播放
        demo_mixing_automation(daw, context)
        demo_project_query(daw, context)
        demo_history_management(daw, context)
        demo_transport_control(daw, context)

        # Part 9-11: 高级功能、帮助系统和保存
        demo_advanced_features(daw, context)
        demo_help_system(daw)
        demo_project_statistics(daw, context)
        demo_save_close(daw, context)

        # 打印最终总结
        print_final_summary()

    except KeyboardInterrupt:
        print("\n\n⚠️  演示被用户中断")
        print("正在清理...")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
