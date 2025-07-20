from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from weschatbot.utils.config import config


# Cấu hình kết nối Milvus
milvus_host = "localhost"
milvus_port = 19530
collection_name = "enterprise_kb"

# milvus_host = config["milvus"]["host"]
# milvus_port = int(config["milvus"]["port"])
# collection_name = "enterprise_kb"

# Khởi tạo vector store Milvus
vector_store = MilvusVectorStore(
    uri=f"http://{milvus_host}:{milvus_port}",
    collection_name=collection_name,
    dim=768,  # Qwen/Qwen3-Embedding-0.6B có dim=1024
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

def retrieve(query, top_k=5):
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    print(f"Top {top_k} results for query: '{query}'\n")
    for i, node in enumerate(nodes, 1):
        print(f"--- Result {i} ---")
        print(node.get_content())
        print()

if __name__ == "__main__":
    user_query = input("Nhập câu hỏi: ")
    retrieve(user_query, top_k=5) 