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
    print("MuzaiCore DAW - 5分钟快速入门")
    print("=" * 70)

    print("\n步骤1: 初始化系统...")
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
    print("✓ 系统初始化完成")

    print("\n步骤2: 创建项目...")
    project = manager.create_project("我的第一个项目")
    print(f"✓ 项目创建: {project.name}")

    print("\n步骤4: 创建轨道...")
    piano = node_factory.create_instrument_track("钢琴")
    project.router.add_node(piano)

    print(f"✓ 创建轨道: {piano.name}")

    print("\n步骤5: 创建MIDI片段...")
    clip = MIDIClip(start_beat=0.0, duration_beats=4.0, name="旋律")

    clip.notes.add(
        Note(pitch=60, velocity=100, start_beat=0.0, duration_beats=1.0))
    clip.notes.add(
        Note(pitch=62, velocity=100, start_beat=1.0, duration_beats=1.0))
    clip.notes.add(
        Note(pitch=64, velocity=100, start_beat=2.0, duration_beats=1.0))
    clip.notes.add(
        Note(pitch=65, velocity=100, start_beat=3.0, duration_beats=1.0))

    piano.add_clip(clip)
    print(f"✓ 创建片段: {clip.name} (包含 {len(clip.notes)} 个音符)")

    print("\n步骤6: 设置速度...")
    project.timeline.add_tempo(0, 120.0)
    print(f"✓ 速度设置为: {project.timeline.timeline_state.tempos}")

    print("\n" + "=" * 70)
    print("✓ 快速入门完成！你已经创建了一个基本的DAW项目")
    print("=" * 70)

    return manager, project


# ============================================================================
# 集成测试：验证所有组件协同工作
# ============================================================================


