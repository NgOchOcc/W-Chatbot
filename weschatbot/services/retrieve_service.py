from typing import List, Dict, Optional

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pymilvus import Collection

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.schemas.embedding import RetrievalConfig
from weschatbot.services.vllm_embedding_service import VLLMEmbeddingService


class Retriever(LoggingMixin):
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

    async def _vector_search(self, query_embedding: List[float], filter_expr: Optional[str], limit: int) -> List[Dict]:
        search_params = {
            "metric_type": self.config.metric_type,
            "params": {"nprobe": 10}
        }

        results = self.collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=limit * 2,
            expr=filter_expr,
            output_fields=["text", "embedding"]
        )

        vector_docs = []
        for hits in results:
            for hit in hits:
                doc = {
                    "text": hit.entity.get("text", ""),
                    "score": hit.score,
                    "id": hit.id,
                    "embedding": hit.entity.get("embedding", []),
                    "vector_score": hit.score,
                }
                vector_docs.append(doc)

        return vector_docs

    async def _fulltext_search(self, query: str, filter_expr: Optional[str], limit: int) -> List[Dict]:
        try:
            escaped_query = query.replace('"', '\\"')
            match_expr = f'text match "{escaped_query}"'

            if filter_expr:
                expr = f"({match_expr}) && ({filter_expr})"
            else:
                expr = match_expr

            results = self.collection.query(
                expr=expr,
                limit=limit * 2,
                output_fields=["text", "embedding", "row_id"]
            )

            fulltext_docs = []
            for idx, result in enumerate(results):
                doc = {
                    "text": result.get("text", ""),
                    "score": 1.0 / (idx + 1),
                    "id": result.get("row_id", result.get("id")),
                    "embedding": result.get("embedding", []),
                    "text_score": 1.0 / (idx + 1),
                }
                fulltext_docs.append(doc)

            if fulltext_docs:
                return fulltext_docs
        except Exception as e:
            self.log.debug(f"Match expression not supported, trying like expression: {str(e)}")

        try:
            query_words = query.split()
            if not query_words:
                return []

            like_conditions = []
            for word in query_words:
                escaped_word = word.replace("'", "''")
                like_conditions.append(f'text like "%{escaped_word}%"')

            like_expr = " || ".join(like_conditions)

            if filter_expr:
                expr = f"({like_expr}) && ({filter_expr})"
            else:
                expr = like_expr

            results = self.collection.query(
                expr=expr,
                limit=limit * 2,
                output_fields=["text", "embedding", "row_id"]
            )

            fulltext_docs = []
            for result in results:
                text = result.get("text", "").lower()
                matching_words = sum(1 for word in query_words if word.lower() in text)
                text_score = matching_words / len(query_words) if query_words else 0.0

                doc = {
                    "text": result.get("text", ""),
                    "score": text_score,
                    "id": result.get("row_id", result.get("id")),
                    "embedding": result.get("embedding", []),
                    "text_score": text_score,
                }
                fulltext_docs.append(doc)

            fulltext_docs.sort(key=lambda x: x["text_score"], reverse=True)

            return fulltext_docs[:limit * 2]
        except Exception as e:
            self.log.warning(f"Full-text search failed, falling back to vector search only: {str(e)}")
            return []

    def _combine_results(self, vector_docs: List[Dict], fulltext_docs: List[Dict], limit: int) -> List[Dict]:
        combined_docs = {}

        for doc in vector_docs:
            doc_id = doc["id"]
            if self.config.metric_type == "L2":
                normalized_score = 1.0 / (1.0 + doc["vector_score"])
            else:
                normalized_score = doc["vector_score"]

            combined_docs[doc_id] = {
                "text": doc["text"],
                "id": doc_id,
                "embedding": doc.get("embedding", []),
                "vector_score": normalized_score,
                "text_score": 0.0,
                "combined_score": normalized_score * self.config.vector_weight,
            }

        for doc in fulltext_docs:
            doc_id = doc["id"]
            text_score = doc.get("text_score", 0.0)

            if doc_id in combined_docs:
                combined_docs[doc_id]["text_score"] = text_score
                combined_docs[doc_id]["combined_score"] = \
                    combined_docs[doc_id]["vector_score"] * self.config.vector_weight + \
                    text_score * self.config.text_weight
            else:
                combined_docs[doc_id] = {
                    "text": doc["text"],
                    "id": doc_id,
                    "embedding": doc.get("embedding", []),
                    "vector_score": 0.0,
                    "text_score": text_score,
                    "combined_score": text_score * self.config.text_weight,
                }

        sorted_docs = sorted(
            combined_docs.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )

        retrieved_docs = []
        for doc in sorted_docs[:limit]:
            retrieved_docs.append({
                "text": doc["text"],
                "score": doc["combined_score"],
                "id": doc["id"],
                "embedding": doc.get("embedding", []),
                "vector_score": doc.get("vector_score", 0.0),
                "text_score": doc.get("text_score", 0.0),
            })

        return retrieved_docs

    async def retrieve(self, query: str, filter_expr: Optional[str] = None, search_limit=None) -> List[Dict]:
        if str(self.config.embedding_mode) == 'huggingface':
            query_embedding = self.embedding_model.get_text_embedding(query)
        elif str(self.config.embedding_mode) == 'vllm':
            if self.vllm_client is None:
                raise ValueError("VLLM client is not initialized")
            query_embedding = await self.vllm_client.get_embedding(query)
        else:
            raise ValueError(f"Unsupported embedding mode: {self.config.embedding_mode}")

        limit = search_limit if search_limit else self.config.search_limit

        if self.config.enable_hybrid_search:
            vector_docs = await self._vector_search(query_embedding, filter_expr, limit)
            fulltext_docs = await self._fulltext_search(query, filter_expr, limit)

            retrieved_docs = self._combine_results(vector_docs, fulltext_docs, limit)
        else:
            vector_docs = await self._vector_search(query_embedding, filter_expr, limit)
            retrieved_docs = []
            for doc in vector_docs[:limit]:
                if self.config.metric_type == "L2":
                    normalized_score = 1.0 / (1.0 + doc["vector_score"])
                else:
                    normalized_score = doc["vector_score"]
                retrieved_docs.append({
                    "text": doc["text"],
                    "score": normalized_score,
                    "id": doc["id"],
                    "embedding": doc.get("embedding", []),
                    "vector_score": normalized_score,
                    "text_score": 0.0,
                })

        return retrieved_docs

    async def close(self):
        if self.vllm_client:
            await self.vllm_client.close()
