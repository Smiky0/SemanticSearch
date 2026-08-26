import uuid

from pydantic import BaseModel


class ExplainRequest(BaseModel):
    repository_id: uuid.UUID
    query: str


class TraceRequest(BaseModel):
    repository_id: uuid.UUID
    query: str


class SourceReference(BaseModel):
    file_path: str
    symbol_name: str
    start_line: int
    end_line: int


class LLMResponse(BaseModel):
    answer: str
    sources: list[SourceReference]
