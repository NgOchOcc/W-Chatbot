from typing import List

import httpx
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.core.embeddings import BaseEmbedding


class VLLMEmbeddingService:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.async_client = httpx.AsyncClient(timeout=60.0)
        self.sync_client = httpx.Client(timeout=60.0)

    def get_embedding_sync(self, text: str) -> List[float]:
        endpoint = f"{self.base_url}/v1/embeddings"
        payload = {
            "input": text,
            "model": self.model
        }

        response = self.sync_client.post(endpoint, json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"][0]["embedding"]

    async def get_embedding(self, text: str) -> List[float]:
        endpoint = f"{self.base_url}/v1/embeddings"
        payload = {
            "input": text,
            "model": self.model
        }

        response = await self.async_client.post(endpoint, json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"][0]["embedding"]

    def close_sync(self):
        self.sync_client.close()

    async def close(self):
        await self.async_client.aclose()


class VLLMEmbeddingAdapter(BaseEmbedding):
    _vllm_service: VLLMEmbeddingService = PrivateAttr()

    def __init__(self, vllm_service: VLLMEmbeddingService, **kwargs):
        super().__init__(**kwargs)
        self._vllm_service = vllm_service
        self.model_name = vllm_service.model

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._vllm_service.get_embedding_sync(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._vllm_service.get_embedding_sync(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self._vllm_service.get_embedding_sync(text) for text in texts]

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return await self._vllm_service.get_embedding(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return await self._vllm_service.get_embedding(text)

    async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            embedding = await self._vllm_service.get_embedding(text)
            embeddings.append(embedding)
        return embeddings
