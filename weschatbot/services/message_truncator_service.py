from typing import List, Dict, Callable, Awaitable


class MessageTruncator:
    def __init__(self, count_tokens_func: Callable[[str], Awaitable[int]]):
        self._count_tokens_func = count_tokens_func
        self._token_cache: Dict[str, int] = {}

    async def truncate_messages(
            self,
            messages: List[Dict[str, str]],
            max_tokens: int,
            min_system_chars: int = 100,
            min_content_chars: int = 50,
    ) -> List[Dict[str, str]]:
        if not messages:
            return messages

        truncated_messages: List[Dict[str, str]] = []
        total_tokens = 0
        start_idx = 0

        if messages[0].get("role") == "system":
            system_message = messages[0]
            system_tokens = await self._get_token_count(system_message["content"])

            if system_tokens < max_tokens:
                truncated_messages.append(system_message)
                total_tokens += system_tokens
            else:
                max_system_tokens = max_tokens // 2
                system_content = await self._truncate_text_to_tokens(
                    text=system_message["content"],
                    available_tokens=max_system_tokens,
                    min_chars=min_system_chars,
                )
                truncated_messages.append({"role": "system", "content": system_content})
                total_tokens += await self._get_token_count(system_content)

            start_idx = 1

        remaining_messages = messages[start_idx:]
        for message in reversed(remaining_messages):
            message_tokens = await self._get_token_count(message["content"])

            if total_tokens + message_tokens <= max_tokens:
                self._insert_after_system(truncated_messages, message)
                total_tokens += message_tokens
            else:
                available_tokens = max_tokens - total_tokens
                if available_tokens > min_content_chars:
                    content = await self._truncate_text_to_tokens(
                        text=message["content"],
                        available_tokens=available_tokens,
                        min_chars=min_content_chars,
                    )
                    truncated_message = {"role": message["role"], "content": content}
                    self._insert_after_system(truncated_messages, truncated_message)
                break

        return truncated_messages

    async def _get_token_count(self, text: str) -> int:
        if text in self._token_cache:
            return self._token_cache[text]
        count = await self._count_tokens_func(text)
        self._token_cache[text] = count
        return count

    async def _truncate_text_to_tokens(
            self,
            text: str,
            available_tokens: int,
            min_chars: int,
    ) -> str:
        if available_tokens <= 0 or not text:
            return ""

        current_tokens = await self._get_token_count(text)
        if current_tokens <= available_tokens:
            return text

        ratio = max(available_tokens / max(current_tokens, 1), 0.0)
        new_len = max(int(len(text) * ratio), min_chars)
        new_len = min(new_len, len(text))
        truncated = text[:new_len]

        truncated_tokens = await self._get_token_count(truncated)
        if truncated_tokens > available_tokens and len(truncated) > min_chars:
            refine_ratio = available_tokens / max(truncated_tokens, 1)
            refined_len = max(int(len(truncated) * refine_ratio), min_chars)
            refined_len = min(refined_len, len(truncated))
            truncated = truncated[:refined_len]

        return truncated

    @staticmethod
    def _insert_after_system(
            truncated_messages: List[Dict[str, str]],
            message: Dict[str, str],
    ) -> None:
        non_system_count = len([m for m in truncated_messages if m.get("role") != "system"])
        insert_index = -non_system_count or len(truncated_messages)
        truncated_messages.insert(insert_index, message)
