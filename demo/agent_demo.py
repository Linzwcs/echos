"""
Agent Demo - 使用AI Agent控制DAW
演示如何使用工具装饰器和AgentToolkit创建智能音乐制作助手
"""
import sys
from pathlib import Path
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from echos.core import DAWManager
from echos.backends.pedalboard import (
    PedalboardEngineFactory,
    PedalboardNodeFactory,
    PedalboardPluginRegistry,
)
from echos.core.plugin import PluginCache
from echos.core.persistence import ProjectSerializer
from echos.facade import DAWFacade
from echos.services import *
from echos.agent.tools import AgentToolkit, tool
from echos.models import ToolResponse

# ============================================================================
# 1. 创建自定义工具服务
# ============================================================================


class MusicCompositionService:
    """音乐创作服务 - 演示如何创建自定义工具"""

    def __init__(self, facade: DAWFacade):
        self._facade = facade

    @tool(category="composition",
          description="Create a basic chord progression on a track",
          returns="Created MIDI clips with chord progression")
    def create_chord_progression(self,
                                 track_name: str,
                                 progression: str,
                                 tempo: float = 120.0) -> ToolResponse:
        """
        Create a chord progression on specified track.
        
        Args:
            track_name: Name of the instrument track
            progression: Chord progression (e.g., "C-Am-F-G")
            tempo: Tempo in BPM
            
        Returns:
            Success response with created clips
        """
        try:
            # 解析和弦进行
            chords = progression.split("-")

            # 和弦音符映射 (简化版)
            chord_notes = {
                "C": [60, 64, 67],  # C E G
                "Am": [57, 60, 64],  # A C E
                "F": [65, 69, 72],  # F A C
                "G": [67, 71, 74],  # G B D
                "Dm": [62, 65, 69],  # D F A
                "Em": [64, 67, 71],  # E G B
            }

            # 查找轨道
            result = self._facade.query.find_node_by_name(name=track_name)
            if result.status == "error" or not result.data["nodes"]:
                return ToolResponse("error", None,
                                    f"Track '{track_name}' not found")

            track_id = result.data["nodes"][0]["node_id"]

            # 创建片段
            clips_created = []

            for i, chord in enumerate(chords):
                if chord not in chord_notes:
                    continue

                # 创建片段
                clip_result = self._facade.editing.create_midi_clip(
                    track_id=track_id,
                    start_beat=float(i * 4),
                    duration_beats=4.0,
                    name=f"{chord} Chord")

                if clip_result.status == "success":
                    clip_id = clip_result.data["clip_id"]

                    # 添加和弦音符
                    notes = [{
                        "pitch": pitch,
                        "velocity": 80,
                        "start_beat": 0.0,
                        "duration_beats": 3.5
                    } for pitch in chord_notes[chord]]

                    self._facade.editing.add_notes_to_clip(clip_id=clip_id,
                                                           notes=notes)

                    clips_created.append({
                        "chord": chord,
                        "clip_id": clip_id,
                        "start_beat": i * 4
                    })

            return ToolResponse(
                "success", {
                    "track_id": track_id,
                    "clips": clips_created,
                    "progression": progression
                }, f"Created {len(clips_created)} chord clips: {progression}")

        except Exception as e:
            return ToolResponse("error", None, str(e))

    @tool(category="composition",
          description="Create a drum pattern",
          returns="Created drum pattern clip")
    def create_drum_pattern(self,
                            track_name: str,
                            pattern: str = "basic",
                            bars: int = 4) -> ToolResponse:
        """
        Create a drum pattern on specified track.
        
        Args:
            track_name: Name of the drum track
            pattern: Pattern type ("basic", "rock", "electronic")
            bars: Number of bars (4 beats per bar)
            
        Returns:
            Success response with created clip
        """
        try:
            # 鼓组音符映射 (General MIDI)
            drum_notes = {
                "kick": 36,
                "snare": 38,
                "hihat_closed": 42,
                "hihat_open": 46,
            }

            # 预设模式
            patterns = {
                "basic": [
                    ("kick", [0.0, 2.0]),
                    ("snare", [1.0, 3.0]),
                    ("hihat_closed", [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]),
                ],
                "rock": [
                    ("kick", [0.0, 1.5, 2.0, 3.5]),
                    ("snare", [1.0, 3.0]),
                    ("hihat_closed", [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]),
                    ("hihat_open", [0.75, 2.75]),
                ],
                "electronic": [
                    ("kick", [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]),
                    ("snare", [1.0, 3.0]),
                    ("hihat_closed",
                     [0.25, 0.75, 1.25, 1.75, 2.25, 2.75, 3.25, 3.75]),
                ],
            }

            if pattern not in patterns:
                return ToolResponse(
                    "error", None,
                    f"Unknown pattern: {pattern}. Available: {list(patterns.keys())}"
                )

            # 查找轨道
            result = self._facade.query.find_node_by_name(name=track_name)
            if result.status == "error" or not result.data["nodes"]:
                return ToolResponse("error", None,
                                    f"Track '{track_name}' not found")

            track_id = result.data["nodes"][0]["node_id"]

            # 创建片段
            clip_result = self._facade.editing.create_midi_clip(
                track_id=track_id,
                start_beat=0.0,
                duration_beats=float(bars * 4),
                name=f"{pattern.title()} Drum Pattern")

            if clip_result.status != "success":
                return clip_result

            clip_id = clip_result.data["clip_id"]

            # 生成音符
            notes = []
            for bar in range(bars):
                for drum, beats in patterns[pattern]:
                    for beat in beats:
                        notes.append({
                            "pitch": drum_notes[drum],
                            "velocity": 100,
                            "start_beat": bar * 4 + beat,
                            "duration_beats": 0.1
                        })

            # 添加音符
            result = self._facade.editing.add_notes_to_clip(clip_id=clip_id,
                                                            notes=notes)

            return ToolResponse(
                "success", {
                    "track_id": track_id,
                    "clip_id": clip_id,
                    "pattern": pattern,
                    "bars": bars,
                    "note_count": len(notes)
                }, f"Created {pattern} drum pattern with {len(notes)} notes")

        except Exception as e:
            return ToolResponse("error", None, str(e))

    @tool(category="composition",
          description="Create a bass line that follows a chord progression",
          returns="Created bass line clip")
    def create_bass_line(self,
                         track_name: str,
                         progression: str,
                         style: str = "root") -> ToolResponse:
        """
        Create a bass line following a chord progression.
        
        Args:
            track_name: Name of the bass track
            progression: Chord progression (e.g., "C-Am-F-G")
            style: Bass style ("root", "walking", "octave")
            
        Returns:
            Success response with created bass clip
        """
        try:
            # 和弦根音映射
            root_notes = {
                "C": 48,  # C2
                "Am": 45,  # A1
                "F": 53,  # F2
                "G": 55,  # G2
                "Dm": 50,  # D2
                "Em": 52,  # E2
            }

            chords = progression.split("-")

            # 查找轨道
            result = self._facade.query.find_node_by_name(name=track_name)
            if result.status == "error" or not result.data["nodes"]:
                return ToolResponse("error", None,
                                    f"Track '{track_name}' not found")

            track_id = result.data["nodes"][0]["node_id"]

            # 创建片段
            clip_result = self._facade.editing.create_midi_clip(
                track_id=track_id,
                start_beat=0.0,
                duration_beats=float(len(chords) * 4),
                name="Bass Line")

            if clip_result.status != "success":
                return clip_result

            clip_id = clip_result.data["clip_id"]

            # 生成贝斯线
            notes = []

            for i, chord in enumerate(chords):
                if chord not in root_notes:
                    continue

                root = root_notes[chord]
                start_beat = float(i * 4)

                if style == "root":
                    # 简单根音
                    notes.append({
                        "pitch": root,
                        "velocity": 100,
                        "start_beat": start_beat,
                        "duration_beats": 3.5
                    })

                elif style == "walking":
                    # 行走贝斯
                    for beat in [0.0, 1.0, 2.0, 3.0]:
                        notes.append({
                            "pitch":
                            root +
                            (1 if beat == 1.0 else
                             0 if beat == 2.0 else -1 if beat == 3.0 else 0),
                            "velocity":
                            100,
                            "start_beat":
                            start_beat + beat,
                            "duration_beats":
                            0.9
                        })

                elif style == "octave":
                    # 八度贝斯
                    notes.extend([
                        {
                            "pitch": root,
                            "velocity": 100,
                            "start_beat": start_beat,
                            "duration_beats": 0.4
                        },
                        {
                            "pitch": root + 12,
                            "velocity": 80,
                            "start_beat": start_beat + 0.5,
                            "duration_beats": 0.4
                        },
                    ])

            # 添加音符
            result = self._facade.editing.add_notes_to_clip(clip_id=clip_id,
                                                            notes=notes)

            return ToolResponse(
                "success", {
                    "track_id": track_id,
                    "clip_id": clip_id,
                    "progression": progression,
                    "style": style,
                    "note_count": len(notes)
                }, f"Created {style} bass line with {len(notes)} notes")

        except Exception as e:
            return ToolResponse("error", None, str(e))


