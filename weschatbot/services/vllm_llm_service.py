import asyncio
import functools
from typing import List, Dict, Optional

import aiohttp

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.services.chatbot_configuration_service import (
    ChatbotConfigurationService,
)
from weschatbot.services.message_truncator_service import MessageTruncator


def provide_loop(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        kwargs["loop"] = loop
        return func(*args, **kwargs)

    return wrapper


chatbot_configuration_service = ChatbotConfigurationService()


class VLLMService(LoggingMixin):
    def __init__(
            self,
            base_url: str = "http://localhost:9292",
            model: str = "AlphaGaO/Qwen3-14B-GPTQ",
    ):
        self.base_url = base_url
        self.model = model
        self.session = None

    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    @staticmethod
    def _ensure_temperature(kwargs: Dict) -> Dict:
        if "temperature" not in kwargs:
            kwargs["temperature"] = 0
        return kwargs

    @provide_loop
    def sync_count_tokens(self, text, loop=None):
        return loop.run_until_complete(self._count_tokens(text))

    def sync_get_summary(self, text):
        return self.sync_call_llm(self.get_summary, text)

    def sync_get_topics(self, text):
        return self.sync_call_llm(self.get_topics, text)

    @provide_loop
    def sync_call_llm(self, func, text, loop=None):
        ret = loop.run_until_complete(func(text))
        try:
            return ret["choices"][0]["message"]["content"].split("</think>")[1]
        except IndexError:
            return ret["choices"][0]["message"]["content"]

    async def get_topics(self, text):
        session = await self._get_session()
        system_prompt = (
            chatbot_configuration_service.get_configuration().analytic_topic_prompt
        )
        messages = self._build_single_turn_messages(system_prompt, text)
        payload = self._build_basic_payload(messages)

        return await self._non_stream_chat(session, payload)

    async def get_summary(self, text):
        session = await self._get_session()
        system_prompt = chatbot_configuration_service.get_configuration().summary_prompt
        messages = self._build_single_turn_messages(system_prompt, text)
        payload = self._build_basic_payload(messages)

        return await self._non_stream_chat(session, payload)

    def _build_single_turn_messages(
            self, system_prompt: str, user_content: str
    ) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _build_basic_payload(self, messages: List[Dict[str, str]]) -> Dict:
        return {
            "model": self.model,
            "messages": messages,
        }

    async def _count_tokens(self, text: str) -> int:
        try:
            session = await self._get_session()
            payload = {
                "model": self.model,
                "prompt": text,
                "add_generation_prompt": False,
            }

            async with session.post(
                    f"{self.base_url}/tokenize",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return len(result.get("tokens", []))
                else:
                    return len(text) // 2
        except Exception:
            return len(text) // 2

    async def _truncate_messages(
            self, messages: List[Dict[str, str]], max_tokens: int = 5120
    ) -> List[Dict[str, str]]:
        truncator = MessageTruncator(self._count_tokens)
        return await truncator.truncate_messages(
            messages=messages,
            max_tokens=max_tokens,
            min_system_chars=100,
            min_content_chars=50,
        )

    async def generate(self, prompt: str, **kwargs) -> str:
        if "temperature" not in kwargs:
            kwargs["temperature"] = 0

        messages = [{"role": "user", "content": prompt}]
        messages = await self._truncate_messages(messages, max_tokens=5120)
        response = await self.chat(messages=messages, stream=False, **kwargs)
        return self._extract_content_from_response(response)

    async def chat(
            self, messages: List[Dict[str, str]], stream: bool = False, **kwargs
    ):
        session = await self._get_session()
        kwargs = self._ensure_temperature(kwargs)
        payload = await self._build_chat_payload(messages, stream=stream, **kwargs)

        if stream:
            return self._stream_chat(session, payload)
        else:
            return await self._non_stream_chat(session, payload)

    async def _build_chat_payload(
            self,
            messages: List[Dict[str, str]],
            stream: bool,
            **kwargs,
    ) -> Dict:
        truncated = await self._truncate_messages(messages, max_tokens=5120)
        return {
            "model": self.model,
            "messages": truncated,
            "stream": stream,
            **kwargs,
        }

    async def _stream_chat(self, session, payload):
        async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
        ) as response:
            if response.status == 200:
                async for line in response.content:
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str != "[DONE]":
                                yield data_str.encode("utf-8")
            else:
                error_text = await response.text()
                raise Exception(f"vLLM API error: {response.status} - {error_text}")

    async def _non_stream_chat(self, session, payload):
        async with session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
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
            **kwargs,
    ) -> str:
        if "temperature" not in kwargs:
            kwargs["temperature"] = 0

        self.log.info(f"Question: {question}")
        self.log.info(f"Context: {context}")

        messages = self._build_context_messages(question, context, conversation_history)
        messages = await self._truncate_messages(messages, max_tokens=5120)
        response = await self.chat(messages=messages, stream=False, **kwargs)
        return self._extract_content_from_response(
            response,
            default="I couldn't generate a response. Please try again.",
        )

    def _build_context_messages(
            self,
            question: str,
            context: str,
            conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        if conversation_history:
            messages.extend(self._limit_conversation_history(conversation_history))

        system_message = self._build_system_message_with_context(context)
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system_message})

        messages.append({"role": "user", "content": question})
        return messages

    @staticmethod
    def _limit_conversation_history(
            conversation_history: List[Dict[str, str]],
            max_items: int = 3,
    ) -> List[Dict[str, str]]:
        if len(conversation_history) <= max_items:
            return conversation_history[-len(conversation_history):]
        return conversation_history[-max_items:]

    @staticmethod
    def _build_system_message_with_context(context: str) -> str:
        return f"{ChatbotConfigurationService().get_prompt()}\n{context}"

    @staticmethod
    def _extract_content_from_response(response: Dict, default: str = "") -> str:
        if response and "choices" in response and len(response["choices"]) > 0:
            return (
                response["choices"][0].get("message", {}).get("content", default or "")
            )
        return default

    async def close(self):
        if self.session:
            await self.session.close()
