# file: src/MuzaiCore/backends/dawdreamer/sync_controller.py
from typing import List, Optional

from ...interfaces.system import IProject, INode, IPlugin, ITrack
from ...models import Connection, Note, PluginDescriptor
from .render_graph import DawDreamerRenderGraph


class DawDreamerSyncController:
    """
    Acts as a simple Adapter that translates domain event notifications
    from the service layer into high-level, transactional calls on the
    DawDreamerRenderGraph.

    This class runs on the main thread and contains no complex logic. Its
    primary role is to decouple the services from the render graph's
    implementation details.
    """

    def __init__(self, render_graph: DawDreamerRenderGraph):
        """
        Initializes the SyncController.

        Args:
            render_graph: The render graph instance that will manage the
                          state and generate commands for the audio thread.
        """
        self._render_graph = render_graph

    def observe_project(self, project: IProject):
        """
        Signals that a new project is being observed. In our current design,
        this is mostly a conceptual step. The actual sync calls are triggered
        by services after commands are executed.
        """
        print(f"SyncController: Now observing project '{project.project_id}'")
        # In a more event-driven system, this would subscribe to project.events.
        # Here, it serves as a hook for potential future use.

    def on_project_closed(self, project: IProject):
        """
        Called when a project is closed. This triggers a full cleanup
        of the render graph.
        """
        print(
            f"SyncController: Scheduling cleanup for project '{project.project_id}'"
        )
        self._render_graph.clear()

    # --- Node and Connection Operations (Delegation) ---

    def on_node_added(self,
                      node: INode,
                      descriptor: Optional[PluginDescriptor] = None):
        """Delegates the creation of a new node to the render graph."""
        self._render_graph.add_node(node, descriptor)

    def on_node_removed(self, node_id: str):
        """Delegates the removal of a node to the render graph."""
        self._render_graph.remove_node(node_id)

    def on_connection_added(self, connection: Connection):
        """Delegates the creation of a connection to the render graph."""
        self._render_graph.add_connection(connection)

    def on_connection_removed(self, connection: Connection):
        """Delegates the removal of a connection to the render graph."""
        # Note: We would need to add a 'remove_connection' method to the render graph.
        # self._render_graph.remove_connection(connection)
        pass  # Placeholder for now

    # --- High-Level, Composite Operations (Delegation) ---

    def on_insert_plugin_added_to_track(self, track: ITrack, plugin: IPlugin,
                                        index: int):
        """
        Delegates the complex operation of adding an insert plugin to a track.
        """
        self._render_graph.add_insert_to_track(track.node_id, plugin, index)

    def on_insert_plugin_removed_from_track(self, track: ITrack,
                                            plugin: IPlugin):
        """
        Delegates the removal of an insert plugin. This is a high-level event
        that the render graph translates into specific connection changes.
        """
        # Note: This requires a corresponding high-level method on the render graph.
        # self._render_graph.remove_insert_from_track(track.node_id, plugin.node_id)
        # For now, a generic node removal is a simpler way to handle this.
        self._render_graph.remove_node(plugin.node_id)

    # --- Parameter and Data Operations (Delegation) ---

    def on_parameter_changed(self, node_id: str, param_name: str,
                             value: float):
        """Delegates a parameter change to the render graph."""
        self._render_graph.set_parameter(node_id, param_name, value)

    def on_notes_added(self, track_id: str, notes: List[Note]):
        """
        Delegates the addition of MIDI-like notes to the render graph.
        The render graph will format them for the audio thread.
        """
        # Note: We would need a corresponding method on the render graph for this.
        # self._render_graph.add_notes_to_instrument(track_id, notes)
        pass  # Placeholder for now
