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
