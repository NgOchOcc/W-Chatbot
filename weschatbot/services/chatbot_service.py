from weschatbot.schemas.embedding import RetrievalConfig
from weschatbot.services.vllm_llm_service import VLLMService
from weschatbot.services.retrieve_service import Retriever
from typing import List, Optional, Dict

class ChatbotPipeline:
    def __init__(
        self,
        retrieval_config: RetrievalConfig,
        vllm_client: VLLMService,
        chatbot_config
    ):
        self.retriever = Retriever(retrieval_config)
        self.vllm_client = vllm_client
        self.chatbot_config = chatbot_config

    async def run(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filter_expr: Optional[str] = None
    ) -> Dict:
        retrieved_docs = await self.retriever.retrieve(query, filter_expr)
        context = "\n".join([doc['text'] for doc in retrieved_docs if doc['text'].strip()])
        response = await self.vllm_client.chat_with_context(
            question=query,
            context=context,
            conversation_history=conversation_history,
            temperature=self.chatbot_config.temperature,
            max_completion_tokens=self.chatbot_config.max_completion_tokens
        )

        response = response.split('</think>')[-1]

        return {
            "response": response,
            "retrieved_docs": retrieved_docs
        }

    async def close(self):
        await self.retriever.close()
        await self.vllm_client.close()