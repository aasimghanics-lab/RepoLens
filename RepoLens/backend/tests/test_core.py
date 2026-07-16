from pathlib import Path
from app.indexer import RepositoryIndexer
from app.analysis import GraphAnalysis
from app.storage import IndexStore

def test_python_index_impact_and_inheritance(tmp_path: Path):
    (tmp_path/"base.py").write_text("class Base:\n    pass\n\ndef helper():\n    return 1\n")
    (tmp_path/"service.py").write_text("from base import Base, helper\n\nclass Service(Base):\n    def run(self):\n        return helper()\n")
    idx = RepositoryIndexer().index(str(tmp_path))
    analysis = GraphAnalysis(idx)
    names = {s.name for s in idx.symbols.values()}
    assert {"Base","helper","Service","run"} <= names
    assert any(e.kind == "inherits" for e in idx.edges)
    helper = next(s.id for s in idx.symbols.values() if s.name == "helper")
    assert analysis.impact(helper)["risk_score"] >= 12

def test_typescript_symbols_and_inheritance(tmp_path: Path):
    (tmp_path/"x.ts").write_text(
        "export class Child extends Parent {}\n"
        "export function authenticate(x:string){ return verify(x) }\n"
        "const verify = (x:string) => true\n"
    )
    idx = RepositoryIndexer().index(str(tmp_path))
    assert {"Child","authenticate","verify"} <= {s.name for s in idx.symbols.values()}
    assert any(e.kind == "inherits" for e in idx.edges)

def test_incremental_indexing(tmp_path: Path):
    (tmp_path/"a.py").write_text("def one():\n    return 1\n")
    indexer = RepositoryIndexer()
    first, first_changes = indexer.incremental(str(tmp_path), None)
    assert first_changes["added"] == ["a.py"]
    second, second_changes = indexer.incremental(str(tmp_path), first)
    assert second_changes["reindexed"] == 0
    (tmp_path/"a.py").write_text("def two():\n    return 2\n")
    third, third_changes = indexer.incremental(str(tmp_path), second)
    assert third_changes["modified"] == ["a.py"]
    assert {s.name for s in third.symbols.values()} == {"two"}

def test_index_store_round_trip(tmp_path: Path):
    (tmp_path/"a.py").write_text("def f():\n    return 1\n")
    idx = RepositoryIndexer().index(str(tmp_path))
    store = IndexStore(tmp_path/"indexes")
    store.save("demo", idx)
    loaded = store.load("demo")
    assert loaded is not None
    assert loaded.to_dict() == idx.to_dict()
