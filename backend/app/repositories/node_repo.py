import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge import Edge
from app.models.enums import SymbolType
from app.models.node import Node


class NodeRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_create(self, nodes: list[Node]) -> None:
        self.db.add_all(nodes)
        await self.db.commit()

    async def get(self, node_id: uuid.UUID) -> Node | None:
        result = await self.db.execute(select(Node).where(Node.id == node_id))
        return result.scalar_one_or_none()

    async def find_by_symbol(
        self, repository_id: uuid.UUID, symbol_name: str
    ) -> list[Node]:
        result = await self.db.execute(
            select(Node).where(
                Node.repository_id == repository_id,
                Node.symbol_name.ilike(f"%{symbol_name}%"),
            )
        )
        return list(result.scalars().all())

    async def get_by_repository(self, repository_id: uuid.UUID) -> list[Node]:
        result = await self.db.execute(
            select(Node).where(Node.repository_id == repository_id)
        )
        return list(result.scalars().all())

    async def get_by_file(
        self, repository_id: uuid.UUID, file_path: str
    ) -> list[Node]:
        result = await self.db.execute(
            select(Node)
            .where(
                Node.repository_id == repository_id,
                Node.file_path == file_path,
            )
            .order_by(Node.start_line)
        )
        return list(result.scalars().all())

    async def get_by_path(
        self, repository_id: uuid.UUID, file_path: str
    ) -> Node | None:
        result = await self.db.execute(
            select(Node).where(
                Node.repository_id == repository_id,
                Node.file_path == file_path,
                Node.symbol_type == SymbolType.FILE,
            )
        )
        return result.scalar_one_or_none()

    async def search(
        self,
        repository_id: uuid.UUID,
        query: str,
        symbol_type: SymbolType | None = None,
        limit: int = 10,
    ) -> list[Node]:
        stmt = select(Node).where(Node.repository_id == repository_id)
        if symbol_type:
            stmt = stmt.where(Node.symbol_type == symbol_type)
        if query:
            stmt = stmt.where(
                Node.symbol_name.ilike(f"%{query}%")
                | Node.source_code.ilike(f"%{query}%")
            )
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_neighbors(
        self, node_id: uuid.UUID
    ) -> tuple[list[Node], list[Edge]]:
        out_edges_result = await self.db.execute(
            select(Edge).where(Edge.source_id == node_id)
        )
        in_edges_result = await self.db.execute(
            select(Edge).where(Edge.target_id == node_id)
        )
        out_edges = list(out_edges_result.scalars().all())
        in_edges = list(in_edges_result.scalars().all())
        all_edges = out_edges + in_edges

        neighbor_ids = set()
        for e in all_edges:
            neighbor_ids.add(e.source_id)
            neighbor_ids.add(e.target_id)
        neighbor_ids.discard(node_id)

        if not neighbor_ids:
            return [], all_edges

        nodes_result = await self.db.execute(
            select(Node).where(Node.id.in_(neighbor_ids))
        )
        nodes = list(nodes_result.scalars().all())
        return nodes, all_edges
