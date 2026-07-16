# RepoLens

RepoLens is a graph-first repository intelligence platform that helps engineers understand a codebase before changing it.

## Implemented capabilities

- Recursive Python, JavaScript, JSX, TypeScript, and TSX indexing
- Python AST extraction for classes, functions, methods, imports, calls, and inheritance
- Static JavaScript/TypeScript extraction for imports, functions, classes, calls, and inheritance
- Cross-file import and unambiguous symbol-call resolution
- Symbol search with source navigation
- Interactive dependency and symbol graph
- Reverse-dependency impact analysis, risk scoring, and connected-test recommendations
- Circular import detection and architecture coupling analysis
- True hash-based incremental re-indexing for added, modified, removed, and unchanged files
- Git hotspot and contributor analysis
- Background indexing jobs and WebSocket progress events
- JSON index snapshots for local durability
- PostgreSQL repository metadata persistence
- Neo4j graph persistence
- FastAPI REST API
- React/TypeScript/Cytoscape dashboard
- Docker Compose, automated tests, and GitHub Actions CI

## Run

PowerShell:

```powershell
$env:REPOLENS_SCAN_ROOT="C:\absolute\path\to\your\repository"
docker compose up --build
```

Linux/macOS:

```bash
REPOLENS_SCAN_ROOT=/absolute/path/to/your/repository docker compose up --build
```

Open `http://localhost:3000` and index `/repo`.

Services:

- UI: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- Neo4j Browser: `http://localhost:7474`
- PostgreSQL: internal Docker service on port 5432

## Tests

```bash
PYTHONPATH=backend pytest backend/tests -q
```

## Resume-safe description

**RepoLens — Repository Intelligence Platform**

Built a graph-first code intelligence platform using FastAPI, React, TypeScript, PostgreSQL, and Neo4j that indexes Python and JavaScript/TypeScript repositories, extracts symbols/imports/calls/inheritance, visualizes dependency graphs, performs incremental re-indexing, and computes change-impact radius, architecture risks, cycles, Git hotspots, and recommended tests.

## Honest limitations

RepoLens uses Python's built-in AST for Python and a static parser for JavaScript/TypeScript. The JS/TS parser is intentionally lightweight and is not a complete compiler frontend. Call resolution is confidence-scored and only promoted when unambiguous. Large enterprise monorepositories may require parser workers and batched Neo4j writes for maximum throughput.

