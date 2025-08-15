import requests
import aiohttp

from typing import List, Dict, Any

class OllamaClient:    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.OLLAMA_API_BASE_URL = "http://localhost:11434/api/generate" 
        
    def generate(self, model: str, prompt: str, context: List[int] = None, stream: bool = False) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "context": context or []
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama API error: {str(e)}")
    
    def chat(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama Chat API error: {str(e)}")
