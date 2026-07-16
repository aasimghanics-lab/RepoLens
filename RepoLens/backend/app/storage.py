from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import Edge, FileRecord, RepositoryIndex, Symbol


class IndexStore:
    """Small JSON persistence layer for local RepoLens indexes."""

    def __init__(self, directory: str | Path = ".repolens/indexes"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, repository_id: str, index: RepositoryIndex) -> Path:
        path = self.directory / f"{repository_id}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(index.to_dict(), indent=2), encoding="utf-8")
        tmp.replace(path)
        return path

    def load(self, repository_id: str) -> RepositoryIndex | None:
        path = self.directory / f"{repository_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        index = RepositoryIndex(root=data["root"])
        index.files = {k: FileRecord(**v) for k, v in data.get("files", {}).items()}
        index.symbols = {k: Symbol(**v) for k, v in data.get("symbols", {}).items()}
        index.edges = [Edge(**e) for e in data.get("edges", [])]
        index.warnings = list(data.get("warnings", []))
        return index

    def delete(self, repository_id: str) -> bool:
        path = self.directory / f"{repository_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_ids(self) -> list[str]:
        return sorted(p.stem for p in self.directory.glob("*.json"))
