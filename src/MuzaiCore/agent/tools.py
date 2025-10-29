from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import inspect

from ..facade import DAWFacade
from ..models import ToolResponse


class ToolCategory(Enum):
    """工具类别"""
    PROJECT = "project"  # 项目管理
    TRANSPORT = "transport"  # 播放控制
    NODES = "nodes"  # 节点管理
    ROUTING = "routing"  # 路由连接
    EDITING = "editing"  # 内容编辑
    MIXING = "mixing"  # 混音处理
    QUERY = "query"  # 状态查询
    SYSTEM = "system"  # 系统信息
    HISTORY = "history"  # 历史管理


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None

    def to_json_schema(self) -> Dict:
        """转换为JSON Schema格式（OpenAI Function Calling）"""
        schema = {"type": self.type, "description": self.description}

        if self.enum:
            schema["enum"] = self.enum

        if self.min_value is not None:
            schema["minimum"] = self.min_value

        if self.max_value is not None:
            schema["maximum"] = self.max_value

        if self.pattern:
            schema["pattern"] = self.pattern

        return schema


@dataclass
class Tool:
    """工具定义"""
    name: str
    category: ToolCategory
    description: str
    parameters: List[ToolParameter]
    returns: str  # 返回值描述
    examples: List[str] = field(default_factory=list)
    function: Optional[Callable] = None

    def to_openai_function(self) -> Dict:
        """
        转换为OpenAI Function Calling格式
        
        这样Agent可以直接使用
        """
        # 构建parameters schema
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
        """
        转换为Anthropic Tool格式
        
        Claude可以使用
        """
        # 构建input_schema
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

    def validate_parameters(
            self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证参数
        
        Returns:
            (is_valid, error_message)
        """
        for param_def in self.parameters:
            # 检查必需参数
            if param_def.required and param_def.name not in params:
                return False, f"Missing required parameter: {param_def.name}"

            if param_def.name in params:
                value = params[param_def.name]

                # 类型检查
                if param_def.type == "number" and not isinstance(
                        value, (int, float)):
                    return False, f"Parameter {param_def.name} must be a number"

                if param_def.type == "string" and not isinstance(value, str):
                    return False, f"Parameter {param_def.name} must be a string"

                if param_def.type == "boolean" and not isinstance(value, bool):
                    return False, f"Parameter {param_def.name} must be a boolean"

                if param_def.type == "array" and not isinstance(value, list):
                    return False, f"Parameter {param_def.name} must be an array"

                # 范围检查
                if param_def.type == "number":
                    if param_def.min_value is not None and value < param_def.min_value:
                        return False, f"Parameter {param_def.name} must be >= {param_def.min_value}"

                    if param_def.max_value is not None and value > param_def.max_value:
                        return False, f"Parameter {param_def.name} must be <= {param_def.max_value}"

                # 枚举检查
                if param_def.enum and value not in param_def.enum:
                    return False, f"Parameter {param_def.name} must be one of {param_def.enum}"

        return True, None

    def execute(self, **kwargs) -> ToolResponse:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResponse
        """
        # 验证参数
        is_valid, error = self.validate_parameters(kwargs)
        if not is_valid:
            return ToolResponse("error", None, error)

        # 执行函数
        if self.function:
            try:
                return self.function(**kwargs)
            except Exception as e:
                return ToolResponse("error", None,
                                    f"Tool execution failed: {str(e)}")

        return ToolResponse("error", None, "Tool function not implemented")


class AgentToolkit:
    """
    AI Agent工具包
    
    提供所有可用的工具，并管理工具的注册、发现和执行
    """

    def __init__(self, daw_facade: DAWFacade):
        """
        初始化工具包
        
        Args:
            daw_facade: DAW Facade实例
        """
        self._facade = daw_facade
        self._tools: Dict[str, Tool] = {}

        # 注册所有工具
        self._register_all_tools()

    def _register_all_tools(self):
        """注册所有工具"""
        # 项目管理工具
        self._register_project_tools()

        # 播放控制工具
        self._register_transport_tools()

        # 节点管理工具
        self._register_node_tools()

        # 路由工具
        self._register_routing_tools()

        # 编辑工具
        self._register_editing_tools()

        # 查询工具
        self._register_query_tools()

        # 系统工具
        self._register_system_tools()

        # 历史管理工具
        self._register_history_tools()

    # ========================================================================
    # 项目管理工具
    # ========================================================================

    def _register_project_tools(self):
        """注册项目管理工具"""

        # 创建项目
        self._tools["create_project"] = Tool(
            name="create_project",
            category=ToolCategory.PROJECT,
            description=
            "Create a new music project. This is always the first step.",
            parameters=[
                ToolParameter(name="name",
                              type="string",
                              description="The name of the project",
                              required=True)
            ],
            returns="Project ID and basic information",
            examples=[
                'create_project(name="My Song")',
                'create_project(name="Electronic Dance Track")'
            ],
            function=lambda name: self._facade.project.create_project(name))

        # 保存项目
        self._tools["save_project"] = Tool(
            name="save_project",
            category=ToolCategory.PROJECT,
            description="Save the project to a file",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="file_path",
                              type="string",
                              description=
                              "The file path to save to (e.g., 'my_song.mzc')",
                              required=True)
            ],
            returns="Success status",
            examples=[
                'save_project(project_id="abc123", file_path="song.mzc")'
            ],
            function=lambda project_id, file_path: self._facade.project.
            save_project(project_id, file_path))

        # 加载项目
        self._tools["load_project"] = Tool(
            name="load_project",
            category=ToolCategory.PROJECT,
            description="Load a project from a file",
            parameters=[
                ToolParameter(name="file_path",
                              type="string",
                              description="The file path to load from",
                              required=True)
            ],
            returns="Project ID and information",
            examples=['load_project(file_path="song.mzc")'],
            function=lambda file_path: self._facade.project.load_project(
                file_path))

    # ========================================================================
    # 播放控制工具
    # ========================================================================

    def _register_transport_tools(self):
        """注册播放控制工具"""

        # 播放
        self._tools["play"] = Tool(
            name="play",
            category=ToolCategory.TRANSPORT,
            description="Start playback of the project",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True)
            ],
            returns="Playback status",
            examples=['play(project_id="abc123")'],
            function=lambda project_id: self._facade.transport.play(project_id
                                                                    ))

        # 停止
        self._tools["stop"] = Tool(
            name="stop",
            category=ToolCategory.TRANSPORT,
            description="Stop playback",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True)
            ],
            returns="Playback status",
            examples=['stop(project_id="abc123")'],
            function=lambda project_id: self._facade.transport.stop(project_id
                                                                    ))

        # 设置速度
        self._tools["set_tempo"] = Tool(
            name="set_tempo",
            category=ToolCategory.TRANSPORT,
            description="Set the tempo (BPM) of the project",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="bpm",
                              type="number",
                              description="Tempo in beats per minute (BPM)",
                              required=True,
                              min_value=20.0,
                              max_value=300.0)
            ],
            returns="New tempo value",
            examples=[
                'set_tempo(project_id="abc123", bpm=120.0)',
                'set_tempo(project_id="abc123", bpm=140.0)'
            ],
            function=lambda project_id, bpm: self._facade.transport.set_tempo(
                project_id, bpm))

        # 设置拍号
        self._tools["set_time_signature"] = Tool(
            name="set_time_signature",
            category=ToolCategory.TRANSPORT,
            description="Set the time signature of the project",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(
                    name="numerator",
                    type="number",
                    description="Time signature numerator (beats per bar)",
                    required=True,
                    min_value=1,
                    max_value=16),
                ToolParameter(
                    name="denominator",
                    type="number",
                    description="Time signature denominator (note value)",
                    required=True,
                    enum=[2, 4, 8, 16])
            ],
            returns="New time signature",
            examples=[
                'set_time_signature(project_id="abc123", numerator=4, denominator=4)',
                'set_time_signature(project_id="abc123", numerator=3, denominator=4)'
            ],
            function=lambda project_id, numerator, denominator: self._facade.
            transport.set_time_signature(project_id, int(numerator),
                                         int(denominator)))

    # ========================================================================
    # 节点管理工具
    # ========================================================================

    def _register_node_tools(self):
        """注册节点管理工具"""

        # 创建乐器轨道
        self._tools["create_instrument_track"] = Tool(
            name="create_instrument_track",
            category=ToolCategory.NODES,
            description=
            "Create an instrument track for MIDI-based virtual instruments",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(
                    name="name",
                    type="string",
                    description=
                    "Name of the track (e.g., 'Lead Synth', 'Bass', 'Drums')",
                    required=True)
            ],
            returns="Track ID and information",
            examples=[
                'create_instrument_track(project_id="abc123", name="Lead Synth")',
                'create_instrument_track(project_id="abc123", name="Bass")'
            ],
            function=lambda project_id, name: self._facade.nodes.
            create_instrument_track(project_id, name))

        # 创建音频轨道
        self._tools["create_audio_track"] = Tool(
            name="create_audio_track",
            category=ToolCategory.NODES,
            description=
            "Create an audio track for recording or playing audio files",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="name",
                              type="string",
                              description="Name of the track",
                              required=True)
            ],
            returns="Track ID and information",
            examples=[
                'create_audio_track(project_id="abc123", name="Vocals")'
            ],
            function=lambda project_id, name: self._facade.nodes.
            create_audio_track(project_id, name))

        # 创建总线轨道
        self._tools["create_bus_track"] = Tool(
            name="create_bus_track",
            category=ToolCategory.NODES,
            description="Create a bus track for grouping and effects sends",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="name",
                              type="string",
                              description="Name of the bus",
                              required=True)
            ],
            returns="Bus ID and information",
            examples=[
                'create_bus_track(project_id="abc123", name="Reverb Send")'
            ],
            function=lambda project_id, name: self._facade.nodes.
            create_bus_track(project_id, name))

        # 添加插件
        self._tools["add_plugin"] = Tool(
            name="add_plugin",
            category=ToolCategory.NODES,
            description="Add a plugin (instrument or effect) to a track",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="track_id",
                              type="string",
                              description="The track ID to add the plugin to",
                              required=True),
                ToolParameter(
                    name="plugin_id",
                    type="string",
                    description=
                    "The unique plugin ID (use list_plugins to see available plugins)",
                    required=True)
            ],
            returns="Plugin instance ID",
            examples=[
                'add_plugin(project_id="abc123", track_id="track1", plugin_id="muzaicore.builtin.basic_synth")'
            ],
            function=lambda project_id, track_id, plugin_id: self._facade.nodes
            .add_insert_plugin(project_id, track_id, plugin_id))

        # 列出节点
        self._tools["list_nodes"] = Tool(
            name="list_nodes",
            category=ToolCategory.NODES,
            description="List all nodes (tracks) in the project",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True)
            ],
            returns="List of all nodes with their IDs and names",
            examples=['list_nodes(project_id="abc123")'],
            function=lambda project_id: self._facade.nodes.list_nodes(
                project_id))

    # ========================================================================
    # 路由工具
    # ========================================================================

    def _register_routing_tools(self):
        """注册路由工具"""

        # 创建发送
        self._tools["create_send"] = Tool(
            name="create_send",
            category=ToolCategory.ROUTING,
            description=
            "Create an effects send from one track to another (typically to a bus)",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="source_track_id",
                              type="string",
                              description="The source track ID",
                              required=True),
                ToolParameter(name="dest_bus_id",
                              type="string",
                              description="The destination bus ID",
                              required=True),
                ToolParameter(
                    name="post_fader",
                    type="boolean",
                    description=
                    "Whether the send is post-fader (after volume control)",
                    required=False,
                    default=True)
            ],
            returns="Send connection information",
            examples=[
                'create_send(project_id="abc123", source_track_id="track1", dest_bus_id="reverb_bus")'
            ],
            function=lambda project_id, source_track_id, dest_bus_id,
            post_fader=True: self._facade.routing.create_send(
                project_id, source_track_id, dest_bus_id, post_fader))

    # ========================================================================
    # 编辑工具
    # ========================================================================

    def _register_editing_tools(self):
        """注册编辑工具"""

        # 创建MIDI片段
        self._tools["create_midi_clip"] = Tool(
            name="create_midi_clip",
            category=ToolCategory.EDITING,
            description="Create a MIDI clip on a track to hold musical notes",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="track_id",
                              type="string",
                              description="The track ID",
                              required=True),
                ToolParameter(name="start_beat",
                              type="number",
                              description="Start position in beats",
                              required=True,
                              min_value=0.0),
                ToolParameter(name="duration_beats",
                              type="number",
                              description="Duration in beats",
                              required=True,
                              min_value=0.25),
                ToolParameter(name="name",
                              type="string",
                              description="Name of the clip",
                              required=False,
                              default="MIDI Clip")
            ],
            returns="Clip ID",
            examples=[
                'create_midi_clip(project_id="abc123", track_id="track1", start_beat=0.0, duration_beats=4.0, name="Pattern 1")'
            ],
            function=lambda project_id, track_id, start_beat, duration_beats,
            name="MIDI Clip": self._facade.editing.create_midi_clip(
                project_id, track_id, start_beat, duration_beats, name))

        # 添加音符
        self._tools["add_notes"] = Tool(
            name="add_notes",
            category=ToolCategory.EDITING,
            description="""Add MIDI notes to a clip. Each note is defined by:
- pitch: MIDI note number (0-127, middle C=60)
- velocity: How hard the note is played (0-127)
- start_beat: When the note starts (relative to clip start)
- duration_beats: How long the note lasts""",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="clip_id",
                              type="string",
                              description="The clip ID",
                              required=True),
                ToolParameter(
                    name="notes",
                    type="array",
                    description=
                    "Array of note objects, each with: pitch, velocity, start_beat, duration_beats",
                    required=True)
            ],
            returns="Number of notes added",
            examples=[
                '''add_notes(
    project_id="abc123",
    clip_id="clip1",
    notes=[
        {"pitch": 60, "velocity": 100, "start_beat": 0.0, "duration_beats": 1.0},
        {"pitch": 64, "velocity": 90, "start_beat": 1.0, "duration_beats": 1.0}
    ]
)'''
            ],
            function=lambda project_id, clip_id, notes: self._facade.editing.
            add_notes_to_clip(project_id, clip_id, notes))

        # 设置参数
        self._tools["set_parameter"] = Tool(
            name="set_parameter",
            category=ToolCategory.EDITING,
            description=
            "Set a parameter value on a track or plugin (e.g., volume, pan, plugin parameters)",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="node_id",
                              type="string",
                              description="The node (track/plugin) ID",
                              required=True),
                ToolParameter(
                    name="parameter_name",
                    type="string",
                    description=
                    "Name of the parameter (e.g., 'volume', 'pan', 'cutoff')",
                    required=True),
                ToolParameter(name="value",
                              type="number",
                              description="The parameter value",
                              required=True)
            ],
            returns="Confirmation",
            examples=[
                'set_parameter(project_id="abc123", node_id="track1", parameter_name="volume", value=-6.0)',
                'set_parameter(project_id="abc123", node_id="track1", parameter_name="pan", value=0.0)'
            ],
            function=lambda project_id, node_id, parameter_name,
            value: self._facade.editing.set_parameter_value(
                project_id, node_id, parameter_name, value))

        # 添加自动化点
        self._tools["add_automation"] = Tool(
            name="add_automation",
            category=ToolCategory.EDITING,
            description=
            "Add parameter automation (change parameter values over time)",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="node_id",
                              type="string",
                              description="The node ID",
                              required=True),
                ToolParameter(name="parameter_name",
                              type="string",
                              description="Name of the parameter",
                              required=True),
                ToolParameter(
                    name="beat",
                    type="number",
                    description="Beat position for the automation point",
                    required=True),
                ToolParameter(name="value",
                              type="number",
                              description="Parameter value at this point",
                              required=True)
            ],
            returns="Confirmation",
            examples=[
                'add_automation(project_id="abc123", node_id="track1", parameter_name="volume", beat=4.0, value=-3.0)'
            ],
            function=lambda project_id, node_id, parameter_name, beat,
            value: self._facade.editing.add_automation_point(
                project_id, node_id, parameter_name, beat, value))

    # ========================================================================
    # 查询工具
    # ========================================================================

    def _register_query_tools(self):
        """注册查询工具"""

        # 获取项目概览
        self._tools["get_project_overview"] = Tool(
            name="get_project_overview",
            category=ToolCategory.QUERY,
            description=
            "Get a high-level overview of the project (tempo, tracks, etc.)",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True)
            ],
            returns="Project overview information",
            examples=['get_project_overview(project_id="abc123")'],
            function=lambda project_id: self._facade.query.
            get_project_overview(project_id))

        # 获取节点详情
        self._tools["get_node_details"] = Tool(
            name="get_node_details",
            category=ToolCategory.QUERY,
            description=
            "Get detailed information about a specific node (track)",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True),
                ToolParameter(name="node_id",
                              type="string",
                              description="The node ID",
                              required=True)
            ],
            returns="Detailed node information",
            examples=[
                'get_node_details(project_id="abc123", node_id="track1")'
            ],
            function=lambda project_id, node_id: self._facade.query.
            get_node_details(project_id, node_id))

    # ========================================================================
    # 系统工具
    # ========================================================================

    def _register_system_tools(self):
        """注册系统工具"""

        # 列出插件
        self._tools["list_plugins"] = Tool(
            name="list_plugins",
            category=ToolCategory.SYSTEM,
            description="List all available plugins (instruments and effects)",
            parameters=[],
            returns="List of available plugins with their IDs",
            examples=['list_plugins()'],
            function=lambda: self._facade.system.list_available_plugins())

    # ========================================================================
    # 历史管理工具
    # ========================================================================

    def _register_history_tools(self):
        """注册历史管理工具"""

        # 撤销
        self._tools["undo"] = Tool(
            name="undo",
            category=ToolCategory.HISTORY,
            description="Undo the last action",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True)
            ],
            returns="Confirmation",
            examples=['undo(project_id="abc123")'],
            function=lambda project_id: self._facade.history.undo(project_id))

        # 重做
        self._tools["redo"] = Tool(
            name="redo",
            category=ToolCategory.HISTORY,
            description="Redo the previously undone action",
            parameters=[
                ToolParameter(name="project_id",
                              type="string",
                              description="The project ID",
                              required=True)
            ],
            returns="Confirmation",
            examples=['redo(project_id="abc123")'],
            function=lambda project_id: self._facade.history.redo(project_id))

    # ========================================================================
    # 工具管理方法
    # ========================================================================

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self,
                   category: Optional[ToolCategory] = None) -> List[Tool]:
        """
        列出所有工具
        
        Args:
            category: 可选的类别过滤
            
        Returns:
            工具列表
        """
        if category:
            return [t for t in self._tools.values() if t.category == category]
        return list(self._tools.values())

    def get_tools_for_openai(self) -> List[Dict]:
        """
        获取OpenAI Function Calling格式的工具列表
        
        Returns:
            OpenAI functions列表
        """
        return [tool.to_openai_function() for tool in self._tools.values()]

    def get_tools_for_anthropic(self) -> List[Dict]:
        """
        获取Anthropic Tool格式的工具列表
        
        Returns:
            Anthropic tools列表
        """
        return [tool.to_anthropic_tool() for tool in self._tools.values()]

    def execute_tool(self, tool_name: str, **kwargs) -> ToolResponse:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResponse
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResponse("error", None, f"Tool '{tool_name}' not found")

        return tool.execute(**kwargs)

    def get_tool_documentation(self, tool_name: str) -> Optional[str]:
        """
        获取工具的完整文档
        
        Args:
            tool_name: 工具名称
            
        Returns:
            文档字符串
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return None

        doc = f"Tool: {tool.name}\n"
        doc += f"Category: {tool.category.value}\n"
        doc += f"Description: {tool.description}\n\n"
        doc += "Parameters:\n"

        for param in tool.parameters:
            req_str = "(required)" if param.required else "(optional)"
            doc += f"  - {param.name} ({param.type}) {req_str}: {param.description}\n"

            if param.default is not None:
                doc += f"    Default: {param.default}\n"

            if param.enum:
                doc += f"    Options: {param.enum}\n"

            if param.min_value is not None or param.max_value is not None:
                range_str = f"    Range: "
                if param.min_value is not None:
                    range_str += f">= {param.min_value}"
                if param.max_value is not None:
                    if param.min_value is not None:
                        range_str += " and "
                    range_str += f"<= {param.max_value}"
                doc += range_str + "\n"

        doc += f"\nReturns: {tool.returns}\n"

        if tool.examples:
            doc += "\nExamples:\n"
            for example in tool.examples:
                doc += f"  {example}\n"

        return doc

    def get_all_documentation(self) -> str:
        """
        获取所有工具的文档
        
        Returns:
            完整文档字符串
        """
        doc = "=== MuzaiCore Agent Toolkit Documentation ===\n\n"

        for category in ToolCategory:
            tools = self.list_tools(category)
            if not tools:
                continue

            doc += f"\n## {category.value.upper()} TOOLS\n"
            doc += "=" * 50 + "\n\n"

            for tool in tools:
                doc += self.get_tool_documentation(tool.name)
                doc += "\n" + "-" * 50 + "\n\n"

        return doc
