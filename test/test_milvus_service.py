from weschatbot.services.collection_service import CollectionService
import pytest

from weschatbot.services.document.index_document_service import IndexDocumentService, PipelineMilvusStore
from weschatbot.services.document.converting import DocumentConverter
from weschatbot.utils.config import config


@pytest.fixture(scope="module")
def milvus_service():
    milvus_service = CollectionService("localhost", 19530)
    assert milvus_service is not None
    return milvus_service


@pytest.fixture(scope="module")
def index_document_service():
    converter = DocumentConverter()
    pipeline = PipelineMilvusStore(collection_name="xxx",
                                   milvus_host=config["milvus"]["host"],
                                   milvus_port=config["milvus"]["port"])
    indexer = IndexDocumentService(converter=converter, pipeline=pipeline, collection_name="xxx",
                                   collection_id=2)
    return indexer


def test_all_collections(milvus_service):
    collections = milvus_service.all_collections()
    assert len(collections) > 0
    assert collections is not None


def test_get_entities(milvus_service):
    entities = milvus_service.get_entities("westaco_documents")
    assert entities is not None


def test_delete_milvus_collection(milvus_service):
    milvus_service.delete_milvus_collection("xxx")


def test_all_documents(milvus_service):
    res = milvus_service.all_documents()
    print(res)


def test_get_documents_by_collection_id(milvus_service):
    res = milvus_service.get_documents_by_collection_id(2)
    print(res)


def test_mark_in_progress(index_document_service):
    index_document_service.mark_in_progress()
