# file: examples/agent_integration_demo.py
"""
AI Agent Integration Demo
==========================
演示AI Agent如何使用工具与DAW交互

场景：
1. Agent使用OpenAI Function Calling格式的工具
2. Agent可以创建音乐项目
3. Agent可以添加轨道和插件
4. Agent可以创建MIDI内容
5. Agent可以查询项目状态
6. 支持所有三种引擎（Mock/Real/DawDreamer）
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from MuzaiCore.drivers.mock.manager import MockDAWManager
from MuzaiCore.drivers.real.manager import RealDAWManager
from MuzaiCore.drivers.dawdreamer_driver.manager import DawDreamerDAWManager
from MuzaiCore.facade import DAWFacade
from MuzaiCore.services import *
from MuzaiCore.agent.tools import AgentToolkit


def print_banner():
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║         🤖  AI Agent + MuzaiCore Integration  🤖            ║
    ║                                                              ║
    ║           Demonstrate Agent-Driven Music Creation            ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('=' * 70)


def create_daw_system(engine_type: str = "mock"):
    """
    创建DAW系统
    
    Args:
        engine_type: "mock", "real", "dawdreamer"
    """
    print(f"\n[System] Initializing {engine_type.upper()} engine...")

    if engine_type == "mock":
        manager = MockDAWManager()
    elif engine_type == "real":
        manager = RealDAWManager(sample_rate=48000, block_size=512)
    elif engine_type == "dawdreamer":
        manager = DawDreamerDAWManager(sample_rate=48000, block_size=512)
    else:
        raise ValueError(f"Unknown engine type: {engine_type}")

    # 创建Services
    services = {
        "project": ProjectService(manager),
        "transport": TransportService(manager),
        "nodes": NodeService(manager, manager.plugin_registry),  # 使用V2
        "routing": RoutingService(manager),
        "editing": EditingService(manager),
        "history": HistoryService(manager),
        "query": QueryService(manager, manager.plugin_registry),
        "system": SystemService(manager, manager.plugin_registry)
    }

    daw = DAWFacade(manager, services)

    print(f"✓ {engine_type.upper()} engine initialized")

    return daw, manager


def demo_tool_discovery(toolkit: AgentToolkit):
    """演示工具发现"""
    print_section("PART 1: Tool Discovery")

    print("\n[1.1] Available tool categories:")
    from MuzaiCore.agent.tools import ToolCategory

    for category in ToolCategory:
        tools = toolkit.list_tools(category)
        print(f"  - {category.value}: {len(tools)} tools")

    print("\n[1.2] Sample tools (OpenAI format):")
    openai_tools = toolkit.get_tools_for_openai()

    for tool in openai_tools[:5]:
        print(f"\n  Tool: {tool['name']}")
        print(f"  Description: {tool['description']}")
        print(f"  Parameters: {len(tool['parameters']['properties'])} params")


def demo_agent_workflow(toolkit: AgentToolkit):
    """演示Agent工作流"""
    print_section("PART 2: Agent Workflow Simulation")

    print("\n[Simulating AI Agent creating a music project]")
    print("-" * 70)

    # 步骤1：创建项目
    print("\n[Agent] I need to create a new project first...")
    result = toolkit.execute_tool("create_project", name="AI Generated Song")
    print(f"[System] {result.message}")

    if result.status != "success":
        print("[Agent] Failed to create project. Stopping.")
        return

    project_id = result.data['project_id']
    print(f"[Agent] Great! Got project_id: {project_id[:16]}...")

    # 步骤2：设置项目参数
    print("\n[Agent] Let me set the tempo to 128 BPM...")
    result = toolkit.execute_tool("set_tempo",
                                  project_id=project_id,
                                  bpm=128.0)
    print(f"[System] {result.message}")

    # 步骤3：创建轨道
    print("\n[Agent] Now I'll create an instrument track for the melody...")
    result = toolkit.execute_tool("create_instrument_track",
                                  project_id=project_id,
                                  name="Lead Synth")
    print(f"[System] {result.message}")

    if result.status != "success":
        print("[Agent] Failed to create track. Continuing anyway...")
        lead_track_id = None
    else:
        lead_track_id = result.data['node_id']
        print(f"[Agent] Track created with ID: {lead_track_id[:16]}...")

    # 步骤4：添加插件
    if lead_track_id:
        print("\n[Agent] Adding a synthesizer plugin to the track...")
        result = toolkit.execute_tool(
            "add_plugin",
            project_id=project_id,
            track_id=lead_track_id,
            plugin_id="muzaicore.builtin.basic_synth")
        print(f"[System] {result.message}")
        print(
            f"[Agent] Plugin added using {result.data.get('engine_type', 'unknown')} engine"
        )

    # 步骤5：创建MIDI内容
    if lead_track_id:
        print("\n[Agent] Creating a MIDI clip for the melody...")
        result = toolkit.execute_tool("create_midi_clip",
                                      project_id=project_id,
                                      track_id=lead_track_id,
                                      start_beat=0.0,
                                      duration_beats=4.0,
                                      name="Melody Pattern")
        print(f"[System] {result.message}")

        if result.status == "success":
            clip_id = result.data['clip_id']
            print(f"[Agent] Clip created: {clip_id[:16]}...")

            # 添加音符
            print("\n[Agent] Adding notes to the clip...")
            notes = [
                {
                    "pitch": 60,
                    "velocity": 100,
                    "start_beat": 0.0,
                    "duration_beats": 0.5
                },
                {
                    "pitch": 64,
                    "velocity": 95,
                    "start_beat": 0.5,
                    "duration_beats": 0.5
                },
                {
                    "pitch": 67,
                    "velocity": 100,
                    "start_beat": 1.0,
                    "duration_beats": 0.5
                },
                {
                    "pitch": 72,
                    "velocity": 105,
                    "start_beat": 1.5,
                    "duration_beats": 1.5
                },
            ]

            result = toolkit.execute_tool("add_notes",
                                          project_id=project_id,
                                          clip_id=clip_id,
                                          notes=notes)
            print(f"[System] {result.message}")
            print(f"[Agent] Added {len(notes)} notes to the melody")

    # 步骤6：查询项目状态
    print("\n[Agent] Let me check the current project status...")
    result = toolkit.execute_tool("get_project_overview",
                                  project_id=project_id)

    if result.status == "success":
        print(f"[System] {result.message}")
        print(f"[Agent] Project overview:")
        print(f"  - Tempo: {result.data['tempo']} BPM")
        print(f"  - Tracks: {result.data['node_count']}")
        print(
            f"  - Time Signature: {result.data['time_signature'][0]}/{result.data['time_signature'][1]}"
        )

    # 步骤7：列出所有节点
    print("\n[Agent] Listing all tracks in the project...")
    result = toolkit.execute_tool("list_nodes", project_id=project_id)

    if result.status == "success":
        print(f"[System] Found {result.data['count']} nodes:")
        for node in result.data['nodes']:
            print(f"  - {node['name']} ({node['type']})")

    # 步骤8：保存项目
    print("\n[Agent] Finally, let me save the project...")
    result = toolkit.execute_tool("save_project",
                                  project_id=project_id,
                                  file_path="ai_generated_song.mzc")
    print(f"[System] {result.message}")

    print("\n[Agent] ✓ Music project creation complete!")


def demo_tool_documentation(toolkit: AgentToolkit):
    """演示工具文档"""
    print_section("PART 3: Tool Documentation")

    print("\n[3.1] Documentation for 'create_midi_clip' tool:")
    print("-" * 70)

    doc = toolkit.get_tool_documentation("create_midi_clip")
    print(doc)

    print("\n[3.2] Documentation for 'add_notes' tool:")
    print("-" * 70)

    doc = toolkit.get_tool_documentation("add_notes")
    print(doc)


def demo_openai_integration(toolkit: AgentToolkit):
    """演示OpenAI集成格式"""
    print_section("PART 4: OpenAI Function Calling Format")

    print("\n[4.1] Sample OpenAI function definition:")

    openai_tools = toolkit.get_tools_for_openai()

    # 找到create_project工具
    create_project_tool = next(
        (t for t in openai_tools if t['name'] == 'create_project'), None)

    if create_project_tool:
        print("\nTool definition (JSON):")
        print(json.dumps(create_project_tool, indent=2))

        print("\n[4.2] How to use with OpenAI API:")
        print("""
