import sys
from pathlib import Path
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
from echos.models import Note, MIDIClip, Tempo
from echos.facade import DAWFacade
from echos.services import *


def quick_start_guide():

    print("\n" + "=" * 70)
    print("MuzaiCore DAW - 5 Minute Quick Start")
    print("=" * 70)

    print("\nStep 1: Initializing the system...")
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
    print("✓ System initialization complete")

    print("\nStep 2: Creating a project...")
    project = manager.create_project("My First Project")
    print(f"✓ Project created: {project.name}")

    print("\nStep 4: Creating a track...")
    piano = node_factory.create_instrument_track("Piano")
    project.router.add_node(piano)

    print(f"✓ Track created: {piano.name}")

    print("\nStep 5: Creating a MIDI clip...")
    clip = MIDIClip(start_beat=0.0, duration_beats=4.0, name="Melody")

    clip.notes.add(
        Note(pitch=60, velocity=100, start_beat=0.0, duration_beats=1.0))
    clip.notes.add(
        Note(pitch=62, velocity=100, start_beat=1.0, duration_beats=1.0))
    clip.notes.add(
        Note(pitch=64, velocity=100, start_beat=2.0, duration_beats=1.0))
    clip.notes.add(
        Note(pitch=65, velocity=100, start_beat=3.0, duration_beats=1.0))

    piano.add_clip(clip)
    print(f"✓ Clip created: {clip.name} (contains {len(clip.notes)} notes)")

    print("\nStep 6: Setting the tempo...")
    project.timeline.add_tempo(0, 120.0)
    print(f"✓ Tempo set to: {project.timeline.timeline_state.tempos}")

    print("\n" + "=" * 70)
    print("✓ Quick start complete! You have created a basic DAW project")
    print("=" * 70)

    return manager, project


# ============================================================================
# Integration Test: Verify all components work together
# ============================================================================


