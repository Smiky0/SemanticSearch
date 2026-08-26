from fastapi import APIRouter

from app.schemas.node import NodeResponse
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.search_service import semantic_search

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    results = await semantic_search(
        repository_id=req.repository_id,
        query=req.query,
        limit=req.limit,
        symbol_type=req.symbol_type,
    )
    return SearchResponse(
        results=[
            SearchResult(
                node=NodeResponse.model_validate(r["node"]),
                score=r["score"],
            )
            for r in results
        ]
    )
