import logging

from pymilvus import (
    connections, FieldSchema, CollectionSchema, DataType, Collection, utility
)
from sentence_transformers import SentenceTransformer

from weschatbot.utils.config import config

logger = logging.getLogger(__name__)


def main():
    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))

    fields = [
        FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096)
    ]
    schema = CollectionSchema(fields, "Knowledge base collection")

    collection_name = "enterprise_kb"
    if collection_name in [col for col in utility.list_collections()]:
        kb_collection = Collection(collection_name)
    else:
        kb_collection = Collection(collection_name, schema)

    model = SentenceTransformer('all-mpnet-base-v2')

    with open("data/procedure.txt", "r") as f:
        documents = f.readlines()

    embeddings = model.encode(documents, show_progress_bar=True)

    entities = [
        [emb.tolist() for emb in embeddings],
        documents
    ]

    insert_result = kb_collection.insert(entities)
    logger.info("Inserted data:", insert_result.primary_keys)

    kb_collection.create_index(field_name="embedding",
                               index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}})


def delete_collection(collection_name):
    from pymilvus import connections, utility

    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))

    if collection_name in utility.list_collections():
        utility.drop_collection(collection_name)
        logger.info(f"Collection '{collection_name}' is successfully deleted.")
    else:
        logger.info(f"Collection '{collection_name}' is not exist.")


def show_collection_data(collection_name):
    from pymilvus import connections, Collection

    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))

    collection = Collection(collection_name)

    results = collection.query(expr="pk >= 0", output_fields=["text", "embedding"])

    logger.info("Data in collection:")
    for data in results:
        logger.info(data)


if __name__ == '__main__':
    delete_collection("enterprise_kb")
    main()
