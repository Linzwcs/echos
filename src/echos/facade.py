# file: src/MuzaiCore/services/facade.py
import inspect
from typing import Dict, List, Any, Optional
from .interfaces import IDAWManager, IService
from .models import ToolResponse, PluginDescriptor


class DAWFacade:

    def __init__(self, manager: IDAWManager, services: Dict[str, IService]):

        self._manager = manager
        self._services = services
        self._active_project_id: Optional[str] = None

        for name, service in self._services.items():
            if hasattr(self, name):

                raise AttributeError(
                    f"Service name '{name}' conflicts with an existing DAWFacade attribute."
                )
            setattr(self, name, service)

    def _get_active_project_id(self) -> str:

        if not self._active_project_id:
            raise ValueError(
                "No active project. Use 'project.create_project' and 'facade.set_active_project', "
                "or 'project.load_project' and 'facade.set_active_project' first."
            )
        if not self._manager.get_project(self._active_project_id):
            raise ValueError(
                f"Active project '{self._active_project_id}' no longer exists."
            )
        return self._active_project_id

    def set_active_project(self, project_id: str) -> ToolResponse:

        if not self._manager.get_project(project_id):
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        self._active_project_id = project_id
        return ToolResponse(
            "success", {"active_project_id": project_id},
            f"Project '{project_id}' is now the active context.")

    def get_active_project(self) -> ToolResponse:

        try:
            project_id = self._get_active_project_id()
            project = self._manager.get_project(project_id)
            return ToolResponse(
                "success", {
                    "project_id": project_id,
                    "project_name": project.name
                },
                f"Current active project is '{project.name}' ({project_id}).")
        except ValueError as e:
            return ToolResponse("error", None, str(e))

    def list_tools(self) -> Dict[str, str]:

        descriptions = {}
        for name, service in self._services.items():
            doc = inspect.getdoc(service) or f"Tools for {name} operations."

            descriptions[name] = doc.split('\n')[0]
        return descriptions

    def list_plugins(self) -> str:
        return self._manager.plugin_registry.list_all()

    def get_available_methods(self) -> Dict[str, List[str]]:

        available_methods = {}
        for cat_name, service_obj in self._services.items():
            methods = []
            for name, method in inspect.getmembers(service_obj,
                                                   inspect.ismethod):

                if not name.startswith('_'):
                    try:
                        sig = str(inspect.signature(method))
                        methods.append(f"{name}{sig}")
                    except ValueError:

                        methods.append(f"{name}()")
            available_methods[cat_name] = sorted(methods)
        return available_methods

    def execute_tool(self, tool_name: str, **kwargs: Any) -> ToolResponse:
        try:
            if '.' not in tool_name:
                return ToolResponse(
                    "error", None,
                    f"Invalid tool name format: '{tool_name}'. Expected 'category.method'."
                )
            category, method = tool_name.split('.', 1)
            service = self._services.get(category)
            if not service:
                return ToolResponse("error", None,
                                    f"Unknown service category: '{category}'")

            method_func = getattr(service, method, None)
            if not method_func or not callable(
                    method_func) or method.startswith('_'):
                return ToolResponse(
                    "error", None,
                    f"Unknown or private method: '{method}' in category '{category}'"
                )

            sig = inspect.signature(method_func)
            if 'project_id' in sig.parameters and 'project_id' not in kwargs:
                # Exclude specific methods like project creation/loading and system services
                if not (category == 'project' and method in ['create_project', 'load_project_from_state']) \
                   and not category == 'system':
                    kwargs['project_id'] = self._get_active_project_id()

            return method_func(**kwargs)

        except ValueError as e:
            return ToolResponse("error", None, str(e))
        except TypeError as e:
            return ToolResponse("error", None,
                                f"Invalid arguments for {tool_name}: {e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ToolResponse(
                "error", None,
                f"An unexpected error occurred while executing '{tool_name}': {str(e)}"
            )

    def get_help(self,
                 category: Optional[str] = None,
                 method: Optional[str] = None) -> ToolResponse:

        if not category:
            return ToolResponse(
                "success", {
                    "categories":
                    self.list_tools(),
                    "tip":
                    "Use get_help(category='name') for details on a specific category."
                }, "Available tool categories")

        if category not in self._services:
            return ToolResponse("error", None,
                                f"Unknown category: '{category}'")

        if not method:
            methods = self.get_available_methods().get(category, [])
            return ToolResponse(
                "success", {
                    "category":
                    category,
                    "description":
                    self.list_tools().get(category, ""),
                    "methods":
                    methods,
                    "tip":
                    f"Use get_help(category='{category}', method='name') for details on a specific method."
                }, f"Available methods in '{category}'")

        service = self._services.get(category)
        method_func = getattr(service, method, None)
        if not method_func or not callable(method_func) or method.startswith(
                '_'):
            return ToolResponse(
                "error", None,
                f"Unknown or private method: '{method}' in '{category}'")

        doc = inspect.getdoc(method_func) or "No documentation available."
        signature = str(inspect.signature(method_func))

        return ToolResponse(
            "success", {
                "category": category,
                "method": method,
                "signature": f"{method}{signature}",
                "documentation": doc.strip()
            }, f"Details for {category}.{method}")

    def __repr__(self) -> str:
        active_project_info = f"active_project='{self._active_project_id}'" if self._active_project_id else "no_active_project"
        return f"DAWFacade(services={list(self._services.keys())}, {active_project_info})"
