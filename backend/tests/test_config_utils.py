import pytest

from app import model_store as ms
from app.config import (
    get_active_embedding_provider,
    get_active_llm_provider,
    set_active_embedding_provider,
    set_active_llm_provider,
)
from app.exceptions import InvalidUUIDError
from app.model_store import ModelStore
from app.utils import parse_uuid


@pytest.fixture
def no_active_model(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Isolate from the real models.json so only the process globals are set.

    get_active_*_provider() consults the durable model store first; these tests
    exercise the global fallback, so the store must report no active model.
    """
    monkeypatch.setattr(ms, "MODELS_FILE", tmp_path / "models.json")
    store = ModelStore()  # empty -> get_active() is None
    monkeypatch.setattr("app.model_store.model_store", store)
    return store


class TestActiveProviders:
    def test_set_and_get_llm(self, no_active_model):
        set_active_llm_provider("OpenAI")
        try:
            assert get_active_llm_provider() == "openai"
        finally:
            set_active_llm_provider("ollama")

    def test_set_and_get_embedding(self, no_active_model):
        set_active_embedding_provider("Ollama")
        try:
            assert get_active_embedding_provider() == "ollama"
        finally:
            set_active_embedding_provider("ollama")


class TestParseUuid:
    def test_valid_uuid(self):
        u = "123e4567-e89b-12d3-a456-426614174000"
        assert str(parse_uuid(u)) == u

    def test_invalid_uuid_raises(self):
        with pytest.raises(InvalidUUIDError):
            parse_uuid("not-a-uuid")