# ============================================================================
# 2. 初始化系统
# ============================================================================


def initialize_daw_system():
    """初始化完整的DAW系统"""
    print("\n" + "=" * 70)
    print("初始化DAW系统...")
    print("=" * 70)

    plugin_cache = PluginCache()
    plugin_registry = PedalboardPluginRegistry(plugin_cache)
    engine_factory = PedalboardEngineFactory()
    node_factory = PedalboardNodeFactory()
    serializer = ProjectSerializer(node_factory, plugin_registry)

    manager = DAWManager(
        serializer,
        plugin_registry,
        engine_factory,
        node_factory,
    )

    services = {
        "project": ProjectService(manager),
        "node": NodeService(manager),
        "transport": TransportService(manager),
        "editing": EditingService(manager),
        "history": HistoryService(manager),
        "query": QueryService(manager),
        "system": SystemService(manager),
        "routing": RoutingService(manager),
    }

    # 创建Facade
    facade = DAWFacade(manager, services)

    # 添加自定义创作服务
    composition_service = MusicCompositionService(facade)
    facade._services["composition"] = composition_service

    # 为自定义服务设置属性访问
    setattr(facade, "composition", composition_service)

    print("✓ DAW系统初始化完成")

    return facade, manager


# ============================================================================
# 3. 创建Agent工具包
# ============================================================================


