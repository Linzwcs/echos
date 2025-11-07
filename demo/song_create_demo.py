import sys
from pathlib import Path
import json
import time

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
from echos.models import ToolResponse, MIDIClip, Note
import mido
from typing import Set, Tuple, Dict


def create_agent_toolkit(facade: DAWFacade):

    print("\n" + "=" * 70)
    print("Creating Agent toolkit...")
    print("=" * 70)

    toolkit = AgentToolkit(facade)

    tools = toolkit.list_tools()

    print(f"\n✓ Toolkit created successfully")
    print(f"  - Total tools: {len(tools)}")

    categories = {}
    for tool in tools:
        if tool.category not in categories:
            categories[tool.category] = []
        categories[tool.category].append(tool.name)

    print(f"\nTool Categories:")
    for category, tool_names in sorted(categories.items()):
        print(f"  {category}: {len(tool_names)} tools")
        for name in tool_names[:3]:  # Display the first 3
            print(f"    - {name}")
        if len(tool_names) > 3:
            print(f"    ... and {len(tool_names) - 3} more")

    return toolkit


def load_midi_to_clip(file_path: str) -> MIDIClip:

    try:
        mid = mido.MidiFile(file_path)
    except FileNotFoundError:
        print(f"Error: File not found at path {file_path}")
        return None
    except Exception as e:
        print(f"Error loading MIDI file: {e}")
        return None

    ticks_per_beat = mid.ticks_per_beat
    notes: Set[Note] = set()

    open_notes: Dict[Tuple[int, int], Tuple[int, int]] = {}

    absolute_time_ticks = 0.0
    max_end_beat = 0.0

    for i, track in enumerate(mid.tracks):
        absolute_time_ticks = 0

        for msg in track:
            absolute_time_ticks += msg.time

            if msg.type == 'note_on' and msg.velocity > 0:

                key = (i, msg.note)
                open_notes[key] = (absolute_time_ticks, msg.velocity)

            elif msg.type == 'note_off' or (msg.type == 'note_on'
                                            and msg.velocity == 0):

                key = (i, msg.note)
                if key in open_notes:
                    start_tick, velocity = open_notes.pop(key)

                    start_beat = start_tick / ticks_per_beat
                    duration_ticks = absolute_time_ticks - start_tick
                    duration_beats = duration_ticks / ticks_per_beat

                    new_note = Note(pitch=msg.note,
                                    velocity=velocity,
                                    start_beat=start_beat,
                                    duration_beats=duration_beats)
                    notes.add(new_note)

                    current_end_beat = start_beat + duration_beats
                    if current_end_beat > max_end_beat:
                        max_end_beat = current_end_beat

    midi_clip = MIDIClip(start_beat=0.0,
                         duration_beats=max_end_beat,
                         name=file_path.split('/')[-1].split('\\')[-1],
                         notes=notes)

    return midi_clip


class MusicCompositionService:

    def __init__(self, facade: DAWFacade):
        self._facade = facade

        self.midi_clip = load_midi_to_clip(
            "./midi/Sacred Play Secret Place.mid")

    @tool(category="composition",
          description="Create a song",
          returns="Created MIDI clips with chord progression")
    def create_song(self) -> ToolResponse:

        return ToolResponse("success",
                            data={
                                "notes": self.midi_clip.notes,
                                "start_beat": 0,
                                "duration_beats": self.midi_clip.duration_beats
                            },
                            message="create song")


def initialize_daw_system():

    print("\n" + "=" * 70)
    print("Initializing DAW system...")
    print("=" * 70)

    plugin_cache = PluginCache()
    plugin_registry = PedalboardPluginRegistry(plugin_cache)
    engine_factory = PedalboardEngineFactory()
    node_factory = PedalboardNodeFactory()
    serializer = ProjectSerializer(node_factory, plugin_registry)
    plugin_registry.load()

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

    composition_service = MusicCompositionService(facade)
    facade._services["composition"] = composition_service
    print("✓ DAW system initialized successfully")

    return facade, manager


def song_create_demo(toolkit: AgentToolkit, facade: DAWFacade):

    print("\n" + "=" * 70)
    print("Demo 3: Agent chain execution for a complex task")
    print("=" * 70)
    print(
        "\nUser: 'Create an electronic music project with a full arrangement'")
    plugins = facade.list_plugins()
    instrument = None
    for p in plugins:
        if p.is_instrument:
            instrument = p
            break
    chain = [
        {
            "tool": "project.create_project",
            "params": {
                "name": "Electronic Music",
                "project_id": "test project",
                "output_channels": 2,
            },
        },
        {
            "tool": "transport.set_tempo",
            "params": {
                "project_id": "$result[0].data.project_id",
                "beat": 0,
                "bpm": 60.0,
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
            "tool": "node.add_insert_plugin",
            "params": {
                "project_id": "$result[0].data.project_id",
                "target_node_id": "$result[2].data.node_id",
                "plugin_unique_id": instrument.unique_plugin_id,
                "index": 0
            },
        },
        {
            "tool": "composition.create_song",
            "params": {},
        },
        {
            "tool": "editing.create_midi_clip",
            "params": {
                "project_id": "$result[0].data.project_id",
                "track_id": "$result[2].data.node_id",
                "start_beat": "$result[4].data.start_beat",
                "duration_beats": "$result[4].data.duration_beats",
                "name": "piano",
                "clip_id": "clip 1",
            },
        },
        {
            "tool": "editing.add_notes_to_clip",
            "params": {
                "project_id": "$result[0].data.project_id",
                "track_id": "$result[2].data.node_id",
                "clip_id": "clip 1",
                "notes": "$result[4].data.notes",
            },
        },
    ]

    print(f"\nAgent Execution Chain ({len(chain)} steps):")

    results = toolkit.execute_chain(chain)

    toolkit.execute("transport.play", **{"project_id": "test project"})

    time.sleep(200)

    toolkit.execute("transport.stop", **{"project_id": "test project"})
    for i, result in enumerate(results, 1):
        status_icon = "✓" if result.status == "success" else "✗"
        print(f"  {status_icon} Step {i}: {result.message}")

        if result.status == "error":
            print(f"    Error: {result.message}")
            break

    if all(r.status == "success" for r in results):
        print("\n✓ All steps executed successfully!")
    else:
        print("\n✗ Execution chain was interrupted")

    return results


if __name__ == "__main__":
    facade, manager = initialize_daw_system()
    toolkit = create_agent_toolkit(facade)
    song_create_demo(toolkit, facade)
