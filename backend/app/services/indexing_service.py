import uuid
from pathlib import Path

import structlog

from app.config import get_settings
from app.core.parser import extract_code_units
from app.core.scanner import scan_repository
from app.database import async_session
from app.embedding.provider import get_embedding_provider
from app.embedding.vector_store import get_vector_store
from app.exceptions import EmbeddingError, VectorStoreError
from app.models.enums import IndexingStatus, SymbolType
from app.models.node import Node
from app.repositories.node_repo import NodeRepo
from app.repositories.repository_repo import RepositoryRepo

logger = structlog.get_logger()


async def index_repository(repo_id: uuid.UUID) -> None:
    settings = get_settings()
    async with async_session() as db:
        repo_repo = RepositoryRepo(db)
        node_repo = NodeRepo(db)

        repo = await repo_repo.get(repo_id)
        if not repo:
            logger.error("repository_not_found", repo_id=str(repo_id))
            return

        await repo_repo.update_status(repo_id, IndexingStatus.INDEXING)
        logger.info("indexing_started", repo_id=str(repo_id), path=repo.path)

        try:
            files = scan_repository(repo.path)
            logger.info("files_found", count=len(files))

            embedding_provider = get_embedding_provider()
            vector_store = get_vector_store()
            await vector_store.ensure_collection(
                settings.qdrant_collection, embedding_provider.dimensions()
            )

            all_nodes: list[Node] = []

            for file_info in files:
                abs_path = file_info["absolute_path"]
                rel_path = file_info["relative_path"]
                language = file_info["language"]

                try:
                    source_code = Path(abs_path).read_text(
                        encoding="utf-8", errors="ignore"
                    )
                except Exception:
                    logger.warning("file_read_failed", path=rel_path)
                    continue

                file_node = _create_file_node(
                    repo_id, rel_path, language, source_code
                )
                all_nodes.append(file_node)

                code_units = extract_code_units(abs_path, source_code, language)
                for unit in code_units:
                    node = Node(
                        repository_id=repo_id,
                        file_path=rel_path,
                        language=language,
                        symbol_name=unit.symbol_name,
                        symbol_type=unit.symbol_type,
                        start_line=unit.start_line,
                        end_line=unit.end_line,
                        source_code=unit.source_code,
                        docstring=unit.docstring,
                    )
                    all_nodes.append(node)

            if all_nodes:
                await node_repo.bulk_create(all_nodes)

            searchable_nodes = [
                n for n in all_nodes if n.symbol_type != SymbolType.FILE
            ]

            if searchable_nodes:
                texts = [_node_embedding_text(n) for n in searchable_nodes]
                all_points: list[dict] = []
                batch_size = 100
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i : i + batch_size]
                    batch_nodes = searchable_nodes[i : i + batch_size]
                    embeddings = await embedding_provider.embed(batch_texts)

                    for node_obj, embedding in zip(batch_nodes, embeddings):
                        all_points.append(
                            {
                                "id": str(node_obj.id),
                                "vector": embedding,
                                "payload": {
                                    "repository_id": str(repo_id),
                                    "file_path": node_obj.file_path,
                                    "symbol_name": node_obj.symbol_name,
                                    "symbol_type": node_obj.symbol_type.value,
                                    "language": node_obj.language,
                                },
                            }
                        )

                await vector_store.upsert(
                    settings.qdrant_collection, all_points
                )

            await repo_repo.update_status(
                repo_id,
                IndexingStatus.COMPLETED,
                file_count=len(files),
                symbol_count=len(searchable_nodes),
            )
            logger.info(
                "indexing_completed",
                repo_id=str(repo_id),
                files=len(files),
                symbols=len(searchable_nodes),
            )

        except EmbeddingError as e:
            await repo_repo.update_status(
                repo_id, IndexingStatus.FAILED, error_message=e.message
            )
            logger.error(
                "indexing_failed_embedding",
                repo_id=str(repo_id),
                error=e.message,
            )
        except VectorStoreError as e:
            await repo_repo.update_status(
                repo_id, IndexingStatus.FAILED, error_message=e.message
            )
            logger.error(
                "indexing_failed_vector_store",
                repo_id=str(repo_id),
                error=e.message,
            )
        except ValueError as e:
            error_msg = str(e)
            await repo_repo.update_status(
                repo_id, IndexingStatus.FAILED, error_message=error_msg
            )
            logger.error(
                "indexing_failed_validation",
                repo_id=str(repo_id),
                error=error_msg,
            )
        except Exception as e:
            error_msg = "An unexpected error occurred during indexing"
            await repo_repo.update_status(
                repo_id, IndexingStatus.FAILED, error_message=error_msg
            )
            logger.error(
                "indexing_failed",
                repo_id=str(repo_id),
                error=str(e),
                exc_info=True,
            )


def _create_file_node(
    repo_id: uuid.UUID, rel_path: str, language: str, source_code: str
) -> Node:
    return Node(
        repository_id=repo_id,
        file_path=rel_path,
        language=language,
        symbol_name=rel_path,
        symbol_type=SymbolType.FILE,
        start_line=1,
        end_line=source_code.count("\n") + 1,
        source_code=source_code,
    )


def _node_embedding_text(node: Node) -> str:
    parts = [
        f"{node.symbol_type.value}: {node.symbol_name}",
        f"File: {node.file_path}",
        f"Language: {node.language}",
    ]
    if node.docstring:
        parts.append(f"Docstring: {node.docstring}")
    parts.append(f"Code:\n{node.source_code}")
    return "\n".join(parts)
