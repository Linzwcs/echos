import pytest
import numpy as np
from pathlib import Path
import time

from echos.core import (
    DAWManager,
    Project,
    EventBus,
    CommandManager,
    Timeline,
    InstrumentTrack,
    AudioTrack,
    BusTrack,
    Parameter,
)
from echos.backends.pedalboard import (
    PedalboardEngine,
    PedalboardEngineFactory,
    PedalboardNodeFactory,
    PedalboardPluginRegistry,
)
from echos.core.plugin import PluginCache
from echos.core.persistence import ProjectSerializer
from echos.models import (Note, MIDIClip, TransportStatus, Tempo,
                          TimeSignature, TimelineState)
from echos.facade import DAWFacade
from echos.services import (
    ProjectService,
    NodeService,
    TransportService,
    EditingService,
    HistoryService,
    QueryService,
    SystemService,
    RoutingService,
)


class TestProjectLifecycle:

    def setup_method(self):

        self.plugin_cache = PluginCache()
        self.plugin_registry = PedalboardPluginRegistry(self.plugin_cache)
        self.engine_factory = PedalboardEngineFactory()
        self.node_factory = PedalboardNodeFactory()
        self.serializer = ProjectSerializer(self.node_factory,
                                            self.plugin_registry)

        self.manager = DAWManager(
            project_serializer=self.serializer,
            plugin_registry=self.plugin_registry,
            engine_factory=self.engine_factory,
            node_factory=self.node_factory,
        )

    def test_create_project(self):

        project = self.manager.create_project("Test Project")

        assert project is not None
        assert project.name == "Test Project"
        assert project.timeline.timeline_state == TimelineState(
            tempos=[Tempo(beat=0.0, bpm=120)],
            time_signatures=[
                TimeSignature(beat=0, numerator=4, denominator=4)
            ])

    def test_project_initialization(self):

        project = self.manager.create_project("Init Test")

        assert project.is_mounted
        assert project.router.is_mounted
        assert project.timeline.is_mounted

    def test_attach_engine(self):

        project = self.manager.create_project("Engine Test")

        assert project._audio_engine is not None
        assert project._audio_engine.is_mounted

    def test_close_project(self):

        project = self.manager.create_project("Close Test")
        project_id = project.project_id
        result = self.manager.close_project(project_id)

        assert result is True
        assert self.manager.get_project(project_id) is None


class TestTrackManagement:

    def setup_method(self):
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
        self.project = self.manager.create_project("Track Test")

    def test_create_instrument_track(self):

        track = self.node_factory.create_instrument_track("Piano")
        self.project.router.add_node(track)
        self.project: Project
        self.project._audio_engine.refresh()

        assert track.name == "Piano"
        assert track.node_type == "InstrumentTrack"
        assert track in list(self.project.router.nodes.values())
        assert track.node_id in self.project._audio_engine._render_graph._nodes

    def test_create_audio_track(self):

        track = self.node_factory.create_audio_track("Vocals")
        self.project.router.add_node(track)

        assert track.name == "Vocals"
        assert track.node_type == "AudioTrack"

    def test_create_bus_track(self):

        bus = self.node_factory.create_bus_track("Reverb Bus")
        self.project.router.add_node(bus)

        assert bus.name == "Reverb Bus"
        assert bus.node_type == "BusTrack"

    def test_rename_track(self):

        track = self.node_factory.create_audio_track("Original")
        self.project.router.add_node(track)
        track.set_name("Renamed")
        assert track.name == "Renamed"

    def test_remove_track(self):

        track = self.node_factory.create_audio_track("To Delete")
        self.project.router.add_node(track)
        node_id = track.node_id
        self.project._audio_engine.refresh()
        assert track.node_id in self.project._audio_engine._render_graph._nodes
        self.project.router.remove_node(node_id)
        self.project._audio_engine.refresh()
        assert self.project.router.get_node_by_id(node_id) is None
        assert track.node_id not in self.project._audio_engine._render_graph._nodes


class TestMixerOperations:

    def setup_method(self):
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
        self.project = self.manager.create_project("Mixer Test")
        self.track = self.node_factory.create_audio_track("Test Track")
        self.project.router.add_node(self.track)

    def test_adjust_volume(self):

        mixer = self.track.mixer_channel

        mixer.volume.set_value(-6.0)

        assert mixer.volume.value == -6.0

    def test_adjust_pan(self):

        mixer = self.track.mixer_channel

        mixer.pan.set_value(0.5)

        assert mixer.pan.value == 0.5

    def test_mute_track(self):

        mixer = self.track.mixer_channel

        mixer.is_muted = True

        assert mixer.is_muted is True

    def test_solo_track(self):

        mixer = self.track.mixer_channel

        mixer.is_solo = True

        assert mixer.is_solo is True


