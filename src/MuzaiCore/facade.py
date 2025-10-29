# file: src/MuzaiCore/services/facade.py
import inspect
from typing import Dict, List, Any, Optional, Union

from .interfaces import IDAWManager, IService

from .models import ToolResponse


class DAWFacade:
    """
    AI Agent与DAW Core交互的单一统一入口点。
    提供按功能组织的、具备自省能力的动态工具集，并管理活动项目上下文。
    """

    def __init__(self, manager: IDAWManager, services: Dict[str, IService]):
        """
        初始化Facade，通过依赖注入接收所有服务实例。

        Args:
            manager: DAW管理器实例，用于项目查找。
            services: 一个将服务类别名称映射到其服务实例的字典。
                      例如: {'project': project_service, 'transport': transport_service}
        """
        self._manager = manager
        self._services = services
        self._active_project_id: Optional[str] = None

        for name, service in self._services.items():
            if hasattr(self, name):
                # 抛出错误或记录警告，以防止意外覆盖现有属性
                raise AttributeError(
                    f"Service name '{name}' conflicts with an existing DAWFacade attribute."
                )
            setattr(self, name, service)

    def _get_active_project_id(self) -> str:
        """
        内部辅助方法，获取当前活动项目的ID。如果未设置，则抛出异常。
        """
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
        """
        设置当前活动项目，后续的工具调用将默认作用于此项目。
        """
        if not self._manager.get_project(project_id):
            return ToolResponse("error", None,
                                f"Project '{project_id}' not found.")
        self._active_project_id = project_id
        return ToolResponse(
            "success", {"active_project_id": project_id},
            f"Project '{project_id}' is now the active context.")

    def get_active_project(self) -> ToolResponse:
        """
        获取当前活动项目的ID。
        """
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
        """
        返回可用工具类别的清单。
        """
        # 描述信息相对固定，可以硬编码或从服务类的文档字符串中动态提取
        descriptions = {}
        for name, service in self._services.items():
            doc = inspect.getdoc(service) or f"Tools for {name} operations."
            # 只取第一行作为简短描述
            descriptions[name] = doc.split('\n')[0]
        return descriptions

    def get_available_methods(self) -> Dict[str, List[str]]:
        """
        动态发现并返回每个服务类别下所有可用的公共方法及其签名。
        """
        available_methods = {}
        for cat_name, service_obj in self._services.items():
            methods = []
            for name, method in inspect.getmembers(service_obj,
                                                   inspect.ismethod):
                # 过滤掉私有方法 (以'_'开头)
                if not name.startswith('_'):
                    try:
                        sig = str(inspect.signature(method))
                        methods.append(f"{name}{sig}")
                    except ValueError:
                        # 某些内置方法可能没有可检查的签名
                        methods.append(f"{name}()")
            available_methods[cat_name] = sorted(methods)
        return available_methods

    def execute_tool(self, category: str, method: str,
                     **kwargs) -> ToolResponse:
        """
        通用工具执行器。
        它会自动将当前活动项目的ID注入到需要它的工具调用中。
        """
        try:
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

            # 自动注入 project_id (如果需要且未提供)
            # project.create_project 和 system 服务下的方法通常不需要 project_id
            if 'project_id' in sig.parameters and 'project_id' not in kwargs:
                # 仅在非项目创建/系统调用时注入
                if not (category == 'project' and method in ['create_project', 'load_project_from_state']) \
                   and not category == 'system':
                    kwargs['project_id'] = self._get_active_project_id()

            return method_func(**kwargs)

        except ValueError as e:  # 主要捕获 _get_active_project_id 的错误
            return ToolResponse("error", None, str(e))
        except TypeError as e:  # 捕获参数不匹配的错误
            return ToolResponse(
                "error", None,
                f"Invalid arguments for {category}.{method}: {e}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            return ToolResponse(
                "error", None, f"Tool execution failed unexpectedly: {str(e)}")

    def get_help(self,
                 category: Optional[str] = None,
                 method: Optional[str] = None) -> ToolResponse:
        """
        获取关于工具类别或特定方法的详细帮助信息。
        """
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
