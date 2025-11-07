import sys
from pathlib import Path
import json

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


def initialize_daw_system():

    print("\n" + "=" * 70)
    print("Initializing DAW system...")
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

    # Create Facade
    facade = DAWFacade(manager, services)

    print("✓ DAW system initialization complete")

    return facade, manager


# ============================================================================
# 3. Create Agent Toolkit
# ============================================================================


def create_agent_toolkit(facade: DAWFacade):
    """Create Agent toolkit"""
    print("\n" + "=" * 70)
    print("Creating Agent toolkit...")
    print("=" * 70)

    toolkit = AgentToolkit(facade)

    # Display available tools
    tools = toolkit.list_tools()

    print(f"\n✓ Toolkit creation complete")
    print(f"  - Total tools: {len(tools)}")

    # Group by category
    categories = {}
    for tool in tools:
        if tool.category not in categories:
            categories[tool.category] = []
        categories[tool.category].append(tool.name)

    print(f"\nTool Categories:")
    for category, tool_names in sorted(categories.items()):
        print(f"  {category}: {len(tool_names)} tools")
        for name in tool_names[:3]:  # Display first 3
            print(f"    - {name}")
        if len(tool_names) > 3:
            print(f"    ... and {len(tool_names) - 3} more")

    return toolkit


def demo_1_simple_project_creation(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("Demo 1: Create a simple project using the Agent")
    print("=" * 70)

    print("\nUser: 'Create a project named Electronic Track'")

    print("\nAgent executes:")

    result = toolkit.execute("project.create_project", name="Electronic Track")
    print(f"  1. {result.message}")
    project_id = result.data["project_id"]

    result = toolkit.execute("manager.set_active_project",
                             project_id=project_id)
    print(f"  2. Set active project")

    result = toolkit.execute("transport.set_tempo", bpm=128.0)
    print(f"  3. {result.message}")

    print("\n✓ Project creation complete!")

    return project_id


def demo_2_create_song_structure(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("Demo 2: Create a complete song structure using the Agent")
    print("=" * 70)

    print("\nUser: 'Create a pop song with drums, bass, and piano'")

    print("\nAgent planning:")
    print("  1. Create a project")
    print("  2. Create three tracks")
    print("  3. Add content to each track")
    print("  4. Adjust the mix")

    print("\nAgent executes:")

    result = toolkit.execute("project.create_project", name="Pop Song")
    print(f"  ✓ {result.message}")
    project_id = result.data["project_id"]

    toolkit.execute("transport.set_tempo", bpm=120.0)
    toolkit.execute("transport.set_time_signature", numerator=4, denominator=4)
    print(f"  ✓ Set tempo: 120 BPM, time signature: 4/4")

    tracks = []

    for name in ["Drums", "Bass", "Piano"]:
        result = toolkit.execute("node.create_instrument_track",
                                 project_id=project_id,
                                 name=name)
        print(result)
        tracks.append(result.data["node_id"])

        print(f"  ✓ Created track: {name}")

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
        print(f"  ✓ Set {track_name} volume: {volume} dB")

    print("\n✓ Song structure creation complete!")

    return project_id


def demo_3_agent_chain_execution(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("Demo 3: Agent chain execution for a complex task")
    print("=" * 70)

    print(
        "\nUser: 'Create an electronic music project with a full arrangement'")

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

    print(f"\nAgent execution chain ({len(chain)} steps):")

    results = toolkit.execute_chain(chain)

    for i, result in enumerate(results, 1):
        status_icon = "✓" if result.status == "success" else "✗"
        print(f"  {status_icon} Step {i}: {result.message}")

        if result.status == "error":
            print(f"    Error: {result.message}")
            break

    if all(r.status == "success" for r in results):
        print("\n✓ All steps executed successfully!")
    else:
        print("\n✗ Execution chain interrupted")

    return results


def demo_4_export_tools_for_llm(toolkit: AgentToolkit):
    """Demo 4: Export tools for LLM use"""
    print("\n" + "=" * 70)
    print("Demo 4: Export tool definitions for LLM use")
    print("=" * 70)

    print("\nExporting tool definitions in OpenAI format...")
    openai_tools = toolkit.export_tools(format="openai")
    print(f"  ✓ Exported {len(openai_tools)} tools")

    if openai_tools:
        print("\nExample tool (OpenAI format):")
        example = openai_tools[0]
        print(json.dumps(example, indent=2))

    print("\nExporting tool definitions in Anthropic format...")
    anthropic_tools = toolkit.export_tools(format="anthropic")
    print(f"  ✓ Exported {len(anthropic_tools)} tools")

    if anthropic_tools:
        print("\nExample tool (Anthropic format):")
        example = anthropic_tools[0]
        print(json.dumps(example, indent=2))

    output_dir = Path("agent_tools_export")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "openai_tools.json", "w") as f:
        json.dump(openai_tools, f, indent=2)

    with open(output_dir / "anthropic_tools.json", "w") as f:
        json.dump(anthropic_tools, f, indent=2)

    print(f"\n✓ Tool definitions saved to {output_dir}/")

    return openai_tools, anthropic_tools


def demo_5_tool_documentation(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("Demo 5: Generate complete tool documentation")
    print("=" * 70)

    doc = toolkit.get_documentation()

    output_file = Path("agent_toolkit_documentation.md")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(doc)

    print(f"✓ Documentation generated: {output_file}")

    print("\nDocumentation preview (first 20 lines):")
    print("-" * 70)
    lines = doc.split("\n")
    for line in lines[:20]:
        print(line)
    print("-" * 70)
    print(f"... Total of {len(lines)} lines")

    return doc


def demo_6_execution_log(toolkit: AgentToolkit):

    print("\n" + "=" * 70)
    print("Demo 6: Execution log and debugging")
    print("=" * 70)

    toolkit.clear_log()

    print("\nExecuting operations...")
    result = toolkit.execute("project.create_project", name="Log Test")
    toolkit.execute("transport.set_tempo",
                    project_id=result.data['project_id'],
                    beat=0,
                    bpm=140.0)
    toolkit.execute("node.create_instrument_track",
                    project_id=result.data['project_id'],
                    name="Test Track")

    log = toolkit.get_execution_log()

    print(f"\nExecution log (total of {len(log)} records):")
    print("-" * 70)

    for entry in log:
        if entry['type'] == 'execution':
            print(f"[Execution] {entry['tool']}")
            print(f"  Parameters: {entry['params']}")
        elif entry['type'] == 'result':
            print(f"[Result] {entry['status']}: {entry['message']}")
        elif entry['type'] == 'error':
            print(f"[Error] {entry['message']}")
        print()

    print("-" * 70)

    return log


def demo_7_interactive_agent():

    print("\n" + "=" * 70)
    print("Demo 7: Interactive Music Production Agent")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    result = toolkit.execute("project.create_project",
                             name="Interactive Session")
    project_id = result.data["project_id"]

    print("\nWelcome to the Music Production Agent!")
    print("Type 'help' to see available commands")
    print("Type 'quit' to exit")

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
            print("Goodbye!")
            break

        if user_input == "help":
            print("Available commands:")
            for cmd in commands.keys():
                print(f"  - {cmd}")
            continue

        # Parse command
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
                    print(f"  ✗ Error: {e}")
            else:
                print("  ✗ Unknown command")

    manager.close_project(project_id)


def run_all_demos():

    print("\n" + "=" * 70)
    print("MuzaiCore Agent System - Complete Demo")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    demos = [
        ("Simple Project Creation",
         lambda: demo_1_simple_project_creation(toolkit)),
        ("Create Song Structure",
         lambda: demo_2_create_song_structure(toolkit)),
        ("Chain Execution", lambda: demo_3_agent_chain_execution(toolkit)),
        ("Export Tool Definitions",
         lambda: demo_4_export_tools_for_llm(toolkit)),
        ("Generate Documentation", lambda: demo_5_tool_documentation(toolkit)),
        ("Execution Log", lambda: demo_6_execution_log(toolkit)),
    ]

    for i, (name, demo_func) in enumerate(demos, 1):
        print(f"\n{'='*70}")
        print(f"Running Demo {i}/{len(demos)}: {name}")
        print(f"{'='*70}")

        try:
            demo_func()
            print(f"\n✓ Demo {i} complete")
        except Exception as e:
            print(f"\n✗ Demo {i} failed: {e}")
            import traceback
            traceback.print_exc()

        input("\nPress Enter to continue...")

    print("\n" + "=" * 70)
    print("All demos complete!")
    print("=" * 70)


def demo_llm_integration():

    print("\n" + "=" * 70)
    print("LLM Integration Example")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    tools = toolkit.export_tools(format="openai")

    print("\nSimulating integration with OpenAI GPT:")
    print("-" * 70)

    conversation = [{
        "role":
        "user",
        "content":
        "Help me create an electronic music track with drums, bass, and a synthesizer"
    }, {
        "role":
        "assistant",
        "content":
        "I will help you create an electronic music track. Let's get started...",
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

    print("\nLLM suggested actions:")
    for msg in conversation:
        if msg["role"] == "user":
            print(f"\nUser: {msg['content']}")
        elif msg["role"] == "assistant":
            print(f"\nAssistant: {msg['content']}")

            if "tool_calls" in msg:
                print("\nExecuting tool calls:")
                for call in msg["tool_calls"]:
                    func_name = call["function"]
                    args = call["arguments"]

                    # Execute tool
                    result = toolkit.execute(func_name, **args)

                    status_icon = "✓" if result.status == "success" else "✗"
                    print(f"  {status_icon} {func_name}({args})")
                    print(f"     → {result.message}")

    print("\n" + "-" * 70)
    print("✓ LLM integration example complete")


def demo_anthropic_integration():

    print("\n" + "=" * 70)
    print("Anthropic Claude Integration Example")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    tools = toolkit.export_tools(format="anthropic")

    print("\nSimulating integration with Claude:")
    print("-" * 70)

    print("\nUser request: 'Create a jazz-style project'")

    print("\nClaude analyzes and calls tools:")

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
            "track_id": "track 1",
            "name": "Track 1"
        }),
        ("node.create_instrument_track", {
            "project_id": "project 1",
            "track_id": "track 2",
            "name": "Track 2"
        }),
        ("node.create_instrument_track", {
            "project_id": "project 1",
            "track_id": "track 3",
            "name": "Track 3"
        }),
    ]

    for tool_name, args in tool_sequence:
        result = toolkit.execute(tool_name, **args)
        status = "✓" if result.status == "success" else "✗"
        print(f"  {status} {tool_name}: {result.message}")

    print(
        "\nClaude: I have created a jazz project with piano, bass, and drums,")
    print("        and added a classic jazz chord progression (Dm-G-C-Am).")

    print("\n" + "-" * 70)


def scenario_1_beginner_tutorial():
    """Scenario 1: Beginner Tutorial"""
    print("\n" + "=" * 70)
    print("Application Scenario 1: Beginner Tutorial Assistant")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    print("\nScenario: A user wants to learn how to create their first song")
    print("\nAgent Tutorial:")

    steps = [
        {
            "instruction":
            "Step 1: Let's create a new project",
            "action": ("project.create_project", {
                "name": "Performance Test",
                "project_id": "project 1"
            }),
            "explanation":
            "A project is a container for all your musical content"
        },
        {
            "instruction":
            "Step 2: Set the tempo to 120 BPM (good for pop music)",
            "action": ("transport.set_tempo", {
                "project_id": "project 1",
                "beat": 0,
                "bpm": 140.0
            }),
            "explanation":
            "BPM determines how fast or slow the music is"
        },
        {
            "instruction":
            "Step 3: Create a drum track",
            "action": ("node.create_instrument_track", {
                "project_id": "project 1",
                "track_id": "track 1",
                "name": "Drums"
            }),
            "explanation":
            "Drums provide the rhythmic foundation"
        },
        {
            "instruction":
            "Step 4: Add a basic drum clip",
            "action": ("editing.create_midi_clip", {
                "project_id": "project 1",
                "track_id": "track 1",
                "start_beat": 0,
                "duration_beats": 4.0,
                "name": "Bass Midi Clip",
                "clip_id": "clip 1",
            }),
            "explanation":
            "This is a simple 4-bar drum beat"
        },
        {
            "instruction":
            "Step 4: Add a basic drum pattern",
            "action": ("editing.add_notes_to_clip", {
                "project_id":
                "project 1",
                "track_id":
                "track 1",
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
            "This is a simple 4-bar drum pattern"
        },
    ]

    for i, step in enumerate(steps, 1):
        print(f"\n{step['instruction']}")

        tool_name, args = step["action"]
        result = toolkit.execute(tool_name, **args)

        print(f"  → {result.message}")
        print(f"  💡 Tip: {step['explanation']}")

    print(
        "\n✓ Tutorial complete! You have created the foundation of your first song."
    )


def scenario_2_professional_workflow():
    """Scenario 2: Professional Production Workflow"""
    print("\n" + "=" * 70)
    print("Application Scenario 2: Professional Music Production Workflow")
    print("=" * 70)

    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)

    print("\nScenario: Quickly create a full pop song arrangement")

    print("\nPhase 1: Project Setup")
    toolkit.execute("project_create_project", name="Pop Hit Production")
    toolkit.execute("transport_set_tempo", bpm=128.0)
    print("  ✓ Project initialization complete")

    print("\nPhase 2: Create Track Structure")
    tracks = ["Kick", "Snare", "Hi-Hat", "Bass", "Lead Synth", "Pad", "Vocals"]
    for track_name in tracks:
        toolkit.execute("node_create_instrument_track", name=track_name)
    print(f"  ✓ Created {len(tracks)} tracks")

    print("\nPhase 3: Add Musical Content")

    # Drum Section
    toolkit.execute("composition_create_drum_pattern",
                    track_name="Kick",
                    pattern="basic",
                    bars=8)
    toolkit.execute("composition_create_drum_pattern",
                    track_name="Hi-Hat",
                    pattern="electronic",
                    bars=8)
    print("  ✓ Added drum patterns")

    # Harmony Section
    toolkit.execute("composition_create_chord_progression",
                    track_name="Pad",
                    progression="C-G-Am-F",
                    tempo=128.0)
    toolkit.execute("composition_create_chord_progression",
                    track_name="Lead Synth",
                    progression="C-G-Am-F",
                    tempo=128.0)
    print("  ✓ Added chord progressions")

    # Bassline
    toolkit.execute("composition_create_bass_line",
                    track_name="Bass",
                    progression="C-G-Am-F",
                    style="octave")
    print("  ✓ Added bassline")

    print("\nPhase 4: Mix Adjustments")
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

    print("\n✓ Professional arrangement workflow complete!")
    print("  - 7 tracks in total")
    print("  - Includes drums, bass, harmony, and lead melody")
    print("  - Basic mix adjustments have been made")


# ============================================================================
# 11. Advanced Feature Demonstration
# ============================================================================


def demo_advanced_tool_features(toolkit: AgentToolkit):
    """Demonstrate advanced tool features"""
    print("\n" + "=" * 70)
    print("Advanced Features: Tool Feature Demonstration")
    print("=" * 70)

    # 1. Tool Search
    print("\n1. Tool Search:")
    print("   Searching for all composition-related tools...")
    composition_tools = toolkit.list_tools(category="composition")
    print(f"   Found {len(composition_tools)} composition tools:")
    for tool in composition_tools:
        print(f"     - {tool.name}: {tool.description}")

    # 2. Get detailed information for a specific tool
    print("\n2. Tool Details:")
    tool = toolkit.get_tool("composition_create_chord_progression")
    if tool:
        print(f"   Tool: {tool.name}")
        print(f"   Description: {tool.description}")
        print(f"   Parameters:")
        for param in tool.parameters:
            req = "Required" if param.required else "Optional"
            print(
                f"     - {param.name} ({param.type}, {req}): {param.description}"
            )

    # 3. Get tool documentation
    print("\n3. Single Tool Documentation:")
    doc = toolkit.get_documentation("composition_create_drum_pattern")
    print(doc)


# ============================================================================
# 12. Performance and Monitoring
# ============================================================================


def demo_performance_monitoring(toolkit: AgentToolkit):
    """Demonstrate performance monitoring"""
    print("\n" + "=" * 70)
    print("Performance Monitoring Demonstration")
    print("=" * 70)

    import time

    # Clear log
    toolkit.clear_log()

    print("\nExecuting a series of operations and monitoring performance...")

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
            "track_id": "track 1",
            "name": "Track 1"
        }),
        ("node_create_instrument_track", {
            "project_id": "project 1",
            "track_id": "track 2",
            "name": "Track 2"
        }),
        ("node_create_instrument_track", {
            "project_id": "project 1",
            "track_id": "track 3",
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

    print(f"\nPerformance Statistics:")
    print(f"  Total operations: {len(operations)}")
    print(f"  Total time: {total_time*1000:.2f}ms")
    print(
        f"  Average time per operation: {total_time*1000/len(operations):.2f}ms"
    )

    # Display execution log
    log = toolkit.get_execution_log()
    print(f"  Number of log records: {len(log)}")


# ============================================================================
# Main Program
# ============================================================================


def main():
    """Main program"""
    import sys

    print("\n" + "=" * 70)
    print("MuzaiCore Agent System - Demonstration Program")
    print("=" * 70)

    print("\nAvailable Demos:")
    print("  1. Run all demos")
    print("  2. Simple project creation")
    print("  3. Create song structure")
    print("  4. Chain execution")
    print("  5. Export tool definitions")
    print("  6. LLM integration example")
    print("  7. Beginner tutorial scenario")
    print("  8. Professional production scenario")
    print("  9. Advanced features demonstration")
    print("  10. Performance monitoring")

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nPlease choose (1-10): ").strip()

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
        facade, manager = initialize_daw_system()
        toolkit = create_agent_toolkit(facade)
        demo_3_agent_chain_execution(toolkit)
    elif choice == "5":
        facade, manager = initialize_daw_system()
        toolkit = create_agent_toolkit(facade)
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
        facade, manager = initialize_daw_system()
        toolkit = create_agent_toolkit(facade)
        demo_performance_monitoring(toolkit)
    else:
        print("Invalid choice")
        return

    print("\n" + "=" * 70)
    print("Demonstration complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
