import time
import numpy as np
from pathlib import Path
import sys
import uuid
# 假设项目结构
sys.path.insert(0, str(Path(__file__).parent.parent))

from echos.core.event_bus import EventBus
from echos.core.plugin import PluginCache
from echos.backends.pedalboard import (
    PedalboardEngine,
    PedalboardNodeFactory,
)
from echos.backends.pedalboard.plugin import (
    PedalboardPluginRegistry,
    PedalboardPluginInstanceManager,
)
from echos.backends.pedalboard.timeline import RealTimeTimeline
from echos.models import (
    event_model,
    Tempo,
    TimeSignature,
    Note,
    MIDIClip,
    TransportStatus,
)
from echos.core.project import Project
from echos.core.router import Router
from echos.core.plugin import Plugin


class TestResults:
    """测试结果收集器"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def assert_equal(self, actual, expected, test_name):
        if actual == expected:
            self.passed += 1
            print(f"  ✓ {test_name}")
            return True
        else:
            self.failed += 1
            error = f"  ✗ {test_name}: Expected {expected}, got {actual}"
            print(error)
            self.errors.append(error)
            return False

    def assert_true(self, condition, test_name):
        if condition:
            self.passed += 1
            print(f"  ✓ {test_name}")
            return True
        else:
            self.failed += 1
            error = f"  ✗ {test_name}: Condition failed"
            print(error)
            self.errors.append(error)
            return False

    def assert_not_none(self, value, test_name):
        return self.assert_true(value is not None, test_name)

    def print_summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")
        print(
            f"Success Rate: {self.passed/(self.passed+self.failed)*100:.1f}%")

        if self.errors:
            print("\nFailed Tests:")
            for error in self.errors:
                print(error)
        print("=" * 70)


def test_event_bus():
    """测试 EventBus 基本功能"""
    print("\n" + "=" * 70)
    print("TEST 1: EventBus Functionality")
    print("=" * 70)

    results = TestResults()
    event_bus = EventBus()

    # 测试订阅和发布
    received_events = []

    def handler1(event):
        received_events.append(('handler1', event))

    def handler2(event):
        received_events.append(('handler2', event))

    # 订阅
    event_bus.subscribe(event_model.ProjectLoaded, handler1)
    event_bus.subscribe(event_model.ProjectLoaded, handler2)

    # 发布事件
    project = Project(name="Test Project")
    event = event_model.ProjectLoaded(project=project)
    event_bus.publish(event)

    results.assert_equal(len(received_events), 2,
                         "Two handlers received event")
    results.assert_equal(received_events[0][0], 'handler1',
                         "Handler1 called first")
    results.assert_equal(received_events[1][0], 'handler2',
                         "Handler2 called second")

    # 测试取消订阅
    received_events.clear()
    event_bus.unsubscribe(event_model.ProjectLoaded, handler1)
    event_bus.publish(event)

    results.assert_equal(len(received_events), 1,
                         "Only one handler after unsubscribe")
    results.assert_equal(received_events[0][0], 'handler2',
                         "Handler2 still active")

    # 测试通配符订阅
    received_events.clear()

    def catch_all_handler(event):
        received_events.append(('catch_all', event))

    event_bus.subscribe(event_model.BaseEvent, catch_all_handler)
    event_bus.publish(
        event_model.NodeAdded(node_id="track1", node_type='IntructmentTrack'))

    results.assert_true(len(received_events) >= 1, "Catch-all handler works")

    # 测试清空
    event_bus.clear()
    received_events.clear()
    event_bus.publish(event)

    results.assert_equal(len(received_events), 0, "All handlers cleared")

    results.print_summary()
    return results


def test_plugin_registry():
    """测试 PluginRegistry"""
    print("\n" + "=" * 70)
    print("TEST 2: Plugin Registry")
    print("=" * 70)

    results = TestResults()

    # 创建临时缓存
    cache_path = Path("/tmp/muzai_test_cache.json")
    cache = PluginCache(cache_path)

    registry = PedalboardPluginRegistry(cache)
    registry.load()

    # 测试插件列表
    all_plugins = registry.list_all()
    print(f"  Found {len(all_plugins)} plugins")

    results.assert_true(len(all_plugins) >= 0, "Plugin list retrieved")

    # 如果有插件，测试查找功能
    if all_plugins:
        first_plugin = all_plugins[0]

        # 测试按ID查找
        found = registry.find_by_id(first_plugin.unique_plugin_id)
        results.assert_not_none(found,
                                f"Find plugin by ID: {first_plugin.name}")
        results.assert_equal(found.unique_plugin_id,
                             first_plugin.unique_plugin_id,
                             "Found plugin matches")

        # 测试按路径查找
        found_by_path = registry.find_by_path(first_plugin.path)
        results.assert_not_none(found_by_path, f"Find plugin by path")

        print(f"  Sample plugin: {first_plugin.name} by {first_plugin.vendor}")

    # 清理
    if cache_path.exists():
        cache_path.unlink()

    results.print_summary()
    return results


def test_plugin_instance_manager():
    """测试 PluginInstanceManager"""
    print("\n" + "=" * 70)
    print("TEST 3: Plugin Instance Manager")
    print("=" * 70)

    results = TestResults()

    cache = PluginCache(Path("/tmp/muzai_test_cache.json"))
    registry = PedalboardPluginRegistry(cache)
    registry.load()

    manager = PedalboardPluginInstanceManager(registry)

    all_plugins = registry.list_all()

    if not all_plugins:
        print("  ⚠ No plugins found, skipping instance tests")
        results.print_summary()
        return results

    # 选择一个非乐器插件进行测试
    test_plugin = None
    for plugin in all_plugins:
        if not plugin.is_instrument:
            test_plugin = plugin
            break

    if not test_plugin:
        print("  ⚠ No effect plugins found, skipping")
        results.print_summary()
        return results

    print(f"  Testing with: {test_plugin.name}")

    # 测试创建实例
    instance_id = uuid.uuid4()
    result = manager.create_instance(instance_id, test_plugin.unique_plugin_id)
    results.assert_not_none(result, "Plugin instance created")

    if result:
        instance_id, instance = result
        results.assert_not_none(instance_id, "Instance ID assigned")
        results.assert_not_none(instance, "Plugin instance valid")

        # 测试获取实例
        retrieved = manager.get_instance(instance_id)
        results.assert_equal(retrieved, instance, "Retrieved instance matches")

        # 测试释放实例
        released = manager.release_instance(instance_id)
        results.assert_true(released, "Instance released successfully")

        # 确认释放后获取失败
        retrieved_after = manager.get_instance(instance_id)
        results.assert_true(retrieved_after is None,
                            "Instance gone after release")

    # 测试批量释放
    instances = []
    for i in range(3):
        result = manager.create_instance(uuid.uuid4(),
                                         test_plugin.unique_plugin_id)
        if result:
            instances.append(result[0])

    manager.release_all()

    all_gone = all(manager.get_instance(iid) is None for iid in instances)
    results.assert_true(all_gone, "All instances released")

    results.print_summary()
    return results


def test_render_graph():
    """测试 RenderGraph"""
    print("\n" + "=" * 70)
    print("TEST 4: Render Graph")
    print("=" * 70)

    results = TestResults()

    cache = PluginCache(Path("/tmp/muzai_test_cache.json"))
    registry = PedalboardPluginRegistry(cache)
    registry.load()
    manager = PedalboardPluginInstanceManager(registry)

    from echos.backends.pedalboard.render_graph import PedalboardRenderGraph

    graph = PedalboardRenderGraph(sample_rate=48000,
                                  block_size=512,
                                  plugin_instance_manager=manager)

    # 测试添加节点
    graph.add_node("track1", "AudioTrack")
    graph.add_node("track2", "InstrumentTrack")
    graph.add_node("bus1", "BusTrack")

    results.assert_equal(graph.get_node_count(), 3, "Three nodes added")

    # 测试连接
    graph.add_connection("track1", "bus1")
    graph.add_connection("track2", "bus1")

    results.assert_equal(graph.get_connection_count(), 2,
                         "Two connections added")

    # 测试循环检测
    graph.add_connection("bus1", "track1")  # 这应该被拒绝
    results.assert_equal(graph.get_connection_count(), 2, "Cycle prevented")

    # 测试添加插件
    plugins = registry.list_all()
    effect_plugin = None

    for p in plugins:
        if not p.is_instrument:
            effect_plugin = p
            effect_plugin = Plugin(effect_plugin, event_bus=None)
            break

    if effect_plugin:

        results.assert_equal(len(graph.get_node("track1").pedalboard), 0,
                             "Before Plugin added to pedalboard")
        graph.add_plugin_to_node("track1", effect_plugin.node_id,
                                 effect_plugin.descriptor.unique_plugin_id, 0)
        results.assert_equal(graph.get_plugin_count(), 1,
                             "Plugin added to node")
        results.assert_equal(len(graph.get_node("track1").pedalboard), 1,
                             "After Plugin added to pedalboard")

        node = graph._nodes["track1"]
        if node.plugin_instance_map:
            plugin_id = list(node.plugin_instance_map.keys())[0]
            graph.remove_plugin_from_node("track1", plugin_id)
            results.assert_equal(graph.get_plugin_count(), 0, "Plugin removed")

    # 测试图验证
    is_valid, issues = graph.validate_graph()
    results.assert_true(is_valid, "Graph is valid")
    results.assert_equal(len(issues), 0, "No validation issues")

    # 测试移除连接
    graph.remove_connection("track1", "bus1")
    results.assert_equal(graph.get_connection_count(), 1, "Connection removed")

    # 测试移除节点
    graph.remove_node("track1")
    results.assert_equal(graph.get_node_count(), 2, "Node removed")

    # 测试清空
    graph.clear()
    results.assert_equal(graph.get_node_count(), 0, "Graph cleared")
    results.assert_equal(graph.get_connection_count(), 0,
                         "Connections cleared")

    results.print_summary()
    return results


def test_timeline():
    """测试 Timeline"""
    print("\n" + "=" * 70)
    print("TEST 5: Timeline")
    print("=" * 70)

    results = TestResults()

    timeline = RealTimeTimeline()
    timeline
    # 测试默认 tempo
    default_tempo = timeline.get_tempo_at_beat(0.0)
    results.assert_equal(default_tempo, 120.0, "Default tempo is 120 BPM")

    # 测试添加 tempo 变化
    tempos = (
        Tempo(beat=0.0, bpm=120.0),
        Tempo(beat=8.0, bpm=140.0),
        Tempo(beat=16.0, bpm=100.0),
    )
    timeline.update_tempos(tempos)

    # 测试不同位置的 tempo
    results.assert_equal(timeline.get_tempo_at_beat(0.0), 120.0,
                         "Tempo at beat 0")
    results.assert_equal(timeline.get_tempo_at_beat(4.0), 120.0,
                         "Tempo at beat 4")
    results.assert_equal(timeline.get_tempo_at_beat(8.0), 140.0,
                         "Tempo at beat 8")
    results.assert_equal(timeline.get_tempo_at_beat(12.0), 140.0,
                         "Tempo at beat 12")
    results.assert_equal(timeline.get_tempo_at_beat(16.0), 100.0,
                         "Tempo at beat 16")
    results.assert_equal(timeline.get_tempo_at_beat(20.0), 100.0,
                         "Tempo at beat 20")

    # 测试时间签名
    time_sigs = (
        TimeSignature(beat=0.0, numerator=4, denominator=4),
        TimeSignature(beat=16.0, numerator=3, denominator=4),
    )
    timeline.update_time_signatures(time_sigs)

    results.print_summary()
    return results


def test_sync_controller():
    """测试 SyncController"""
    print("\n" + "=" * 70)
    print("TEST 6: Sync Controller")
    print("=" * 70)

    results = TestResults()

    # 创建完整的引擎环境
    cache = PluginCache(Path("/tmp/muzai_test_cache.json"))
    registry = PedalboardPluginRegistry(cache)
    registry.load()
    manager = PedalboardPluginInstanceManager(registry)

    engine = PedalboardEngine(
        sample_rate=48000,
        block_size=512,
        plugin_ins_manager=manager,
    )

    event_bus = EventBus()
    sync_controller = engine.sync_controller

    # 挂载到 event bus
    sync_controller._on_mount(event_bus)

    # 创建测试项目
    project = Project(name="Test Project")
    factory = PedalboardNodeFactory()

    # 添加轨道
    track1 = factory.create_instrument_track("Piano")
    track2 = factory.create_audio_track("Vocals")
    project.add_node(track1)
    project.add_node(track2)

    # 发布 ProjectLoaded 事件
    message_count_before = len(engine._nrt_message_queue)
    event_bus.publish(event_model.ProjectLoaded(project=project))

    # 等待消息处理
    time.sleep(0.1)
    engine.refresh()

    # 验证节点已添加到 render graph
    results.assert_true(engine._render_graph.get_node_count() >= 2,
                        "Nodes synced to render graph")

    # 测试添加插件事件
    plugins = registry.list_all()
    if plugins:
        instrument_plugin = None
        for p in plugins:
            if p.is_instrument:
                instrument_plugin = p
                break

        if instrument_plugin:
            from echos.core.plugin import Plugin
            plugin_instance = Plugin(descriptor=instrument_plugin,
                                     event_bus=event_bus)

            event_bus.publish(
                event_model.InsertAdded(
                    owner_node_id=track1.node_id,
                    plugin_instance_id=uuid.uuid4(),
                    plugin_unique_id=plugin_instance.node_id,
                    index=0))

            time.sleep(0.1)

            engine.refresh()
            results.assert_true(engine._render_graph.get_plugin_count() >= 1,
                                "Plugin synced to render graph")

    # 清理
    sync_controller._on_unmount()

    results.print_summary()
    return results


def test_engine_workflow():
    """测试完整的 Engine 工作流"""
    print("\n" + "=" * 70)
    print("TEST 7: Complete Engine Workflow")
    print("=" * 70)

    results = TestResults()

    # 创建引擎
    cache = PluginCache(Path("/tmp/muzai_test_cache.json"))
    registry = PedalboardPluginRegistry(cache)
    registry.load()
    manager = PedalboardPluginInstanceManager(registry)

    engine = PedalboardEngine(
        sample_rate=48000,
        block_size=1024,
        plugin_ins_manager=manager,
    )

    event_bus = EventBus()
    engine.mount(event_bus)

    # 测试初始状态
    results.assert_equal(engine.transport_status, TransportStatus.STOPPED,
                         "Initial state is STOPPED")
    results.assert_equal(engine.current_beat, 0.0, "Initial beat is 0")

    # 添加 MIDI clip
    clip = MIDIClip(clip_id="clip1",
                    start_beat=8.0,
                    duration_beats=12.0,
                    notes=[
                        Note(note_id=1,
                             pitch=60,
                             velocity=100,
                             start_beat=0.0,
                             duration_beats=2.0),
                        Note(note_id=2,
                             pitch=64,
                             velocity=100,
                             start_beat=2.0,
                             duration_beats=2.0),
                        Note(note_id=3,
                             pitch=67,
                             velocity=100,
                             start_beat=4.0,
                             duration_beats=2.0),
                    ])

    plugins = registry.list_all()
    instructment_plugin = None

    for p in plugins:
        if p.is_instrument:
            instructment_plugin = Plugin(p, event_bus=None)
            break

    event_bus.publish(
        event_model.NodeAdded(node_id="track1", node_type="InstrumentTrack"))
    event_bus.publish(event_model.ClipAdded(owner_track_id="track1",
                                            clip=clip))
    event_bus.publish(
        event_model.InsertAdded(
            owner_node_id="track1",
            plugin_instance_id=instructment_plugin.node_id,
            plugin_unique_id=instructment_plugin.descriptor.unique_plugin_id,
            index=0))
    engine.refresh()
    results.assert_true(engine._render_graph.get_node_count() >= 1,
                        "node loadeded")
    results.assert_true(
        len(engine._render_graph.get_node("track1").clips) == 1,
        "clip loadeded")
    print(engine._render_graph.get_node("track1").instrument)
    results.assert_true((engine._render_graph.get_node("track1").instrument),
                        "plugin loadeded")

    engine.seek(8.0)
    results.assert_equal(engine.current_beat, 8.0, "Seek to beat 8")
    frame_start = time.perf_counter()
    engine.play()
    results.assert_true(engine.is_playing, "Engine is playing")
    for i in range(10):
        frame_start = time.perf_counter()
        stats = engine.get_performance_stats()
        elapsed = time.perf_counter() - frame_start
        print(f"  [{elapsed:5.1f}s] "
              f"Beat: {engine.current_beat:6.2f} | "
              f"CPU: {stats['cpu_load_percent']:5.1f}% | "
              f"Pending: {stats['pending_nrt_messages']}")
        time.sleep(1)

    engine.pause()
    results.assert_equal(engine.transport_status, TransportStatus.PAUSED,
                         "Engine paused")
    time.sleep(0.5)

    engine.stop()
    results.assert_equal(engine.transport_status, TransportStatus.STOPPED,
                         "Engine stopped")

    # 测试性能统计
    stats = engine.get_performance_stats()
    results.assert_not_none(stats, "Performance stats available")
    results.assert_true('cpu_load_percent' in stats, "CPU load tracked")

    # 清理
    engine.unmount()

    results.print_summary()
    return results


def test_stress_and_edge_cases():
    """压力测试和边界情况"""
    print("\n" + "=" * 70)
    print("TEST 8: Stress Tests and Edge Cases")
    print("=" * 70)

    results = TestResults()

    cache = PluginCache(Path("/tmp/muzai_test_cache.json"))
    registry = PedalboardPluginRegistry(cache)
    registry.load()
    manager = PedalboardPluginInstanceManager(registry)

    from echos.backends.pedalboard.render_graph import PedalboardRenderGraph

    graph = PedalboardRenderGraph(48000, 512, manager)

    # 测试大量节点
    print("  Creating 100 nodes...")
    for i in range(100):
        graph.add_node(f"node_{i}", "AudioTrack")

    results.assert_equal(graph.get_node_count(), 100, "100 nodes created")

    # 测试大量连接
    print("  Creating chain connections...")
    for i in range(99):
        graph.add_connection(f"node_{i}", f"node_{i+1}")

    results.assert_equal(graph.get_connection_count(), 99,
                         "99 connections created")

    # 验证处理顺序
    is_valid, issues = graph.validate_graph()
    results.assert_true(is_valid, "Large graph is valid")

    # 测试清空
    graph.clear()
    results.assert_equal(graph.get_node_count(), 0, "Graph cleared")

    # 边界情况：空图处理
    from echos.models import TransportContext
    context = TransportContext(current_beat=0.0,
                               sample_rate=48000,
                               block_size=512,
                               tempo=120.0)

    output = graph.process_block(context)
    results.assert_equal(output.shape, (2, 512),
                         "Empty graph produces silence")
    results.assert_true(np.allclose(output, 0.0), "Output is silent")

    # 边界情况：不存在的节点操作
    graph.remove_node("nonexistent")  # 应该安全地失败
    graph.add_connection("nonexistent1", "nonexistent2")  # 应该安全地失败

    results.assert_equal(graph.get_node_count(), 0,
                         "No nodes after invalid ops")

    # 测试重复操作
    graph.add_node("dup1", "AudioTrack")
    graph.add_node("dup1", "AudioTrack")  # 重复添加应该被忽略
    results.assert_equal(graph.get_node_count(), 1, "Duplicate add ignored")

    results.print_summary()
    return results


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("RUNNING COMPLETE TEST SUITE")
    print("=" * 70)

    all_results = []

    #try:
    #    all_results.append(test_event_bus())
    #except Exception as e:
    #    print(f"EventBus test crashed: {e}")
    #    import traceback
    #    traceback.print_exc()

    # try:
    #     all_results.append(test_plugin_registry())
    # except Exception as e:
    #     print(f"PluginRegistry test crashed: {e}")
    #     import traceback
    #     traceback.print_exc()

    #try:
    #    all_results.append(test_plugin_instance_manager())
    #except Exception as e:
    #    print(f"PluginInstanceManager test crashed: {e}")
    #    import traceback
    #    traceback.print_exc()

    #try:
    #    all_results.append(test_render_graph())
    #except Exception as e:
    #    print(f"RenderGraph test crashed: {e}")
    #    import traceback
    #    traceback.print_exc()

    #try:
    #    all_results.append(test_timeline())
    #except Exception as e:
    #    print(f"Timeline test crashed: {e}")
    #    import traceback
    #    traceback.print_exc()

    # try:
    #     all_results.append(test_sync_controller())
    # except Exception as e:
    #     print(f"SyncController test crashed: {e}")
    #     import traceback
    #     traceback.print_exc()

    try:
        all_results.append(test_engine_workflow())
    except Exception as e:
        print(f"Engine workflow test crashed: {e}")
        import traceback
        traceback.print_exc()

    #try:
    #    all_results.append(test_stress_and_edge_cases())
    #except Exception as e:
    #    print(f"Stress test crashed: {e}")
    #    import traceback
    #    traceback.print_exc()

    # 汇总结果
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    total_tests = total_passed + total_failed

    print(f"Total Tests: {total_tests}")
    print(f"Passed:      {total_passed}")
    print(f"Failed:      {total_failed}")

    if total_tests > 0:
        print(f"Success Rate: {total_passed/total_tests*100:.1f}%")

    print("=" * 70)

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