class TestClipOperations:

    def setup_method(self):
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
        self.project = self.manager.create_project("Clip Test")
        self.track = self.node_factory.create_instrument_track("MIDI Track")
        self.project.router.add_node(self.track)

    def test_create_midi_clip(self):

        clip = MIDIClip(start_beat=0.0, duration_beats=4.0, name="Test Clip")
        self.track.add_clip(clip)

        assert len(self.track.clips) == 1
        assert clip in self.track.clips

    def test_add_notes_to_clip(self):

        clip = MIDIClip(start_beat=0.0, duration_beats=4.0)

        note1 = Note(pitch=60,
                     velocity=100,
                     start_beat=0.0,
                     duration_beats=1.0)
        note2 = Note(pitch=64,
                     velocity=100,
                     start_beat=1.0,
                     duration_beats=1.0)

        clip.notes.add(note1)
        clip.notes.add(note2)

        assert len(clip.notes) == 2

    def test_remove_clip(self):

        clip = MIDIClip(start_beat=0.0, duration_beats=4.0)
        self.track.add_clip(clip)
        clip_id = clip.clip_id

        result = self.track.remove_clip(clip_id)

        assert result is True
        assert len(self.track.clips) == 0


class TestTransportControl:

    def setup_method(self):
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
        self.project = self.manager.create_project("Transport Test")

    def test_play_stop(self):

        self.project._audio_engine.play()
        assert self.project._audio_engine.is_playing is True

        self.project._audio_engine.stop()
        assert self.project._audio_engine.is_playing is False


class TestCommandHistory:

    def setup_method(self):
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
        self.project = self.manager.create_project("History Test")

    def test_undo_redo(self):
        from echos.core.history.commands.transport_command import SetTempoCommand

        cmd = SetTempoCommand(self.project.timeline, 0, 140.0)
        self.project.command_manager.execute_command(cmd)

        assert self.project.timeline.tempos == [Tempo(beat=0, bpm=140.0)]
        self.project._audio_engine.refresh()
        assert self.project._audio_engine.timeline.tempos == [
            Tempo(beat=0, bpm=140.0)
        ]

        self.project.command_manager.undo()
        assert self.project.timeline.tempos == [Tempo(beat=0, bpm=120.0)]
        self.project._audio_engine.refresh()
        assert self.project._audio_engine.timeline.tempos == [
            Tempo(beat=0, bpm=120.0)
        ]

        self.project.command_manager.redo()
        self.project._audio_engine.refresh()
        assert self.project.timeline.tempos == [Tempo(beat=0, bpm=140.0)]
        assert self.project._audio_engine.timeline.tempos == [
            Tempo(beat=0, bpm=140.0)
        ]


class TestEventSystem:

    def test_event_subscription(self):

        event_bus = EventBus()
        events_received = []

        def handler(event):
            events_received.append(event)

        from echos.models.event_model import NodeAdded
        event_bus.subscribe(NodeAdded, handler)

        # 发布事件
        event = NodeAdded(node_id="test", node_type="Track")
        event_bus.publish(event)

        assert len(events_received) == 1
        assert events_received[0] == event


class TestTimeline:

    def test_beats_to_seconds(self):

        timeline = Timeline(tempo=120.0)

        seconds = timeline.beats_to_seconds(4.0)

        assert abs(seconds - 2.0) < 0.001

    def test_seconds_to_beats(self):

        timeline = Timeline(tempo=120.0)

        beats = timeline.seconds_to_beats(2.0)

        assert abs(beats - 4.0) < 0.001

    def test_tempo_changes(self):

        timeline = Timeline()

        timeline.add_tempo(0.0, 120.0)
        timeline.add_time_signature(0, 4.0, 140.0)
        print(timeline.timeline_state)

        assert timeline.get_tempo_at_beat(2.0) == Tempo(0, 120.0)
        assert timeline.get_time_signature_at_beat(5.0) == TimeSignature(
            0, 4, 140)


class TestRouting:

    def setup_method(self):
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
        self.project = self.manager.create_project("Routing Test")

    def test_add_nodes_to_router(self):

        track1 = self.node_factory.create_audio_track("Track 1")
        track2 = self.node_factory.create_audio_track("Track 2")

        self.project.router.add_node(track1)
        self.project.router.add_node(track2)

        assert len(self.project.router.nodes) == 2


# 运行所有测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
