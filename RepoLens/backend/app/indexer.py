from __future__ import annotations
import hashlib
from pathlib import Path
from .models import RepositoryIndex, FileRecord, Edge
from .parsers import parse_python, parse_javascript

EXT = {".py":"python",".js":"javascript",".jsx":"javascript",".ts":"typescript",".tsx":"typescript"}
SKIP = {".git","node_modules",".venv","venv","dist","build","__pycache__",".next","coverage",".repolens"}

class RepositoryIndexer:
    def __init__(self, max_bytes: int = 1_000_000):
        self.max_bytes = max_bytes

    def index(self, root: str) -> RepositoryIndex:
        return self.incremental(root, None)[0]

    def incremental(self, root: str, previous: RepositoryIndex | None) -> tuple[RepositoryIndex, dict]:
        base = Path(root).resolve()
        if not base.exists() or not base.is_dir():
            raise ValueError("Repository path must be an existing directory")

        current_files: dict[str, Path] = {}
        hashes: dict[str, tuple[bytes, str]] = {}
        warnings: list[str] = []

        for path in sorted(base.rglob("*")):
            if not path.is_file() or any(part in SKIP for part in path.parts):
                continue
            if path.suffix.lower() not in EXT:
                continue
            rel = path.relative_to(base).as_posix()
            if path.stat().st_size > self.max_bytes:
                warnings.append(f"Skipped oversized file: {rel}")
                continue
            try:
                raw = path.read_bytes()
            except OSError as exc:
                warnings.append(f"Could not read {rel}: {exc}")
                continue
            digest = hashlib.sha256(raw).hexdigest()
            current_files[rel] = path
            hashes[rel] = (raw, digest)

        previous_files = set(previous.files) if previous else set()
        current_names = set(current_files)
        removed = sorted(previous_files - current_names)
        added = sorted(current_names - previous_files)
        modified = sorted(
            rel for rel in current_names & previous_files
            if previous and previous.files[rel].sha256 != hashes[rel][1]
        )
        unchanged = sorted(current_names - set(added) - set(modified))

        idx = RepositoryIndex(str(base))
        idx.warnings = list(warnings)

        if previous:
            for rel in unchanged:
                idx.files[rel] = previous.files[rel]
                for sid in previous.files[rel].symbols:
                    if sid in previous.symbols:
                        idx.symbols[sid] = previous.symbols[sid]
            unchanged_set = set(unchanged)
            idx.edges.extend([
                e for e in previous.edges
                if self._edge_file(e.source) in unchanged_set
                and self._edge_file(e.target) in unchanged_set
            ])

        for rel in [*added, *modified]:
            raw, digest = hashes[rel]
            path = current_files[rel]
            language = EXT[path.suffix.lower()]
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                idx.warnings.append(f"Could not decode {rel}: {exc}")
                continue
            record = FileRecord(rel, language, len(raw), digest, text.count("\n") + 1)
            try:
                symbols, edges, imports = (
                    parse_python(text, rel) if language == "python"
                    else parse_javascript(text, rel, language)
                )
            except SyntaxError as exc:
                idx.warnings.append(f"Parse error in {rel}:{exc.lineno}")
                symbols, edges, imports = [], [], []
            for symbol in symbols:
                idx.symbols[symbol.id] = symbol
                record.symbols.append(symbol.id)
            record.imports = imports
            idx.files[rel] = record
            idx.edges.extend(edges)

        self._resolve(idx)
        change_set = {
            "added": added,
            "modified": modified,
            "removed": removed,
            "unchanged": len(unchanged),
            "reindexed": len(added) + len(modified),
        }
        return idx, change_set

    def _resolve(self, idx: RepositoryIndex):
        module_map: dict[str, str] = {}
        for path in idx.files:
            module = self._module_name(path)
            module_map[module] = path
            module_map[module.replace(".", "/")] = path
            module_map[Path(path).stem] = path

        names: dict[str, list[str]] = {}
        for sid, symbol in idx.symbols.items():
            names.setdefault(symbol.name, []).append(sid)

        filtered = [e for e in idx.edges if e.kind != "imports"]
        idx.edges = filtered
        for path, record in idx.files.items():
            for imported in record.imports:
                candidates = [
                    imported,
                    imported.replace(".", "/"),
                    imported.split(".")[-1],
                ]
                target = next((module_map.get(c) for c in candidates if module_map.get(c)), None)
                if target:
                    idx.edges.append(Edge(path, target, "imports", imported, 0.96))

        for edge in idx.edges:
            if edge.target.startswith("name::"):
                candidates = names.get(edge.target[6:], [])
                if len(candidates) == 1:
                    edge.target = candidates[0]
                    edge.confidence = max(edge.confidence, 0.86)

    @staticmethod
    def _module_name(path: str) -> str:
        p = Path(path)
        parts = list(p.with_suffix("").parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    @staticmethod
    def _edge_file(node: str) -> str | None:
        if "::" in node:
            return node.split("::", 1)[0]
        if ":" in node:
            return node.split(":", 1)[0]
        return node if "." in node or "/" in node else None
