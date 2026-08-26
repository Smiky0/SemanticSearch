from abc import ABC, abstractmethod

import httpx
import structlog

from app.config import get_settings
from app.exceptions import EmbeddingError

logger = structlog.get_logger()


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def dimensions(self) -> int:
        ...


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions

    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:batchEmbedContents"
        )

        requests = [
            {
                "model": f"models/{self._model}",
                "content": {"parts": [{"text": t}]},
                "outputDimensionality": self._dimensions,
            }
            for t in texts
        ]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    params={"key": self._api_key},
                    json={"requests": requests},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return [item["values"] for item in data["embeddings"]]
        except httpx.HTTPStatusError as e:
            logger.error(
                "gemini_embedding_http_error",
                status_code=e.response.status_code,
                model=self._model,
            )
            raise EmbeddingError(
                f"Embedding API returned status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("gemini_embedding_timeout", model=self._model)
            raise EmbeddingError("Embedding request timed out") from e
        except httpx.ConnectError as e:
            logger.error("gemini_embedding_connection_error", model=self._model)
            raise EmbeddingError("Could not connect to embedding API") from e
        except KeyError as e:
            logger.error("gemini_embedding_unexpected_response", model=self._model)
            raise EmbeddingError("Embedding API returned unexpected response") from e


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str = "text-embedding-3-small"):
        self._model = model
        settings = get_settings()
        self._api_key = settings.openai_api_key
        self._dimensions = settings.embedding_dimensions

    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": self._model, "input": texts},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return [item["embedding"] for item in data["data"]]
        except httpx.HTTPStatusError as e:
            logger.error(
                "openai_embedding_http_error",
                status_code=e.response.status_code,
                model=self._model,
            )
            raise EmbeddingError(
                f"Embedding API returned status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("openai_embedding_timeout", model=self._model)
            raise EmbeddingError("Embedding request timed out") from e
        except httpx.ConnectError as e:
            logger.error("openai_embedding_connection_error", model=self._model)
            raise EmbeddingError("Could not connect to embedding API") from e
        except KeyError as e:
            logger.error("openai_embedding_unexpected_response", model=self._model)
            raise EmbeddingError("Embedding API returned unexpected response") from e


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self):
        settings = get_settings()
        self._url = settings.ollama_url.rstrip("/")
        self._model = settings.ollama_embedding_model
        self._dimensions = settings.embedding_dimensions

    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            embeddings = []
            async with httpx.AsyncClient() as client:
                for text in texts:
                    response = await client.post(
                        f"{self._url}/api/embed",
                        json={"model": self._model, "input": text},
                        timeout=60.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    embeddings.append(data["embeddings"][0])
            return embeddings
        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_embedding_http_error",
                status_code=e.response.status_code,
                model=self._model,
            )
            raise EmbeddingError(
                f"Ollama embedding returned status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("ollama_embedding_timeout", model=self._model)
            raise EmbeddingError("Ollama embedding request timed out") from e
        except httpx.ConnectError as e:
            logger.error("ollama_embedding_connection_error", model=self._model)
            raise EmbeddingError(
                f"Could not connect to Ollama at {self._url}. "
                "Make sure Ollama is running (ollama serve)."
            ) from e
        except (KeyError, IndexError) as e:
            logger.error("ollama_embedding_unexpected_response", model=self._model, error=str(e))
            raise EmbeddingError("Ollama returned unexpected embedding response") from e


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider.lower()
    if provider == "gemini":
        return GeminiEmbeddingProvider()
    if provider == "openai":
        return OpenAIEmbeddingProvider(model=settings.embedding_model)
    if provider == "ollama":
        return OllamaEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {provider}. Supported: gemini, openai, ollama")
