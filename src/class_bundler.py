import ast
import os
import sys
import argparse
from collections import deque


def resolve_module_path(module_name, base_dir, project_root):
    """
    将模块名（如 'my_app.models' 或 '.utils'）解析为绝对文件路径。
    仅处理在 project_root 内的相对和绝对导入。
    """
    if not module_name:
        # e.g., from . import something
        # module_name can be empty for relative imports from __init__.py
        path_py = os.path.join(base_dir, '__init__.py')
        if os.path.isfile(path_py):
            return os.path.abspath(path_py)
        return None

    # 处理相对导入 (e.g., from . import models, from .. import utils)
    if module_name.startswith('.'):
        level = 0
        while module_name[level] == '.':
            level += 1

        module_name_parts = module_name[level:].split('.')

        # 计算基础路径
        current_dir = base_dir
        for _ in range(level - 1):
            current_dir = os.path.dirname(current_dir)

        if module_name_parts == ['']:  # from . import ...
            module_path_py = os.path.join(current_dir, '__init__.py')
        else:
            module_path_py = os.path.join(current_dir, *
                                          module_name_parts) + '.py'

        module_path_dir = os.path.join(current_dir, *module_name_parts)
    # 处理项目内的绝对导入 (e.g., from my_project.utils import ...)
    else:
        module_parts = module_name.split('.')
        module_path_py = os.path.join(project_root, *module_parts) + '.py'
        module_path_dir = os.path.join(project_root, *module_parts)

    # 检查文件或包（目录 + __init__.py）是否存在
    if os.path.isfile(module_path_py):
        return os.path.abspath(module_path_py)
    if os.path.isdir(module_path_dir) and os.path.isfile(
            os.path.join(module_path_dir, '__init__.py')):
        return os.path.abspath(os.path.join(module_path_dir, '__init__.py'))

    return None


class ClassVisitor(ast.NodeVisitor):
    """
    AST访问者，用于提取类定义、基类和导入信息。
    """

    def __init__(self, file_path, project_root):
        self.file_path = file_path
        self.project_root = project_root
        self.module_name = self.get_module_name(file_path, project_root)

        self.classes = {
        }  # { 'full.class.name': {'node': node, 'bases': [...]} }
        self.imports = {}  # { 'alias': 'full.module.name' }

    @staticmethod
    def get_module_name(file_path, project_root):
        """
        --- IMPROVEMENT ---
        将文件路径转换为 Python 模块名，正确处理 __init__.py。
        """
        rel_path = os.path.relpath(file_path, project_root)
        # 移除 .py 扩展名
        module_part, _ = os.path.splitext(rel_path)

        # 如果是 __init__.py, 模块名是其父目录
        if module_part.endswith(os.path.join('', '__init__')):
            module_part = os.path.dirname(module_part)

        # 将路径分隔符替换为点
        # 对于根目录下的 __init__.py，module_part 可能是空字符串，应返回空
        if not module_part or module_part == '.':
            return ""
        return module_part.replace(os.sep, '.')

    def visit_ClassDef(self, node):
        base_names = [ast.unparse(base) for base in node.bases]

        full_class_name = f"{self.module_name}.{node.name}" if self.module_name else node.name

        self.classes[full_class_name] = {
            'node': node,
            'source': ast.get_source_segment(self.source_code, node),
            'bases': base_names,
            'file_path': self.file_path
        }
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """
        --- IMPROVEMENT ---
        更稳健地处理相对导入。
        """
        module_str = node.module or ''

        if node.level > 0:  # 相对导入
            # 计算基础模块路径
            base_parts = self.module_name.split('.')
            # 如果当前文件是包（__init__.py），其模块名不包含文件名部分
            # 如果是普通模块，需要去掉最后一个部分来获取目录
            if not self.file_path.endswith('__init__.py'):
                base_parts = base_parts[:-1]

            # 根据 '..' 的数量上溯
            if node.level > 1:
                base_parts = base_parts[:-(node.level - 1)]

            # 组合成最终的模块路径
            if module_str:
                base_parts.append(module_str)

            final_module = '.'.join(base_parts)
        else:  # 绝对导入
            final_module = module_str

        for alias in node.names:
            # 导入的具体项可以是模块也可以是类/函数等
            # 我们将别名映射到可能的完整路径
            # 例如 from a.b import c -> imports['c'] = 'a.b.c'
            full_name = f"{final_module}.{alias.name}" if final_module else alias.name
            self.imports[alias.asname or alias.name] = full_name
        self.generic_visit(node)

    def parse(self, source_code):
        self.source_code = source_code
        tree = ast.parse(source_code)
        self.visit(tree)


def topological_sort(dependency_graph):
    """对依赖图进行拓扑排序。"""
    in_degree = {u: 0 for u in dependency_graph}
    # 建立反向图以快速查找依赖者
    reverse_graph = {u: [] for u in dependency_graph}

    for u, dependencies in dependency_graph.items():
        for v in dependencies:
            if v in in_degree:
                in_degree[u] += 1
                reverse_graph[v].append(u)

    queue = deque([u for u, deg in in_degree.items() if deg == 0])
    sorted_list = []

    while queue:
        u = queue.popleft()
        sorted_list.append(u)

        for v in reverse_graph.get(u, []):
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    if len(sorted_list) != len(dependency_graph):
        cycle_nodes = sorted(
            list(set(dependency_graph.keys()) - set(sorted_list)))
        raise RuntimeError(f"检测到循环依赖，无法排序。\n"
                           f"可能是这些类之间存在循环继承: {cycle_nodes}")
    return sorted_list


