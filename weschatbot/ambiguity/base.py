from typing import List

from weschatbot.ambiguity.chunk import Chunk
from weschatbot.log.logging_mixin import LoggingMixin


class BaseTask(LoggingMixin):
    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        return chunks
