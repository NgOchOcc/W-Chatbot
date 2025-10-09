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

        if str(config.embedding_mode) == 'huggingface':
            self.embedding_model = HuggingFaceEmbedding(
                model_name=config.embedding_model,
                trust_remote_code=True
            )
            self.vllm_client = None
        elif str(config.embedding_mode) == 'vllm':
            if not config.vllm_base_url:
                raise ValueError("Ollama base URL required for Ollama mode")
            self.vllm_client = VLLMEmbeddingService(
                base_url=config.vllm_base_url,
                model=config.embedding_model
            )
            self.embedding_model = None

    async def retrieve(self, query: str, filter_expr: Optional[str] = None) -> List[Dict]:
        if str(self.config.embedding_mode) == 'huggingface':
            query_embedding = self.embedding_model.get_text_embedding(query)
        elif str(self.config.embedding_mode) == 'vllm':
            if self.vllm_client is None:
                raise ValueError("VLLM client is not initialized")
            query_embedding = await self.vllm_client.get_embedding(query)
        else:
            raise ValueError(f"Unsupported embedding mode: {self.config.embedding_mode}")

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