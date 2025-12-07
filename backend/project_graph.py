"""
project_graph.py — Project graph prototype for Tyme Frontier (Python)
Produces:
 - file import graph (directed)
 - symbol index (functions / classes -> files)
 - get_callers(fn_name)
 - find_implementations(interface_name)
 - impact_of_change(path) -> list of affected files
"""

import ast
import os
import json
from pathlib import Path
from collections import defaultdict

class ProjectGraph:
    def __init__(self, root="."):
        self.root = Path(root).resolve()
        self.files = []
        self.import_graph = defaultdict(set)   # file -> set(files it imports)
        self.symbol_index = defaultdict(set)   # symbol -> set(files that define it)
        self.call_index = defaultdict(set)     # function -> set(files that call it)
        self._scan()

    def _scan(self):
        for p in self.root.rglob("*.py"):
            if "venv" in p.parts or ".git" in p.parts:
                continue
            self.files.append(p)
            try:
                src = p.read_text(encoding="utf-8")
                tree = ast.parse(src)
                self._index_ast(p, tree)
            except Exception:
                continue

    def _index_ast(self, path, tree):
        module_name = str(path.relative_to(self.root))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    # heuristics: map import to file by name (best-effort)
                    self.import_graph[module_name].add(n.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for n in node.names:
                    name = f"{mod}.{n.name}" if mod else n.name
                    self.import_graph[module_name].add(name)
            elif isinstance(node, ast.FunctionDef):
                self.symbol_index[node.name].add(module_name)
                # find calls inside function
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        fn = self._get_call_name(sub.func)
                        if fn:
                            self.call_index[fn].add(module_name)
            elif isinstance(node, ast.ClassDef):
                self.symbol_index[node.name].add(module_name)
                # record methods
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef):
                        self.symbol_index[f"{node.name}.{sub.name}"].add(module_name)

    def _get_call_name(self, call_node):
        # return string name of call for indexing
        if isinstance(call_node, ast.Name):
            return call_node.id
        elif isinstance(call_node, ast.Attribute):
            return self._get_attribute_name(call_node)
        return None

    def _get_attribute_name(self, node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))

    def get_callers(self, fn_name):
        # callers = files that call fn_name
        return sorted(list(self.call_index.get(fn_name, [])))

    def find_implementations(self, interface_name):
        # naive: return files that define classes implementing name (heuristic)
        return sorted(list(self.symbol_index.get(interface_name, [])))

    def impact_of_change(self, path):
        # return files that depend on the given path (module)
        # map path to module-like key
        rel = str(Path(path).resolve().relative_to(self.root))
        impacted = set()
        # direct imports
        for f, imports in self.import_graph.items():
            if rel in imports or any(rel.endswith(f"__init__.py") and rel.startswith(i) for i in imports):
                impacted.add(f)
        # plus callers referencing symbols within the file
        for sym, files in self.symbol_index.items():
            for f in files:
                if f == rel:
                    # find callers of sym
                    callers = self.call_index.get(sym.split(".")[-1], set())
                    impacted.update(callers)
        return sorted(list(impacted))

    def dump(self, path="chronicle/project_graph.json"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        out = {
            "import_graph": {k: list(v) for k, v in self.import_graph.items()},
            "symbol_index": {k: list(v) for k, v in self.symbol_index.items()},
            "call_index": {k: list(v) for k, v in self.call_index.items()},
        }
        Path(path).write_text(json.dumps(out, indent=2))
        return path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Repo root")
    args = parser.parse_args()
    pg = ProjectGraph(root=args.root)
    print("Scanned files:", len(pg.files))
    print("Example callers for 'main':", pg.get_callers("main"))
    pg.dump()
    print("Wrote project graph to chronicle/project_graph.json")
