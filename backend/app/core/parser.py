
import tree_sitter
import tree_sitter_languages
from tree_sitter import Parser

from app.models.enums import SymbolType

TREESITTER_LANG_MAP = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
}


class CodeUnit:
    def __init__(
        self,
        symbol_name: str,
        symbol_type: SymbolType,
        start_line: int,
        end_line: int,
        source_code: str,
        docstring: str | None = None,
        parent_symbol: str | None = None,
    ):
        self.symbol_name = symbol_name
        self.symbol_type = symbol_type
        self.start_line = start_line
        self.end_line = end_line
        self.source_code = source_code
        self.docstring = docstring
        self.parent_symbol = parent_symbol


def get_parser(language: str) -> Parser:
    lang_name = TREESITTER_LANG_MAP.get(language)
    if not lang_name:
        raise ValueError(f"Unsupported language: {language}")

    return tree_sitter_languages.get_parser(lang_name)


def extract_code_units(file_path: str, source_code: str, language: str) -> list[CodeUnit]:
    """Extract meaningful code units from source code using Tree-sitter."""
    parser = get_parser(language)
    tree = parser.parse(bytes(source_code, "utf8"))

    units: list[CodeUnit] = []
    lines = source_code.splitlines()

    if language == "python":
        units = _extract_python(tree, lines)
    elif language in ("javascript", "typescript"):
        units = _extract_js_ts(tree, lines)

    return units


def _extract_python(tree: tree_sitter.Tree, lines: list[str]) -> list[CodeUnit]:
    units: list[CodeUnit] = []
    root = tree.root_node

    def _extract_node(node: tree_sitter.Node, parent: str | None = None):
        if node.type in ("function_definition", "async_function_definition"):
            name = _get_name(node)
            if not name:
                return
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            source = _get_source(lines, start_line, end_line)
            docstring = _extract_python_docstring(node)
            units.append(
                CodeUnit(
                    symbol_name=name,
                    symbol_type=SymbolType.FUNCTION,
                    start_line=start_line + 1,
                    end_line=end_line + 1,
                    source_code=source,
                    docstring=docstring,
                    parent_symbol=parent,
                )
            )
            _walk_children(node, parent=name)

        elif node.type == "class_definition":
            name = _get_name(node)
            if not name:
                return
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            source = _get_source(lines, start_line, end_line)
            units.append(
                CodeUnit(
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=start_line + 1,
                    end_line=end_line + 1,
                    source_code=source,
                    parent_symbol=parent,
                )
            )
            _walk_children(node, parent=name)

    def _walk_children(node: tree_sitter.Node, parent: str | None = None):
        for child in node.children:
            if child.type in (
                "function_definition",
                "async_function_definition",
                "class_definition",
            ):
                _extract_node(child, parent=parent)

    _walk_children(root)

    return units


def _extract_python_docstring(node: tree_sitter.Node) -> str | None:
    """Extract docstring from a Python function/class node."""
    for child in node.children:
        if child.type == "block":
            for stmt in child.children:
                if stmt.type == "expression_statement":
                    expr = stmt.children[0] if stmt.children else None
                    if expr and expr.type == "string":
                        raw = _node_text(stmt)
                        return raw.strip().strip("\"'").strip('"""').strip("'''")
    return None


def _extract_js_ts(tree: tree_sitter.Tree, lines: list[str]) -> list[CodeUnit]:
    units: list[CodeUnit] = []
    root = tree.root_node

    def _extract_node(node: tree_sitter.Node, parent: str | None = None):
        node_type = node.type

        if node_type in ("function_declaration", "function"):
            name = _get_name(node)
            if not name:
                return
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            source = _get_source(lines, start_line, end_line)
            units.append(
                CodeUnit(
                    symbol_name=name,
                    symbol_type=SymbolType.FUNCTION,
                    start_line=start_line + 1,
                    end_line=end_line + 1,
                    source_code=source,
                    parent_symbol=parent,
                )
            )

        elif node_type == "class_declaration":
            name = _get_name(node)
            if not name:
                return
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            source = _get_source(lines, start_line, end_line)
            units.append(
                CodeUnit(
                    symbol_name=name,
                    symbol_type=SymbolType.CLASS,
                    start_line=start_line + 1,
                    end_line=end_line + 1,
                    source_code=source,
                    parent_symbol=parent,
                )
            )

        elif node_type == "method_definition":
            name = _get_name(node)
            if not name:
                return
            start_line = node.start_point[0]
            end_line = node.end_point[0]
            source = _get_source(lines, start_line, end_line)
            units.append(
                CodeUnit(
                    symbol_name=name,
                    symbol_type=SymbolType.METHOD,
                    start_line=start_line + 1,
                    end_line=end_line + 1,
                    source_code=source,
                    parent_symbol=parent,
                )
            )

        for child in node.children:
            _extract_node(child, parent=parent)

    _extract_node(root)
    return units


def _get_name(node: tree_sitter.Node) -> str | None:
    for child in node.children:
        if child.type == "identifier":
            return _node_text(child)
        if child.type == "field_identifier":
            return _node_text(child)
    return None


def _node_text(node: tree_sitter.Node) -> str:
    return node.text.decode("utf8") if node.text else ""


def _get_source(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start : end + 1])
