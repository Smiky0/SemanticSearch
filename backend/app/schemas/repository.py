import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import IndexingStatus


class RepositoryCreate(BaseModel):
    path: str


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    path: str
    name: str
    status: IndexingStatus
    indexed_at: datetime | None
    created_at: datetime
    file_count: int
    symbol_count: int
    error_message: str | None = None

    model_config = {"from_attributes": True}


class IndexingStatusResponse(BaseModel):
    repository_id: uuid.UUID
    status: IndexingStatus
    file_count: int
    symbol_count: int
    error_message: str | None = None
