"""
插件扫描工作脚本 - 在隔离的子进程中运行
此脚本会被主进程调用来安全地扫描单个插件
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any


def extract_port_info(plugin) -> List[Dict[str, Any]]:

    ports = []

    try:

        if hasattr(plugin, 'num_input_channels'):
            for i in range(plugin.num_input_channels):
                ports.append({
                    "type": "audio",
                    "direction": "input",
                    "index": i,
                    "name": f"Audio In {i + 1}"
                })

        if hasattr(plugin, 'num_output_channels'):
            for i in range(plugin.num_output_channels):
                ports.append({
                    "type": "audio",
                    "direction": "output",
                    "index": i,
                    "name": f"Audio Out {i + 1}"
                })

        if hasattr(plugin, 'is_instrument') and plugin.is_instrument:
            ports.append({
                "type": "midi",
                "direction": "input",
                "index": 0,
                "name": "MIDI In"
            })
    except Exception as e:
        print(f"Warning: Could not extract port info: {e}", file=sys.stderr)

    return ports


def extract_latency_info(plugin) -> tuple[bool, int]:

    try:

        if hasattr(plugin, 'latency_samples'):
            return True, int(plugin.latency_samples)
        elif hasattr(plugin, 'get_latency'):
            latency = plugin.get_latency()
            return True, int(latency) if latency else 0
    except Exception:
        pass

    return False, 0


def scan_plugin(plugin_path: str) -> dict:

    import pedalboard as pb

    path = Path(plugin_path)

    plugin = pb.load_plugin(plugin_path)

    unique_id = f"{plugin.manufacturer_name}::{plugin.name}::{path.suffix}"

    parameters = {}
    for p_name, p in plugin.parameters.items():
        try:
            parameters[p_name] = {
                "min": float(p.range[0]) if hasattr(p, 'range') else 0.0,
                "max": float(p.range[1]) if hasattr(p, 'range') else 1.0,
                "default":
                float(p.raw_value) if hasattr(p, 'raw_value') else 0.0
            }
        except (AttributeError, TypeError, ValueError):
            parameters[p_name] = {"min": 0.0, "max": 1.0, "default": 0.0}

    reports_latency, latency_samples = extract_latency_info(plugin)

    plugin_info = {
        "unique_plugin_id": unique_id,
        "name": plugin.name,
        "vendor": plugin.manufacturer_name,
        "path": plugin_path,
        "is_instrument": plugin.is_instrument,
        "plugin_format": path.suffix,
        "reports_latency": reports_latency,
        "latency_samples": latency_samples,
        "default_parameters": parameters
    }

    return plugin_info


def main():
    if len(sys.argv) < 2:
        print("Usage: scan_worker.py <plugin_path>", file=sys.stderr)
        sys.exit(1)

    plugin_path = sys.argv[1]
    try:
        plugin_info = scan_plugin(plugin_path)
        print(json.dumps(plugin_info, indent=2))
        sys.exit(0)

    except Exception as e:
        # 错误信息输出到stderr
        error_info = {
            "error": str(e),
            "type": type(e).__name__,
            "plugin_path": plugin_path
        }
        print(json.dumps(error_info), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
