from __future__ import annotations
import json
import os
from contextlib import contextmanager
from .models import RepositoryIndex

class PostgresMetadataStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.getenv("DATABASE_URL", "")

    @contextmanager
    def connection(self):
        if not self.dsn:
            yield None
            return
        try:
            import psycopg
            with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                yield conn
        except Exception:
            yield None

    def initialize(self):
        with self.connection() as conn:
            if not conn:
                return False
            conn.execute("""
                CREATE TABLE IF NOT EXISTS repository_indexes (
                    repository_id TEXT PRIMARY KEY,
                    root TEXT NOT NULL,
                    metrics JSONB NOT NULL,
                    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            conn.commit()
            return True

    def upsert(self, repository_id: str, index: RepositoryIndex, metrics: dict):
        with self.connection() as conn:
            if not conn:
                return False
            conn.execute(
                """
                INSERT INTO repository_indexes(repository_id, root, metrics)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT(repository_id) DO UPDATE
                SET root=EXCLUDED.root, metrics=EXCLUDED.metrics, indexed_at=NOW()
                """,
                (repository_id, index.root, json.dumps(metrics)),
            )
            conn.commit()
            return True

class Neo4jGraphStore:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        self.uri = uri or os.getenv("NEO4J_URI", "")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "repolens-password")

    def save(self, repository_id: str, index: RepositoryIndex):
        if not self.uri:
            return False
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            with driver.session() as session:
                session.run("MATCH (n {repository_id:$rid}) DETACH DELETE n", rid=repository_id)
                for path, record in index.files.items():
                    session.run(
                        """
                        MERGE (f:File {repository_id:$rid, id:$id})
                        SET f.path=$path, f.language=$language, f.lines=$lines
                        """,
                        rid=repository_id, id=path, path=path,
                        language=record.language, lines=record.lines,
                    )
                for symbol in index.symbols.values():
                    session.run(
                        """
                        MERGE (s:Symbol {repository_id:$rid, id:$id})
                        SET s.name=$name, s.kind=$kind, s.file=$file, s.line=$line
                        WITH s
                        MATCH (f:File {repository_id:$rid, id:$file})
                        MERGE (f)-[:CONTAINS]->(s)
                        """,
                        rid=repository_id, id=symbol.id, name=symbol.name,
                        kind=symbol.kind, file=symbol.file, line=symbol.line,
                    )
                for edge in index.edges:
                    session.run(
                        """
                        MERGE (a:CodeNode {repository_id:$rid, id:$source})
                        MERGE (b:CodeNode {repository_id:$rid, id:$target})
                        MERGE (a)-[r:RELATES {kind:$kind}]->(b)
                        SET r.confidence=$confidence, r.evidence=$evidence
                        """,
                        rid=repository_id, source=edge.source, target=edge.target,
                        kind=edge.kind, confidence=edge.confidence, evidence=edge.evidence,
                    )
            driver.close()
            return True
        except Exception:
            return False
