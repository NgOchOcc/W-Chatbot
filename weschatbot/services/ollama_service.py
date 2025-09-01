# import requests
# import aiohttp

# from typing import List, Dict, Any

# class OllamaClient:    
#     def __init__(self, base_url: str = "http://localhost:11434"):
#         self.base_url = base_url
#         self.OLLAMA_API_BASE_URL = "http://localhost:11434/api/generate" 
        
#     def generate(self, model: str, prompt: str, context: List[int] = None, stream: bool = False) -> Dict[str, Any]:
#         url = f"{self.base_url}/api/generate"
#         payload = {
#             "model": model,
#             "prompt": prompt,
#             "stream": stream,
#             "context": context or []
#         }
        
#         try:
#             response = requests.post(url, json=payload, timeout=30)
#             response.raise_for_status()
#             return response.json()
#         except requests.exceptions.RequestException as e:
#             raise Exception(f"Ollama API error: {str(e)}")
    
#     def chat(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> Dict[str, Any]:
#         url = f"{self.base_url}/api/chat"
#         payload = {
#             "model": model,
#             "messages": messages,
#             "stream": stream
#         }
        
#         try:
#             response = requests.post(url, json=payload, timeout=30)
#             response.raise_for_status()
#             return response.json()
#         except requests.exceptions.RequestException as e:
#             raise Exception(f"Ollama Chat API error: {str(e)}")

import aiohttp
from typing import List, Dict, Optional

class VLLMClient:
    def __init__(self, base_url: str = "http://localhost:9292", model: str = "AlphaGaO/Qwen3-14B-GPTQ"):
        self.base_url = base_url
        self.model = model
        self.session = None
        
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using vLLM API with prompt format"""
        # Set default temperature to 0 for deterministic results
        if 'temperature' not in kwargs:
            kwargs['temperature'] = 0
            
        messages = [
            {"role": "user", "content": prompt}
        ]
        response = await self.chat(messages=messages, stream=False, **kwargs)
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs):
        session = await self._get_session()
        
        # Set default temperature to 0 for deterministic results
        if 'temperature' not in kwargs:
            kwargs['temperature'] = 0
    
        # vLLM OpenAI-compatible API format
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
    
        if stream:
            return self._stream_chat(session, payload)
        else:
            return await self._non_stream_chat(session, payload)
    
    async def _stream_chat(self, session, payload):
        async with session.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            if response.status == 200:
                async for line in response.content:
                    if line:
                        # Parse SSE format for streaming
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str != "[DONE]":
                                yield data_str.encode('utf-8')
            else:
                error_text = await response.text()
                raise Exception(f"vLLM API error: {response.status} - {error_text}")
    
    async def _non_stream_chat(self, session, payload):
        async with session.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                error_text = await response.text()
                raise Exception(f"vLLM API error: {response.status} - {error_text}")
    
    async def chat_with_context(
        self,
        question: str,
        context: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        messages = []
        
        # Set default temperature to 0 for deterministic results
        if 'temperature' not in kwargs:
            kwargs['temperature'] = 0
    
        if conversation_history:
            messages.extend(conversation_history)
    
        # Improved system prompt with better structure and instructions
        system_message = f"""You are **Westaco-chatbot**, an expert AI assistant developed by **OMV AG**. Your purpose is to provide accurate and official information about Westaco, Westaco Express, and OMV AG.

*Core Principles:*

1.  **Identity:** You are Westaco-chatbot, not a general-purpose AI like Qwen or any other model. You were specifically created to assist with Westaco and OMV-related queries.

2.  **Source of Truth:** Your knowledge is based *exclusively* on official documents provided in the context below. You must not use any external knowledge.
    * If a question is about Westaco, Westaco Express, or OMV AG, you **must** only answer with information from the provided context.
    * If the information is not in the context, state clearly, "I do not have information on this topic." Do not guess or invent answers.

3.  **General & Conversational:**
    * For greetings and small talk, respond in a natural, professional manner without referencing the context.
    * If asked about your identity, state that you are an AI assistant designed to help with Westaco-related information, developed by OMV AG.

4.  **Language & Formatting:**
    * Respond in the same language as the user.
    * Follow explicit user instructions for formatting (e.g., bullet points, tables, character limits).

5.  **Safety & Ethics:**
    * Decline all requests for personal, confidential, or harmful information.
    * Do not provide medical, legal, or financial advice.
    * Do not execute code or access external links.

6.  **Uncertainty & User Intent:**
    * If a user's request is unclear, ask for clarification.
    * Focus on the user's main intent, ignoring minor typos or conversational fillers.

*Context:*
{context}
"""
    
    
        if not conversation_history or len(conversation_history) == 0:
            messages.insert(0, {"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": question})
        
        response = await self.chat(
            messages=messages,
            stream=False,
            **kwargs
        )
        
        # vLLM returns OpenAI-compatible format
        if response and "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            return "I couldn't generate a response. Please try again."
    
    async def close(self):
        if self.session:
            await self.session.close()