class IntegrationTest:
    """完整的集成测试"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def setup(self):
        """设置测试环境"""
        print("\n" + "=" * 70)
        print("集成测试：设置测试环境")
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

            print("✓ 测试环境设置完成")
            return True
        except Exception as e:
            print(f"✗ 设置失败: {e}")
            return False

    def test_project_lifecycle(self):

        print("\n测试1: 项目生命周期")

        try:

            project = self.manager.create_project("Test Project")
            assert project is not None
            assert project.name == "Test Project"
            print("  ✓ 项目创建成功")

            retrieved = self.manager.get_project(project.project_id)
            assert retrieved is project
            print("  ✓ 项目检索成功")

            result = self.manager.close_project(project.project_id)
            assert result is True
            print("  ✓ 项目关闭成功")

            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"项目生命周期测试失败: {e}")
            print(f"  ✗ 测试失败: {e}")
            return False

    def test_track_creation(self):

        print("\n测试2: 轨道创建")

        try:
            project = self.manager.create_project("Track Test")

            # 创建不同类型的轨道
            inst_track = self.node_factory.create_instrument_track(
                "Instrument")
            audio_track = self.node_factory.create_audio_track("Audio")
            bus_track = self.node_factory.create_bus_track("Bus")

            project.router.add_node(inst_track)
            project.router.add_node(audio_track)
            project.router.add_node(bus_track)

            assert len(project.router.nodes) == 3
            print("  ✓ 所有轨道类型创建成功")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"轨道创建测试失败: {e}")
            print(f"  ✗ 测试失败: {e}")
            return False

    def test_mixer_operations(self):

        print("\n测试3: 混音器操作")

        try:
            project = self.manager.create_project("Mixer Test")
            track = self.node_factory.create_audio_track("Test Track")
            project.router.add_node(track)

            mixer = track.mixer_channel

            # 测试音量
            mixer.volume.set_value(-6.0)
            assert mixer.volume.value == -6.0
            print("  ✓ 音量调整成功")

            # 测试声相
            mixer.pan.set_value(0.5)
            assert mixer.pan.value == 0.5
            print("  ✓ 声相调整成功")

            # 测试静音
            mixer.is_muted = True
            assert mixer.is_muted is True
            print("  ✓ 静音功能正常")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"混音器操作测试失败: {e}")
            print(f"  ✗ 测试失败: {e}")
            return False

    def test_midi_clips(self):
        """测试4: MIDI片段"""
        print("\n测试4: MIDI片段")

        try:
            project = self.manager.create_project("MIDI Test")
            track = self.node_factory.create_instrument_track("Piano")
            project.router.add_node(track)

            # 创建片段
            clip = MIDIClip(start_beat=0.0, duration_beats=4.0)
            track.add_clip(clip)

            assert len(track.clips) == 1
            print("  ✓ 片段创建成功")

            # 添加音符
            note = Note(pitch=60,
                        velocity=100,
                        start_beat=0.0,
                        duration_beats=1.0)
            clip.notes.add(note)

            assert len(clip.notes) == 1
            print("  ✓ 音符添加成功")

            # 删除片段
            result = track.remove_clip(clip.clip_id)
            assert result is True
            assert len(track.clips) == 0
            print("  ✓ 片段删除成功")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"MIDI片段测试失败: {e}")
            print(f"  ✗ 测试失败: {e}")
            return False

    def test_transport_control(self):

        print("\n测试5: 传输控制")

        try:
            project = self.manager.create_project("Transport Test",
                                                  output_channels=2)

            # 测试播放/停止

            project.engine_controller.play()

            print(project.engine_controller.is_playing)
            assert project.engine_controller.is_playing is True
            print("  ✓ 播放功能正常")

            project.engine_controller.stop()

            assert project.engine_controller.is_playing is False
            print("  ✓ 停止功能正常")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"传输控制测试失败: {e}")
            print(f"  ✗ 测试失败: {e}")
            return False

    def test_command_history(self):
        """测试6: 命令历史"""
        print("\n测试6: 命令历史")

        try:
            from echos.core.history.commands.transport_command import SetTempoCommand

            project = self.manager.create_project("History Test")

            cmd = SetTempoCommand(project.timeline, 0, 140.0)
            project.command_manager.execute_command(cmd)
            assert project.timeline.tempos == [Tempo(beat=0, bpm=140.0)]
            print("  ✓ 命令执行成功")

            project.command_manager.undo()
            assert project.timeline.tempos == [Tempo(beat=0, bpm=120.0)]
            print("  ✓ 撤销功能正常")

            # 重做
            project.command_manager.redo()
            assert project.timeline.tempos == [Tempo(beat=0, bpm=140.0)]
            print("  ✓ 重做功能正常")

            self.manager.close_project(project.project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"命令历史测试失败: {e}")
            print(f"  ✗ 测试失败: {e}")
            return False

    def test_event_system(self):

        print("\n测试7: 事件系统")

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
            print("  ✓ 事件发布/订阅正常")

            event_bus.clear()
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"事件系统测试失败: {e}")
            print(f"  ✗ 测试失败: {e}")
            return False

    def test_facade_interface(self):

        print("\n测试8: Facade接口")

        try:
            # 创建服务
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
            print("  ✓ Facade项目创建成功")

            project_id = result.data["project_id"]
            result = facade.set_active_project(project_id)
            assert result.status == "success"
            print("  ✓ Facade活动项目设置成功")

            result = facade.execute_tool(
                "node.create_instrument_track",
                project_id=project_id,
                name="Piano",
            )

            assert result.status == "success"
            print("  ✓ Facade轨道创建成功")

            self.manager.close_project(project_id)
            self.passed += 1
            return True

        except Exception as e:
            self.failed += 1
            self.errors.append(f"Facade接口测试失败: {e}")
            print(f"  ✗ 测试失败: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("开始集成测试")
        print("=" * 70)

        if not self.setup():
            print("\n✗ 测试环境设置失败，终止测试")
            return False

        # 运行所有测试
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

        # 显示结果
        self.show_results()

        return self.failed == 0

    def show_results(self):
        """显示测试结果"""
        print("\n" + "=" * 70)
        print("集成测试结果")
        print("=" * 70)

        total = self.passed + self.failed
        print(f"\n总测试数: {total}")
        print(f"通过: {self.passed}")
        print(f"失败: {self.failed}")

        if self.failed > 0:
            print(f"\n失败的测试:")
            for error in self.errors:
                print(f"  - {error}")

        if self.failed == 0:
            print("\n✓ 所有测试通过！")
        else:
            print(f"\n✗ {self.failed} 个测试失败")

        print("=" * 70)


# ============================================================================
# 主程序
# ============================================================================


def main():
    """主程序"""
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "quick":
            # 运行快速入门
            quick_start_guide()
        elif sys.argv[1] == "test":
            # 运行集成测试
            tester = IntegrationTest()
            success = tester.run_all_tests()
            sys.exit(0 if success else 1)
        else:
            print("用法:")
            print("  python quick_start.py quick  - 运行快速入门指南")
            print("  python quick_start.py test   - 运行集成测试")
    else:
        # 默认运行快速入门
        print("\n选择运行模式:")
        print("1. 快速入门指南")
        print("2. 集成测试")

        choice = input("\n请选择 (1 或 2): ").strip()

        if choice == "1":
            quick_start_guide()
        elif choice == "2":
            tester = IntegrationTest()
            tester.run_all_tests()
        else:
            print("无效的选择")


if __name__ == "__main__":
    main()
