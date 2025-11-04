from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field

import inspect
from functools import wraps
from ..facade import DAWFacade
from ..models import ToolResponse


def tool(
    category: str,
    description: str = "",
    returns: str = "",
    examples: Optional[List[str]] = None,
):

    def decorator(func: Callable) -> Callable:

        sig = inspect.signature(func)
        params = []

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            param_type = _infer_type(param.annotation)

            param_desc = _extract_param_description(func, param_name)

            params.append(
                ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=param_desc,
                    required=param.default == inspect.Parameter.empty,
                    default=param.default
                    if param.default != inspect.Parameter.empty else None))

        func._tool_metadata = {
            'category':
            category,
            'description':
            description or (inspect.getdoc(func) or "").split('\n')[0],
            'parameters':
            params,
            'returns':
            returns or _infer_return_description(func),
            'examples':
            examples or []
        }

        return func

    return decorator


def _infer_type(annotation) -> str:

    if annotation == str or annotation == 'str':
        return "string"
    elif annotation in (int, float) or annotation in ('int', 'float'):
        return "number"
    elif annotation == bool or annotation == 'bool':
        return "boolean"
    elif annotation == list or annotation == 'list':
        return "array"
    elif annotation == dict or annotation == 'dict':
        return "object"
    return "string"  # 默认


def _extract_param_description(func: Callable, param_name: str) -> str:

    doc = inspect.getdoc(func) or ""
    lines = doc.split('\n')

    in_args_section = False
    for line in lines:
        if 'Args:' in line or 'Parameters:' in line:
            in_args_section = True
            continue

        if in_args_section:
            if line.strip().startswith(param_name + ':'):
                return line.split(':', 1)[1].strip()
            elif not line.strip() or line.strip().startswith('Returns:'):
                break

    return f"The {param_name} parameter"


def _infer_return_description(func: Callable) -> str:

    doc = inspect.getdoc(func) or ""
    lines = doc.split('\n')

    in_returns_section = False
    result = []

    for line in lines:
        if 'Returns:' in line:
            in_returns_section = True
            continue

        if in_returns_section:
            if line.strip() and not line.strip().startswith(
                ('Args:', 'Raises:')):
                result.append(line.strip())
            else:
                break

    return ' '.join(result) or "Operation result"


@dataclass
class ToolParameter:

    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def to_json_schema(self) -> Dict:
        """转换为JSON Schema"""
        schema = {"type": self.type, "description": self.description}
        if self.enum:
            schema["enum"] = self.enum
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        return schema


@dataclass
class Tool:

    name: str
    category: str
    description: str
    parameters: List[ToolParameter]
    returns: str
    examples: List[str] = field(default_factory=list)
    function: Optional[Callable] = None

    def to_openai_function(self) -> Dict:

        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

    def to_anthropic_tool(self) -> Dict:

        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


