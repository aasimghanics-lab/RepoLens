from __future__ import annotations
from collections import defaultdict, deque

class GraphAnalysis:
    def __init__(self, index):
        self.index = index
        self.forward = defaultdict(set)
        self.reverse = defaultdict(set)
        for edge in index.edges:
            self.forward[edge.source].add(edge.target)
            self.reverse[edge.target].add(edge.source)

    def search(self, query, limit=50):
        query = query.lower().strip()
        output = []
        for symbol in self.index.symbols.values():
            score = (
                5 if symbol.name.lower() == query
                else 3 if symbol.name.lower().startswith(query)
                else 2 if query in symbol.name.lower()
                else 1 if query in symbol.qualified_name.lower()
                else 0
            )
            if score:
                output.append((score, symbol))
        output.sort(key=lambda row: (-row[0], row[1].qualified_name))
        return [symbol.__dict__ for _, symbol in output[:limit]]

    def impact(self, node, max_depth=5):
        seen = {node}
        queue = deque([(node, 0)])
        levels = defaultdict(list)
        while queue:
            current, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for nxt in sorted(self.reverse.get(current, ())):
                if nxt not in seen:
                    seen.add(nxt)
                    levels[depth + 1].append(nxt)
                    queue.append((nxt, depth + 1))
        files = sorted({f for item in seen if (f := self._file(item))})
        tests = sorted({
            path for path in self.index.files
            if ("test" in path.lower() or "spec" in path.lower())
            and any(Pathish(path).stem in impacted for impacted in files)
        })
        direct = len(levels.get(1, []))
        risk = min(100, 12 + len(seen) * 4 + direct * 8 + len(files) * 2)
        return {
            "source": node,
            "affected_nodes": sorted(seen - {node}),
            "affected_files": files,
            "recommended_tests": tests,
            "radius": max(levels.keys(), default=0),
            "risk_score": risk,
            "levels": dict(levels),
        }

    def cycles(self):
        graph = defaultdict(set)
        for edge in self.index.edges:
            if edge.kind == "imports" and edge.source in self.index.files and edge.target in self.index.files:
                graph[edge.source].add(edge.target)
        cycles = []
        state = {}
        stack = []

        def dfs(node):
            state[node] = 1
            stack.append(node)
            for nxt in graph[node]:
                if state.get(nxt) == 1:
                    i = stack.index(nxt)
                    cycle = stack[i:] + [nxt]
                    canonical = min(tuple(cycle[i:] + cycle[1:i+1]) for i in range(len(cycle)-1))
                    if list(canonical) not in cycles:
                        cycles.append(list(canonical))
                elif not state.get(nxt):
                    dfs(nxt)
            stack.pop()
            state[node] = 2

        for node in list(graph):
            if not state.get(node):
                dfs(node)
        return cycles

    def architecture(self):
        fan_in = {node: len(self.reverse.get(node, ())) for node in self.index.files}
        fan_out = {node: len(self.forward.get(node, ())) for node in self.index.files}
        hotspots = sorted(
            [
                {"file": node, "fan_in": fan_in[node], "fan_out": fan_out[node], "coupling": fan_in[node] + fan_out[node]}
                for node in self.index.files
            ],
            key=lambda row: (-row["coupling"], row["file"]),
        )
        inheritance = [e.__dict__ for e in self.index.edges if e.kind == "inherits"]
        return {"hotspots": hotspots[:25], "inheritance": inheritance, "cycles": self.cycles()}

    def metrics(self):
        languages = defaultdict(int)
        edge_types = defaultdict(int)
        for record in self.index.files.values():
            languages[record.language] += 1
        for edge in self.index.edges:
            edge_types[edge.kind] += 1
        return {
            "files": len(self.index.files),
            "symbols": len(self.index.symbols),
            "edges": len(self.index.edges),
            "languages": dict(languages),
            "edge_types": dict(edge_types),
            "cycles": len(self.cycles()),
            "warnings": len(self.index.warnings),
        }

    def _file(self, node):
        if node in self.index.files:
            return node
        if node in self.index.symbols:
            return self.index.symbols[node].file
        if "::" in node:
            return node.split("::", 1)[0]
        if ":" in node:
            return node.split(":", 1)[0]
        return None

class Pathish:
    def __init__(self, path): self.path = path
    @property
    def stem(self):
        name = self.path.rsplit("/", 1)[-1]
        return name.rsplit(".", 1)[0]
