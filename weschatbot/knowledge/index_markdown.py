import os
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore

# Config conection Milvus
milvus_host = "localhost"
milvus_port = 19530
collection_name = "enterprise_kb"

# 1. Read and chunk file
reader = SimpleDirectoryReader(
    input_dir="data",  
    required_exts=[".md"],
    recursive=True
)
documents = reader.load_data()

# 2. Initial embedding model
embed_model = HuggingFaceEmbedding(model_name="all-mpnet-base-v2")

# 3. Initial vector store Milvus
vector_store = MilvusVectorStore(
    uri=f"http://{milvus_host}:{milvus_port}",
    collection_name=collection_name,
    dim=768,     
    overwrite=True 
)

storage_context = StorageContext.from_defaults(vector_store=vector_store)

# 4. Create index and insert to Milvus
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context,
    embed_model=embed_model,
    show_progress=True
)

