from abc import ABC, abstractmethod

import httpx
import structlog

from app.config import get_active_embedding_provider, get_settings
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
    def __init__(self, api_key: str = "", model: str = "", dimensions: int = 0):
        settings = get_settings()
        self._api_key = api_key or settings.gemini_api_key
        self._model = model or settings.embedding_model
        self._dimensions = dimensions or settings.embedding_dimensions

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
            logger.error("gemini_embedding_http_error", status_code=e.response.status_code)
            raise EmbeddingError(
                f"Gemini embedding failed with status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("gemini_embedding_timeout")
            raise EmbeddingError("Gemini embedding timed out") from e
        except httpx.ConnectError as e:
            logger.error("gemini_embedding_connection_error")
            raise EmbeddingError("Could not connect to Gemini API") from e
        except KeyError as e:
            logger.error("gemini_embedding_unexpected_response", error=str(e))
            raise EmbeddingError("Gemini embedding returned unexpected response") from e


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str = "", model: str = "", dimensions: int = 0):
        settings = get_settings()
        self._api_key = api_key or settings.openai_api_key
        self._model = model or settings.embedding_model
        self._dimensions = dimensions or settings.embedding_dimensions

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
            logger.error("openai_embedding_http_error", status_code=e.response.status_code)
            raise EmbeddingError(
                f"OpenAI embedding failed with status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("openai_embedding_timeout")
            raise EmbeddingError("OpenAI embedding timed out") from e
        except httpx.ConnectError as e:
            logger.error("openai_embedding_connection_error")
            raise EmbeddingError("Could not connect to OpenAI API") from e
        except (KeyError, IndexError) as e:
            logger.error("openai_embedding_unexpected_response", error=str(e))
            raise EmbeddingError("OpenAI embedding returned unexpected response") from e


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str = "", model: str = "", dimensions: int = 0):
        settings = get_settings()
        self._url = (base_url or settings.ollama_url).rstrip("/")
        self._model = model or settings.ollama_embedding_model
        self._dimensions = dimensions or settings.embedding_dimensions

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
            logger.error("ollama_embedding_http_error", status_code=e.response.status_code)
            raise EmbeddingError(
                f"Ollama embedding failed with status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("ollama_embedding_timeout")
            raise EmbeddingError("Ollama embedding timed out") from e
        except httpx.ConnectError as e:
            logger.error("ollama_embedding_connection_error")
            raise EmbeddingError(f"Could not connect to Ollama at {self._url}") from e
        except (KeyError, IndexError) as e:
            logger.error("ollama_embedding_unexpected_response", error=str(e))
            raise EmbeddingError("Ollama embedding returned unexpected response") from e


class CustomEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str, model: str = "", dimensions: int = 768):
        self._url = base_url.rstrip("/")
        self._model = model
        self._dimensions = dimensions

    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._url}/v1/embeddings",
                    json={"model": self._model, "input": texts},
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return [item["embedding"] for item in data["data"]]
        except httpx.HTTPStatusError as e:
            raise EmbeddingError(
                f"Custom embedding failed with status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            raise EmbeddingError("Custom embedding timed out") from e
        except httpx.ConnectError as e:
            raise EmbeddingError(f"Could not connect to custom embedding at {self._url}") from e
        except (KeyError, IndexError) as e:
            raise EmbeddingError("Custom embedding returned unexpected response") from e


def get_embedding_provider() -> EmbeddingProvider:
    from app.model_store import model_store

    active = model_store.get_active()
    if active:
        if active.provider == "gemini":
            return GeminiEmbeddingProvider(
                api_key=active.api_key,
                model=active.embedding_model,
                dimensions=active.embedding_dimensions,
            )
        if active.provider == "openai":
            return OpenAIEmbeddingProvider(
                api_key=active.api_key,
                model=active.embedding_model,
                dimensions=active.embedding_dimensions,
            )
        if active.provider == "ollama":
            return OllamaEmbeddingProvider(
                base_url=active.base_url,
                model=active.embedding_model,
                dimensions=active.embedding_dimensions,
            )
        if active.provider == "custom":
            return CustomEmbeddingProvider(
                base_url=active.base_url,
                model=active.embedding_model,
                dimensions=active.embedding_dimensions,
            )

    provider = get_active_embedding_provider()
    if provider == "gemini":
        return GeminiEmbeddingProvider()
    if provider == "openai":
        settings = get_settings()
        return OpenAIEmbeddingProvider(model=settings.embedding_model)
    if provider == "ollama":
        return OllamaEmbeddingProvider()
    raise ValueError(f"Unknown embedding provider: {provider}. Supported: gemini, openai, ollama")
