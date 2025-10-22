# file: src/MuzaiCore/main.py
import os
import sys
import time

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from MuzaiCore.interfaces import IDAWManager, IPluginRegistry
from MuzaiCore.implementations.mock.manager import MockDAWManager
from MuzaiCore.implementations.mock.plugin_registry import MockPluginRegistry
from MuzaiCore.services import DAWFacade
from MuzaiCore.models.engine_model import MIDIEvent  # For demo


def main():
    print("--- MuzaiCore System Bootstrap ---")

    # 1. Setup Manager and Registry
    manager: IDAWManager = MockDAWManager()
    registry: IPluginRegistry = MockPluginRegistry()
    registry.scan_for_plugins()  # Discover our virtual plugins

    # 2. Setup Facade
    daw_api = DAWFacade(manager, registry)

    print("\n--- [DEMO] Agent Interaction Example ---")

    # 3. Create Project
    response = daw_api.project.create_project(name="Agent's Mock Song")
    project_id = response.data['project_id']
    print(f"Project created with ID: {project_id}")

    # 4. Create an Instrument Track using the API
    track_resp = daw_api.nodes.create_instrument_track(project_id,
                                                       name="Synth Lead")
    track_id = track_resp.data['node_id']
    print(f"Created track '{track_resp.data['name']}' with ID {track_id}")

    # 5. Add an Instrument Plugin to the Track
    plugin_resp1 = daw_api.nodes.add_plugin_to_node(
        project_id,
        target_node_id=track_id,
        plugin_unique_id="muzaicore.mock.basic_synth")
    print(plugin_resp1.message)

    # 6. Add an Effect Plugin after the Instrument
    plugin_resp2 = daw_api.nodes.add_plugin_to_node(
        project_id,
        target_node_id=track_id,
        plugin_unique_id="muzaicore.mock.simple_reverb")
    print(plugin_resp2.message)

    # 7. Manually add the track to the router for processing (TEMPORARY)
    project = manager.get_project(project_id)
    track_node = project.get_node_by_id(track_id)
    # This part of the routing will be improved later. For now, we need a node in the graph.
    project.router._graph.add_node(track_node.node_id)

    # 8. Start Playback and simulate some MIDI
    print("\n--- Starting Playback for 2 seconds with simulated MIDI ---")
    daw_api.transport.play(project_id)

    # HACK: Manually inject a MIDI event into the engine's processing for demo
    # In a real system, this would come from a MIDI clip on the timeline.
    track_node.process_block(None, [MIDIEvent(60, 100, 0)],
                             project.engine._project.timeline)

    try:
        time.sleep(2)
    finally:
        # 9. Stop Playback
        print("\n--- Stopping Playback ---")
        daw_api.transport.stop(project_id)

    print("\n--- System Demo Finished ---")


if __name__ == "__main__":
    main()
