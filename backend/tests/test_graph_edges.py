"""Graph endpoint edge filtering.

The graph response returns a bounded page of nodes plus their edges. get_between
restricts edges to that page, which is what keeps the response from referencing
nodes the client never received. graph_api depends on that and only filters
self-loops itself, so both halves are pinned here.
"""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.api.graph_api import get_graph
from app.models.edge import Edge
from app.models.enums import EdgeType, SymbolType
from app.repositories.edge_repo import EdgeRepo


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return SimpleNamespace(all=lambda: list(self._rows))


class RecordingSession:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return FakeResult(self.rows)


def make_edge(source: uuid.UUID, target: uuid.UUID) -> Edge:
    return Edge(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        source_id=source,
        target_id=target,
        edge_type=EdgeType.CALLS,
    )


def sql(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


class TestEdgeRepoGetBetween:
    async def test_empty_node_set_skips_the_query(self):
        session = RecordingSession()

        assert await EdgeRepo(session).get_between(uuid.uuid4(), set()) == []
        assert session.statement is None

    async def test_query_constrains_repository_and_both_endpoints(self):
        session = RecordingSession()
        nodes = {uuid.uuid4(), uuid.uuid4()}

        await EdgeRepo(session).get_between(uuid.uuid4(), nodes)

        text = sql(session.statement)
        assert "edges.repository_id" in text
        assert "edges.source_id IN" in text
        assert "edges.target_id IN" in text
        for node_id in nodes:
            assert str(node_id) in text

    async def test_returns_session_rows(self):
        rows = [make_edge(uuid.uuid4(), uuid.uuid4())]
        repo = EdgeRepo(RecordingSession(rows))

        assert await repo.get_between(uuid.uuid4(), {r.source_id for r in rows}) == rows

    async def test_statement_is_a_select(self):
        session = RecordingSession()
        await EdgeRepo(session).get_between(uuid.uuid4(), {uuid.uuid4()})

        assert isinstance(session.statement, type(select(Edge)))


class FakeNodeRepo:
    def __init__(self, nodes, total):
        self.nodes = nodes
        self.total = total
        self.requested_limit = None
        self.requested_symbol_type = None

    async def count_by_repository(self, repository_id):
        return self.total

    async def get_by_repository(self, repository_id, limit=None, symbol_type=None):
        self.requested_limit = limit
        self.requested_symbol_type = symbol_type
        return self.nodes[:limit] if limit else self.nodes


class FakeEdgeRepo:
    def __init__(self, edges):
        self.edges = edges
        self.seen_node_ids = None

    async def get_between(self, repository_id, node_ids):
        self.seen_node_ids = set(node_ids)
        return list(self.edges)


def make_node(node_id: uuid.UUID) -> SimpleNamespace:
    return SimpleNamespace(
        id=node_id,
        symbol_type=SymbolType.FUNCTION,
        symbol_name=f"fn_{node_id.hex[:6]}",
        file_path="src/app.py",
    )


@pytest.fixture
def patched(monkeypatch):
    def _apply(nodes, edges, total=None):
        node_repo = FakeNodeRepo(nodes, total if total is not None else len(nodes))
        edge_repo = FakeEdgeRepo(edges)
        monkeypatch.setattr("app.api.graph_api.NodeRepo", lambda db: node_repo)
        monkeypatch.setattr("app.api.graph_api.EdgeRepo", lambda db: edge_repo)
        return node_repo, edge_repo

    return _apply


class TestGetGraph:
    async def test_edges_are_asked_for_using_the_returned_node_page(self, patched):
        nodes = [make_node(uuid.uuid4()) for _ in range(3)]
        _, edge_repo = patched(nodes, [])

        await get_graph(str(uuid.uuid4()), limit=100, db=None)

        assert edge_repo.seen_node_ids == {n.id for n in nodes}

    async def test_limit_is_passed_through_and_reported(self, patched):
        nodes = [make_node(uuid.uuid4()) for _ in range(5)]
        node_repo, _ = patched(nodes, [], total=42)

        response = await get_graph(str(uuid.uuid4()), limit=2, db=None)

        assert node_repo.requested_limit == 2
        assert response.returned_nodes == 2
        assert response.total_nodes == 42
        assert response.truncated is True

    async def test_not_truncated_when_everything_fits(self, patched):
        nodes = [make_node(uuid.uuid4()) for _ in range(2)]
        patched(nodes, [], total=2)

        response = await get_graph(str(uuid.uuid4()), limit=10, db=None)

        assert response.truncated is False

    async def test_symbol_type_filter_is_forwarded(self, patched):
        nodes = [make_node(uuid.uuid4())]
        node_repo, _ = patched(nodes, [])

        await get_graph(str(uuid.uuid4()), limit=100, symbol_type=SymbolType.CLASS, db=None)

        assert node_repo.requested_symbol_type == SymbolType.CLASS

    async def test_self_loops_are_omitted(self, patched):
        node_id = uuid.uuid4()
        other_id = uuid.uuid4()
        loop = make_edge(node_id, node_id)
        chained = make_edge(node_id, other_id)
        patched([make_node(node_id), make_node(other_id)], [loop, chained])

        response = await get_graph(str(uuid.uuid4()), limit=100, db=None)

        assert [e.source for e in response.edges] == [str(node_id)]
        assert response.edges[0].target == str(other_id)

    async def test_no_edges_when_page_is_empty(self, patched):
        patched([], [])

        response = await get_graph(str(uuid.uuid4()), limit=100, db=None)

        assert response.nodes == []
        assert response.edges == []

    async def test_edge_endpoints_reference_returned_nodes(self, patched):
        nodes = [make_node(uuid.uuid4()) for _ in range(2)]
        edges = [make_edge(nodes[0].id, nodes[1].id)]
        patched(nodes, edges)

        response = await get_graph(str(uuid.uuid4()), limit=100, db=None)

        returned = {n.id for n in response.nodes}
        for edge in response.edges:
            assert edge.source in returned
            assert edge.target in returned