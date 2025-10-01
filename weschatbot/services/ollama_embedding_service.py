import aiohttp
from typing import List

class OllamaEmbeddingService:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    async def get_embedding(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=1200)) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["embedding"]
                else:
                    error_text = await response.text()
                    raise Exception(f"Error: {response.status} - {error_text}")

    async def close(self):
        pass