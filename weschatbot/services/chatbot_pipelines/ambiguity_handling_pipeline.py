from typing import Optional, List, Dict

from weschatbot.ambiguity.ambiguity_pipeline import AmbiguityPipeline, Decision
from weschatbot.ambiguity.chunk import Chunk
from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.schemas.embedding import RetrievalConfig
from weschatbot.services.chatbot_pipelines.base_pipeline import ChatbotPipeline
from weschatbot.services.vllm_llm_service import VLLMService
from weschatbot.utils.config import config


class ChatbotAmbiguityHandlingPipeline(ChatbotPipeline, LoggingMixin):

    def __init__(self, retrieval_config: RetrievalConfig,
                 vllm_client: VLLMService,
                 chatbot_config,
                 ambiguity_pipeline: AmbiguityPipeline = None):
        super().__init__(retrieval_config, vllm_client, chatbot_config)
        self.clarity_prompt = """
                You are an assistant whose task is to help clarify unclear user questions. The user has asked a question that is incomplete, ambiguous, or not fully supported by consistent information from RAG. Use the conversation history and the provided context as if they were part of your internal company knowledge. Do not mention documents, sources, or context explicitly. Do not answer the original question. Do not provide explanations.
                Generate 2–4 short, specific, and helpful clarifying questions that guide the user toward expressing their intent more clearly. When the information retrieved from RAG is inconsistent or conflicting, prioritize clarifying questions that begin with “which” or “what” to help narrow down the user’s intended meaning. Keep the tone polite, professional, and aligned with the communication style of a corporate representative.
                Additional information from RAG may help clarify:
            """ # noqa

        if ambiguity_pipeline is None:
            self.ambiguity_pipeline = AmbiguityPipeline(decision_task=Decision(
                confidence_threshold=config.getfloat("ambiguity", "decision_threshold", fallback=0.5)), )

    async def run(
            self,
            query: str,
            conversation_history: Optional[List[Dict[str, str]]] = None,
            filter_expr: Optional[str] = None):
        retrieved_docs = await self.retriever.retrieve(query, filter_expr, search_limit=30)
        chunks = [
            Chunk(
                question_id=0,
                question=query,
                content=doc["text"],
                vector=doc["embedding"],
                score=doc["score"],
                vector_score=doc.get("vector_score", doc["score"]),
                text_score=doc.get("text_score", 0.0)
            )
            for doc in retrieved_docs
        ]
        reviewed_chunks = self.ambiguity_pipeline.run(chunks)
        elbow_idx = reviewed_chunks[0].elbow_idx
        if elbow_idx and elbow_idx > 5:
            filtered_chunks = reviewed_chunks[:5]
        elif elbow_idx and elbow_idx > 0:
            filtered_chunks = reviewed_chunks[:elbow_idx - 1]
        elif elbow_idx:
            filtered_chunks = [reviewed_chunks[0]]
        else:
            filtered_chunks = reviewed_chunks
        decision = reviewed_chunks[0].decision
        self.log.debug(f"Confidence: {reviewed_chunks[0].confidence} - Query: {query}")
        self.log.debug(f"Decision: {decision}")
        self.log.debug(filtered_chunks)
        if decision != "ask_clarification":
            context = "Context:\n" + "\n".join([x.content for x in filtered_chunks])
        else:
            context = self.clarity_prompt + "\nContext:\n" + "\n".join([x.content for x in filtered_chunks])
            self.log.debug(f"Confidence: {reviewed_chunks[0].confidence} - Query: {query}")
            self.log.debug(f"Context:\n{context}")

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