class IntegrationTest:
    """Complete integration test"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def setup(self):
        """Set up the test environment"""
        print("\n" + "=" * 70)
        print("Integration Test: Setting up the test environment")
        print("=" * 70)

        try:
            self.plugin_cache = PluginCache()
            self.plugin_registry = PedalboardPluginRegistry(self.plugin_cache)
            self.engine_factory = PedalboardEngineFactory()
            self.node_factory = PedalboardNodeFactory()
            self.serializer = ProjectSerializer(self.node_factory,
                                                self.plugin_registry)

            self.manager = DAWManager(
                self.serializer,
                self.plugin_registry,
                self.engine_factory,
                self.node_factory,
            )

            print("✓ Test environment setup complete")
            return True
        except Exception as e:
            print(f"✗ Setup failed: {e}")
            return False

    def test_project_lifecycle(self):

        print("\nTest 1: Project Lifecycle")

        try:

            project = self.manager.create_project("Test Project")
            assert project is not None
            assert project.name == "Test Project"
            print("  ✓ Project created successfully")

            retrieved = self.manager.get_project(project.project_id)
            assert retrieved is project
            print("  ✓ Project retrieved successfully")

            result = self.manager.close_project(project.project_id)
            assert result is True
            print("  ✓ Project closed successfully")

            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"Project lifecycle test failed: {e}")
            print(f"  ✗ Test failed: {e}")
            return False

    def test_track_creation(self):

        print("\nTest 2: Track Creation")

        try:
            project = self.manager.create_project("Track Test")

            # Create different types of tracks
            inst_track = self.node_factory.create_instrument_track(
                "Instrument")
            audio_track = self.node_factory.create_audio_track("Audio")
            bus_track = self.node_factory.create_bus_track("Bus")

            project.router.add_node(inst_track)
            project.router.add_node(audio_track)
            project.router.add_node(bus_track)

            assert len(project.router.nodes) == 3
            print("  ✓ All track types created successfully")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"Track creation test failed: {e}")
            print(f"  ✗ Test failed: {e}")
            return False

    def test_mixer_operations(self):

        print("\nTest 3: Mixer Operations")

        try:
            project = self.manager.create_project("Mixer Test")
            track = self.node_factory.create_audio_track("Test Track")
            project.router.add_node(track)

            mixer = track.mixer_channel

            # Test volume
            mixer.volume.set_value(-6.0)
            assert mixer.volume.value == -6.0
            print("  ✓ Volume adjustment successful")

            # Test pan
            mixer.pan.set_value(0.5)
            assert mixer.pan.value == 0.5
            print("  ✓ Pan adjustment successful")

            # Test mute
            mixer.is_muted = True
            assert mixer.is_muted is True
            print("  ✓ Mute function is working correctly")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"Mixer operations test failed: {e}")
            print(f"  ✗ Test failed: {e}")
            return False

    def test_midi_clips(self):
        """Test 4: MIDI Clips"""
        print("\nTest 4: MIDI Clips")

        try:
            project = self.manager.create_project("MIDI Test")
            track = self.node_factory.create_instrument_track("Piano")
            project.router.add_node(track)

            # Create clip
            clip = MIDIClip(start_beat=0.0, duration_beats=4.0)
            track.add_clip(clip)

            assert len(track.clips) == 1
            print("  ✓ Clip created successfully")

            # Add note
            note = Note(pitch=60,
                        velocity=100,
                        start_beat=0.0,
                        duration_beats=1.0)
            clip.notes.add(note)

            assert len(clip.notes) == 1
            print("  ✓ Note added successfully")

            # Delete clip
            result = track.remove_clip(clip.clip_id)
            assert result is True
            assert len(track.clips) == 0
            print("  ✓ Clip deleted successfully")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"MIDI clips test failed: {e}")
            print(f"  ✗ Test failed: {e}")
            return False

    def test_transport_control(self):

        print("\nTest 5: Transport Control")

        try:
            project = self.manager.create_project("Transport Test",
                                                  output_channels=2)

            # Test play/stop

            project.engine_controller.play()

            print(project.engine_controller.is_playing)
            assert project.engine_controller.is_playing is True
            print("  ✓ Play function is working correctly")

            project.engine_controller.stop()

            assert project.engine_controller.is_playing is False
            print("  ✓ Stop function is working correctly")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"Transport control test failed: {e}")
            print(f"  ✗ Test failed: {e}")
            return False

    def test_command_history(self):
        """Test 6: Command History"""
        print("\nTest 6: Command History")

        try:
            from echos.core.history.commands.transport_command import SetTempoCommand

            project = self.manager.create_project("History Test")

            cmd = SetTempoCommand(project.timeline, 0, 140.0)
            project.command_manager.execute_command(cmd)
            assert project.timeline.tempos == [Tempo(beat=0, bpm=140.0)]
            print("  ✓ Command executed successfully")

            project.command_manager.undo()
            assert project.timeline.tempos == [Tempo(beat=0, bpm=120.0)]
            print("  ✓ Undo function is working correctly")

            # Redo
            project.command_manager.redo()
            assert project.timeline.tempos == [Tempo(beat=0, bpm=140.0)]
            print("  ✓ Redo function is working correctly")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"Command history test failed: {e}")
            print(f"  ✗ Test failed: {e}")
            return False

    def test_event_system(self):

        print("\nTest 7: Event System")

        try:
            from echos.models.event_model import NodeAdded
            from echos.core import EventBus

            event_bus = EventBus()
            events_received = []

            def handler(event):
                events_received.append(event)

            event_bus.subscribe(NodeAdded, handler)

            event = NodeAdded(node_id="test", node_type="Track")
            event_bus.publish(event)

            assert len(events_received) == 1
            print("  ✓ Event publish/subscribe is working correctly")

            event_bus.clear()
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"Event system test failed: {e}")
            print(f"  ✗ Test failed: {e}")
            return False

    def test_facade_interface(self):

        print("\nTest 8: Facade Interface")

        try:
            # Create services
            services = {
                "project": ProjectService(self.manager),
                "node": NodeService(self.manager),
                "transport": TransportService(self.manager),
                "editing": EditingService(self.manager),
                "history": HistoryService(self.manager),
                "query": QueryService(self.manager),
                "system": SystemService(self.manager),
                "routing": RoutingService(self.manager),
            }

            facade = DAWFacade(self.manager, services)

            result = facade.project.create_project("Facade Test")
            assert result.status == "success"
            print("  ✓ Facade project created successfully")

            project_id = result.data["project_id"]
            result = facade.set_active_project(project_id)
            assert result.status == "success"
            print("  ✓ Facade active project set successfully")

            result = facade.execute_tool(
                "node.create_instrument_track",
                project_id=project_id,
                name="Piano",
            )

            assert result.status == "success"
            print("  ✓ Facade track created successfully")

            self.manager.close_project(project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"Facade interface test failed: {e}")
            print(f"  ✗ Test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 70)
        print("Starting Integration Tests")
        print("=" * 70)

        if not self.setup():
            print("\n✗ Test environment setup failed, aborting tests")
            return False

        # Run all tests
        tests = [
            self.test_project_lifecycle,
            self.test_track_creation,
            self.test_mixer_operations,
            self.test_midi_clips,
            self.test_transport_control,
            self.test_command_history,
            self.test_event_system,
            self.test_facade_interface,
        ]

        for test in tests:
            test()

        # Show results
        self.show_results()

        return self.failed == 0

    def show_results(self):
        """Show test results"""
        print("\n" + "=" * 70)
        print("Integration Test Results")
        print("=" * 70)

        total = self.passed + self.failed
        print(f"\nTotal tests: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")

        if self.failed > 0:
            print(f"\nFailed tests:")
            for error in self.errors:
                print(f"  - {error}")

        if self.failed == 0:
            print("\n✓ All tests passed!")
        else:
            print(f"\n✗ {self.failed} tests failed")

        print("=" * 70)


# ============================================================================
# Main program
# ============================================================================


def main():
    """Main program"""
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            # Run quick start
            quick_start_guide()
        elif sys.argv[1] == "test":
            # Run integration tests
            tester = IntegrationTest()
            success = tester.run_all_tests()
            sys.exit(0 if success else 1)
        else:
            print("Usage:")
            print("  python quick_start.py quick  - Run the quick start guide")
            print("  python quick_start.py test   - Run the integration tests")
    else:
        # Default to running quick start
        print("\nSelect a mode to run:")
        print("1. Quick Start Guide")
        print("2. Integration Tests")

        choice = input("\nPlease choose (1 or 2): ").strip()

        if choice == "1":
            quick_start_guide()
        elif choice == "2":
            tester = IntegrationTest()
            tester.run_all_tests()
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
