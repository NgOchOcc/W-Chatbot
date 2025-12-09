from typing import List

import numpy as np

from weschatbot.log.logging_mixin import LoggingMixin


class Chunk(LoggingMixin):
    def __init__(self, question_id, question, content: str, vector: List[float], score: float):
        self.question_id = question_id
        self.question = question
        self.content = content
        self.vector = np.array(vector)
        self.score = score
        self.entropy = None
        self.cluster = None
        self.cluster_label = None
        self.silhouette = None
        self.decision = None

    def __repr__(self):
        return (f"Chunk(score={self.score:.3f}, "
                f"cluster={self.cluster}, "
                f"decision={self.decision}, "
                f"content='{self.content[:40]}...')")
