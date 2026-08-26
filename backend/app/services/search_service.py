import uuid

import structlog

from app.config import get_settings
from app.database import async_session
from app.embedding.provider import get_embedding_provider
from app.embedding.vector_store import get_vector_store
from app.models.enums import SymbolType
from app.repositories.node_repo import NodeRepo

logger = structlog.get_logger()


async def semantic_search(
    repository_id: uuid.UUID,
    query: str,
    limit: int = 10,
    symbol_type: SymbolType | None = None,
) -> list[dict]:
    settings = get_settings()
    embedding_provider = get_embedding_provider()
    vector_store = get_vector_store()

    query_embedding = await embedding_provider.embed([query])

    search_filter: dict[str, str] = {"repository_id": str(repository_id)}
    if symbol_type:
        search_filter["symbol_type"] = symbol_type.value

    results = await vector_store.search(
        collection=settings.qdrant_collection,
        query_vector=query_embedding[0],
        limit=limit,
        filter=search_filter,
    )

    async with async_session() as db:
        node_repo = NodeRepo(db)
        enriched = []
        for r in results:
            try:
                node = await node_repo.get(uuid.UUID(r["id"]))
            except ValueError:
                logger.warning("invalid_vector_id", vector_id=r["id"])
                continue
            if node:
                enriched.append({"node": node, "score": r["score"]})

    return enriched
