import uuid

from app.database import async_session
from app.llm.provider import get_llm_provider
from app.models.enums import EdgeType
from app.repositories.node_repo import NodeRepo
from app.services.search_service import semantic_search


async def trace_query(repository_id: uuid.UUID, query: str) -> dict:
    results = await semantic_search(repository_id, query, limit=5)

    if not results:
        return {
            "answer": "No relevant code found for tracing.",
            "sources": [],
        }

    async with async_session() as db:
        node_repo = NodeRepo(db)

        expanded_results = list(results)
        visited_node_ids = {r["node"].id for r in results}

        for r in results[:3]:
            node = r["node"]
            neighbors, edges = await node_repo.get_neighbors(node.id)
            for neighbor in neighbors:
                if neighbor.id not in visited_node_ids:
                    visited_node_ids.add(neighbor.id)
                    expanded_results.append(
                        {
                            "node": neighbor,
                            "score": 0.0,
                            "relationship": _find_edge_type(
                                edges, node.id, neighbor.id
                            ),
                        }
                    )

    context = _build_trace_context(expanded_results)
    llm = get_llm_provider()

    instructions = (
        "Trace the code flow step-by-step. "
        "Show the execution path from entry point through function calls. "
        "Reference specific files and line numbers. "
        "Distinguish observed code from inference."
    )

    answer = await llm.generate(
        context=context, query=query, instructions=instructions
    )

    sources = [
        {
            "file_path": r["node"].file_path,
            "symbol_name": r["node"].symbol_name,
            "start_line": r["node"].start_line,
            "end_line": r["node"].end_line,
        }
        for r in expanded_results
    ]

    return {"answer": answer, "sources": sources}


def _build_trace_context(results: list[dict]) -> str:
    parts = []
    for r in results:
        node = r["node"]
        rel = r.get("relationship")
        rel_str = f" [via {rel.value}]" if rel else ""
        parts.append(
            f"## {node.symbol_type.value}: {node.symbol_name}{rel_str}\n"
            f"File: {node.file_path}:{node.start_line}-{node.end_line}\n"
            f"```{node.language}\n{node.source_code}\n```\n"
        )
    return "\n".join(parts)


def _find_edge_type(
    edges: list, source_id: uuid.UUID, target_id: uuid.UUID
) -> EdgeType | None:
    for e in edges:
        if e.source_id == source_id and e.target_id == target_id:
            return e.edge_type
        if e.source_id == target_id and e.target_id == source_id:
            return e.edge_type
    return None
