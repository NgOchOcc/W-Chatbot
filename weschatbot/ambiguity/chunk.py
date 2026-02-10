from typing import List, Optional

import numpy as np

from weschatbot.log.logging_mixin import LoggingMixin


class Chunk(LoggingMixin):
    def __init__(self,
                 question_id,
                 question: str,
                 content: str,
                 vector: List[float],
                 score: float,
                 vector_score: Optional[float] = None,
                 text_score: Optional[float] = None):
        self.question_id = question_id
        self.question = question
        self.content = content
        self.vector = np.array(vector)
        self.score = float(score)

        self.vector_score = float(vector_score) if vector_score is not None else float(score)
        self.text_score = float(text_score) if text_score is not None else 0.0

        self.entropy: Optional[float] = None
        self.cluster: Optional[int] = None
        self.cluster_label: Optional[str] = None
        self.silhouette: Optional[float] = None
        self.decision: Optional[str] = None

        self.elbow_idx: Optional[int] = None
        self.elbow_value: Optional[float] = None
        self.steepness: Optional[float] = None
        self.steepness_norm: Optional[float] = None
        self.steepness_pos_weight: Optional[float] = None
        self.steepness_combined: Optional[float] = None

        self.probs: Optional[np.ndarray] = None
        self.normalized_entropy: Optional[float] = None

        self.confidence: Optional[float] = None

        self.score_discrepancy: Optional[float] = None
        self.score_ratio: Optional[float] = None

        self.hybrid_avg_discrepancy: Optional[float] = None
        self.hybrid_max_discrepancy: Optional[float] = None
        self.hybrid_avg_ratio: Optional[float] = None

    def __repr__(self):
        content_preview = (self.content[:40] + '...') if self.content and len(self.content) > 40 else self.content
        return (
            f"Chunk(score={self.score:.3f}, "
            f"cluster={self.cluster}, "
            f"elbow_idx={self.elbow_idx}, "
            f"steepness_combined={self.steepness_combined}, "
            f"decision={self.decision}, "
            f"content='{content_preview}')"
        )
