from .engine import PedalboardEngine
from .render_graph import PedalboardRenderGraph
from .sync_controller import PedalboardSyncController
from .factory import PedalboardNodeFactory, PedalboardEngineFactory
from .registry import PedalboardPluginRegistry

__all__ = [
    "PedalboardEngine",
    "PedalboardEngineFactory",
    "PedalboardRenderGraph",
    "PedalboardSyncController",
    "PedalboardNodeFactory",
    "PedalboardPluginRegistry",
    "create_pedalboard_backend",
]


def create_pedalboard_backend(
    sample_rate: int = 48000,
    block_size: int = 512,
):
    """
    便捷函数：创建完整的 Pedalboard 后端
    
    Returns:
        (node_factory, plugin_registry, engine_factory) 的元组
    """
    node_factory = PedalboardNodeFactory()
    plugin_registry = PedalboardPluginRegistry()
    engine_factory = PedalboardEngineFactory()

    print("=" * 70)
    print("Pedalboard Backend Initialized")
    print("=" * 70)
    print(f"Sample Rate: {sample_rate} Hz")
    print(f"Block Size: {block_size} samples")
    print(f"Latency: {block_size/sample_rate*1000:.1f} ms")
    print("=" * 70)

    return node_factory, plugin_registry, engine_factory
