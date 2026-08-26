from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import SymbolNotFoundError
from app.repositories.node_repo import NodeRepo
from app.schemas.node import NodeResponse, RelationshipResponse
from app.utils import parse_uuid

router = APIRouter()


@router.get("/symbols/{symbol_id}", response_model=NodeResponse)
async def get_symbol(symbol_id: str, db: AsyncSession = Depends(get_db)):
    rid = parse_uuid(symbol_id)
    node_repo = NodeRepo(db)
    node = await node_repo.get(rid)
    if not node:
        raise SymbolNotFoundError(symbol_id)
    return NodeResponse.model_validate(node)


@router.get(
    "/symbols/{symbol_id}/relationships",
    response_model=list[RelationshipResponse],
)
async def get_symbol_relationships(
    symbol_id: str, db: AsyncSession = Depends(get_db)
):
    rid = parse_uuid(symbol_id)
    node_repo = NodeRepo(db)
    node = await node_repo.get(rid)
    if not node:
        raise SymbolNotFoundError(symbol_id)

    neighbors, edges = await node_repo.get_neighbors(node.id)
    node_map = {n.id: n for n in neighbors}
    node_map[node.id] = node

    relationships = []
    for edge in edges:
        source = node_map.get(edge.source_id)
        target = node_map.get(edge.target_id)
        if source and target:
            relationships.append(
                RelationshipResponse(
                    source=NodeResponse.model_validate(source),
                    target=NodeResponse.model_validate(target),
                    edge_type=edge.edge_type,
                )
            )
    return relationships
