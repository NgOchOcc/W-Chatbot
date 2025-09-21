import aiohttp
from typing import List, Dict, Optional
import json

class VLLMClient:
    def __init__(self, base_url: str = "http://localhost:9292", model: str = "AlphaGaO/Qwen3-14B-GPTQ"):
        self.base_url = base_url
        self.model = model
        self.session = None
        
    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _count_tokens(self, text: str) -> int:
        try:
            session = await self._get_session()
            payload = {
                "model": self.model,
                "prompt": text,
                "add_generation_prompt": False
            }
            
            async with session.post(
                f"{self.base_url}/tokenize",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return len(result.get("tokens", []))
                else:
                    return len(text) // 2
        except Exception:
            return len(text) // 2
    
    async def _truncate_messages(self, messages: List[Dict[str, str]], max_tokens: int = 5120) -> List[Dict[str, str]]:
        if not messages:
            return messages
        
        truncated_messages = []
        total_tokens = 0
        system_message = None
        start_idx = 0
        if messages and messages[0].get("role") == "system":
            system_message = messages[0]
            system_tokens = await self._count_tokens(system_message["content"])
            if system_tokens < max_tokens:
                truncated_messages.append(system_message)
                total_tokens += system_tokens
                start_idx = 1
            else:
                max_system_tokens = max_tokens // 2  
                system_content = system_message["content"]
                while await self._count_tokens(system_content) > max_system_tokens and len(system_content) > 100:
                    system_content = system_content[:int(len(system_content) * 0.9)]
                truncated_messages.append({"role": "system", "content": system_content})
                total_tokens += await self._count_tokens(system_content)
                start_idx = 1
        
        remaining_messages = messages[start_idx:]
        for message in reversed(remaining_messages):
            message_tokens = await self._count_tokens(message["content"])
            if total_tokens + message_tokens <= max_tokens:
                truncated_messages.insert(-len([m for m in truncated_messages if m.get("role") != "system"]) or len(truncated_messages), message)
                total_tokens += message_tokens
            else:
                content = message["content"]
                available_tokens = max_tokens - total_tokens
                if available_tokens > 50: 
                    while await self._count_tokens(content) > available_tokens and len(content) > 50:
                        content = content[:int(len(content) * 0.9)]
                    truncated_message = {"role": message["role"], "content": content}
                    truncated_messages.insert(-len([m for m in truncated_messages if m.get("role") != "system"]) or len(truncated_messages), truncated_message)
                break
        
        return truncated_messages
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using vLLM API with prompt format"""
        if 'temperature' not in kwargs:
            kwargs['temperature'] = 0
            
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        messages = await self._truncate_messages(messages, max_tokens=5120)

        response = await self.chat(messages=messages, stream=False, **kwargs)
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs):
        session = await self._get_session()
        
        if 'temperature' not in kwargs:
            kwargs['temperature'] = 0
        
        messages = await self._truncate_messages(messages, max_tokens=5120)
    
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
        
        if 'temperature' not in kwargs:
            kwargs['temperature'] = 0
        
        if conversation_history and len(conversation_history) > 0:
            # Take only the last 2 messages (1 conversation turn)
            limited_history = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history[-1:]
            messages.extend(limited_history)

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
        
#         system_message = f"""You are Westaco-chatbot, an expert AI assistant developed by OMV AG. Your purpose is to provide accurate and official information exclusively about Westaco, Westaco Express, and OMV AG.

# Core Principles:

# * Identity:
# - You are Westaco-chatbot, a specialized AI created to assist with inquiries related to Westaco and OMV AG.
# - You are not a general-purpose AI and should not answer questions outside this domain.

# * Source of Truth (Anti-Hallucination):
# - Your knowledge is based strictly on the official documents provided in the context.
# - You must answer questions about Westaco, Westaco Express, or OMV AG using only the information found in the provided context.
# - Do not use general knowledge or any external sources.
# - If the requested information is not available in the context, respond: "I do not have information on this topic." Do not guess, invent, or speculate.
# - **Important:** Do not include phrases such as "based on the provided context" or "according to the documents" in your answers. Just respond naturally and directly, as if the knowledge is already part of your core training.

# * Handling Unclear, Broad, or Incomplete Questions:
# - If a user's question is unclear or too broad, ask for clarification before providing an answer.
# - If the topic is relevant to Westaco or OMV AG but not covered in the context, ask the user to clarify or narrow the question. For example:
#    - "Could you please clarify your question so I can assist you more accurately?"
#    - "I do not have enough information to answer this based on the current documents. Could you specify what aspect you're referring to?"
# - If the topic is not recognized at all in the procedures, respond with:
#    - "I do not understand this question as it is not covered in my procedures."
# - If a question may relate to multiple procedures or categories, ask a follow-up to narrow it down (e.g., gasoline vs. diesel refueling).

# * General & Conversational:
# - For greetings and small talk, respond in a natural and professional tone without referencing the context.
# - If asked about your identity, state that you are an AI assistant developed by OMV AG to provide support on topics related to Westaco, Westaco Express, and OMV AG.

# * Language & Formatting:
# - Respond in the same language as the user.
# - Follow any formatting instructions from the user, such as bullet points, tables, or character limits.

# * Safety & Ethics:
# - Decline all requests for personal, confidential, or harmful information.
# - Do not provide medical, legal, or financial advice.
# - Do not execute code or access external links.

# Context:
# {context}
# """

        
        
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_message})
        
        messages.append({"role": "user", "content": question})
        messages = await self._truncate_messages(messages, max_tokens=5120)
        response = await self.chat(
            messages=messages,
            stream=False,
            **kwargs
        )
        
        if response and "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        else:
            return "I couldn't generate a response. Please try again."
    
    async def close(self):
        if self.session:
            await self.session.close()

