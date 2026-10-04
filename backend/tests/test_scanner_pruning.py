import os
import uuid
from pathlib import Path

import pytest

from app.core.scanner import scan_repository


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Build a small repo tree containing paths that must be excluded."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "src" / "app.ts").write_text("const x = 1\n", encoding="utf-8")

    # Excluded directories that must never be walked into.
    for d in ("node_modules", ".venv", "__pycache__", "dist", ".next"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "junk.py").write_text("should not be indexed\n", encoding="utf-8")
        nested = tmp_path / d / "pkg" / "deep"
        nested.mkdir(parents=True)
        (nested / "deep.py").write_text("deep\n", encoding="utf-8")

    (tmp_path / "README.md").write_text("not indexed\n", encoding="utf-8")
    return tmp_path


class TestScanRepositoryPruning:
    def test_returns_only_supported_files(self, repo: Path):
        files = scan_repository(str(repo))
        rels = {f["relative_path"] for f in files}
        assert rels == {"src/app.py", "src/app.ts"}

    def test_excluded_directories_are_not_walked(self, repo: Path):
        files = scan_repository(str(repo))
        for f in files:
            assert "node_modules" not in f["relative_path"]
            assert ".venv" not in f["relative_path"]
            assert "__pycache__" not in f["relative_path"]
            assert "dist" not in f["relative_path"]
            assert ".next" not in f["relative_path"]

    def test_empty_and_oversized_files_skipped(self, repo: Path):
        (repo / "src" / "empty.py").write_text("", encoding="utf-8")
        (repo / "src" / "big.py").write_text("x" * 200_000, encoding="utf-8")
        rels = {f["relative_path"] for f in scan_repository(str(repo))}
        assert "src/empty.py" not in rels
        assert "src/big.py" not in rels

    def test_results_are_deterministically_ordered(self, repo: Path):
        first = [f["relative_path"] for f in scan_repository(str(repo))]
        second = [f["relative_path"] for f in scan_repository(str(repo))]
        assert first == second == sorted(first)

    def test_gitignore_is_respected(self, repo: Path):
        (repo / ".gitignore").write_text("src/app.ts\n", encoding="utf-8")
        rels = {f["relative_path"] for f in scan_repository(str(repo))}
        assert "src/app.ts" not in rels
        assert "src/app.py" in rels

    def test_missing_directory_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Not a directory"):
            scan_repository(str(tmp_path / "nope"))

    def test_unreadable_subtree_does_not_abort_scan(self, repo: Path, monkeypatch):
        """A permission error inside the tree must not abort the whole scan."""
        real_walk = os.walk
        calls = {"n": 0}

        def flaky_walk(top, onerror=None, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                if onerror is not None:
                    onerror(PermissionError(13, "Permission denied"))
                return
            yield from real_walk(top, onerror=onerror, **kwargs)

        monkeypatch.setattr(os, "walk", flaky_walk)
        files = scan_repository(str(repo))
        assert isinstance(files, list)


class TestScanRepositoryScale:
    def test_pruning_bounds_work_on_large_trees(self, tmp_path: Path):
        """Many excluded entries must not multiply the amount of work."""
        deep = tmp_path / "node_modules"
        for i in range(40):
            d = deep / f"pkg{i}" / "node_modules" / "deeper"
            d.mkdir(parents=True)
            (d / "index.js").write_text("x", encoding="utf-8")

        (tmp_path / "keep.py").write_text("x = 1\n", encoding="utf-8")

        files = scan_repository(str(tmp_path))
        assert [f["relative_path"] for f in files] == ["keep.py"]


class TestGetMany:
    async def test_get_many_returns_empty_for_empty_input(self):
        from app.repositories.node_repo import NodeRepo

        repo = NodeRepo(db=None)  # type: ignore[arg-type]
        assert await repo.get_many(set()) == {}

    async def test_get_many_returns_empty_when_no_rows(self):
        from app.repositories.node_repo import NodeRepo

        class FakeResult:
            def scalars(self):
                class S:
                    def all(self):
                        return []

                return S()

        class FakeDb:
            async def execute(self, stmt):
                return FakeResult()

        repo = NodeRepo(db=FakeDb())  # type: ignore[arg-type]
        assert await repo.get_many({uuid.uuid4(), uuid.uuid4()}) == {}

    async def test_get_many_keys_results_by_node_id(self):
        """One query must be issued and results keyed by id."""
        from app.repositories.node_repo import NodeRepo

        ids = [uuid.uuid4(), uuid.uuid4()]

        class FakeNode:
            def __init__(self, node_id):
                self.id = node_id

        class FakeResult:
            def scalars(self):
                nodes = [FakeNode(i) for i in ids]

                class S:
                    def all(self):
                        return nodes

                return S()

        queries = []

        class FakeDb:
            async def execute(self, stmt):
                queries.append(stmt)
                return FakeResult()

        repo = NodeRepo(db=FakeDb())  # type: ignore[arg-type]
        result = await repo.get_many(set(ids))

        assert len(queries) == 1, "get_many must issue exactly one query"
        assert result == {i: result[i] for i in ids}
        assert len(result) == 2