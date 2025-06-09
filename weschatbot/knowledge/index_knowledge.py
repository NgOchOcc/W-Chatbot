from sentence_transformers import SentenceTransformer
from pymilvus import (
    connections, FieldSchema, CollectionSchema, DataType, Collection, utility
)


def main():
    connections.connect("default", host="localhost", port="19530")

    fields = [
        FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1024)
    ]
    schema = CollectionSchema(fields, "Knowledge base collection")

    collection_name = "enterprise_kb"
    if collection_name in [col.name for col in utility.list_collections()]:
        kb_collection = Collection(collection_name)
    else:
        kb_collection = Collection(collection_name, schema)

    model = SentenceTransformer('all-MiniLM-L6-v2')

    documents = [
        "In Milvus, we need a collection to store vectors and their associated metadata. You can think of it as a table in traditional SQL databases. When creating a collection, you can define schema and index params to configure vector specs such as dimensionality, index types and distant metrics. There are also complex concepts to optimize the index for vector search performance. For now, let’s just focus on the basics and use default for everything possible. At minimum, you only need to set the collection name and the dimension of the vector field of the collection.",
        "Since all data of Milvus Lite is stored in a local file, you can load all data into memory even after the program terminates, by creating a MilvusClient with the existing file. For example, this will recover the collections from “milvus_demo.db” file and continue to write data into it.",
        "Milvus Lite is great for getting started with a local python program. If you have large scale data or would like to use Milvus in production, you can learn about deploying Milvus on Docker and Kubernetes. All deployment modes of Milvus share the same API, so your client side code doesn’t need to change much if moving to another deployment mode. Simply specify the URI and Token of a Milvus server deployed anywhere:",
        "You can also conduct vector search while considering the values of the metadata (called “scalar” fields in Milvus, as scalar refers to non-vector data). This is done with a filter expression specifying certain criteria. Let’s see how to search and filter with the subject field in the following example."
        "Now we can do semantic searches by representing the search query text as vector, and conduct vector similarity search on Milvus.",
        "You can also conduct vector search while considering the values of the metadata (called “scalar” fields in Milvus, as scalar refers to non-vector data). This is done with a filter expression specifying certain criteria. Let’s see how to search and filter with the subject field in the following example."
    ]

    embeddings = model.encode(documents, show_progress_bar=True)

    entities = [
        [emb.tolist() for emb in embeddings],
        documents
    ]

    insert_result = kb_collection.insert(entities)
    print("Inserted data:", insert_result.primary_keys)

    kb_collection.create_index(field_name="embedding",
                               index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}})


def delete_collection(collection_name):
    from pymilvus import connections, utility

    connections.connect("default", host="localhost", port="19530")

    if collection_name in utility.list_collections():
        utility.drop_collection(collection_name)
        print(f"Collection '{collection_name}' is successfully deleted.")
    else:
        print(f"Collection '{collection_name}' is not exist.")

def show_collection_data(collection_name):
    from pymilvus import connections, Collection

    connections.connect("default", host="localhost", port="19530")

    collection = Collection(collection_name)

    results = collection.query(expr="pk >= 0", output_fields=["text", "embedding"])

    print("Data in collection:")
    for data in results:
        print(data)


if __name__ == '__main__':
    # delete_collection("enterprise_kb")
    show_collection_data("enterprise_kb")
    # main()
