import enum


class SymbolType(str, enum.Enum):
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class EdgeType(str, enum.Enum):
    IMPORTS = "imports"
    CALLS = "calls"
    DEFINES = "defines"
    CONTAINS = "contains"
    REFERENCES = "references"
    INHERITS = "inherits"


class IndexingStatus(str, enum.Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"
