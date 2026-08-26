import uuid

from pydantic import BaseModel

from app.models.enums import SymbolType
from app.schemas.node import NodeResponse


class SearchRequest(BaseModel):
    repository_id: uuid.UUID
    query: str
    limit: int = 10
    symbol_type: SymbolType | None = None


class SearchResult(BaseModel):
    node: NodeResponse
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
