import aiohttp

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url
        self.model = model
        self.session = None
    
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def generate(self, prompt: str, **kwargs) -> str:
        session = await self._get_session()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }
        
        try:
            async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "")
                else:
                    raise Exception(f"Ollama API error: {response.status}")
        except Exception as e:
            raise Exception(f"Failed to call Ollama API: {str(e)}")
    
    async def close(self):
        if self.session:
            await self.session.close()