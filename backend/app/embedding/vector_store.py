import uuid as _uuid
from abc import ABC, abstractmethod

import structlog
from qdrant_client import QdrantClient
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
    async def ensure_collection(self, collection: str, dimensions: int) -> None: ...


class QdrantVectorStore(VectorStore):
    def __init__(self):
        settings = get_settings()
        try:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
            )
        except Exception as e:
            logger.error("qdrant_connection_failed", error=str(e))
            raise VectorStoreError("Could not connect to vector store") from e

    async def ensure_collection(self, collection: str, dimensions: int) -> None:
        try:
            collections = self.client.get_collections().collections
            existing = {c.name: c for c in collections}

            if collection in existing:
                self.client.delete_collection(collection_name=collection)

            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE),
            )
            self.client.create_payload_index(
                collection_name=collection,
                field_name="repository_id",
                field_schema=KeywordIndexParams(type="keyword"),
            )
            logger.info("qdrant_collection_created", collection=collection, dimensions=dimensions)
        except VectorStoreError:
            raise
        except Exception as e:
            logger.error("qdrant_collection_setup_failed", collection=collection, error=str(e))
            raise VectorStoreError(f"Failed to setup collection: {e}") from e

    async def upsert(self, collection: str, points: list[dict]) -> None:
        try:
            self.client.upsert(
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
            results = self.client.query_points(
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
                self.client.delete(
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
