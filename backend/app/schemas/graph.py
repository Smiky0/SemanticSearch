from pydantic import BaseModel

from app.models.enums import EdgeType, SymbolType


class GraphNode(BaseModel):
    id: str
    label: str
    symbol_type: SymbolType
    file_path: str


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: EdgeType


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
