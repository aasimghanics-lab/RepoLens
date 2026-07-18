# RepoLens

> Graph-first repository intelligence for understanding unfamiliar codebases before making changes.

RepoLens is a developer tool that indexes a local repository, extracts symbols and relationships, builds a dependency graph, and estimates the downstream impact of code changes. It is designed to reduce the time engineers spend manually navigating large codebases.

---

# 🎥 Live Demo

**4-minute walkthrough**

https://loom.com/share/ca5f6f98c82d4089b59aebbce95cc3fb

The demo shows:

- Repository indexing
- Interactive dependency graph
- Impact analysis
- Architecture health
- Repository summary
- Incremental re-indexing

---

# Why RepoLens?

When joining a new project, engineers often spend hours tracing imports, dependencies, and architecture before safely making a change.

RepoLens automates much of that discovery by generating a graph-based representation of the repository and exposing structural insights through an interactive dashboard.

---

# Features

### Repository Analysis

- Recursive Python, JavaScript, JSX, TypeScript, and TSX indexing
- Cross-file symbol extraction
- Import and dependency analysis
- Interactive dependency graph
- Symbol search with source navigation

### Impact Analysis

- Reverse dependency traversal
- Change impact estimation
- Risk scoring
- Recommended test targets

### Architecture Intelligence

- Circular dependency detection
- Architecture coupling analysis
- Repository summary
- Git hotspots
- Contributor analysis

### Incremental Indexing

- Hash-based incremental re-indexing
- Added / modified / removed file detection
- Background indexing jobs
- WebSocket progress updates

### Persistence

- PostgreSQL repository metadata
- Neo4j graph persistence
- JSON snapshot storage

---

# Tech Stack

### Backend

- FastAPI
- Python
- PostgreSQL
- Neo4j

### Frontend

- React
- TypeScript
- Cytoscape.js

### Infrastructure

- Docker Compose
- GitHub Actions
- WebSockets

---

# Running RepoLens

### Windows

```powershell
$env:REPOLENS_SCAN_ROOT="C:\absolute\path\to\your\repository"
docker compose up --build
```

### Linux / macOS

```bash
REPOLENS_SCAN_ROOT=/absolute/path/to/your/repository docker compose up --build
```

Open

```
http://localhost:3000
```

Index

```
/repo
```

---

# Services

| Service | URL |
|---------|-----|
| UI | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |

---

# Testing

```bash
PYTHONPATH=backend pytest backend/tests -q
```

---

# Resume Description

**RepoLens — Repository Intelligence Platform**

Built a graph-first repository intelligence platform using FastAPI, React, TypeScript, PostgreSQL, and Neo4j that indexes Python and JavaScript/TypeScript repositories, extracts symbols and relationships, visualizes dependency graphs, performs incremental re-indexing, and estimates downstream change impact.

---

# Current Limitations

RepoLens currently uses Python's built-in AST for Python and a lightweight static parser for JavaScript/TypeScript.

Call resolution is confidence scored and promoted only when unambiguous.

Very large monorepositories would benefit from parser worker pools, batched graph persistence, and additional language frontends.
