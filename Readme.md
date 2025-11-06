# 🎼 Echos:The Core of Next-Generation AI Agent-Driven Digital Audio Workstation

### Next-Generation AI Agent-Driven Digital Audio Workstation

> **A revolutionary DAW architecture designed from the ground up for AI agents to compose, produce, and master music autonomously.**

[![License](https://img.shields.io/badge/License-Apache%202.0-red.svg)](https://opensource.org/license/apache-2-0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pedalboard](https://img.shields.io/badge/audio-Spotify%20Pedalboard-1DB954.svg)](https://github.com/spotify/pedalboard)

---

## 🌟 Vision

**echos** is not just another DAW—it's a **DAW-as-a-Service** platform where AI agents are first-class citizens. Unlike traditional DAWs designed for human users clicking buttons, echos provides a **clean, event-driven API** that enables AI to:

- 🎹 **Compose** complete musical arrangements
- 🎚️ **Mix** multi-track projects with professional techniques
- 🎛️ **Master** final outputs with industry-standard processing
- 🔄 **Iterate** based on feedback and constraints
- 🤖 **Collaborate** with other AI agents in real-time

---

## 🏗️ Architecture Overview

```重画图，facade面向ai agent 与前端ui，我们的core不包含前端，前端可以网页，桌面端等等不同技术路线：


┌───────────────────────────────────────────────────────────┐
│                       AI Agent Layer                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   OpenAI    │  │   Anthropic  │  │   Custom Agents  │  │
│  │  Function   │  │    Claude    │  │                  │  │
│  │  Calling    │  │     Tools    │  │    Your Model    │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────────┬──────────────────────────────────┘
                         │
                    Agent Toolkit
                         │
┌────────────────────────▼──────────────────────────────────┐
│                      DAW Facade                           │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────────────┐ │
│  │ Project  │ │Transport │ │  Nodes  │ │    Editing     │ │
│  │ Service  │ │ Service  │ │ Service │ │    Service     │ │
│  └──────────┘ └──────────┘ └─────────┘ └────────────────┘ │
└────────────────────────┬──────────────────────────────────┘
                         │
                         │
┌────────────────────────▼───────────────────────────────────┐
│                   Core Domain Model                        │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌────────────────┐  │
│  │ Project  │ │ Timeline │ │ Router  │ │ Command Manager│  │
│  └──────────┘ └──────────┘ └─────────┘ └────────────────┘  │
│  ┌──────────┐ ┌──────────────────────┐                     |
│  │  Track   │ │   Engine Controller  │                     |   
│  └──────────┘ └──────────────────────┘                     │
└────────────────────────┬───────────────────────────────────┘
                      Event Bus
              (Decoupled Communication)   
                         │
                    Sync Controller
              (Frontend → Backend Sync)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  Audio Engine Backend                       │
│   ┌─────────────┐              ┌───────────────────┐        |
|   | Mock Engine |    ......    | Pedalboard Engine |        │
│   └─────────────┘              └───────────────────┘        |
└─────────────────────────────────────────────────────────────┘

```

---

## ✨ Key Features

### 🤖 **AI-First Design**

- **80+ Specialized Tools** organized by workflow (Project, Transport, Nodes, Editing, Mixing)
- **OpenAI Function Calling** format for GPT-4/GPT-4-turbo integration
- **Anthropic Claude Tools** format for Claude 3 Opus/Sonnet
- **Automatic parameter validation** and type checking
- **Rich documentation** with examples for every tool

### 🎹 **Professional Audio Engine**

- **Spotify Pedalboard** backend for high-performance DSP
- **VST3/AU plugin hosting** - use your favorite instruments and effects
- **Real-time audio processing** with <10ms latency
- **Automatic latency compensation** across plugin chains
- **Multi-threaded rendering** for complex projects

### 📊 **Event-Driven Architecture**

- **Complete decoupling** between frontend state and audio processing
- **Automatic synchronization** - change anything, it just works
- **Undo/Redo system** with command pattern
- **Macro commands** for batch operations
- **Event replay** for debugging and testing

### 🎚️ **Complete DAW Feature Set**

- ✅ Multi-track MIDI and audio recording
- ✅ Non-destructive editing with clips
- ✅ Automation lanes for every parameter
- ✅ Plugin insert chains with routing
- ✅ Effects sends and buses
- ✅ VCA groups for mix control
- ✅ Tempo and time signature automation
- ✅ Project save/load with full state serialization

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/echos.git
cd echos

# Install dependencies
pip install -e .

# Install audio backend
pip install pedalboard sounddevice

# Optional: MIDI support
pip install mido

# Optional: Plugin scanning
pip install python-rtmidi
```

### Hello World: AI Creates Music

```python
from echos import create_pedalboard_backend, DAWManager, ProjectSerializer
from echos.agent import AgentToolkit

# 1. Initialize the system
node_factory, plugin_registry, engine_factory = create_pedalboard_backend()

manager = DAWManager(
    project_serializer=ProjectSerializer(node_factory, plugin_registry),
    plugin_registry=plugin_registry,
    engine_factory=engine_factory,
    node_factory=node_factory
)

# 2. Create a toolkit for AI agents
from echos.facade import DAWFacade
from echos.services import (
    ProjectService, TransportService, NodeService, 
    EditingService, QueryService, SystemService, HistoryService
)

services = {
    'project': ProjectService(manager),
    'transport': TransportService(manager),
    'nodes': NodeService(manager),
    'editing': EditingService(manager),
    'query': QueryService(manager),
    'system': SystemService(manager),
    'history': HistoryService(manager)
}

facade = DAWFacade(manager, services)
toolkit = AgentToolkit(facade)

# 3. Get tools for your AI agent
openai_tools = toolkit.get_tools_for_openai()  # For GPT-4
anthropic_tools = toolkit.get_tools_for_anthropic()  # For Claude

# 4. Let the AI create music!
# Example: Using the toolkit directly
result = toolkit.execute_tool('create_project', name='AI Symphony')
project_id = result.data['project_id']

# Create an instrument track
result = toolkit.execute_tool('create_instrument_track', 
                              project_id=project_id, 
                              name='Lead Synth')
track_id = result.data['node_id']

# Add a synthesizer plugin
result = toolkit.execute_tool('add_plugin',
                              project_id=project_id,
                              track_id=track_id,
                              plugin_id='pedalboard.builtin.chorus')

# Create a MIDI clip
result = toolkit.execute_tool('create_midi_clip',
                              project_id=project_id,
                              track_id=track_id,
                              start_beat=0.0,
                              duration_beats=8.0)
clip_id = result.data['clip_id']

# Add notes (C major scale)
notes = [
    {"pitch": 60, "velocity": 100, "start_beat": 0.0, "duration_beats": 1.0},
    {"pitch": 62, "velocity": 90, "start_beat": 1.0, "duration_beats": 1.0},
    {"pitch": 64, "velocity": 95, "start_beat": 2.0, "duration_beats": 1.0},
    {"pitch": 65, "velocity": 100, "start_beat": 3.0, "duration_beats": 1.0},
]

result = toolkit.execute_tool('add_notes',
                              project_id=project_id,
                              clip_id=clip_id,
                              notes=notes)

# Set tempo and play
toolkit.execute_tool('set_tempo', project_id=project_id, bpm=120.0)
toolkit.execute_tool('play', project_id=project_id)
```

---

## 🤖 AI Agent Integration

### OpenAI GPT-4 Example

```python
import openai
from echos.agent import AgentToolkit

toolkit = AgentToolkit(facade)
tools = toolkit.get_tools_for_openai()

response = openai.ChatCompletion.create(
    model="gpt-4-turbo",
    messages=[
        {"role": "system", "content": "You are a professional music producer."},
        {"role": "user", "content": "Create a chill lofi hip hop beat at 85 BPM"}
    ],
    tools=tools,
    tool_choice="auto"
)

# Execute the tool calls
for tool_call in response.choices[0].message.tool_calls:
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    result = toolkit.execute_tool(function_name, **arguments)
    print(f"✓ {function_name}: {result.message}")
```

### Anthropic Claude Example

```python
import anthropic
from echos.agent import AgentToolkit

toolkit = AgentToolkit(facade)
tools = toolkit.get_tools_for_anthropic()

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=4096,
    tools=tools,
    messages=[
        {"role": "user", "content": "Produce a cinematic orchestral piece with strings and brass"}
    ]
)

# Process tool uses
for content in response.content:
    if content.type == "tool_use":
        result = toolkit.execute_tool(content.name, **content.input)
        print(f"✓ {content.name}: {result.message}")
```

---

## 📖 Core Concepts

### 1. **Project** - The Top-Level Container

A Project contains everything: tracks, timeline, routing, and commands.

```python
# Create a project
project = manager.create_project("My Song")
project.set_tempo(128.0)
project.set_time_signature(4, 4)

# Attach audio engine
engine = engine_factory.create_engine(sample_rate=48000)
project.attach_engine(engine)
```

### 2. **Tracks** - Audio and MIDI Containers

```python
# Instrument track (for MIDI + VST instruments)
piano = node_factory.create_instrument_track("Piano")
project.add_node(piano)

# Audio track (for recording or audio files)
vocals = node_factory.create_audio_track("Lead Vocals")
project.add_node(vocals)

# Bus track (for grouping and effects)
reverb_bus = node_factory.create_bus_track("Reverb Send")
project.add_node(reverb_bus)
```

### 3. **Clips** - Musical Content

```python
# Create a MIDI clip
clip = MIDIClip(
    start_beat=0.0,
    duration_beats=16.0,
    name="Verse Melody"
)

# Add notes
from echos.models import Note

clip.notes.add(Note(pitch=60, velocity=100, start_beat=0.0, duration_beats=1.0))
clip.notes.add(Note(pitch=64, velocity=95, start_beat=1.0, duration_beats=1.0))

# Add to track
piano.add_clip(clip)
```

### 4. **Plugins** - Sound Processing

```python
# Add a synthesizer
synth = plugin_registry.get_plugin_descriptor("pedalboard.builtin.chorus")
plugin = node_factory.create_plugin_instance(synth)
piano.mixer_channel.add_insert(plugin)

# Set plugin parameters
plugin.set_parameter_value("rate_hz", 1.5)
plugin.set_parameter_value("depth", 0.3)
```

### 5. **Automation** - Parameter Changes Over Time

```python
# Automate volume
volume = piano.mixer_channel.volume
volume.add_automation_point(beat=0.0, value=-6.0)   # Start at -6dB
volume.add_automation_point(beat=4.0, value=0.0)    # Rise to 0dB
volume.add_automation_point(beat=8.0, value=-12.0)  # Fade to -12dB
```

### 6. **Routing** - Signal Flow

```python
# Create effects send
piano.mixer_channel.add_send(
    target_bus_id=reverb_bus.node_id,
    is_post_fader=True
)

# Direct connection
project.router.connect(
    source_port=piano.get_ports()[0],  # Piano output
    dest_port=reverb_bus.get_ports()[0]  # Reverb input
)
```

---

## 🎛️ Agent Toolkit API

The toolkit provides **80+ tools** organized into categories:

### Project Management

- `create_project(name)` - Start a new project
- `save_project(project_id, file_path)` - Save to disk
- `load_project(file_path)` - Load from disk

### Transport Control

- `play(project_id)` - Start playback
- `stop(project_id)` - Stop playback
- `set_tempo(project_id, bpm)` - Change tempo
- `set_time_signature(project_id, numerator, denominator)`

### Node Management

- `create_instrument_track(project_id, name)`
- `create_audio_track(project_id, name)`
- `create_bus_track(project_id, name)`
- `add_plugin(project_id, track_id, plugin_id)`
- `list_nodes(project_id)` - Query all nodes

### Editing

- `create_midi_clip(project_id, track_id, start_beat, duration_beats)`
- `add_notes(project_id, clip_id, notes)` - Add MIDI notes
- `set_parameter(project_id, node_id, parameter_name, value)`
- `add_automation(project_id, node_id, parameter_name, beat, value)`

### Mixing

- `create_send(project_id, source_track_id, dest_bus_id)`
- `set_volume(project_id, track_id, db)`
- `set_pan(project_id, track_id, position)`

### Query

- `get_project_overview(project_id)` - Get high-level stats
- `get_node_details(project_id, node_id)` - Inspect a node
- `find_node_by_name(project_id, name)` - Search nodes

### History

- `undo(project_id)` - Undo last action
- `redo(project_id)` - Redo last undone action
- `begin_macro(project_id, description)` - Start batch operation
- `end_macro(project_id)` - Commit batch operation

**Full API documentation:** See `docs/agent_toolkit.md`

---

## 🧪 Testing

### Run the Complete Test Suite

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Audio engine tests
pytest tests/backends/

# Full system test with MIDI
python tests/test_midi_project.py

# Quick test (generated melody)
python tests/standalone_test.py
```

### Test with Real MIDI Files

```bash
# Load and play a MIDI file
python tests/test_midi_project.py --midi path/to/song.mid

# Render to audio file
python tests/test_midi_project.py --midi song.mid --render output.wav
```

---

## 🎨 Example Projects

### Example 1: AI Composes a Song

```python
"""
Agent task: "Create a 16-bar pop song in C major with drums, bass, and melody"
"""

# Project setup
toolkit.execute_tool('create_project', name='Pop Song')
toolkit.execute_tool('set_tempo', project_id=pid, bpm=120)

# Create tracks
drums = toolkit.execute_tool('create_instrument_track', project_id=pid, name='Drums')
bass = toolkit.execute_tool('create_instrument_track', project_id=pid, name='Bass')
melody = toolkit.execute_tool('create_instrument_track', project_id=pid, name='Lead')

# Add plugins
toolkit.execute_tool('add_plugin', project_id=pid, track_id=drums['node_id'], 
                    plugin_id='pedalboard.builtin.compressor')

# Create MIDI clips and notes
# ... (AI generates appropriate notes)

# Mix
toolkit.execute_tool('set_parameter', project_id=pid, node_id=drums['node_id'], 
                    parameter_name='volume', value=-3.0)

# Export
toolkit.execute_tool('play', project_id=pid)
```

### Example 2: AI Masters a Track

```python
"""
Agent task: "Master this track for streaming platforms"
"""

# Create mastering chain
master = toolkit.execute_tool('get_master_track', project_id=pid)

# Add mastering plugins
toolkit.execute_tool('add_plugin', project_id=pid, track_id=master['node_id'],
                    plugin_id='pedalboard.builtin.compressor')
toolkit.execute_tool('add_plugin', project_id=pid, track_id=master['node_id'],
                    plugin_id='pedalboard.builtin.eq')

# Set mastering parameters
toolkit.execute_tool('set_parameter', project_id=pid, node_id=master['node_id'],
                    parameter_name='plugin.0.threshold_db', value=-10.0)
toolkit.execute_tool('set_parameter', project_id=pid, node_id=master['node_id'],
                    parameter_name='plugin.0.ratio', value=3.0)
```

---

## 🔧 Advanced Features

### Custom Backends

echos supports pluggable audio backends:

```python
# Pedalboard (default - high performance)
from echos.backends.pedalboard import create_pedalboard_backend
backend = create_pedalboard_backend()

# Mock (testing - no audio)
from echos.backends.mock import create_mock_backend
backend = create_mock_backend()

# Real (pure Python - educational)
from echos.backends.real import create_real_backend
backend = create_real_backend()
```

### Custom Plugin Registry

```python
class CustomPluginRegistry(IPluginRegistry):
    def scan_for_plugins(self):
        # Scan your custom plugin directories
        pass
    
    def get_plugin_descriptor(self, plugin_id):
        # Return plugin metadata
        pass
```

### Event Listening

```python
from echos.models.event_model import NodeAdded, ParameterChanged

def on_node_added(event: NodeAdded):
    print(f"Node added: {event.node.name}")

def on_parameter_changed(event: ParameterChanged):
    print(f"Parameter {event.param_name} changed to {event.new_value}")

# Subscribe to events
project.event_bus.subscribe(NodeAdded, on_node_added)
project.event_bus.subscribe(ParameterChanged, on_parameter_changed)
```

---

## 📚 Documentation

- **[Architecture Guide](docs/architecture.md)** - Deep dive into the system design
- **[Agent Toolkit API](docs/agent_toolkit.md)** - Complete tool reference
- **[Backend Development](docs/backends.md)** - Create custom audio engines
- **[Event System](docs/events.md)** - Understanding the event bus
- **[Plugin Development](docs/plugins.md)** - Write custom plugins
- **[Testing Guide](docs/testing.md)** - Comprehensive testing strategies

---

## 🛣️ Roadmap

### v0.2.0 (Q2 2024)
- ✅ Complete Pedalboard backend
- ✅ VST3 plugin hosting
- ✅ MIDI file import/export
- ✅ Audio file recording

### v0.3.0 (Q3 2024)
- 🔄 Real-time collaboration
- 🔄 Cloud rendering API
- 🔄 Web-based UI
- 🔄 Streaming integration

### v1.0.0 (Q4 2024)
- 🔄 Production-ready stability
- 🔄 Comprehensive plugin library
- 🔄 Multi-platform binaries
- 🔄 Commercial plugin support

### Future
- 🔮 Distributed rendering
- 🔮 ML-based mixing assistant
- 🔮 Stem separation
- 🔮 Audio-to-MIDI transcription
---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone and install in development mode
git clone https://github.com/linzwcs/echos.git
cd echos
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Spotify** for the amazing [Pedalboard](https://github.com/spotify/pedalboard) library
- **The DAW community** for decades of innovation
- **AI researchers** pushing the boundaries of creative AI
- **Open source contributors** making this possible

---



<div align="center">

**Built with ❤️ for the future of DAW Copilot**

[Website](https://echos.dev) • [Documentation](https://docs.echos.dev) • [Examples](https://github.com/linzwcs/echos-examples)

</div>