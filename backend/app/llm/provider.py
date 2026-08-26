from abc import ABC, abstractmethod

import httpx
import structlog

from app.config import get_settings
from app.exceptions import LLMError

logger = structlog.get_logger()


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, context: str, query: str, instructions: str) -> str:
        ...


SYSTEM_INSTRUCTIONS = (
    "You are a code intelligence assistant. "
    "Answer questions about code using ONLY the provided context.\n\n"
    "Rules:\n"
    "- Only make claims supported by the retrieved code\n"
    "- Explicitly say when information is unavailable\n"
    "- Cite relevant files and symbols\n"
    "- Distinguish observed code from inference\n"
    "- Explain code in clear developer-friendly language\n"
    "- Do not invent functions, files, or relationships"
)


class GeminiProvider(LLMProvider):
    def __init__(self):
        settings = get_settings()
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model

    async def generate(self, context: str, query: str, instructions: str) -> str:
        prompt = (
            f"{SYSTEM_INSTRUCTIONS}\n\n{instructions}\n\n"
            f"## Code Context\n\n{context}\n\n## Question\n\n{query}"
        )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self._model}:generateContent"
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    params={"key": self._api_key},
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.HTTPStatusError as e:
            logger.error(
                "gemini_llm_http_error",
                status_code=e.response.status_code,
                model=self._model,
            )
            raise LLMError(
                f"LLM API returned status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("gemini_llm_timeout", model=self._model)
            raise LLMError("LLM request timed out") from e
        except httpx.ConnectError as e:
            logger.error("gemini_llm_connection_error", model=self._model)
            raise LLMError("Could not connect to LLM API") from e
        except (KeyError, IndexError) as e:
            logger.error("gemini_llm_unexpected_response", model=self._model, error=str(e))
            raise LLMError("LLM API returned unexpected response") from e


class OllamaProvider(LLMProvider):
    def __init__(self):
        settings = get_settings()
        self._url = settings.ollama_url.rstrip("/")
        self._model = settings.ollama_model

    async def generate(self, context: str, query: str, instructions: str) -> str:
        prompt = (
            f"{SYSTEM_INSTRUCTIONS}\n\n{instructions}\n\n"
            f"## Code Context\n\n{context}\n\n## Question\n\n{query}"
        )

        url = f"{self._url}/api/chat"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "user", "content": prompt},
                        ],
                        "stream": False,
                    },
                    timeout=300.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_llm_http_error",
                status_code=e.response.status_code,
                model=self._model,
            )
            raise LLMError(
                f"Ollama returned status {e.response.status_code}"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("ollama_llm_timeout", model=self._model)
            raise LLMError(
                "Ollama request timed out (300s). "
                "Model may be loading or too slow."
            ) from e
        except httpx.ConnectError as e:
            logger.error("ollama_llm_connection_error", model=self._model)
            raise LLMError(
                f"Could not connect to Ollama at {self._url}. "
                "Make sure Ollama is running (ollama serve)."
            ) from e
        except (KeyError, IndexError) as e:
            logger.error("ollama_llm_unexpected_response", model=self._model, error=str(e))
            raise LLMError("Ollama returned unexpected response") from e


def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider_name = settings.llm_provider.lower()
    if provider_name == "gemini":
        return GeminiProvider()
    if provider_name == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown LLM provider: {provider_name}. Supported: gemini, ollama")
