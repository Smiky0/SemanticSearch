from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.enums import SymbolType
from app.repositories.edge_repo import EdgeRepo
from app.repositories.node_repo import NodeRepo
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse
from app.utils import parse_uuid

router = APIRouter()

# Bounded so the graph view can't pull the whole repository in one request.
GRAPH_DEFAULT_LIMIT = 500
GRAPH_MAX_LIMIT = 2000


@router.get("/graph/{repo_id}", response_model=GraphResponse)
async def get_graph(
    repo_id: str,
    limit: int = Query(
        GRAPH_DEFAULT_LIMIT, ge=1, le=GRAPH_MAX_LIMIT, description="Max nodes to return"
    ),
    symbol_type: SymbolType | None = Query(
        None, description="Restrict to a single symbol type"
    ),
    db: AsyncSession = Depends(get_db),
):
    rid = parse_uuid(repo_id)
    node_repo = NodeRepo(db)
    edge_repo = EdgeRepo(db)

    total = await node_repo.count_by_repository(rid)
    nodes = await node_repo.get_by_repository(rid, limit=limit, symbol_type=symbol_type)

    # get_between only returns edges with both ends in this page, so the
    # response can't reference nodes the client never received.
    node_ids = {n.id for n in nodes}
    edges = await edge_repo.get_between(rid, node_ids)

    graph_nodes = [
        GraphNode(
            id=str(n.id),
            label=f"{n.symbol_type.value}: {n.symbol_name}",
            symbol_type=n.symbol_type,
            file_path=n.file_path,
        )
        for n in nodes
    ]

    graph_edges = [
        GraphEdge(
            id=str(e.id),
            source=str(e.source_id),
            target=str(e.target_id),
            label=e.edge_type,
        )
        for e in edges
        if e.source_id != e.target_id
    ]

    return GraphResponse(
        nodes=graph_nodes,
        edges=graph_edges,
        total_nodes=total,
        returned_nodes=len(graph_nodes),
        truncated=total > len(graph_nodes),
    )