class AgentToolkit:

    def __init__(self, facade: DAWFacade):
        self._facade = facade
        self._tools: Dict[str, Tool] = {}
        self._execution_log: List[Dict] = []
        self._auto_register_tools()

    def _auto_register_tools(self):

        for service_name, service in self._facade._services.items():

            for method_name, method in inspect.getmembers(
                    service, inspect.ismethod):

                if method_name.startswith('_'):
                    continue

                if hasattr(method, '_tool_metadata'):

                    metadata = method._tool_metadata
                    tool_func = self._create_tool_wrapper(
                        service_name,
                        method_name,
                        method,
                    )

                    tool = Tool(name=f"{service_name}.{method_name}",
                                category=metadata['category'],
                                description=metadata['description'],
                                parameters=metadata['parameters'],
                                returns=metadata['returns'],
                                examples=metadata['examples'],
                                function=tool_func)

                    self._tools[tool.name] = tool

    def _create_tool_wrapper(self, service_name: str, method_name: str,
                             method: Callable) -> Callable:
        """创建工具包装函数,处理上下文注入和错误"""

        @wraps(method)
        def wrapper(**kwargs) -> ToolResponse:
            try:

                self._log_execution(f"{service_name}.{method_name}", kwargs)

                result = self._facade.execute_tool(
                    f"{service_name}.{method_name}", **kwargs)
                self._log_result(result)
                return result

            except Exception as e:
                error_msg = f"Error executing {service_name}.{method_name}: {str(e)}"
                self._log_error(error_msg)
                return ToolResponse("error", None, error_msg)

        return wrapper

    def _log_execution(self, tool_name: str, params: Dict):

        self._execution_log.append({
            'type': 'execution',
            'tool': tool_name,
            'params': params,
            'timestamp': self._get_timestamp()
        })

    def _log_result(self, result: ToolResponse):

        self._execution_log.append({
            'type': 'result',
            'status': result.status,
            'data': result.data,
            'message': result.message,
            'timestamp': self._get_timestamp()
        })

    def _log_error(self, error_msg: str):

        self._execution_log.append({
            'type': 'error',
            'message': error_msg,
            'timestamp': self._get_timestamp()
        })

    def _get_timestamp(self) -> str:

        from datetime import datetime
        return datetime.now().isoformat()

    def get_tool(self, name: str) -> Optional[Tool]:

        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[Tool]:

        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def execute(self, tool_name: str, **kwargs) -> ToolResponse:

        tool = self.get_tool(tool_name)

        if not tool:
            return ToolResponse("error", None, f"Tool '{tool_name}' not found")

        return tool.function(**kwargs)

    def execute_chain(self, chain: List[Dict[str, Any]]) -> List[ToolResponse]:

        results = []
        context = {}

        for step in chain:
            tool_name = step.get('tool')
            params = step.get('params', {})

            params = self._resolve_references(params, results)

            result = self.execute(tool_name, **params)
            results.append(result)

            if result.status == 'error' and not step.get(
                    'continue_on_error', False):
                break

        return results

    def _resolve_references(self, params: Dict,
                            previous_results: List[ToolResponse]) -> Dict:

        resolved = {}

        for key, value in params.items():
            if isinstance(value, str) and value.startswith('$result'):

                try:
                    parts = value.replace('$result[',
                                          '').replace(']', '.').split('.')
                    index = int(parts[0])
                    result = previous_results[index]

                    data = result
                    for part in parts[1:]:
                        if part:
                            data = getattr(data, part) if hasattr(
                                data, part) else data.get(part)

                    resolved[key] = data
                except:
                    resolved[key] = value
            else:
                resolved[key] = value

        return resolved

    def get_execution_log(self) -> List[Dict]:

        return self._execution_log.copy()

    def clear_log(self):

        self._execution_log.clear()

    def export_tools(self, format: str = 'openai') -> List[Dict]:

        if format == 'openai':
            return [tool.to_openai_function() for tool in self._tools.values()]
        elif format == 'anthropic':
            return [tool.to_anthropic_tool() for tool in self._tools.values()]
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_documentation(self, tool_name: Optional[str] = None) -> str:
        """获取文档"""
        if tool_name:
            tool = self.get_tool(tool_name)
            if not tool:
                return f"Tool '{tool_name}' not found"
            return self._format_tool_doc(tool)

        # 返回所有工具的文档
        doc = "=== Echos Agent Toolkit ===\n\n"

        categories = {}
        for tool in self._tools.values():
            if tool.category not in categories:
                categories[tool.category] = []
            categories[tool.category].append(tool)

        for category, tools in sorted(categories.items()):
            doc += f"\n## {category.upper()}\n"
            doc += "=" * 50 + "\n\n"

            for tool in tools:
                doc += self._format_tool_doc(tool)
                doc += "\n" + "-" * 50 + "\n\n"

        return doc

    def _format_tool_doc(self, tool: Tool) -> str:
        """格式化工具文档"""
        doc = f"Tool: {tool.name}\n"
        doc += f"Description: {tool.description}\n\n"
        doc += "Parameters:\n"

        for param in tool.parameters:
            req = "(required)" if param.required else "(optional)"
            doc += f"  - {param.name} ({param.type}) {req}: {param.description}\n"

            if param.default is not None:
                doc += f"    Default: {param.default}\n"
            if param.enum:
                doc += f"    Options: {param.enum}\n"

        doc += f"\nReturns: {tool.returns}\n"

        if tool.examples:
            doc += "\nExamples:\n"
            for example in tool.examples:
                doc += f"  {example}\n"

        return doc
