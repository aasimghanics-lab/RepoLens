from __future__ import annotations
import asyncio
import os
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .indexer import RepositoryIndexer
from .analysis import GraphAnalysis
from .storage import IndexStore
from .git_analysis import GitAnalysis
from .persistence import PostgresMetadataStore, Neo4jGraphStore

VERSION = "1.0.0"
app = FastAPI(title="RepoLens", version=VERSION, description="Graph-first repository intelligence platform")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

INDEXES = {}
JOBS = {}
SUBS = set()
STORE = IndexStore(os.getenv("REPOLENS_INDEX_DIR", ".repolens/indexes"))
POSTGRES = PostgresMetadataStore()
NEO4J = Neo4jGraphStore()

class IndexRequest(BaseModel):
    path: str
    name: str | None = None

async def broadcast(message):
    dead = []
    for websocket in list(SUBS):
        try:
            await websocket.send_json(message)
        except Exception:
            dead.append(websocket)
    for websocket in dead:
        SUBS.discard(websocket)

@app.on_event("startup")
def startup():
    POSTGRES.initialize()

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": VERSION,
        "persistence": {
            "json": True,
            "postgres_configured": bool(os.getenv("DATABASE_URL")),
            "neo4j_configured": bool(os.getenv("NEO4J_URI")),
        },
    }

async def run_index(job_id: str, path: str, repository_id: str | None = None):
    try:
        JOBS[job_id].update(status="running", progress=10)
        await broadcast({"type":"index_progress","job_id":job_id,**JOBS[job_id]})
        previous = get(repository_id) if repository_id else None
        idx, changes = await asyncio.to_thread(RepositoryIndexer().incremental, path, previous)
        rid = repository_id or str(uuid.uuid4())
        INDEXES[rid] = idx
        STORE.save(rid, idx)
        analysis = GraphAnalysis(idx)
        metrics = analysis.metrics()
        postgres_saved = await asyncio.to_thread(POSTGRES.upsert, rid, idx, metrics)
        neo4j_saved = await asyncio.to_thread(NEO4J.save, rid, idx)
        JOBS[job_id].update(
            status="complete", progress=100, repository_id=rid,
            metrics=metrics, changes=changes,
            persistence={"postgres":postgres_saved,"neo4j":neo4j_saved,"json":True},
        )
    except Exception as exc:
        JOBS[job_id].update(status="failed", error=str(exc))
    await broadcast({"type":"index_progress","job_id":job_id,**JOBS[job_id]})

@app.post("/api/repositories/index")
async def create_index(req: IndexRequest):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status":"queued","progress":0,"path":req.path,"mode":"full"}
    asyncio.create_task(run_index(job_id, req.path))
    return {"job_id":job_id}

@app.post("/api/repositories/{rid}/reindex")
async def reindex(rid: str):
    idx = get(rid)
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status":"queued","progress":0,"path":idx.root,"mode":"incremental"}
    asyncio.create_task(run_index(job_id, idx.root, rid))
    return {"job_id":job_id}

@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(404, "Job not found")
    return JOBS[job_id]

@app.get("/api/repositories")
def repositories():
    for rid in STORE.list_ids():
        if rid not in INDEXES:
            loaded = STORE.load(rid)
            if loaded:
                INDEXES[rid] = loaded
    return [{"id":rid,"root":idx.root,"metrics":GraphAnalysis(idx).metrics()} for rid,idx in INDEXES.items()]

def get(rid: str | None):
    if not rid:
        raise HTTPException(404, "Repository not found")
    if rid not in INDEXES:
        loaded = STORE.load(rid)
        if loaded:
            INDEXES[rid] = loaded
    if rid not in INDEXES:
        raise HTTPException(404, "Repository not found")
    return INDEXES[rid]

@app.get("/api/repositories/{rid}/overview")
def overview(rid: str):
    idx = get(rid)
    analysis = GraphAnalysis(idx)
    return {"root":idx.root,"metrics":analysis.metrics(),"warnings":idx.warnings,"cycles":analysis.cycles()[:20]}

@app.get("/api/repositories/{rid}/search")
def search(rid: str, q: str):
    return GraphAnalysis(get(rid)).search(q)

@app.get("/api/repositories/{rid}/graph")
def graph(rid: str, limit: int = 1500):
    idx = get(rid)
    nodes = [{"id":p,"label":Path(p).name,"type":"file","language":f.language} for p,f in idx.files.items()]
    nodes += [{"id":s.id,"label":s.name,"type":s.kind,"file":s.file,"language":s.language} for s in idx.symbols.values()]
    edges = [e.__dict__ for e in idx.edges[:limit]]
    return {"nodes":nodes[:limit],"edges":edges}

@app.get("/api/repositories/{rid}/impact")
def impact(rid: str, node: str):
    return GraphAnalysis(get(rid)).impact(node)

@app.get("/api/repositories/{rid}/architecture")
def architecture(rid: str):
    return GraphAnalysis(get(rid)).architecture()

@app.get("/api/repositories/{rid}/symbols/{symbol_id:path}")
def symbol(rid: str, symbol_id: str):
    idx = get(rid)
    if symbol_id not in idx.symbols:
        raise HTTPException(404, "Symbol not found")
    item = idx.symbols[symbol_id]
    source = (Path(idx.root) / item.file).read_text(encoding="utf-8", errors="ignore").splitlines()
    start = max(0, item.line - 4)
    end = min(len(source), item.end_line + 3)
    return {**item.__dict__, "source": "\n".join(source[start:end]), "source_start_line":start + 1}

@app.delete("/api/repositories/{rid}")
def delete_repository(rid: str):
    existed = rid in INDEXES or STORE.load(rid) is not None
    INDEXES.pop(rid, None)
    STORE.delete(rid)
    if not existed:
        raise HTTPException(404, "Repository not found")
    return {"deleted":rid}

@app.get("/api/repositories/{rid}/git/hotspots")
def git_hotspots(rid: str, limit: int = 20):
    return GitAnalysis(get(rid).root).hotspots(limit)

@app.get("/api/repositories/{rid}/git/contributors")
def git_contributors(rid: str, limit: int = 20):
    return GitAnalysis(get(rid).root).contributors(limit)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    SUBS.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        SUBS.discard(websocket)
