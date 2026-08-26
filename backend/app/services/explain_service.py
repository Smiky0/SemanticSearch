import uuid

from app.llm.provider import get_llm_provider
from app.services.search_service import semantic_search


async def explain_query(repository_id: uuid.UUID, query: str) -> dict:
    results = await semantic_search(repository_id, query, limit=10)

    if not results:
        return {"answer": "No relevant code found for your query.", "sources": []}

    context = _build_context(results)
    llm = get_llm_provider()

    instructions = (
        "Provide a clear, step-by-step explanation of the code. "
        "Reference specific files and symbols. "
        "If the provided context is insufficient, say so."
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
        for r in results
    ]

    return {"answer": answer, "sources": sources}


def _build_context(results: list[dict]) -> str:
    parts = []
    for r in results:
        node = r["node"]
        doc = f"Docstring: {node.docstring}\n" if node.docstring else ""
        parts.append(
            f"## {node.symbol_type.value}: {node.symbol_name}\n"
            f"File: {node.file_path}:{node.start_line}-{node.end_line}\n"
            f"Language: {node.language}\n"
            f"{doc}"
            f"```{node.language}\n{node.source_code}\n```\n"
        )
    return "\n".join(parts)
