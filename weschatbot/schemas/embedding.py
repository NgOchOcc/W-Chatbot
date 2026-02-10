from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EmbeddingMode(Enum):
    VLLM: str = "vllm"
    HUGGINGFACE: str = "huggingface"


@dataclass
class RetrievalConfig:
    collection_name: str
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    embedding_mode: str = EmbeddingMode.VLLM
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    vllm_base_url: Optional[str] = None
    search_limit: int = 5
    metric_type: str = "COSINE"
    enable_hybrid_search: bool = True
    vector_weight: float = 0.5
    text_weight: float = 0.5


@dataclass
class ResponseConfig:
    model_name: str
    base_url: str
    temperature: float = 0.0
    max_tokens: int = 3192
    system_prompt: Optional[str] = None
