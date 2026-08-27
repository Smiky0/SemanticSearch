from pathlib import Path

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BROWSE_ROOT, get_settings
from app.database import async_session, get_db
from app.embedding.vector_store import get_vector_store
from app.exceptions import RepositoryNotFoundError
from app.models.enums import IndexingStatus
from app.repositories.edge_repo import EdgeRepo
from app.repositories.node_repo import NodeRepo
from app.repositories.repository_repo import RepositoryRepo
from app.schemas.repository import (
    IndexingStatusResponse,
    RepositoryCreate,
    RepositoryResponse,
)
from app.services.indexing_service import index_repository
from app.utils import parse_uuid

logger = structlog.get_logger()
router = APIRouter()


class DirectoryEntry(BaseModel):
    name: str
    path: str
    is_git: bool


@router.get("/repositories/browse")
async def browse_directories(path: str = BROWSE_ROOT):
    try:
        target = Path(path).expanduser().resolve()
    except (RuntimeError, OSError):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries: list[DirectoryEntry] = []
    try:
        for item in sorted(target.iterdir()):
            if item.name.startswith(".") and item.name != ".git":
                continue
            if not item.is_dir():
                continue
            is_git = (item / ".git").is_dir()
            entries.append(
                DirectoryEntry(
                    name=item.name,
                    path=str(item),
                    is_git=is_git,
                )
            )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    parent = str(target.parent) if target != target.parent else None
    return {"current": str(target), "parent": parent, "entries": entries}


@router.post("/repositories/index", response_model=RepositoryResponse)
async def create_repository(
    req: RepositoryCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    repo_path = Path(req.path).resolve()
    if not repo_path.is_dir():
        raise HTTPException(status_code=400, detail="Invalid repository path")

    repo_repo = RepositoryRepo(db)
    existing = await repo_repo.get_by_path(str(repo_path))

    if existing:
        if existing.status == "indexing":
            raise HTTPException(
                status_code=409, detail="Repository is currently being indexed"
            )
        if existing.status == "completed":
            raise HTTPException(
                status_code=409,
                detail="Repository already indexed. Delete it first to re-index.",
            )
        repo = await repo_repo.update_status(
            existing.id,
            IndexingStatus.PENDING,
            file_count=0,
            symbol_count=0,
            error_message=None,
        )
        background_tasks.add_task(index_repository, repo.id)
        logger.info("repository_reindexed", repo_id=str(repo.id), path=str(repo_path))
        return repo

    name = repo_path.name
    repo = await repo_repo.create(str(repo_path), name)
    background_tasks.add_task(index_repository, repo.id)
    logger.info("repository_created", repo_id=str(repo.id), path=str(repo_path))
    return repo


@router.get("/repositories", response_model=list[RepositoryResponse])
async def list_repositories(db: AsyncSession = Depends(get_db)):
    repo_repo = RepositoryRepo(db)
    return await repo_repo.list_all()


@router.get(
    "/repositories/{repo_id}/status", response_model=IndexingStatusResponse
)
async def get_indexing_status(
    repo_id: str, db: AsyncSession = Depends(get_db)
):
    rid = parse_uuid(repo_id)
    repo_repo = RepositoryRepo(db)
    repo = await repo_repo.get(rid)
    if not repo:
        raise RepositoryNotFoundError(repo_id)
    return IndexingStatusResponse(
        repository_id=repo.id,
        status=repo.status,
        file_count=repo.file_count,
        symbol_count=repo.symbol_count,
        error_message=repo.error_message,
    )


@router.delete("/repositories/{repo_id}")
async def delete_repository(
    repo_id: str, db: AsyncSession = Depends(get_db)
):
    rid = parse_uuid(repo_id)
    repo_repo = RepositoryRepo(db)
    repo = await repo_repo.get(rid)
    if not repo:
        raise RepositoryNotFoundError(repo_id)

    settings = get_settings()

    async with async_session() as del_db:
        node_repo = NodeRepo(del_db)
        edge_repo = EdgeRepo(del_db)

        nodes = await node_repo.get_by_repository(rid)
        point_ids = [str(n.id) for n in nodes if n.qdrant_point_id]

        if point_ids:
            try:
                vector_store = get_vector_store()
                await vector_store.delete(
                    settings.qdrant_collection, point_ids
                )
            except Exception as e:
                logger.warning(
                    "vector_delete_failed",
                    repo_id=repo_id,
                    error=str(e),
                )

        all_edges = await edge_repo.get_by_repository(rid)
        for e in all_edges:
            await del_db.delete(e)
        for n in nodes:
            await del_db.delete(n)

        await del_db.commit()

    await repo_repo.hard_delete(rid)
    logger.info("repository_deleted", repo_id=repo_id)
    return {"status": "deleted"}
