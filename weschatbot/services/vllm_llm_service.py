import aiohttp
from typing import List, Dict, Optional
import json

from weschatbot.services.chatbot_configuration_service import ChatbotConfigurationService


class VLLMService:
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
                truncated_messages.insert(
                    -len([m for m in truncated_messages if m.get("role") != "system"]) or len(truncated_messages),
                    message)
                total_tokens += message_tokens
            else:
                content = message["content"]
                available_tokens = max_tokens - total_tokens
                if available_tokens > 50:
                    while await self._count_tokens(content) > available_tokens and len(content) > 50:
                        content = content[:int(len(content) * 0.9)]
                    truncated_message = {"role": message["role"], "content": content}
                    truncated_messages.insert(
                        -len([m for m in truncated_messages if m.get("role") != "system"]) or len(truncated_messages),
                        truncated_message)
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
            # Take only the last 3 messages (1 conversation turn)
            limited_history = conversation_history[-3:] if len(conversation_history) >= 3 else conversation_history[-len(conversation_history):]
            messages.extend(limited_history)

        system_message = f"{ChatbotConfigurationService().get_prompt()}\n{context}"

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
