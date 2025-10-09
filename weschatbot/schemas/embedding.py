from typing import Optional
from enum import Enum
from dataclasses import dataclass

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


@dataclass
class ResponseConfig:
    model_name: str
    base_url: str
    temperature: float = 0.0
    max_tokens: int = 3192
    system_prompt: Optional[str] = None