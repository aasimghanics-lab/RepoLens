from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Literal

SymbolKind = Literal['module','class','function','method','variable']

@dataclass
class Symbol:
    id: str
    name: str
    qualified_name: str
    kind: SymbolKind
    file: str
    line: int
    end_line: int
    language: str
    parent: str | None = None
    signature: str = ''

@dataclass
class Edge:
    source: str
    target: str
    kind: Literal['imports','calls','inherits','contains']
    evidence: str = ''
    confidence: float = 1.0

@dataclass
class FileRecord:
    path: str
    language: str
    size: int
    sha256: str
    lines: int
    symbols: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

@dataclass
class RepositoryIndex:
    root: str
    files: dict[str, FileRecord] = field(default_factory=dict)
    symbols: dict[str, Symbol] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'root': self.root,
            'files': {k: asdict(v) for k,v in self.files.items()},
            'symbols': {k: asdict(v) for k,v in self.symbols.items()},
            'edges': [asdict(e) for e in self.edges],
            'warnings': self.warnings,
        }
