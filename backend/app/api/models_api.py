import httpx
from fastapi import APIRouter

from app.exceptions import AppError
from app.model_store import ModelConfig, model_store

router = APIRouter()


class ModelNotFoundError(AppError):
    def __init__(self, model_id: str = ""):
        super().__init__(f"Model not found: {model_id}" if model_id else "Model not found", 404)


class InvalidModelError(AppError):
    def __init__(self, message: str = "Invalid model configuration"):
        super().__init__(message, 400)


@router.get("/models")
async def list_models():
    models = model_store.list()
    return {"models": [m.model_dump() for m in models]}


@router.post("/models")
async def create_model(body: dict):
    required = ["name", "type", "provider"]
    for field in required:
        if not body.get(field):
            raise InvalidModelError(f"Missing required field: {field}")

    if body["type"] not in ("cloud", "local"):
        raise InvalidModelError("type must be 'cloud' or 'local'")
    if body["provider"] not in ("gemini", "openai", "anthropic", "ollama", "custom"):
        raise InvalidModelError("provider must be gemini, openai, anthropic, ollama, or custom")

    config = ModelConfig(**{k: v for k, v in body.items() if k in ModelConfig.model_fields})
    model = model_store.add(config)
    return model.model_dump()


@router.put("/models/{model_id}")
async def update_model(model_id: str, body: dict):
    model = model_store.get(model_id)
    if not model:
        raise ModelNotFoundError(model_id)

    allowed = {
        "name", "type", "provider", "api_key", "base_url",
        "llm_model", "llm_max_tokens", "llm_temperature",
        "embedding_model", "embedding_dimensions", "timeout", "active",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    updated = model_store.update(model_id, updates)
    return updated.model_dump()


@router.delete("/models/{model_id}")
async def delete_model(model_id: str):
    if not model_store.delete(model_id):
        raise ModelNotFoundError(model_id)
    return {"status": "deleted"}


@router.post("/models/{model_id}/activate")
async def activate_model(model_id: str):
    model = model_store.set_active(model_id)
    if not model:
        raise ModelNotFoundError(model_id)
    return model.model_dump()


@router.get("/models/{model_id}/health")
async def check_model_health(model_id: str):
    model = model_store.get(model_id)
    if not model:
        raise ModelNotFoundError(model_id)

    if model.provider == "ollama":
        url = (model.base_url or "http://localhost:11434").rstrip("/")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{url}/api/tags", timeout=5.0)
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                return {"available": True, "models": models, "error": None}
        except httpx.ConnectError:
            return {"available": False, "models": [], "error": "Ollama is not running"}
        except Exception as e:
            return {"available": False, "models": [], "error": str(e)}

    if model.provider == "gemini":
        if not model.api_key:
            return {"available": False, "error": "No API key"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": model.api_key},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return {"available": True, "error": None}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                return {"available": False, "error": "Invalid API key"}
            return {"available": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    if model.provider == "openai":
        if not model.api_key:
            return {"available": False, "error": "No API key"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {model.api_key}"},
                    timeout=10.0,
                )
                resp.raise_for_status()
                return {"available": True, "error": None}
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                return {"available": False, "error": "Invalid API key"}
            return {"available": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    if model.provider == "anthropic":
        if not model.api_key:
            return {"available": False, "error": "No API key"}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": model.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                return {"available": True, "error": None}
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                return {"available": False, "error": "Invalid API key"}
            return {"available": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            return {"available": False, "error": str(e)}

    # Custom provider - just check if base_url is reachable
    if not model.base_url:
        return {"available": False, "error": "No base URL configured"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(model.base_url.rstrip("/"), timeout=5.0)
            return {"available": resp.status_code < 500, "error": None}
    except Exception as e:
        return {"available": False, "error": str(e)}
