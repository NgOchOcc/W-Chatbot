from typing import List, Tuple

import numpy as np

from weschatbot.ambiguity.base import BaseTask
from weschatbot.ambiguity.chunk import Chunk


def gaussian_weighted_elbow(alpha: float = 0.5, min_index: int = 1, sigma_factor: float = 0.2):
    def wrap(scores: List[float]) -> Tuple[int | None, float | None]:
        scores = np.sort(np.asarray(scores))[::-1]
        n = len(scores)

        if n == 0:
            return None, None
        if n == 1:
            return 0, float(scores[0])
        if n == 2:
            return 1, float(scores[1])

        diffs = scores[:-1] - scores[1:]
        k = len(diffs)

        positions = np.arange(k)
        mu = (k - 1) / 2
        sigma = max(1e-6, k * sigma_factor)

        gauss = np.exp(-((positions - mu) ** 2) / (2 * sigma ** 2))
        weights = (1 - alpha) + alpha * gauss
        combined = diffs * weights

        valid_range = positions >= min_index
        combined_masked = np.where(valid_range, combined, -np.inf)

        elbow_idx = int(np.argmax(combined_masked))
        elbow_value = float(scores[elbow_idx + 1])

        return elbow_idx + 1, elbow_value

    return wrap


class ElbowDetection(BaseTask):
    def __init__(self, alpha: float = 0.5, min_index: int = 1, sigma_factor: float = 0.2):
        self.calc = gaussian_weighted_elbow(alpha=alpha, min_index=min_index, sigma_factor=sigma_factor)
        self.alpha = alpha
        self.min_index = min_index
        self.sigma_factor = sigma_factor

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        self.log.debug(f"ElbowDetection input: {chunks}")
        if not chunks:
            return chunks

        scores = [float(c.score) for c in chunks]
        elbow_idx, elbow_value = self.calc(scores)

        for c in chunks:
            c.elbow_idx = int(elbow_idx) if elbow_idx is not None else None
            c.elbow_value = float(elbow_value) if elbow_value is not None else None

        self.log.debug(f"ElbowDetection found idx={elbow_idx}, value={elbow_value}")
        return chunks
