import uuid

from pydantic import BaseModel

from app.models.enums import EdgeType, SymbolType


class NodeResponse(BaseModel):
    id: uuid.UUID
    file_path: str
    language: str
    symbol_name: str
    symbol_type: SymbolType
    parent_symbol_id: uuid.UUID | None
    start_line: int
    end_line: int
    source_code: str
    docstring: str | None

    model_config = {"from_attributes": True}


class EdgeResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    edge_type: EdgeType

    model_config = {"from_attributes": True}


class RelationshipResponse(BaseModel):
    source: NodeResponse
    target: NodeResponse
    edge_type: EdgeType
