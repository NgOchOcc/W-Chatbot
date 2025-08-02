from typing import List, Dict, Optional
from dataclasses import dataclass
from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore
from pymilvus import connections, Collection, utility

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.utils.config import config


@dataclass
class QueryResult:
    """Data class for query results"""
    query: str
    source_nodes: List[Dict]
    metadata: Dict


class DocumentQueryService(LoggingMixin):
    """Service for querying and retrieving documents from Milvus vector store"""
    
    def __init__(
        self,
        collection_name: str = "westaco_documents",
        embedding_model_name: str = "Qwen/Qwen3-Embedding-0.6B",
        embedding_dim: int = 1024,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ):
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name
        self.embedding_dim = embedding_dim
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        self.embed_model = HuggingFaceEmbedding(model_name=self.embedding_model_name)
        
        # self.milvus_host = config.get('milvus', 'host', fallback='localhost')
        # self.milvus_port = config.getint('milvus', 'port', fallback=19530)
        self.milvus_host = 'localhost'
        self.milvus_port = 19530
        
        self.vector_store = MilvusVectorStore(
            uri=f"http://{self.milvus_host}:{self.milvus_port}",
            collection_name=self.collection_name,
            dim=self.embedding_dim,
            overwrite=False
        )
        
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize the vector store index and retriever"""
        try:
            # Create index from existing vector store
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                embed_model=self.embed_model
            )
            
            # Configure retriever
            self.retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=self.top_k,
            )
            
            self.log.info(f"Index initialized for collection: {self.collection_name}")
            
        except Exception as e:
            self.log.error(f"Error initializing index: {str(e)}")
            raise
    
    def query(self, query_text: str, filter_metadata: Optional[Dict] = None) -> QueryResult:
        """
        Query the vector store and return relevant documents
        
        Args:
            query_text: The query string
            filter_metadata: Optional metadata filters
            
        Returns:
            QueryResult object containing the query results
        """
        try:
            # Use retriever to get similar chunks
            nodes = self.retriever.retrieve(query_text)
            
            # Apply similarity threshold
            filtered_nodes = [
                node for node in nodes 
                if node.score >= self.similarity_threshold
            ]
            
            # Extract source nodes
            source_nodes = []
            for node in filtered_nodes:
                source_nodes.append({
                    'text': node.node.text,
                    'score': node.score,
                    'metadata': node.node.metadata
                })
            
            # Create result object
            result = QueryResult(
                query=query_text,
                source_nodes=source_nodes,
                metadata={
                    'total_nodes': len(source_nodes),
                    'collection': self.collection_name
                }
            )
            
            self.log.info(f"Query executed successfully. Found {len(source_nodes)} relevant chunks.")
            return result
            
        except Exception as e:
            self.log.error(f"Error executing query: {str(e)}")
            raise
    
    def retrieve_similar_chunks(
        self,
        query_text: str,
        top_k: Optional[int] = None,
        return_metadata: bool = True
    ) -> List[Dict]:
        try:
            if top_k:
                retriever = VectorIndexRetriever(
                    index=self.index,
                    similarity_top_k=top_k
                )
            else:
                retriever = self.retriever
            
            nodes = retriever.retrieve(query_text)
            
            results = []
            for node in nodes:
                result = {
                    'text': node.node.text,
                    'score': node.score
                }
                
                if return_metadata:
                    result['metadata'] = node.node.metadata
                
                results.append(result)
            
            self.log.info(f"Retrieved {len(results)} similar chunks")
            return results
            
        except Exception as e:
            self.log.error(f"Error retrieving similar chunks: {str(e)}")
            raise
    
    def search_by_metadata(self, metadata_filters: Dict) -> List[Dict]:
        try:
            connections.connect(
                "default",
                host=self.milvus_host,
                port=self.milvus_port
            )
            
            collection = Collection(self.collection_name)
            
            filter_expr = " and ".join([
                f'{key} == "{value}"' for key, value in metadata_filters.items()
            ])
            
            results = collection.query(
                expr=filter_expr,
                output_fields=["text", "embedding"] + list(metadata_filters.keys()),
                limit=100
            )
            
            self.log.info(f"Found {len(results)} documents matching metadata filters")
            return results
            
        except Exception as e:
            self.log.error(f"Error searching by metadata: {str(e)}")
            raise
    
    def get_collection_stats(self) -> Dict:
        try:
            connections.connect(
                "default",
                host=self.milvus_host,
                port=self.milvus_port
            )
            
            if self.collection_name not in utility.list_collections():
                return {"error": f"Collection '{self.collection_name}' does not exist"}
            
            collection = Collection(self.collection_name)
            
            stats = {
                "collection_name": self.collection_name,
                "num_entities": collection.num_entities,
                "schema": str(collection.schema),
                "indexes": str(collection.indexes)
            }
            
            return stats
            
        except Exception as e:
            self.log.error(f"Error getting collection stats: {str(e)}")
            raise


class DocumentQueryExample:
    @staticmethod
    def basic_query_example():
        query_service = DocumentQueryService(
            collection_name="westaco_documents",
            top_k=5,
            similarity_threshold=0.7
        )
        
        query = "What are the company policies for remote work?"
        result = query_service.query(query)
        
        print(f"Query: {result.query}")
        print(f"Found {len(result.source_nodes)} relevant chunks:")
        
        for i, node in enumerate(result.source_nodes):
            print(f"\n--- Chunk {i+1} (Score: {node['score']:.3f}) ---")
            print(f"Text: {node['text'][:200]}...")
            print(f"Metadata: {node['metadata']}")
    
    @staticmethod
    def retrieve_similar_example():
        query_service = DocumentQueryService()
        
        query = "sales report Q1 2024"
        similar_chunks = query_service.retrieve_similar_chunks(
            query_text=query,
            top_k=3,
            return_metadata=True
        )
        
        print(f"Query: {query}")
        print(f"Similar chunks found:")
        
        for chunk in similar_chunks:
            print(f"\nScore: {chunk['score']:.3f}")
            print(f"Text: {chunk['text'][:150]}...")
            print(f"Document: {chunk['metadata'].get('file_name', 'Unknown')}")
    
    @staticmethod
    def metadata_search_example():
        query_service = DocumentQueryService()
        
        results = query_service.search_by_metadata({
            "doc_type": "technical_report"
        })
        
        print(f"Found {len(results)} technical reports")
        for result in results[:3]:
            print(f"\nDocument: {result.get('file_name', 'Unknown')}")
            print(f"Text preview: {result.get('text', '')[:100]}...")


if __name__ == "__main__":
    print("=== Basic Query Example ===")
    DocumentQueryExample.basic_query_example()
    
    print("\n\n=== Retrieve Similar Example ===")
    DocumentQueryExample.retrieve_similar_example()
    
    print("\n\n=== Metadata Search Example ===")
    DocumentQueryExample.metadata_search_example()