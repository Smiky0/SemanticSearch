from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.edge_repo import EdgeRepo
from app.repositories.node_repo import NodeRepo
from app.schemas.graph import GraphEdge, GraphNode, GraphResponse
from app.utils import parse_uuid

router = APIRouter()


@router.get("/graph/{repo_id}", response_model=GraphResponse)
async def get_graph(repo_id: str, db: AsyncSession = Depends(get_db)):
    rid = parse_uuid(repo_id)
    node_repo = NodeRepo(db)
    edge_repo = EdgeRepo(db)

    nodes = await node_repo.get_by_repository(rid)
    edges = await edge_repo.get_by_repository(rid)

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

    return GraphResponse(nodes=graph_nodes, edges=graph_edges)
