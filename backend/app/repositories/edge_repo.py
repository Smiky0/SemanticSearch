import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge import Edge
from app.models.enums import EdgeType


class EdgeRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_create(self, edges: list[Edge]) -> None:
        self.db.add_all(edges)
        await self.db.commit()

    async def get_by_repository(self, repository_id: uuid.UUID) -> list[Edge]:
        result = await self.db.execute(
            select(Edge).where(Edge.repository_id == repository_id)
        )
        return list(result.scalars().all())

    async def get_outgoing(
        self, node_id: uuid.UUID, edge_type: EdgeType | None = None
    ) -> list[Edge]:
        stmt = select(Edge).where(Edge.source_id == node_id)
        if edge_type:
            stmt = stmt.where(Edge.edge_type == edge_type)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_incoming(
        self, node_id: uuid.UUID, edge_type: EdgeType | None = None
    ) -> list[Edge]:
        stmt = select(Edge).where(Edge.target_id == node_id)
        if edge_type:
            stmt = stmt.where(Edge.edge_type == edge_type)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
