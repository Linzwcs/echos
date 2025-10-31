from .factory import (
    MockNodeFactory,
    MockEngineFactory,
)
from .register import MockPluginRegistry
from ...models import PluginCategory


def create_mock_backend():
    """
    便捷函数：创建完整的Mock后端
    
    Returns:
        (node_factory, plugin_registry, engine_factory)的元组
    """
    node_factory = MockNodeFactory()
    plugin_registry = MockPluginRegistry()
    engine_factory = MockEngineFactory()

    return node_factory, plugin_registry, engine_factory


def print_available_plugins(registry: MockPluginRegistry):
    """
    打印所有可用插件的信息
    
    Args:
        registry: 插件注册表
    """
    print("\n" + "=" * 70)
    print("Available Mock Plugins")
    print("=" * 70)

    for category in PluginCategory:
        plugins = registry.list_plugins_by_category(category)
        if plugins:
            print(f"\n{category.value.upper()} ({len(plugins)})")
            print("-" * 70)
            for plugin in plugins:
                print(f"  • {plugin.name}")
                print(f"    ID: {plugin.unique_plugin_id}")
                print(f"    Latency: {plugin.latency_samples} samples")
                print(f"    Parameters: {len(plugin.default_parameters)}")
                print()


__all__ = [
    "MockNodeFactory",
    "MockPluginRegistry",
    "MockAudioEngineFactory",
    "create_mock_backend",
    "print_available_plugins",
]
