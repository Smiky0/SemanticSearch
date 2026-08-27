import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import IndexingStatus
from app.models.repository import Repository

logger = structlog.get_logger()


class RepositoryRepo:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, path: str, name: str) -> Repository:
        repo = Repository(path=path, name=name, status=IndexingStatus.PENDING)
        self.db.add(repo)
        await self.db.commit()
        await self.db.refresh(repo)
        return repo

    async def get(self, repo_id: uuid.UUID) -> Repository | None:
        return await self.db.get(Repository, repo_id)

    async def get_by_path(self, path: str) -> Repository | None:
        result = await self.db.execute(
            select(Repository).where(Repository.path == path)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Repository]:
        result = await self.db.execute(
            select(Repository).order_by(Repository.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        repo_id: uuid.UUID,
        status: IndexingStatus,
        file_count: int | None = None,
        symbol_count: int | None = None,
        error_message: str | None = None,
    ) -> Repository | None:
        repo = await self.db.get(Repository, repo_id)
        if not repo:
            return None
        repo.status = status
        if file_count is not None:
            repo.file_count = file_count
        if symbol_count is not None:
            repo.symbol_count = symbol_count
        if error_message is not None:
            repo.error_message = error_message
        if status == IndexingStatus.COMPLETED:
            repo.indexed_at = datetime.now(UTC)
            repo.error_message = None
        await self.db.commit()
        await self.db.refresh(repo)
        return repo

    async def hard_delete(self, repo_id: uuid.UUID) -> None:
        repo = await self.db.get(Repository, repo_id)
        if repo:
            await self.db.delete(repo)
            await self.db.commit()
