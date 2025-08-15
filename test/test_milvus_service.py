from weschatbot.services.collection_service import CollectionService
import pytest


@pytest.fixture(scope="module")
def milvus_service():
    milvus_service = CollectionService("localhost", 19530)
    assert milvus_service is not None
    return milvus_service


def test_all_collections(milvus_service):
    collections = milvus_service.all_collections()
    assert len(collections) > 0
    assert collections is not None


def test_get_entities(milvus_service):
    entities = milvus_service.get_entities("westaco_documents")
    assert entities is not None
