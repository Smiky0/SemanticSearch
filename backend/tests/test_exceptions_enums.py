
from app.exceptions import (
    AppError,
    EmbeddingError,
    IndexingError,
    InvalidUUIDError,
    LLMError,
    RepositoryNotFoundError,
    SymbolNotFoundError,
    VectorStoreError,
)
from app.models.enums import EdgeType, IndexingStatus, SymbolType


class TestAppError:
    def test_defaults(self):
        err = AppError()
        assert err.status_code == 500

    def test_custom(self):
        err = AppError("boom", 418)
        assert err.message == "boom"
        assert err.status_code == 418

    def test_subclasses_status_codes(self):
        assert RepositoryNotFoundError().status_code == 404
        assert SymbolNotFoundError().status_code == 404
        assert InvalidUUIDError().status_code == 400
        assert EmbeddingError().status_code == 502
        assert VectorStoreError().status_code == 502
        assert LLMError().status_code == 502
        assert IndexingError().status_code == 500


class TestEnums:
    def test_symbol_type_values(self):
        assert SymbolType.FILE.value == "file"
        assert SymbolType.MODULE.value == "module"
        assert SymbolType.CLASS.value == "class"
        assert SymbolType.FUNCTION.value == "function"
        assert SymbolType.METHOD.value == "method"

    def test_edge_type_values(self):
        assert EdgeType.IMPORTS.value == "imports"
        assert EdgeType.CALLS.value == "calls"
        assert EdgeType.INHERITS.value == "inherits"

    def test_indexing_status_values(self):
        assert IndexingStatus.COMPLETED.value == "completed"
        assert IndexingStatus.FAILED.value == "failed"
