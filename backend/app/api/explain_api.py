from fastapi import APIRouter

from app.schemas.llm import ExplainRequest, LLMResponse, SourceReference
from app.services.explain_service import explain_query

router = APIRouter()


@router.post("/explain", response_model=LLMResponse)
async def explain(req: ExplainRequest):
    result = await explain_query(
        repository_id=req.repository_id, query=req.query
    )
    return LLMResponse(
        answer=result["answer"],
        sources=[SourceReference(**s) for s in result["sources"]],
    )
