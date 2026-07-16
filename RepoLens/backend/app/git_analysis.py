from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path


class GitAnalysis:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _run(self, *args: str) -> str:
        if not (self.root / ".git").exists():
            return ""
        try:
            return subprocess.check_output(
                ["git", *args],
                cwd=self.root,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
        except (subprocess.SubprocessError, OSError):
            return ""

    def hotspots(self, limit: int = 20) -> list[dict[str, int | str]]:
        output = self._run("log", "--name-only", "--pretty=format:")
        counts = Counter(line.strip() for line in output.splitlines() if line.strip())
        return [
            {"file": file, "changes": changes}
            for file, changes in counts.most_common(max(1, min(limit, 200)))
        ]

    def contributors(self, limit: int = 20) -> list[dict[str, int | str]]:
        output = self._run("shortlog", "-sne", "HEAD")
        rows = []
        for line in output.splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) != 2:
                continue
            try:
                rows.append({"author": parts[1], "commits": int(parts[0])})
            except ValueError:
                continue
        return rows[: max(1, min(limit, 200))]
