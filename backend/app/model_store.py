import json
import uuid
from pathlib import Path
from typing import Literal

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

CONFIG_DIR = Path(__file__).parent.parent
MODELS_FILE = CONFIG_DIR / "models.json"


class ModelConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: Literal["cloud", "local"]
    provider: Literal["gemini", "openai", "anthropic", "ollama", "custom"]

    # Cloud specific
    api_key: str = ""

    # Local / custom specific
    base_url: str = ""

    # LLM settings
    llm_model: str = ""
    llm_max_tokens: int = 8192
    llm_temperature: float = 0.7

    # Embedding settings
    embedding_model: str = ""
    embedding_dimensions: int = 768

    # Advanced
    timeout: int = 120
    active: bool = False


class ModelStore:
    def __init__(self):
        self._models: list[ModelConfig] = []
        self._load()

    def _load(self):
        if MODELS_FILE.exists():
            try:
                data = json.loads(MODELS_FILE.read_text(encoding="utf-8"))
                self._models = [ModelConfig(**m) for m in data]
                logger.info("models_loaded", count=len(self._models))
            except Exception as e:
                logger.error("models_load_failed", error=str(e))
                self._models = []

    def _save(self):
        try:
            MODELS_FILE.write_text(
                json.dumps([m.model_dump() for m in self._models], indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("models_save_failed", error=str(e))

    def list(self) -> list[ModelConfig]:
        return list(self._models)

    def get(self, model_id: str) -> ModelConfig | None:
        for m in self._models:
            if m.id == model_id:
                return m
        return None

    def add(self, config: ModelConfig) -> ModelConfig:
        self._models.append(config)
        self._save()
        return config

    def update(self, model_id: str, updates: dict) -> ModelConfig | None:
        for i, m in enumerate(self._models):
            if m.id == model_id:
                updated = m.model_copy(update=updates)
                self._models[i] = updated
                self._save()
                return updated
        return None

    def delete(self, model_id: str) -> bool:
        for i, m in enumerate(self._models):
            if m.id == model_id:
                self._models.pop(i)
                self._save()
                return True
        return False

    def set_active(self, model_id: str) -> ModelConfig | None:
        for m in self._models:
            m.active = m.id == model_id
        self._save()
        return self.get(model_id)

    def get_active(self) -> ModelConfig | None:
        for m in self._models:
            if m.active:
                return m
        return None


model_store = ModelStore()
