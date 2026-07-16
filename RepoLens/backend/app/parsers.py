from __future__ import annotations
import ast
import re
from .models import Symbol, Edge

JS_DEF = re.compile(
    r'(?m)^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?'
    r'(?:function\s+([A-Za-z_$][\w$]*)|'
    r'class\s+([A-Za-z_$][\w$]*)(?:\s+extends\s+([A-Za-z_$][\w$]*))?|'
    r'(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>)'
)
JS_IMPORT = re.compile(
    r'(?:import\s+(?:[\s\S]*?)\s+from\s+|import\s*|require\s*\()\s*[\'"]([^\'"]+)'
)
JS_CALL = re.compile(r'\b([A-Za-z_$][\w$]*)\s*\(')

class PythonVisitor(ast.NodeVisitor):
    def __init__(self, rel: str):
        self.rel = rel
        self.stack: list[str] = []
        self.symbol_stack: list[str] = []
        self.symbols: list[Symbol] = []
        self.edges: list[Edge] = []
        self.imports: list[str] = []

    def _symbol(self, node: ast.AST, name: str, kind: str, signature: str = "") -> str:
        parent = ".".join(self.stack) or None
        qualified = ".".join([self.rel.replace("/", "."), *self.stack, name])
        sid = f"{self.rel}:{getattr(node, 'lineno', 1)}:{qualified}"
        self.symbols.append(
            Symbol(
                sid, name, qualified, kind, self.rel,
                getattr(node, "lineno", 1),
                getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                "python", parent, signature,
            )
        )
        if self.symbol_stack:
            self.edges.append(Edge(self.symbol_stack[-1], sid, "contains", f"line {getattr(node, 'lineno', 1)}"))
        return sid

    def visit_ClassDef(self, node: ast.ClassDef):
        sid = self._symbol(node, node.name, "class")
        for base in node.bases:
            if isinstance(base, ast.Name):
                target = base.id
            elif isinstance(base, ast.Attribute):
                parts = []
                cur = base
                while isinstance(cur, ast.Attribute):
                    parts.append(cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name):
                    parts.append(cur.id)
                target = ".".join(reversed(parts))
            else:
                target = ast.unparse(base) if hasattr(ast, "unparse") else "unknown"
            self.edges.append(Edge(sid, f"name::{target.split('.')[-1]}", "inherits", f"line {node.lineno}", 0.8))
        self.stack.append(node.name)
        self.symbol_stack.append(sid)
        self.generic_visit(node)
        self.symbol_stack.pop()
        self.stack.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        args = ", ".join(a.arg for a in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs])
        kind = "method" if self.stack else "function"
        sid = self._symbol(node, node.name, kind, args)
        self.stack.append(node.name)
        self.symbol_stack.append(sid)
        self.generic_visit(node)
        self.symbol_stack.pop()
        self.stack.pop()

    def visit_FunctionDef(self, node): self._visit_function(node)
    def visit_AsyncFunctionDef(self, node): self._visit_function(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)

    def visit_Call(self, node):
        name = None
        if isinstance(node.func, ast.Name):
            name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            name = node.func.attr
        if name:
            source = self.symbol_stack[-1] if self.symbol_stack else f"{self.rel}::<module>"
            self.edges.append(Edge(source, f"name::{name}", "calls", f"line {node.lineno}", 0.72))
        self.generic_visit(node)

def parse_python(text: str, rel: str):
    tree = ast.parse(text, filename=rel)
    visitor = PythonVisitor(rel)
    visitor.visit(tree)
    return visitor.symbols, visitor.edges, visitor.imports

def parse_javascript(text: str, rel: str, language: str):
    symbols: list[Symbol] = []
    edges: list[Edge] = []
    imports = JS_IMPORT.findall(text)
    known: dict[str, str] = {}

    for match in JS_DEF.finditer(text):
        function_name, class_name, parent_name, arrow_name = match.groups()
        name = function_name or class_name or arrow_name
        if not name:
            continue
        kind = "class" if class_name else "function"
        line = text.count("\n", 0, match.start()) + 1
        sid = f"{rel}:{line}:{name}"
        symbols.append(Symbol(sid, name, f"{rel.replace('/', '.')}.{name}", kind, rel, line, line, language))
        known[name] = sid
        if parent_name:
            edges.append(Edge(sid, f"name::{parent_name}", "inherits", f"line {line}", 0.8))

    for match in JS_CALL.finditer(text):
        name = match.group(1)
        if name in {"if", "for", "while", "switch", "catch", "function", "require", "return"}:
            continue
        line = text.count("\n", 0, match.start()) + 1
        edges.append(Edge(f"{rel}::<module>", known.get(name, f"name::{name}"), "calls", f"line {line}", 0.66))
    return symbols, edges, imports
