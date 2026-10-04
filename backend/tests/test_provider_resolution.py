"""Regression tests for provider resolution.

BUG-003/BUG-004: the API reported one provider while requests were routed to
another, and the selection was lost on restart. These tests pin the invariant
that the reported provider and the provider actually used are the same.
"""

import pytest

from app import config as config_mod


class _FakeActive:
    """Minimal stand-in for ModelConfig with the fields the resolvers read."""

    def __init__(
        self,
        provider: str,
        api_key: str = "",
        base_url: str = "",
        llm_model: str = "",
        embedding_model: str = "",
        embedding_dimensions: int = 768,
    ):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions


class _FakeStore:
    def __init__(self, active: _FakeActive | None):
        self._active = active

    def get_active(self):
        return self._active


@pytest.fixture
def fake_model_store(monkeypatch: pytest.MonkeyPatch):
    """Patch the model_store instance that config resolves through."""

    def _install(active_provider: str | None):
        if active_provider == "ollama":
            active = _FakeActive(
                "ollama",
                base_url="http://ollama:11434",
                llm_model="qwen2.5-coder:3b",
                embedding_model="nomic-embed-text",
            )
        elif active_provider == "gemini":
            active = _FakeActive(
                "gemini",
                api_key="test-key",
                llm_model="gemini-2.5-flash",
                embedding_model="text-embedding-004",
            )
        else:
            active = None

        store = _FakeStore(active)
        monkeypatch.setattr("app.model_store.model_store", store, raising=True)
        return store

    return _install


class TestReportedProviderMatchesModelStore:
    def test_llm_reports_active_model_provider(self, fake_model_store):
        fake_model_store("ollama")
        assert config_mod.get_active_llm_provider() == "ollama"

    def test_embedding_reports_active_model_provider(self, fake_model_store):
        fake_model_store("gemini")
        assert config_mod.get_active_embedding_provider() == "gemini"

    def test_model_store_wins_over_process_global(self, fake_model_store):
        """The persisted selection must beat the volatile global.

        This is the divergence that made the UI and the runtime disagree.
        """
        fake_model_store("ollama")
        config_mod.set_active_llm_provider("gemini")
        try:
            assert config_mod.get_active_llm_provider() == "ollama"
        finally:
            config_mod.set_active_llm_provider("gemini")


class TestFallbackWhenNoModelConfigured:
    def test_falls_back_to_process_global(self, fake_model_store):
        fake_model_store(None)
        config_mod.set_active_llm_provider("ollama")
        try:
            assert config_mod.get_active_llm_provider() == "ollama"
        finally:
            config_mod.set_active_llm_provider("gemini")

    def test_falls_back_to_settings_when_nothing_set(self, fake_model_store):
        fake_model_store(None)
        settings = config_mod.get_settings()
        config_mod.set_active_llm_provider(settings.llm_provider)
        assert config_mod.get_active_llm_provider() == settings.llm_provider


class TestProviderResolutionConsistency:
    async def test_llm_provider_follows_active_model(self, fake_model_store):
        """get_llm_provider must build the same provider config reports."""
        fake_model_store("ollama")

        from app.llm.provider import OllamaProvider, get_llm_provider

        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)
        assert config_mod.get_active_llm_provider() == "ollama"

    async def test_embedding_provider_follows_active_model(self, fake_model_store):
        fake_model_store("ollama")

        from app.embedding.provider import OllamaEmbeddingProvider, get_embedding_provider

        provider = get_embedding_provider()
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert config_mod.get_active_embedding_provider() == "ollama"


class TestConfigApiReportsWhatIsUsed:
    async def test_put_persists_through_model_store(
        self, fake_model_store, monkeypatch: pytest.MonkeyPatch
    ):
        """PUT /config/providers must survive a restart, not just a global."""
        store = fake_model_store(None)
        activated = []

        def set_active_provider(provider: str):
            activated.append(provider)
            store._active = _FakeActive(provider, base_url="http://ollama:11434")
            return store._active

        store.set_active_provider = set_active_provider  # type: ignore[attr-defined]

        from app.api.config_api import set_provider

        # config_api binds model_store at import time, so patching the model_store
        # module is not enough once anything has imported it first.
        monkeypatch.setattr("app.api.config_api.model_store", store, raising=True)

        result = await set_provider({"provider": "ollama"})

        assert activated == ["ollama"]
        assert result["active_llm"] == "ollama"
        assert result["active_embedding"] == "ollama"
        assert result["persisted"] is True

    async def test_put_rejects_unknown_provider(self, fake_model_store):
        from app.api.config_api import InvalidProviderError, set_provider

        with pytest.raises(InvalidProviderError):
            await set_provider({"provider": "definitely-not-real"})