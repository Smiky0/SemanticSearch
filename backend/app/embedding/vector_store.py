import uuid as _uuid
from abc import ABC, abstractmethod

import structlog
from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qm
from qdrant_client.models import Distance, KeywordIndexParams, VectorParams

from app.config import get_settings
from app.exceptions import VectorStoreError

logger = structlog.get_logger()


class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, collection: str, points: list[dict]) -> None: ...

    @abstractmethod
    async def search(
        self, collection: str, query_vector: list[float], limit: int, filter: dict | None = None
    ) -> list[dict]: ...

    @abstractmethod
    async def delete(self, collection: str, point_ids: list[str]) -> None: ...

    @abstractmethod
    async def delete_by_repository(self, collection: str, repository_id: str) -> None: ...

    @abstractmethod
    async def ensure_collection(self, collection: str, dimensions: int) -> None: ...


class QdrantVectorStore(VectorStore):
    """Async Qdrant store.

    The sync client inside `async def` serialised the whole single-worker
    server behind every Qdrant call.
    """

    def __init__(self):
        settings = get_settings()
        try:
            self.client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
            )
        except Exception as e:
            logger.error("qdrant_connection_failed", error=str(e))
            raise VectorStoreError("Could not connect to vector store") from e

    async def close(self) -> None:
        await self.client.close()

    async def ensure_collection(self, collection: str, dimensions: int) -> None:
        """Create the collection if missing, otherwise leave it alone.

        The collection is shared by every repository, so recreating it here
        used to wipe all the others. A dimension change is the one case where
        the old vectors are unusable, and that's handled separately below.
        """
        try:
            collections = await self.client.get_collections()
            existing = {c.name: c for c in collections.collections}

            if collection not in existing:
                await self.client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
                )
                await self.client.create_payload_index(
                    collection_name=collection,
                    field_name="repository_id",
                    field_schema=KeywordIndexParams(type="keyword"),
                )
                logger.info(
                    "qdrant_collection_created",
                    collection=collection,
                    dimensions=dimensions,
                )
                return

            # Vector config lives on the full description, not the summary.
            try:
                info = await self.client.get_collection(collection_name=collection)
                actual_dim = info.config.params.vectors.size
            except Exception as e:
                logger.warning(
                    "qdrant_config_read_failed",
                    collection=collection,
                    error=str(e),
                )
                actual_dim = None

            if actual_dim is not None and actual_dim != dimensions:
                # Different dimensions means the old vectors are unusable.
                logger.warning(
                    "qdrant_dimension_mismatch_recreating",
                    collection=collection,
                    existing=actual_dim,
                    requested=dimensions,
                )
                await self.client.delete_collection(collection_name=collection)
                await self.client.create_collection(
                    collection_name=collection,
                    vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
                )
                await self.client.create_payload_index(
                    collection_name=collection,
                    field_name="repository_id",
                    field_schema=KeywordIndexParams(type="keyword"),
                )
                logger.info(
                    "qdrant_collection_created",
                    collection=collection,
                    dimensions=dimensions,
                )
                return

            logger.info("qdrant_collection_reused", collection=collection, dimensions=dimensions)
        except VectorStoreError:
            raise
        except Exception as e:
            logger.error("qdrant_collection_setup_failed", collection=collection, error=str(e))
            raise VectorStoreError(f"Failed to setup collection: {e}") from e

    async def delete_by_repository(self, collection: str, repository_id: str) -> None:
        """Drop every vector for one repository.

        Called before a re-upsert so deleted or renamed symbols don't
        survive as stale hits.
        """
        try:
            await self.client.delete(
                collection_name=collection,
                points_selector=qm.FilterSelector(
                    filter=qm.Filter(
                        must=[
                            qm.FieldCondition(
                                key="repository_id",
                                match=qm.MatchValue(value=repository_id),
                            )
                        ]
                    )
                ),
            )
            logger.info("qdrant_repository_vectors_cleared", repository_id=repository_id)
        except Exception as e:
            logger.error(
                "qdrant_repository_clear_failed",
                repository_id=repository_id,
                error=str(e),
            )
            raise VectorStoreError(f"Failed to clear repository vectors: {e}") from e

    async def upsert(self, collection: str, points: list[dict]) -> None:
        if not points:
            return
        try:
            await self.client.upsert(
                collection_name=collection,
                points=[
                    qm.PointStruct(
                        id=point["id"],
                        vector=point["vector"],
                        payload=point.get("payload", {}),
                    )
                    for point in points
                ],
            )
        except Exception as e:
            logger.error(
                "qdrant_upsert_failed",
                collection=collection,
                count=len(points),
                error=str(e),
            )
            raise VectorStoreError(f"Failed to upsert vectors: {e}") from e

    async def search(
        self, collection: str, query_vector: list[float], limit: int, filter: dict | None = None
    ) -> list[dict]:
        query_filter = None
        if filter:
            must_conditions = []
            for key, value in filter.items():
                must_conditions.append(qm.FieldCondition(key=key, match=qm.MatchValue(value=value)))
            query_filter = qm.Filter(must=must_conditions)

        try:
            results = await self.client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=limit,
                query_filter=query_filter,
            )
            return [
                {"id": str(r.id), "score": r.score, "payload": r.payload or {}}
                for r in results.points
            ]
        except Exception as e:
            logger.error("qdrant_search_failed", collection=collection, error=str(e))
            raise VectorStoreError(f"Vector search failed: {e}") from e

    async def delete(self, collection: str, point_ids: list[str]) -> None:
        try:
            uuids = []
            for pid in point_ids:
                try:
                    uuids.append(_uuid.UUID(pid))
                except ValueError:
                    logger.warning("invalid_point_id", point_id=pid)
                    continue

            if uuids:
                await self.client.delete(
                    collection_name=collection,
                    points_selector=qm.PointIdsList(points=uuids),
                )
        except VectorStoreError:
            raise
        except Exception as e:
            logger.error("qdrant_delete_failed", collection=collection, error=str(e))
            raise VectorStoreError(f"Failed to delete vectors: {e}") from e


def get_vector_store() -> VectorStore:
    return QdrantVectorStore()