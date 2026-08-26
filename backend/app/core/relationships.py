import re
from dataclasses import dataclass

from app.models.enums import EdgeType


@dataclass
class ExtractedRelationship:
    target_name: str
    edge_type: EdgeType


def extract_relationships(source_code: str, language: str) -> list[ExtractedRelationship]:
    """Extract call/import relationships from source code."""
    if language == "python":
        return _extract_python_relationships(source_code)
    elif language in ("javascript", "typescript"):
        return _extract_js_ts_relationships(source_code)
    return []


def _extract_python_relationships(source_code: str) -> list[ExtractedRelationship]:
    rels: list[ExtractedRelationship] = []

    for match in re.finditer(r"^\s*import\s+([\w.]+)", source_code, re.MULTILINE):
        rels.append(
            ExtractedRelationship(target_name=match.group(1), edge_type=EdgeType.IMPORTS)
        )

    for match in re.finditer(r"^\s*from\s+([\w.]+)\s+import", source_code, re.MULTILINE):
        rels.append(
            ExtractedRelationship(target_name=match.group(1), edge_type=EdgeType.IMPORTS)
        )

    for match in re.finditer(r"(\w+)\s*\(", source_code):
        name = match.group(1)
        if name in (
            "if", "for", "while", "with", "return", "print", "len",
            "range", "str", "int", "float", "list", "dict", "set",
            "tuple", "type", "isinstance",
        ):
            continue
        rels.append(ExtractedRelationship(target_name=name, edge_type=EdgeType.CALLS))

    return rels


def _extract_js_ts_relationships(source_code: str) -> list[ExtractedRelationship]:
    rels: list[ExtractedRelationship] = []

    for match in re.finditer(r'import\s+.*?\s+from\s+["\']([^"\']+)["\']', source_code):
        rels.append(
            ExtractedRelationship(target_name=match.group(1), edge_type=EdgeType.IMPORTS)
        )

    for match in re.finditer(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)', source_code):
        rels.append(
            ExtractedRelationship(target_name=match.group(1), edge_type=EdgeType.IMPORTS)
        )

    for match in re.finditer(r"(\w+)\s*\(", source_code):
        name = match.group(1)
        if name in ("if", "for", "while", "switch", "return", "console", "require", "import"):
            continue
        rels.append(ExtractedRelationship(target_name=name, edge_type=EdgeType.CALLS))

    return rels
