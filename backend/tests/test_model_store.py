from pathlib import Path

import pytest

from app import model_store as ms
from app.model_store import ModelConfig, ModelStore


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Return a ModelStore backed by a temp file so real models.json is untouched."""
    fake = tmp_path / "models.json"
    monkeypatch.setattr(ms, "MODELS_FILE", fake)
    return ModelStore()


def _config(**overrides) -> ModelConfig:
    base = dict(
        name="gemini-test",
        type="cloud",
        provider="gemini",
        llm_model="gemini-2.5-flash",
        embedding_model="text-embedding-004",
    )
    base.update(overrides)
    return ModelConfig(**base)


class TestModelStoreCrud:
    def test_add_and_list(self, store: ModelStore):
        model = store.add(_config())
        assert len(store.list()) == 1
        assert store.get(model.id) is not None

    def test_get_returns_none_for_missing(self, store: ModelStore):
        assert store.get("does-not-exist") is None

    def test_update(self, store: ModelStore):
        model = store.add(_config())
        updated = store.update(model.id, {"llm_model": "gemini-2.5-pro"})
        assert updated is not None
        assert updated.llm_model == "gemini-2.5-pro"

    def test_delete(self, store: ModelStore):
        model = store.add(_config())
        assert store.delete(model.id) is True
        assert len(store.list()) == 0

    def test_delete_missing_returns_false(self, store: ModelStore):
        assert store.delete("nope") is False

    def test_persists_to_disk(self, store: ModelStore, tmp_path: Path):
        store.add(_config())
        assert (tmp_path / "models.json").exists()

    def test_load_reads_existing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        import json

        fake = tmp_path / "models.json"
        model = _config()
        fake.write_text(json.dumps([model.model_dump()]), encoding="utf-8")
        monkeypatch.setattr(ms, "MODELS_FILE", fake)
        loaded = ModelStore()
        assert len(loaded.list()) == 1
        assert loaded.list()[0].name == "gemini-test"


class TestModelStoreActive:
    def test_set_active_deactivates_others(self, store: ModelStore):
        a = store.add(_config(name="a"))
        b = store.add(_config(name="b"))
        store.set_active(b.id)
        assert store.get_active().id == b.id
        assert store.get(a.id).active is False

    def test_get_active_none_when_none_active(self, store: ModelStore):
        assert store.get_active() is None

    def test_new_model_not_active_by_default(self, store: ModelStore):
        m = store.add(_config())
        assert m.active is False


class TestSetActiveProvider:
    """PUT /api/config/providers routes through this, so it must persist."""

    def test_activates_matching_existing_provider(self, store: ModelStore):
        gem = store.add(_config(name="gem", provider="gemini"))
        oll = store.add(
            _config(name="oll", provider="ollama", type="local", base_url="http://x:11434")
        )
        store.set_active(gem.id)

        result = store.set_active_provider("ollama")

        assert result is not None
        assert result.provider == "ollama"
        assert result.id == oll.id
        assert store.get(gem.id).active is False
        assert store.get(oll.id).active is True

    def test_is_case_insensitive(self, store: ModelStore):
        oll = store.add(_config(name="oll", provider="ollama", type="local"))
        store.set_active_provider("OLLAMA")
        assert store.get_active().provider == "ollama"
        assert store.get(oll.id).active is True

    def test_synthesises_config_when_provider_absent(self, store: ModelStore):
        """A provider that was never configured still becomes active."""
        assert store.get_active() is None

        result = store.set_active_provider("ollama")

        assert result is not None
        assert result.provider == "ollama"
        assert result.active is True
        assert len(store.list()) == 1

    def test_synthesised_gemini_config_carries_api_key(self, store: ModelStore):
        result = store.set_active_provider("gemini")
        assert result is not None
        assert result.provider == "gemini"
        assert result.type == "cloud"

    def test_selection_survives_reload(self, store: ModelStore, tmp_path: Path):
        """BUG-004 regression: the selection must be durable."""
        store.add(_config(name="gem", provider="gemini"))
        store.set_active_provider("ollama")

        reloaded = ModelStore()
        active = reloaded.get_active()
        assert active is not None
        assert active.provider == "ollama"

    def test_unknown_provider_raises(self, store: ModelStore):
        with pytest.raises(ValueError, match="Unknown provider"):
            store.set_active_provider("not-a-provider")