import openai

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Create a music project called 'My Song'"}
    ],
    functions=toolkit.get_tools_for_openai(),
    function_call="auto"
)

# Extract function call
function_call = response.choices[0].message.function_call
tool_name = function_call.name
arguments = json.loads(function_call.arguments)

# Execute the tool
result = toolkit.execute_tool(tool_name, **arguments)
        """)


def demo_anthropic_integration(toolkit: AgentToolkit):
    """演示Anthropic集成格式"""
    print_section("PART 5: Anthropic Tool Format")

    print("\n[5.1] Sample Anthropic tool definition:")

    anthropic_tools = toolkit.get_tools_for_anthropic()

    # 找到create_project工具
    create_project_tool = next(
        (t for t in anthropic_tools if t['name'] == 'create_project'), None)

    if create_project_tool:
        print("\nTool definition (JSON):")
        print(json.dumps(create_project_tool, indent=2))

        print("\n[5.2] How to use with Anthropic API:")
        print("""
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=toolkit.get_tools_for_anthropic(),
    messages=[
        {"role": "user", "content": "Create a music project called 'My Song'"}
    ]
)

# Extract tool use
for content in response.content:
    if content.type == "tool_use":
        tool_name = content.name
        arguments = content.input
        
        # Execute the tool
        result = toolkit.execute_tool(tool_name, **arguments)
        """)


def demo_error_handling(toolkit: AgentToolkit):
    """演示错误处理"""
    print_section("PART 6: Error Handling")

    print("\n[6.1] Testing invalid parameters:")

    # 无效的tempo值
    print("\n[Test] Setting tempo to invalid value (-100)...")
    result = toolkit.execute_tool("set_tempo", project_id="test", bpm=-100.0)
    print(f"[Result] Status: {result.status}")
    print(f"[Result] Message: {result.message}")

    # 缺少必需参数
    print("\n[Test] Creating project without name...")
    result = toolkit.execute_tool("create_project")
    print(f"[Result] Status: {result.status}")
    print(f"[Result] Message: {result.message}")

    # 不存在的工具
    print("\n[Test] Calling non-existent tool...")
    result = toolkit.execute_tool("non_existent_tool")
    print(f"[Result] Status: {result.status}")
    print(f"[Result] Message: {result.message}")


def print_summary():
    """打印总结"""
    print_section("Demo Complete")

    summary = """
    🎉 AI Agent Integration Demo Complete!
    
    Demonstrated Features:
    
    ✓ Tool Discovery
      - 40+ tools organized by category
      - OpenAI Function Calling format
      - Anthropic Tool format
      - Complete documentation
    
    ✓ Agent Workflow
      - Project creation
      - Track and plugin management
      - MIDI content creation
      - Project state queries
      - Error handling
    
    ✓ Multi-Engine Support
      - Mock engine (fast testing)
      - Real engine (Python DSP)
      - DawDreamer engine (VST3 support)
      - Automatic engine detection
      - Transparent plugin creation
    
    ✓ LLM Integration
      - OpenAI GPT-4 compatible
      - Anthropic Claude compatible
      - Structured tool definitions
      - Parameter validation
      - Clear error messages
    
    Architecture Benefits:
    
    • Unified Interface
      - Single toolkit for all engines
      - Consistent tool format
      - Automatic adaptation
    
    • Type Safety
      - Parameter validation
      - Type checking
      - Range verification
    
    • Discoverability
      - Self-documenting tools
      - Rich descriptions
      - Usage examples
    
    • Extensibility
      - Easy to add new tools
      - Pluggable architecture
      - Engine-agnostic design
    
    Next Steps:
    
    1. Integrate with real LLM (GPT-4/Claude)
    2. Add more complex workflows
    3. Implement multi-turn conversations
    4. Add tool chaining capabilities
    5. Create domain-specific agents
    """

    print(summary)
    print("  " + "═" * 66)
    print("  🤖 AI-Powered Music Production Ready! 🤖")
    print("  " + "═" * 66 + "\n")


def main():
    """主程序"""
    try:
        print_banner()

        # 选择引擎类型
        print("\nSelect engine type:")
        print("  1. Mock (fastest, for testing)")
        print("  2. Real (Python DSP, real audio)")
        print("  3. DawDreamer (VST3 support, best quality)")

        choice = input("\nEnter choice (1-3, default=1): ").strip() or "1"

        engine_map = {"1": "mock", "2": "real", "3": "dawdreamer"}

        engine_type = engine_map.get(choice, "mock")

        # 创建DAW系统
        print_section("Initialization")
        daw, manager = create_daw_system(engine_type)

        # 创建Agent工具包
        toolkit = AgentToolkit(daw)
        print(
            f"✓ Agent toolkit initialized with {len(toolkit.list_tools())} tools"
        )

        # 运行演示
        demo_tool_discovery(toolkit)
        demo_agent_workflow(toolkit)
        demo_tool_documentation(toolkit)
        demo_openai_integration(toolkit)
        demo_anthropic_integration(toolkit)
        demo_error_handling(toolkit)

        print_summary()

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        return 1

    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
