class AppError(Exception):
    def __init__(self, message: str = "An unexpected error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class RepositoryNotFoundError(AppError):
    def __init__(self, identifier: str = ""):
        msg = f"Repository not found: {identifier}" if identifier else "Repository not found"
        super().__init__(msg, 404)


class SymbolNotFoundError(AppError):
    def __init__(self, identifier: str = ""):
        msg = f"Symbol not found: {identifier}" if identifier else "Symbol not found"
        super().__init__(msg, 404)


class InvalidUUIDError(AppError):
    def __init__(self, value: str = ""):
        super().__init__(f"Invalid identifier: {value}" if value else "Invalid identifier", 400)


class EmbeddingError(AppError):
    def __init__(self, message: str = "Embedding generation failed"):
        super().__init__(message, 502)


class VectorStoreError(AppError):
    def __init__(self, message: str = "Vector store operation failed"):
        super().__init__(message, 502)


class LLMError(AppError):
    def __init__(self, message: str = "LLM request failed"):
        super().__init__(message, 502)


class IndexingError(AppError):
    def __init__(self, message: str = "Indexing failed"):
        super().__init__(message, 500)
