import enum


class SymbolType(enum.StrEnum):
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class EdgeType(enum.StrEnum):
    IMPORTS = "imports"
    CALLS = "calls"
    DEFINES = "defines"
    CONTAINS = "contains"
    REFERENCES = "references"
    INHERITS = "inherits"


class IndexingStatus(enum.StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
