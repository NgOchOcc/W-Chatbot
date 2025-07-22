from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore
from pymilvus import connections, utility
from weschatbot.utils.config import config

class ModelConfig:
    def __init__(self, model_name='qwen'):
        QWEN_MODEL = {
            'model_name': 'Qwen/Qwen3-Embedding-0.6B',
            'dim': 1024
        }
        
        MPNET_BASE = {
            'model_name': 'all-mpnet-base-v2',
            'dim': 768
        }
        if model_name == 'qwen':
            self.model = QWEN_MODEL
        else:
            self.model = MPNET_BASE
        

def main():
    model = ModelConfig()
    
    # Config connection Milvus from config file
    milvus_host = config["milvus"]["host"]
    milvus_port = int(config["milvus"]["port"])
    collection_name = "enterprise_kb"
    
    # 1. Read and chunk files (text files instead of markdown)
    reader = SimpleDirectoryReader(
        input_dir="data",
        required_exts=[".md"], 
        recursive=True
    )
    documents = reader.load_data()
    
    # 2. Initialize embedding model
    embed_model = HuggingFaceEmbedding(model_name=model.model['model_name'])
    
    # 3. Initialize vector store Milvus
    vector_store = MilvusVectorStore(
        uri=f"http://{milvus_host}:{milvus_port}",
        collection_name=collection_name,
        dim=model.model['dim'],
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
    
    print(f"Successfully created index for collection: {collection_name}")

def delete_collection(collection_name):
    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))
    if collection_name in utility.list_collections():
        utility.drop_collection(collection_name)
        print(f"Collection '{collection_name}' is successfully deleted.")
    else:
        print(f"Collection '{collection_name}' does not exist.")

def show_collection_data(collection_name):
    from pymilvus import Collection
    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))
    collection = Collection(collection_name)
    results = collection.query(expr="pk >= 0", output_fields=["text", "embedding"])
    print("Data in collection:")
    for data in results:
        print(data)

if __name__ == '__main__':
    delete_collection("enterprise_kb")
    # show_collection_data("enterprise_kb")
    main()