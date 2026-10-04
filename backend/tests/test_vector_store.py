"""Tests for shared-collection safety.

BUG-012: ensure_collection() used to delete the whole Qdrant collection on every
index run. Because the collection is shared by every repository, indexing one
repository destroyed every other repository's vectors.
"""

from qdrant_client import models as qm

from app.embedding.vector_store import QdrantVectorStore


class FakeVectorParams:
    def __init__(self, size):
        self.size = size


class FakeCollectionDescription:
    """Mirrors qdrant_client's CollectionDescription, which only has a name."""

    def __init__(self, name):
        self.name = name


class FakeClient:
    def __init__(self, collections, size=768):
        self._collections = collections
        self._size = size
        self.deleted = []
        self.created = []
        self.indexed = []
        self.get_collection_calls = 0

    async def get_collections(self):
        return type(
            "R",
            (),
            {"collections": [FakeCollectionDescription(n) for n in self._collections]},
        )()

    async def get_collection(self, collection_name):
        self.get_collection_calls += 1
        vectors = FakeVectorParams(self._size)
        config = type("Cfg", (), {"params": type("P", (), {"vectors": vectors})()})()
        return type("Info", (), {"config": config})()

    async def delete_collection(self, collection_name):
        self.deleted.append(collection_name)
        self._collections = [c for c in self._collections if c != collection_name]

    async def create_collection(self, collection_name, vectors_config):
        self.created.append((collection_name, vectors_config.size))
        self._size = vectors_config.size

    async def create_payload_index(self, collection_name, field_name, field_schema):
        self.indexed.append((collection_name, field_name))

    async def delete(self, collection_name, points_selector):
        self.deleted.append((collection_name, "delete"))


def make_store(collections, size=768):
    store = QdrantVectorStore.__new__(QdrantVectorStore)
    client = FakeClient(collections, size)
    store.client = client
    return store, client


class TestEnsureCollectionPreservesExisting:
    async def test_existing_collection_is_not_deleted(self):
        """The core regression: indexing must not drop other repositories."""
        store, client = make_store(["code_embeddings"])

        await store.ensure_collection("code_embeddings", 768)

        assert client.deleted == [], "existing collection must never be deleted"
        assert client.created == []
        assert client.indexed == []

    async def test_missing_collection_is_created(self):
        store, client = make_store([])

        await store.ensure_collection("code_embeddings", 768)

        assert client.created == [("code_embeddings", 768)]
        assert client.indexed == [("code_embeddings", "repository_id")]

    async def test_dimension_mismatch_recreates(self):
        """Only a real dimension change justifies destroying the collection."""
        store, client = make_store(["code_embeddings"], size=768)

        await store.ensure_collection("code_embeddings", 1536)

        assert "code_embeddings" in client.deleted
        assert client.created == [("code_embeddings", 1536)]

    async def test_matching_dimensions_reuses(self):
        store, client = make_store(["code_embeddings"], size=768)

        await store.ensure_collection("code_embeddings", 768)

        assert client.deleted == []
        assert client.created == []


class TestDeleteByRepository:
    async def test_targets_a_filtered_delete_not_a_collection_drop(self):
        store, client = make_store(["code_embeddings"])
        repo_id = "11111111-1111-1111-1111-111111111111"

        await store.delete_by_repository("code_embeddings", repo_id)

        # A plain string would mean the collection itself was dropped.
        assert client.deleted == [("code_embeddings", "delete")]

    async def test_filter_selects_repository_id(self):
        store, client = make_store(["code_embeddings"])
        captured = {}

        async def capture(collection_name, points_selector):
            captured["selector"] = points_selector

        client.delete = capture
        await store.delete_by_repository("code_embeddings", "abc")

        selector = captured["selector"]
        assert isinstance(selector, qm.FilterSelector)
        condition = selector.filter.must[0]
        assert condition.key == "repository_id"
        assert condition.match.value == "abc"