def create_agent_toolkit(facade: DAWFacade):
    """创建Agent工具包"""
    print("\n" + "=" * 70)
    print("创建Agent工具包...")
    print("=" * 70)

    toolkit = AgentToolkit(facade)

    # 显示可用工具
    tools = toolkit.list_tools()

    print(f"\n✓ 工具包创建完成")
    print(f"  - 总工具数: {len(tools)}")

    # 按类别分组
    categories = {}
    for tool in tools:
        if tool.category not in categories:
            categories[tool.category] = []
        categories[tool.category].append(tool.name)

    print(f"\n工具分类:")
    for category, tool_names in sorted(categories.items()):
        print(f"  {category}: {len(tool_names)} 个工具")
        for name in tool_names[:3]:  # 显示前3个
            print(f"    - {name}")
        if len(tool_names) > 3:
            print(f"    ... 还有 {len(tool_names) - 3} 个")

    return toolkit


def demo_1_simple_project_creation(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("演示1: 使用Agent创建简单项目")
    print("=" * 70)

    print("\n用户: '创建一个名为 Electronic Track 的项目'")

    print("\nAgent执行:")

    result = toolkit.execute("project.create_project", name="Electronic Track")
    print(f"  1. {result.message}")
    project_id = result.data["project_id"]

    result = toolkit.execute("manager.set_active_project",
                             project_id=project_id)
    print(f"  2. 设置活动项目")

    result = toolkit.execute("transport.set_tempo", bpm=128.0)
    print(f"  3. {result.message}")

    print("\n✓ 项目创建完成!")

    return project_id


def demo_2_create_song_structure(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("演示2: 使用Agent创建完整歌曲结构")
    print("=" * 70)

    print("\n用户: '创建一首包含鼓、贝斯和钢琴的流行歌曲'")

    print("\nAgent规划:")
    print("  1. 创建项目")
    print("  2. 创建三个轨道")
    print("  3. 添加内容到每个轨道")
    print("  4. 调整混音")

    print("\nAgent执行:")

    result = toolkit.execute("project.create_project", name="Pop Song")
    print(f"  ✓ {result.message}")
    project_id = result.data["project_id"]

    toolkit.execute("transport.set_tempo", bpm=120.0)
    toolkit.execute("transport.set_time_signature", numerator=4, denominator=4)
    print(f"  ✓ 设置速度: 120 BPM, 拍号: 4/4")

    tracks = []

    for name in ["Drums", "Bass", "Piano"]:
        result = toolkit.execute("node.create_instrument_track",
                                 project_id=project_id,
                                 name=name)
        print(result)
        tracks.append(result.data["node_id"])

        print(f"  ✓ 创建轨道: {name}")

    result = toolkit.execute("editing.create_midi_clip",
                             project_id=project_id,
                             track_id=tracks[1],
                             start_beat=0,
                             duration_beats=4.0,
                             name="Bass Midi Clip")
    print(f"  ✓ {result.message}")

    result = toolkit.execute("editing.add_notes_to_clip",
                             project_id=project_id,
                             track_id=result.data['track_id'],
                             clip_id=result.data['clip_id'],
                             notes=[{
                                 "pitch": 60,
                                 "velocity": 100,
                                 "start_beat": 0.0,
                                 "duration_beats": 1.0
                             }, {
                                 "pitch": 64,
                                 "velocity": 100,
                                 "start_beat": 1.0,
                                 "duration_beats": 1.0
                             }])

    print(f"  ✓ {result.message}")

    adjustments = [
        ("Drums", -3.0),
        ("Bass", -6.0),
        ("Piano", -9.0),
    ]

    for track_name, volume in adjustments:
        result = toolkit.execute("editing.set_parameter_value",
                                 node_id=tracks[["Drums", "Bass",
                                                 "Piano"].index(track_name)],
                                 parameter_name="volume",
                                 value=volume)
        print(f"  ✓ 设置 {track_name} 音量: {volume} dB")

    print("\n✓ 歌曲结构创建完成!")

    return project_id


def demo_3_agent_chain_execution(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("演示3: Agent链式执行复杂任务")
    print("=" * 70)

    print("\n用户: '创建一个电子音乐项目，包含完整的编曲'")

    chain = [
        {
            "tool": "project.create_project",
            "params": {
                "name": "Electronic Music"
            },
        },
        {
            "tool": "transport.set_tempo",
            "params": {
                "project_id": "$result[0].data.project_id",
                "beat": 0,
                "bpm": 128.0,
            },
        },
        {
            "tool": "node.create_instrument_track",
            "params": {
                "project_id": "$result[0].data.project_id",
                "name": "Kick"
            },
        },
        {
            "tool": "node.create_instrument_track",
            "params": {
                "project_id": "$result[0].data.project_id",
                "name": "Synth Lead",
            },
        },
        {
            "tool": "node.create_instrument_track",
            "params": {
                "project_id": "$result[0].data.project_id",
                "name": "Bass"
            },
        },
        {
            "tool": "node.create_bus_track",
            "params": {
                "project_id": "$result[0].data.project_id",
                "name": "Reverb Bus"
            },
        },
    ]

    print(f"\nAgent执行链 ({len(chain)} 步):")

    results = toolkit.execute_chain(chain)

    for i, result in enumerate(results, 1):
        status_icon = "✓" if result.status == "success" else "✗"
        print(f"  {status_icon} 步骤 {i}: {result.message}")

        if result.status == "error":
            print(f"    错误: {result.message}")
            break

    if all(r.status == "success" for r in results):
        print("\n✓ 所有步骤执行成功!")
    else:
        print("\n✗ 执行链中断")

    return results


def demo_4_export_tools_for_llm(toolkit: AgentToolkit):
    """演示4: 导出工具供LLM使用"""
    print("\n" + "=" * 70)
    print("演示4: 导出工具定义供LLM使用")
    print("=" * 70)

    print("\n导出OpenAI格式工具定义...")
    openai_tools = toolkit.export_tools(format="openai")
    print(f"  ✓ 导出 {len(openai_tools)} 个工具")

    if openai_tools:
        print("\n示例工具 (OpenAI格式):")
        example = openai_tools[0]
        print(json.dumps(example, indent=2))

    print("\n导出Anthropic格式工具定义...")
    anthropic_tools = toolkit.export_tools(format="anthropic")
    print(f"  ✓ 导出 {len(anthropic_tools)} 个工具")

    if anthropic_tools:
        print("\n示例工具 (Anthropic格式):")
        example = anthropic_tools[0]
        print(json.dumps(example, indent=2))

    output_dir = Path("agent_tools_export")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "openai_tools.json", "w") as f:
        json.dump(openai_tools, f, indent=2)

    with open(output_dir / "anthropic_tools.json", "w") as f:
        json.dump(anthropic_tools, f, indent=2)

    print(f"\n✓ 工具定义已保存到 {output_dir}/")

    return openai_tools, anthropic_tools


def demo_5_tool_documentation(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("演示5: 生成完整工具文档")
    print("=" * 70)

    doc = toolkit.get_documentation()

    output_file = Path("agent_toolkit_documentation.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(doc)

    print(f"✓ 文档已生成: {output_file}")

    print("\n文档预览 (前20行):")
    print("-" * 70)
    lines = doc.split("\n")
    for line in lines[:20]:
        print(line)
    print("-" * 70)
    print(f"... 总共 {len(lines)} 行")

    return doc


def demo_6_execution_log(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("演示6: 执行日志和调试")
    print("=" * 70)

    toolkit.clear_log()

    print("\n执行操作...")
    result = toolkit.execute("project.create_project", name="Log Test")
    toolkit.execute("transport.set_tempo",
                    project_id=result.data['project_id'],
                    beat=0,
                    bpm=140.0)
    toolkit.execute("node.create_instrument_track",
                    project_id=result.data['project_id'],
                    name="Test Track")

    log = toolkit.get_execution_log()

    print(f"\n执行日志 (共 {len(log)} 条记录):")
    print("-" * 70)

    for entry in log:
        if entry['type'] == 'execution':
            print(f"[执行] {entry['tool']}")
            print(f"  参数: {entry['params']}")
        elif entry['type'] == 'result':
            print(f"[结果] {entry['status']}: {entry['message']}")
        elif entry['type'] == 'error':
            print(f"[错误] {entry['message']}")
        print()

    print("-" * 70)

    return log


def demo_7_interactive_agent():

    print("\n" + "=" * 70)
    print("演示7: 交互式音乐制作Agent")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    result = toolkit.execute("project.create_project",
                             name="Interactive Session")
    project_id = result.data["project_id"]

    print("\n欢迎使用音乐制作Agent!")
    print("输入 'help' 查看可用命令")
    print("输入 'quit' 退出")

    commands = {
        "create track":
        lambda project_id, name: toolkit.execute(
            "node.create_instrument_track", project_id=project_id, name=name),
        "set tempo":
        lambda project_id, beat, bpm: toolkit.execute("transport.set_tempo",
                                                      project_id=project_id,
                                                      beat=beat,
                                                      bpm=float(bpm)),
        "list tracks":
        lambda: toolkit.execute("node.list_nodes"),
        "create drums":
        lambda project_id, track_id, start_beat, duration_beats: toolkit.
        execute("editing.create_midi_clip",
                project_id=project_id,
                track_id=track_id,
                start_beat=start_beat,
                duration_beats=duration_beats,
                name="Bass Midi Clip"),
        "create chords":
        lambda project_id, track_id, clip_id: toolkit.execute(
            "editing.add_notes_to_clip",
            project_id=project_id,
            track_id=track_id,
            clip_id=clip_id,
            notes=[{
                "pitch": 60,
                "velocity": 100,
                "start_beat": 0.0,
                "duration_beats": 1.0
            }, {
                "pitch": 64,
                "velocity": 100,
                "start_beat": 1.0,
                "duration_beats": 1.0
            }]),
    }

    simulated_inputs = [
        "set tempo 128", "create track Drums", "create track Piano",
        "create drums Drums rock", "create chords Piano C-Am-F-G",
        "list tracks", "quit"
    ]

    for user_input in simulated_inputs:
        print(f"\n> {user_input}")

        if user_input == "quit":
            print("再见!")
            break

        if user_input == "help":
            print("可用命令:")
            for cmd in commands.keys():
                print(f"  - {cmd}")
            continue

        # 解析命令
        parts = user_input.split()

        if len(parts) >= 2:
            cmd_key = " ".join(parts[:2])

            if cmd_key in commands:
                try:
                    if cmd_key == "set tempo":
                        result = commands[cmd_key](parts[2])
                    elif cmd_key == "create track":
                        result = commands[cmd_key](" ".join(parts[2:]))
                    elif cmd_key == "create drums":
                        result = commands[cmd_key](
                            parts[2], parts[3] if len(parts) > 3 else "basic")
                    elif cmd_key == "create chords":
                        result = commands[cmd_key](
                            parts[2],
                            parts[3] if len(parts) > 3 else "C-G-Am-F")
                    elif cmd_key == "list tracks":
                        result = commands[cmd_key]()

                    print(f"  → {result.message}")

                except Exception as e:
                    print(f"  ✗ 错误: {e}")
            else:
                print("  ✗ 未知命令")

    manager.close_project(project_id)


def run_all_demos():

    print("\n" + "=" * 70)
    print("MuzaiCore Agent System - 完整演示")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    demos = [
        ("简单项目创建", lambda: demo_1_simple_project_creation(toolkit)),
        ("创建歌曲结构", lambda: demo_2_create_song_structure(toolkit)),
        ("链式执行", lambda: demo_3_agent_chain_execution(toolkit)),
        ("导出工具定义", lambda: demo_4_export_tools_for_llm(toolkit)),
        ("生成文档", lambda: demo_5_tool_documentation(toolkit)),
        ("执行日志", lambda: demo_6_execution_log(toolkit)),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n{'='*70}")
        print(f"运行演示 {i}/{len(demos)}: {name}")
        print(f"{'='*70}")

        try:
            demo_func()
            print(f"\n✓ 演示 {i} 完成")
        except Exception as e:
            print(f"\n✗ 演示 {i} 失败: {e}")
            import traceback
            traceback.print_exc()

        input("\n按回车继续...")

    print("\n" + "=" * 70)
    print("所有演示完成!")
    print("=" * 70)


def demo_llm_integration():

    print("\n" + "=" * 70)
    print("LLM集成示例")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    tools = toolkit.export_tools(format="openai")

    print("\n模拟与OpenAI GPT集成:")
    print("-" * 70)

    conversation = [{
        "role": "user",
        "content": "帮我创建一首电子音乐，包含鼓、贝斯和合成器"
    }, {
        "role":
        "assistant",
        "content":
        "我会帮您创建一首电子音乐。让我开始...",
        "tool_calls": [{
            "function": "project.create_project",
            "arguments": {
                "name": "Electronic Music",
                "project_id": "project_1"
            }
        }, {
            "function": "transport.set_tempo",
            "arguments": {
                "project_id": "project_1",
                "beat": 0,
                "bpm": 128.0
            }
        }, {
            "function": "node.create_instrument_track",
            "arguments": {
                "project_id": "project_1",
                "track_id": "track_1",
                "name": "Drums"
            }
        }, {
            "function": "node.create_instrument_track",
            "arguments": {
                "project_id": "project_1",
                "track_id": "track_2",
                "name": "Bass"
            }
        }, {
            "function": "node.create_instrument_track",
            "arguments": {
                "project_id": "project_1",
                "track_id": "track_3",
                "name": "Synth"
            }
        }]
    }]

    print("\nLLM建议的操作:")
    for msg in conversation:
        if msg["role"] == "user":
            print(f"\n用户: {msg['content']}")
        elif msg["role"] == "assistant":
            print(f"\nAssistant: {msg['content']}")

            if "tool_calls" in msg:
                print("\n执行工具调用:")
                for call in msg["tool_calls"]:
                    func_name = call["function"]
                    args = call["arguments"]

                    # 执行工具
                    result = toolkit.execute(func_name, **args)

                    status_icon = "✓" if result.status == "success" else "✗"
                    print(f"  {status_icon} {func_name}({args})")
                    print(f"     → {result.message}")

    print("\n" + "-" * 70)
    print("✓ LLM集成示例完成")


def demo_anthropic_integration():

    print("\n" + "=" * 70)
    print("Anthropic Claude集成示例")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    tools = toolkit.export_tools(format="anthropic")

    print("\n模拟与Claude集成:")
    print("-" * 70)

    print("\n用户请求: '创建一个爵士风格的项目'")

    print("\nClaude分析并调用工具:")

    tool_sequence = [
        ("project.create_project", {
            "name": "Performance Test",
            "project_id": "project 1"
        }),
        ("transport.set_tempo", {
            "project_id": "project 1",
            "beat": 0,
            "bpm": 140.0
        }),
        ("node.create_instrument_track", {
            "project_id": "project 1",
            "track_id": "tracl 1",
            "name": "Track 1"
        }),
        ("node.create_instrument_track", {
            "project_id": "project 1",
            "track_id": "tracl 2",
            "name": "Track 2"
        }),
        ("node.create_instrument_track", {
            "project_id": "project 1",
            "track_id": "tracl 3",
            "name": "Track 3"
        }),
    ]

    for tool_name, args in tool_sequence:
        result = toolkit.execute(tool_name, **args)
        status = "✓" if result.status == "success" else "✗"
        print(f"  {status} {tool_name}: {result.message}")

    print("\nClaude: 我已经创建了一个爵士项目，包含钢琴、贝斯和鼓，")
    print("        并添加了一个经典的爵士和弦进行 (Dm-G-C-Am)。")

    print("\n" + "-" * 70)


def scenario_1_beginner_tutorial():
    """场景1: 初学者教程"""
    print("\n" + "=" * 70)
    print("应用场景1: 初学者教程助手")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    print("\n场景: 用户想学习如何创建第一首歌")
    print("\nAgent教程:")

    steps = [
        {
            "instruction":
            "第一步: 让我们创建一个新项目",
            "action": ("project.create_project", {
                "name": "Performance Test",
                "project_id": "project 1"
            }),
            "explanation":
            "项目是所有音乐内容的容器"
        },
        {
            "instruction":
            "第二步: 设置速度为120 BPM（适合流行音乐）",
            "action": ("transport.set_tempo", {
                "project_id": "project 1",
                "beat": 0,
                "bpm": 140.0
            }),
            "explanation":
            "BPM决定音乐的快慢"
        },
        {
            "instruction":
            "第三步: 创建一个鼓轨道",
            "action": ("node.create_instrument_track", {
                "project_id": "project 1",
                "track_id": "tracl 1",
                "name": "Drums"
            }),
            "explanation":
            "鼓提供节奏基础"
        },
        {
            "instruction":
            "第四步: 添加基础鼓点Clip",
            "action": ("editing.create_midi_clip", {
                "project_id": "project 1",
                "track_id": "tracl 1",
                "start_beat": 0,
                "duration_beats": 4.0,
                "name": "Bass Midi Clip",
                "clip_id": "clip 1",
            }),
            "explanation":
            "这是一个简单的4小节鼓点"
        },
        {
            "instruction":
            "第四步: 添加基础鼓点模式",
            "action": ("editing.add_notes_to_clip", {
                "project_id":
                "project 1",
                "track_id":
                "tracl 1",
                "clip_id":
                "clip 1",
                "notes": [{
                    "pitch": 60,
                    "velocity": 100,
                    "start_beat": 0.0,
                    "duration_beats": 1.0
                }, {
                    "pitch": 64,
                    "velocity": 100,
                    "start_beat": 1.0,
                    "duration_beats": 1.0
                }]
            }),
            "explanation":
            "这是一个简单的4小节鼓点"
        },
    ]

    for i, step in enumerate(steps, 1):
        print(f"\n{step['instruction']}")

        tool_name, args = step["action"]
        result = toolkit.execute(tool_name, **args)

        print(f"  → {result.message}")
        print(f"  💡 提示: {step['explanation']}")

    print("\n✓ 教程完成！您已经创建了第一首歌的基础。")


def scenario_2_professional_workflow():
    """场景2: 专业制作流程"""
    print("\n" + "=" * 70)
    print("应用场景2: 专业音乐制作工作流")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    print("\n场景: 快速创建一首完整的流行歌曲编曲")

    print("\n阶段1: 项目设置")
    toolkit.execute("project_create_project", name="Pop Hit Production")
    toolkit.execute("transport_set_tempo", bpm=128.0)
    print("  ✓ 项目初始化完成")

    print("\n阶段2: 创建轨道结构")
    tracks = ["Kick", "Snare", "Hi-Hat", "Bass", "Lead Synth", "Pad", "Vocals"]
    for track_name in tracks:
        toolkit.execute("node_create_instrument_track", name=track_name)
    print(f"  ✓ 创建了 {len(tracks)} 个轨道")

    print("\n阶段3: 添加音乐内容")

    # 鼓组部分
    toolkit.execute("composition_create_drum_pattern",
                    track_name="Kick",
                    pattern="basic",
                    bars=8)
    toolkit.execute("composition_create_drum_pattern",
                    track_name="Hi-Hat",
                    pattern="electronic",
                    bars=8)
    print("  ✓ 添加鼓组模式")

    # 和声部分
    toolkit.execute("composition_create_chord_progression",
                    track_name="Pad",
                    progression="C-G-Am-F",
                    tempo=128.0)
    toolkit.execute("composition_create_chord_progression",
                    track_name="Lead Synth",
                    progression="C-G-Am-F",
                    tempo=128.0)
    print("  ✓ 添加和弦进行")

    # 贝斯线
    toolkit.execute("composition_create_bass_line",
                    track_name="Bass",
                    progression="C-G-Am-F",
                    style="octave")
    print("  ✓ 添加贝斯线")

    print("\n阶段4: 混音调整")
    mix_settings = [
        ("Kick", -3.0),
        ("Snare", -6.0),
        ("Hi-Hat", -9.0),
        ("Bass", -6.0),
        ("Lead Synth", -9.0),
        ("Pad", -12.0),
    ]

    for track_name, volume in mix_settings:
        print(f"  ✓ {track_name}: {volume} dB")

    print("\n✓ 专业编曲流程完成！")
    print("  - 总计 7 个轨道")
    print("  - 包含鼓组、贝斯、和声和主旋律")
    print("  - 混音已经过基础调整")


# ============================================================================
# 11. 高级功能演示
# ============================================================================


def demo_advanced_tool_features(toolkit: AgentToolkit):
    """演示高级工具特性"""
    print("\n" + "=" * 70)
    print("高级功能: 工具特性演示")
    print("=" * 70)

    # 1. 工具搜索
    print("\n1. 工具搜索:")
    print("   搜索所有创作相关的工具...")
    composition_tools = toolkit.list_tools(category="composition")
    print(f"   找到 {len(composition_tools)} 个创作工具:")
    for tool in composition_tools:
        print(f"     - {tool.name}: {tool.description}")

    # 2. 获取特定工具的详细信息
    print("\n2. 工具详细信息:")
    tool = toolkit.get_tool("composition_create_chord_progression")
    if tool:
        print(f"   工具: {tool.name}")
        print(f"   描述: {tool.description}")
        print(f"   参数:")
        for param in tool.parameters:
            req = "必需" if param.required else "可选"
            print(
                f"     - {param.name} ({param.type}, {req}): {param.description}"
            )

    # 3. 获取工具文档
    print("\n3. 单个工具文档:")
    doc = toolkit.get_documentation("composition_create_drum_pattern")
    print(doc)


# ============================================================================
# 12. 性能和监控
# ============================================================================


def demo_performance_monitoring(toolkit: AgentToolkit):
    """演示性能监控"""
    print("\n" + "=" * 70)
    print("性能监控演示")
    print("=" * 70)

    import time

    # 清空日志
    toolkit.clear_log()

    print("\n执行一系列操作并监控性能...")

    operations = [
        ("project.create_project", {
            "name": "Performance Test",
            "project_id": "project 1"
        }),
        ("transport.set_tempo", {
            "project_id": "project 1",
            "beat": 0,
            "bpm": 140.0
        }),
        ("node.create_instrument_track", {
            "project_id": "project 1",
            "track_id": "tracl 1",
            "name": "Track 1"
        }),
        ("node_create_instrument_track", {
            "project_id": "project 1",
            "track_id": "tracl 2",
            "name": "Track 2"
        }),
        ("node_create_instrument_track", {
            "project_id": "project 1",
            "track_id": "tracl 3",
            "name": "Track 3"
        }),
    ]

    start_time = time.time()

    for tool_name, args in operations:
        op_start = time.time()
        result = toolkit.execute(tool_name, **args)
        op_time = time.time() - op_start

        print(f"  {tool_name}: {op_time*1000:.2f}ms")

    total_time = time.time() - start_time

    print(f"\n性能统计:")
    print(f"  总操作数: {len(operations)}")
    print(f"  总耗时: {total_time*1000:.2f}ms")
    print(f"  平均耗时: {total_time*1000/len(operations):.2f}ms")

    # 显示执行日志
    log = toolkit.get_execution_log()
    print(f"  日志记录数: {len(log)}")


# ============================================================================
# 主程序
# ============================================================================


def main():
    """主程序"""
    import sys

    print("\n" + "=" * 70)
    print("MuzaiCore Agent System - 演示程序")
    print("=" * 70)

    print("\n可用演示:")
    print("  1. 运行所有演示")
    print("  2. 简单项目创建")
    print("  3. 创建歌曲结构")
    print("  4. 链式执行")
    print("  5. 导出工具定义")
    print("  6. LLM集成示例")
    print("  7. 初学者教程场景")
    print("  8. 专业制作场景")
    print("  9. 协作Agent场景")
    print(" 10. 交互式Agent")
    print(" 11. 高级功能演示")
    print(" 12. 性能监控")

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\n请选择 (1-12): ").strip()

    if choice not in ["1", "7", "8", "9", "10"]:
        facade, manager = initialize_daw_system()
        toolkit = create_agent_toolkit(facade)

    if choice == "1":
        run_all_demos()
    elif choice == "2":
        facade, manager = initialize_daw_system()
        toolkit = create_agent_toolkit(facade)
        demo_1_simple_project_creation(toolkit)
    elif choice == "3":
        facade, manager = initialize_daw_system()
        toolkit = create_agent_toolkit(facade)
        demo_2_create_song_structure(toolkit)
    elif choice == "4":
        demo_3_agent_chain_execution(toolkit)
    elif choice == "5":
        demo_4_export_tools_for_llm(toolkit)
    elif choice == "6":
        demo_llm_integration()
        demo_anthropic_integration()
    elif choice == "7":
        scenario_1_beginner_tutorial()
    elif choice == "8":
        scenario_2_professional_workflow()
    elif choice == "9":
        facade, manager = initialize_daw_system()
        toolkit = create_agent_toolkit(facade)
        demo_advanced_tool_features(toolkit)
    elif choice == "10":
        demo_performance_monitoring(toolkit)
    else:
        print("无效选择")
        return

    print("\n" + "=" * 70)
    print("演示完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
