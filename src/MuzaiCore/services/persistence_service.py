# file: src/MuzaiCore/persistence/persistence_service.py
import json
from typing import Optional
from ..interfaces.service import IPersistenceService
from ..models import ProjectState


class PersistenceService(IPersistenceService):
    """
    Handles the low-level file I/O for saving and loading projects.
    It operates solely on ProjectState DTOs.
    """

    def save(self, state: ProjectState, file_path: str) -> None:
        """Serializes the ProjectState DTO to a JSON file."""
        import dataclasses
        try:
            # Convert the dataclass-heavy state object to a plain dictionary
            state_dict = dataclasses.asdict(state)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2)
            print(f"PersistenceService: Project state saved to {file_path}")

        except Exception as e:
            print(
                f"PersistenceService: Error saving project to {file_path}: {e}"
            )
            raise

    def load(self, file_path: str) -> Optional[ProjectState]:
        """Deserializes a ProjectState DTO from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)

            # Here you would need a robust way to reconstruct the dataclasses
            # from the dict, as dataclasses.from_dict is not a built-in function.
            # This is a simplification; a real app might use a library like `dacite`.

            # For now, we manually reconstruct the top-level object.
            # A full implementation would recursively reconstruct nested objects.
            state = ProjectState(**state_dict)  # Simplified reconstruction

            print(f"PersistenceService: Project state loaded from {file_path}")
            return state

        except FileNotFoundError:
            print(f"PersistenceService: Error - file not found at {file_path}")
            return None
        except Exception as e:
            print(
                f"PersistenceService: Error loading project from {file_path}: {e}"
            )
            raise
