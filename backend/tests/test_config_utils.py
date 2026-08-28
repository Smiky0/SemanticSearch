import pytest

from app.config import (
    get_active_embedding_provider,
    get_active_llm_provider,
    set_active_embedding_provider,
    set_active_llm_provider,
)
from app.exceptions import InvalidUUIDError
from app.utils import parse_uuid


class TestActiveProviders:
    def test_set_and_get_llm(self):
        set_active_llm_provider("OpenAI")
        assert get_active_llm_provider() == "openai"

    def test_set_and_get_embedding(self):
        set_active_embedding_provider("Ollama")
        assert get_active_embedding_provider() == "ollama"


class TestParseUuid:
    def test_valid_uuid(self):
        u = "123e4567-e89b-12d3-a456-426614174000"
        assert str(parse_uuid(u)) == u

    def test_invalid_uuid_raises(self):
        with pytest.raises(InvalidUUIDError):
            parse_uuid("not-a-uuid")
