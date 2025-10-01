class VLLMEmbeddingClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)

    async def get_embedding(self, text: str) -> List[float]:
        endpoint = f"{self.base_url}/embeddings"
        payload = {
            "input": text,
            "model": self.model
        }

        response = await self.client.post(endpoint, json=payload)
        response.raise_for_status()

        result = response.json()
        return result["data"][0]["embedding"]

    async def close(self):
        await self.client.aclose()