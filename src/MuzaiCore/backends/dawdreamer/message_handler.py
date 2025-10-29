# file: src/MuzaiCore/backends/dawdreamer/message_handler.py
"""
The command handler for the audio thread. It dispatches message objects
to dedicated handler functions.
"""
from typing import Dict, Callable, Optional, Type
import dawdreamer as daw

from .messages import (AnyMessage, AddNode, RemoveNode, AddConnection,
                       RemoveConnection, SetParameter, AddNotes)
from ...interfaces.system import ITimeline
from ...models import AutomationLane


class AudioThreadStateHandler:

    def __init__(self):
        self.node_id_to_processor_name: Dict[str, str] = {}
        self.timeline: Optional[ITimeline] = None
        # 新增：存储自动化数据
        # 结构: { node_id: { param_name: AutomationLane } }
        self.automation_data: Dict[str, Dict[str, AutomationLane]] = {}


def _handle_add_node(engine: daw.RenderEngine, state: AudioThreadStateHandler,
                     msg: AddNode):
    processor_name = f"proc_{msg.node_id}"
    state.node_id_to_processor_name[msg.node_id] = processor_name
    if msg.node_type == 'plugin' and msg.plugin_path:
        engine.make_plugin_processor(processor_name, msg.plugin_path)
    else:  # 'sum'
        engine.make_add_processor(processor_name, [])


def _handle_remove_node(engine: daw.RenderEngine,
                        state: AudioThreadStateHandler, msg: RemoveNode):
    if msg.node_id in state.node_id_to_processor_name:
        name_to_remove = state.node_id_to_processor_name.pop(msg.node_id)
        engine.remove_processor(name_to_remove)


def _handle_add_connection(engine: daw.RenderEngine,
                           state: AudioThreadStateHandler, msg: AddConnection):
    source_name = state.node_id_to_processor_name.get(msg.source_node_id)
    dest_name = state.node_id_to_processor_name.get(msg.dest_node_id)
    if not (source_name and dest_name):
        return

    dest_proc = engine.get_processor(dest_name)
    if hasattr(dest_proc, 'set_ins'):  # It's a summing processor
        current_ins = dest_proc.get_ins()
        if source_name not in current_ins:
            dest_proc.set_ins(current_ins + [source_name])
    else:  # Direct connection (e.g., plugin to output)
        engine.add_connection(source_name, dest_name)


def _handle_remove_connection(engine: daw.RenderEngine,
                              state: AudioThreadStateHandler,
                              msg: RemoveConnection):
    source_name = state.node_id_to_processor_name.get(msg.source_node_id)
    dest_name = state.node_id_to_processor_name.get(msg.dest_node_id)
    if not (source_name and dest_name):
        return

    dest_proc = engine.get_processor(dest_name)
    if hasattr(dest_proc, 'set_ins'):  # It's a summing processor
        current_ins = dest_proc.get_ins()
        if source_name in current_ins:
            current_ins.remove(source_name)
            dest_proc.set_ins(current_ins)
    else:
        engine.remove_connection(source_name, dest_name)


def _handle_set_parameter(engine: daw.RenderEngine,
                          state: AudioThreadStateHandler, msg: SetParameter):
    proc_name = state.node_id_to_processor_name.get(msg.node_id)
    if not proc_name:
        return

    processor = engine.get_processor(proc_name)
    # Using set_parameter_by_name is more robust and preferred
    if hasattr(processor, 'set_parameter_by_name'):
        processor.set_parameter_by_name(msg.param_name, msg.value)
    else:  # Fallback for older/simpler plugins
        for i in range(processor.get_parameter_count()):
            if processor.get_parameter_name(i) == msg.param_name:
                processor.set_parameter(i, msg.value)
                break


def _handle_add_notes(engine: daw.RenderEngine, state: AudioThreadStateHandler,
                      msg: AddNotes):
    proc_name = state.node_id_to_processor_name.get(msg.node_id)
    timeline = state.timeline
    if not (proc_name and timeline):
        return

    processor = engine.get_processor(proc_name)
    if hasattr(processor, 'add_midi_note'):
        for note in msg.notes:
            start_sec = timeline.beats_to_seconds(note.start_beat)
            duration_sec = timeline.beats_to_seconds(note.duration_beats)
            processor.add_midi_note(note.pitch, note.velocity, start_sec,
                                    duration_sec)


class MessageHandler:
    """Dispatches messages to the appropriate handler function."""

    def __init__(self):
        self._handlers: Dict[Type[AnyMessage], Callable] = {
            AddNode: _handle_add_node,
            RemoveNode: _handle_remove_node,
            AddConnection: _handle_add_connection,
            RemoveConnection: _handle_remove_connection,
            SetParameter: _handle_set_parameter,
            AddNotes: _handle_add_notes,
        }

    def handle(self, msg: AnyMessage, engine: daw.RenderEngine,
               state: AudioThreadStateHandler):
        handler = self._handlers.get(type(msg))
        if handler:
            try:
                handler(engine, state, msg)
            except Exception as e:
                # In a real-time thread, we must never crash. Log errors instead.
                print(
                    f"Audio Thread Error handling message '{type(msg).__name__}': {e}"
                )
        else:
            print(
                f"Audio Thread Warning: No handler found for message type '{type(msg).__name__}'"
            )
