from typing import List, Dict, Optional
from pymilvus import Collection
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from weschatbot.schemas.embedding import EmbeddingMode, RetrievalConfig
from weschatbot.services.vllm_embedding_service import VLLMEmbeddingService


class Retriever:
    def __init__(self, config: RetrievalConfig):
        self.config = config
        self.collection = Collection(config.collection_name)
        self.collection.load()

        if config.embedding_mode == EmbeddingMode.HUGGINGFACE:
            self.embedding_model = HuggingFaceEmbedding(
                model_name=config.embedding_model,
                trust_remote_code=True
            )
            self.vllm_client = None
        elif config.embedding_mode == EmbeddingMode.VLLM:
            if not config.vllm_base_url:
                raise ValueError("Ollama base URL required for Ollama mode")
            self.vllm_client = VLLMEmbeddingService(
                base_url=config.vllm_base_url,
                model=config.embedding_model
            )
            self.embedding_model = None

    async def retrieve(self, query: str, filter_expr: Optional[str] = None) -> List[Dict]:
        if self.config.embedding_mode == EmbeddingMode.HUGGINGFACE:
            query_embedding = self.embedding_model.get_text_embedding(query)
        else:  
            query_embedding = await self.vllm_client.get_embedding(query)

        search_params = {
            "metric_type": self.config.metric_type,
            "params": {"nprobe": 10}
        }

        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=self.config.search_limit,
            expr=filter_expr,
            output_fields=["text"]
        )

        retrieved_docs = []
        for hits in results:
            for hit in hits:
                doc = {
                    "text": hit.entity.get("text", ""),
                    "score": hit.score,
                    "id": hit.id
                }
                retrieved_docs.append(doc)

        print("Retrieved Documents:", retrieved_docs)
        return retrieved_docs

    async def close(self):
        if self.vllm_client:
            await self.vllm_client.close()