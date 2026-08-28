from app.core.relationships import extract_relationships
from app.models.enums import EdgeType


class TestPythonRelationships:
    def test_import_detection(self):
        rels = extract_relationships("import os\nfrom pathlib import Path\n", "python")
        imports = [r for r in rels if r.edge_type == EdgeType.IMPORTS]
        targets = {r.target_name for r in imports}
        assert "os" in targets
        assert "pathlib" in targets

    def test_call_detection(self):
        rels = extract_relationships("result = compute(x)\n", "python")
        calls = {r.target_name for r in rels if r.edge_type == EdgeType.CALLS}
        assert "compute" in calls

    def test_filters_builtin_calls(self):
        rels = extract_relationships("print('hi')\n", "python")
        calls = {r.target_name for r in rels if r.edge_type == EdgeType.CALLS}
        assert "print" not in calls


class TestJsTsRelationships:
    def test_es_module_import(self):
        rels = extract_relationships('import foo from "lodash";\n', "javascript")
        imports = {r.target_name for r in rels if r.edge_type == EdgeType.IMPORTS}
        assert "lodash" in imports

    def test_require_import(self):
        rels = extract_relationships('const fs = require("fs");\n', "javascript")
        imports = {r.target_name for r in rels if r.edge_type == EdgeType.IMPORTS}
        assert "fs" in imports

    def test_call_detection(self):
        rels = extract_relationships("doThing();\n", "typescript")
        calls = {r.target_name for r in rels if r.edge_type == EdgeType.CALLS}
        assert "doThing" in calls

    def test_unsupported_language_returns_empty(self):
        assert extract_relationships("fn main() {}", "rust") == []
