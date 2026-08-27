import httpx
from fastapi import APIRouter

from app.config import (
    get_active_embedding_provider,
    get_active_llm_provider,
    get_settings,
    set_active_embedding_provider,
    set_active_llm_provider,
)
from app.exceptions import AppError

router = APIRouter()


class InvalidProviderError(AppError):
    def __init__(self, provider: str) -> None:
        super().__init__(
            f"Unsupported LLM provider: '{provider}'. "
            "Supported: gemini, ollama",
            status_code=400,
        )


async def _check_ollama_health(url: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{url.rstrip('/')}/api/tags", timeout=5.0)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            return {"available": True, "models": models, "error": None}
    except httpx.ConnectError:
        return {
            "available": False,
            "models": [],
            "error": "Ollama is not running. Start it with: ollama serve",
        }
    except Exception as e:
        return {"available": False, "models": [], "error": str(e)}


async def _check_gemini_health(api_key: str) -> dict:
    if not api_key:
        return {"available": False, "error": "No API key configured. Set GEMINI_API_KEY in .env"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": api_key},
                timeout=10.0,
            )
            resp.raise_for_status()
            return {"available": True, "error": None}
    except httpx.ConnectError:
        return {"available": False, "error": "Cannot reach Google API. Check your network."}
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            return {"available": False, "error": "Invalid API key."}
        return {"available": False, "error": f"API error: {e.response.status_code}"}
    except Exception as e:
        return {"available": False, "error": str(e)}


@router.get("/config/providers")
async def get_providers():
    settings = get_settings()

    gemini_health = await _check_gemini_health(settings.gemini_api_key)
    ollama_health = await _check_ollama_health(settings.ollama_url)

    providers = [
        {
            "id": "gemini",
            "label": "Gemini (Cloud)",
            "type": "cloud",
            "model": settings.gemini_model,
            "available": gemini_health["available"],
            "error": gemini_health.get("error"),
        },
        {
            "id": "ollama",
            "label": "Ollama (Local)",
            "type": "local",
            "model": settings.ollama_model,
            "available": ollama_health["available"],
            "error": ollama_health.get("error"),
            "ollama_models": ollama_health.get("models", []),
        },
    ]

    return {
        "active_llm": get_active_llm_provider(),
        "active_embedding": get_active_embedding_provider(),
        "providers": providers,
    }


@router.put("/config/providers")
async def set_provider(body: dict):
    provider = body.get("provider", "").strip().lower()
    if provider not in ("gemini", "ollama"):
        raise InvalidProviderError(provider)
    set_active_llm_provider(provider)
    set_active_embedding_provider(provider)
    return {"active_llm": provider, "active_embedding": provider}
