"""Contract checks for the real Qdrant client model.

The unit fakes in test_vector_store.py modelled CollectionDescription as
carrying a `.config` attribute. It does not — the real object only has `.name`,
and the vector config lives on get_collection(). That mismatch let an
AttributeError through the unit suite and failed every index run in the
container. These tests pin the real attribute paths so the fakes cannot drift
again.
"""

import pytest
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest


class TestCollectionDescriptionShape:
    def test_list_description_only_exposes_name(self):
        """Regression guard: CollectionDescription has no .config."""
        desc = rest.CollectionDescription(name="code_embeddings")
        assert desc.name == "code_embeddings"
        assert not hasattr(desc, "config")

    def test_full_info_model_declares_config_field(self):
        """The code reads info.config.params.vectors.size."""
        assert "config" in rest.CollectionInfo.model_fields


@pytest.mark.integration
class TestAgainstLiveQdrant:
    """Requires a reachable Qdrant. Skipped unless QDRANT_URL is set."""

    @pytest.fixture
    async def client(self):
        import os

        url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
        try:
            import httpx

            await httpx.AsyncClient(timeout=2).get(f"{url}/collections")
        except Exception as e:
            pytest.skip(f"Qdrant not reachable at {url}: {e}")

        c = AsyncQdrantClient(url=url)
        yield c
        await c.close()

    async def test_get_collections_entries_have_no_config(self, client):
        """This is the exact attribute access that broke indexing."""
        result = await client.get_collections()
        for desc in result.collections:
            assert hasattr(desc, "name")
            assert not hasattr(desc, "config"), (
                "CollectionDescription unexpectedly exposes .config; "
                "the code under test may be reading the wrong attribute"
            )

    async def test_get_collection_exposes_vector_size(self, client):
        result = await client.get_collections()
        if not result.collections:
            pytest.skip("no collections present")

        name = result.collections[0].name
        info = await client.get_collection(collection_name=name)
        size = info.config.params.vectors.size
        assert isinstance(size, int)
        assert size > 0