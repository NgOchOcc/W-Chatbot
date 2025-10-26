import re
from typing import Dict, List
from abc import ABC, abstractmethod
from llama_index.core import Document as LlamaDocument


class BaseChunkingStrategy(ABC):
    def __init__(
        self,
        chunk_size: int = 768,
        chunk_overlap: int = 128,
        min_chunk_size: int = 128,
        max_chunk_size: int = 1024
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    @abstractmethod
    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[LlamaDocument]:
        pass

    def add_context_to_chunks(self, chunks: List[LlamaDocument]) -> List[LlamaDocument]:
        enhanced_chunks = []

        for i, chunk in enumerate(chunks):
            enhanced_chunks.append(chunk)
        return enhanced_chunks
