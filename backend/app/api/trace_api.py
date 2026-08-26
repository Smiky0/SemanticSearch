from fastapi import APIRouter

from app.schemas.llm import LLMResponse, SourceReference, TraceRequest
from app.services.trace_service import trace_query

router = APIRouter()


@router.post("/trace", response_model=LLMResponse)
async def trace(req: TraceRequest):
    result = await trace_query(
        repository_id=req.repository_id, query=req.query
    )
    return LLMResponse(
        answer=result["answer"],
        sources=[SourceReference(**s) for s in result["sources"]],
    )