def main():
    parser = argparse.ArgumentParser(
        description="将一个 Python 文件及其所有项目内依赖的类打包到一个文件中。",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("entry_file", help="作为入口的 Python 文件路径。")
    parser.add_argument("-o", "--output", required=True, help="输出文件的路径。")
    parser.add_argument("-p",
                        "--project-root",
                        default=".",
                        help="项目根目录，用于解析绝对导入和区分项目内/外代码。\n默认为当前目录。")
    args = parser.parse_args()

    entry_file = os.path.abspath(args.entry_file)
    project_root = os.path.abspath(args.project_root)
    output_file = args.output

    if not os.path.isfile(entry_file):
        print(f"错误: 入口文件不存在 '{entry_file}'")
        sys.exit(1)
    if not entry_file.startswith(project_root):
        print(f"错误: 入口文件必须在项目根目录内。\n  入口: {entry_file}\n  根目录: {project_root}")
        sys.exit(1)

    # --- 1. 发现和解析阶段 ---
    files_to_process = deque([entry_file])
    processed_files = set()
    all_classes = {}  # { 'full.class.name': {'source': ..., 'bases': [...]} }
    all_imports = {}  # { 'file/path.py': {'alias': 'full.name'} }

    print("开始分析文件依赖...")
    while files_to_process:
        current_file = files_to_process.popleft()
        if current_file in processed_files:
            continue

        processed_files.add(current_file)
        print(f"  - 正在处理: {os.path.relpath(current_file, project_root)}")

        try:
            with open(current_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            print(f"警告: 无法读取文件 {current_file}: {e}")
            continue

        visitor = ClassVisitor(current_file, project_root)
        try:
            visitor.parse(source_code)
        except SyntaxError as e:
            print(f"警告: 文件 {current_file} 存在语法错误，已跳过: {e}")
            continue

        all_classes.update(visitor.classes)
        all_imports[current_file] = visitor.imports

        # 将新发现的项目内文件加入处理队列
        file_dir = os.path.dirname(current_file)
        # 扫描所有导入语句（包括导入模块和从模块导入成员）
        combined_imports = set(visitor.imports.values())
        # 对于 from a.b import C, 我们需要解析 a.b 模块
        for imp_path in visitor.imports.values():
            parts = imp_path.split('.')
            for i in range(1, len(parts)):
                combined_imports.add('.'.join(parts[:i]))

        for full_module_name in combined_imports:
            module_path = resolve_module_path(full_module_name, file_dir,
                                              project_root)
            if module_path and module_path.startswith(
                    project_root) and module_path not in processed_files:
                files_to_process.append(module_path)

    print(f"\n分析完成。共找到 {len(all_classes)} 个类定义。")

    # --- 2. 构建依赖图 ---
    print("正在构建类继承依赖图...")
    dependency_graph = {name: set() for name in all_classes}

    for class_name, info in all_classes.items():
        file_path = info['file_path']
        imports_in_file = all_imports.get(file_path, {})
        current_module_name = ClassVisitor.get_module_name(
            file_path, project_root)

        for base_name_str in info['bases']:
            # 可能性 1: 基类是内建类型 (e.g., object)
            if hasattr(__builtins__, base_name_str):
                continue

            # --- IMPROVEMENT: 更可靠的基类解析 ---
            resolved_base_name = None
            # 可能性 2: 基类是通过别名导入的 (e.g., from a.b import C as D, class MyClass(D):)
            if base_name_str in imports_in_file and imports_in_file[
                    base_name_str] in all_classes:
                resolved_base_name = imports_in_file[base_name_str]
            # 可能性 3: 基类是 'module.Class' 形式，其中 module 是导入的别名
            elif '.' in base_name_str:
                alias = base_name_str.split('.')[0]
                if alias in imports_in_file:
                    # e.g., import a.b as ab; class MyClass(ab.C):
                    # base_name_str = "ab.C", alias = "ab", imports_in_file[alias] = "a.b"
                    # resolved_name = "a.b.C"
                    full_prefix = imports_in_file[alias]
                    rest = '.'.join(base_name_str.split('.')[1:])
                    potential_name = f"{full_prefix}.{rest}"
                    if potential_name in all_classes:
                        resolved_base_name = potential_name

            # 可能性 4: 基类在当前文件中定义
            if not resolved_base_name:
                potential_name = f"{current_module_name}.{base_name_str}" if current_module_name else base_name_str
                if potential_name in all_classes:
                    resolved_base_name = potential_name

            if resolved_base_name and resolved_base_name in all_classes:
                dependency_graph[class_name].add(resolved_base_name)
            else:
                print(
                    f"警告: 无法解析类 '{class_name}' 的基类 '{base_name_str}'。可能来自外部库或未被追踪。"
                )

    # --- 3. 拓扑排序 ---
    print("正在对类进行拓扑排序...")
    try:
        sorted_classes = topological_sort(dependency_graph)
    except RuntimeError as e:
        print(f"错误: {e}")
        sys.exit(1)
    print("排序完成。")

    # --- 4. 生成输出文件 ---
    print(f"正在写入到输出文件: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# -*- coding: utf-8 -*-\n")
        f.write("# This file is auto-generated by class_bundler.py\n")
        f.write("# --------------------------------------------------\n\n")

        for class_name in sorted_classes:
            info = all_classes[class_name]
            f.write(
                f"# Source from: {os.path.relpath(info['file_path'], project_root)}\n"
            )
            f.write(info['source'])
            f.write("\n\n")

    print(f"\n任务完成！输出文件已生成: {output_file}")


if __name__ == "__main__":
    main()
