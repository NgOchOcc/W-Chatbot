from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from sentence_transformers import SentenceTransformer
from pymilvus import (
    connections, FieldSchema, CollectionSchema, DataType, Collection, utility
)
from weschatbot.utils.config import config

def main():
    # Kết nối tới Milvus
    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))
    
    # Định nghĩa schema cho collection
    fields = [
        FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096)
    ]
    schema = CollectionSchema(fields, "Knowledge base collection")
    collection_name = "enterprise_kb"
    
    # Tạo hoặc lấy collection
    if collection_name in [col for col in utility.list_collections()]:
        kb_collection = Collection(collection_name)
    else:
        kb_collection = Collection(collection_name, schema)
    
    # Load và encode documents
    model = SentenceTransformer('all-mpnet-base-v2')
    with open("data/procedure.txt", "r", encoding="utf-8") as f:
        documents = f.readlines()
    
    # Loại bỏ dòng trống và strip whitespace
    documents = [doc.strip() for doc in documents if doc.strip()]
    
    embeddings = model.encode(documents, show_progress_bar=True)
    
    # Insert data vào Milvus
    entities = [
        [emb.tolist() for emb in embeddings],
        documents
    ]
    insert_result = kb_collection.insert(entities)
    print("Inserted data:", insert_result.primary_keys)
    
    # Tạo index
    kb_collection.create_index(
        field_name="embedding",
        index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
    )

def retrieve_with_llamaindex(query, top_k=5):
    """
    Sử dụng LlamaIndex để retrieve documents như trong file retrieve.py
    """
    # Cấu hình kết nối Milvus
    milvus_host = config["milvus"]["host"]
    milvus_port = int(config["milvus"]["port"])
    collection_name = "enterprise_kb"
    
    # Khởi tạo vector store Milvus
    vector_store = MilvusVectorStore(
        uri=f"http://{milvus_host}:{milvus_port}",
        collection_name=collection_name,
        dim=768,
        overwrite=False
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Khởi tạo embedding model (phải giống lúc insert)
    embed_model = HuggingFaceEmbedding(model_name="all-mpnet-base-v2")
    
    # Tạo index object
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
        embed_model=embed_model,
    )
    
    # Thực hiện retrieve
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    
    print(f"Top {top_k} results for query: '{query}'\n")
    for i, node in enumerate(nodes, 1):
        print(f"--- Result {i} ---")
        print(node.get_content())
        print()
    
    return nodes

def delete_collection(collection_name):
    """Xóa collection"""
    from pymilvus import connections, utility
    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))
    
    if collection_name in utility.list_collections():
        utility.drop_collection(collection_name)
        print(f"Collection '{collection_name}' is successfully deleted.")
    else:
        print(f"Collection '{collection_name}' does not exist.")

def show_collection_data(collection_name):
    """Hiển thị dữ liệu trong collection"""
    from pymilvus import connections, Collection
    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))
    
    collection = Collection(collection_name)
    results = collection.query(expr="pk >= 0", output_fields=["text", "embedding"])
    
    print("Data in collection:")
    for data in results:
        print(data)

def interactive_retrieve():
    """Chế độ tương tác để test retrieve"""
    while True:
        user_query = input("\nNhập câu hỏi (hoặc 'quit' để thoát): ")
        if user_query.lower() in ['quit', 'exit', 'q']:
            break
        
        try:
            retrieve_with_llamaindex(user_query, top_k=5)
        except Exception as e:
            print(f"Lỗi khi retrieve: {e}")

if __name__ == '__main__':
    # Uncomment dòng dưới nếu muốn xóa collection cũ
    # delete_collection("enterprise_kb")
    
    # Tạo và insert data
    main()
    
    # Test retrieve
    print("\n" + "="*50)
    print("Testing retrieve functionality...")
    print("="*50)
    
    # Test với một câu hỏi mẫu
    test_query = "quy trình"
    retrieve_with_llamaindex(test_query, top_k=3)
    
    # Chế độ tương tác
    interactive_retrieve()