# file: src/MuzaiCore/subsystems/commands/node_commands.py
from ...interfaces import ICommand, IProject, INode


class CreateTrackCommand(ICommand):

    def __init__(self, project: IProject, track: INode):
        self._project = project
        self._track = track
        self._track_id = track.node_id

    def execute(self) -> bool:
        try:
            self._project.add_node(self._track)
            print(f"Executed: Created track {self._track_id}")
            return True
        except ValueError:
            return False

    def undo(self) -> bool:
        try:
            self._project.remove_node(self._track_id)
            print(f"Undone: Removed track {self._track_id}")
            return True
        except ValueError:
            return False
