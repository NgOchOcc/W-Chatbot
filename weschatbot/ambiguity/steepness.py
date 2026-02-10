from typing import List

import numpy as np

from weschatbot.ambiguity.base import BaseTask
from weschatbot.ambiguity.chunk import Chunk


def steepness_top1_elbow(scores: List[float],
                         elbow_idx: int | None = None,
                         alpha: float = 0.8,
                         sigma_factor: float = 0.25,
                         fallback: str = "top2"):
    s = np.sort(np.asarray(scores))[::-1]
    n = len(s)
    if n == 0:
        return {"gap": 0.0, "gap_norm": 0.0, "pos_weight": 0.0, "combined": 0.0}

    s1 = float(s[0])

    if elbow_idx is None:
        if fallback == "top2" and n >= 2:
            elbow_idx = 1
        else:
            elbow_idx = int(np.floor(n / 2))

    elbow_idx = int(max(0, min(elbow_idx, n - 1)))
    elbow_value = float(s[elbow_idx])

    gap = s1 - elbow_value
    gap_norm = gap / s1 if s1 != 0 else 0.0

    p = elbow_idx / max(1, n - 1)

    sigma = max(1e-6, sigma_factor)
    gauss = float(np.exp(-((p - 0.5) ** 2) / (2 * sigma ** 2)))

    combined = float(alpha * gap_norm + (1 - alpha) * gauss)

    return {
        "gap": float(gap),
        "gap_norm": float(gap_norm),
        "pos_weight": gauss,
        "combined": combined,
        "elbow_idx": elbow_idx,
        "elbow_value": elbow_value
    }


class Steepness(BaseTask):
    def __init__(self, alpha: float = 0.8, sigma_factor: float = 0.25, fallback: str = "top2"):
        self.alpha = alpha
        self.sigma_factor = sigma_factor
        self.fallback = fallback

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        self.log.debug(f"Steepness input: {chunks}")
        if not chunks:
            return chunks

        scores = [float(c.score) for c in chunks]
        elbow_idx = None
        if hasattr(chunks[0], "elbow_idx") and chunks[0].elbow_idx is not None:
            elbow_idx = int(chunks[0].elbow_idx)

        metrics = steepness_top1_elbow(scores,
                                       elbow_idx=elbow_idx,
                                       alpha=self.alpha,
                                       sigma_factor=self.sigma_factor,
                                       fallback=self.fallback)

        for c in chunks:
            c.steepness = float(metrics["gap"])
            c.steepness_norm = float(metrics["gap_norm"])
            c.steepness_pos_weight = float(metrics["pos_weight"])
            c.steepness_combined = float(metrics["combined"])
            c.elbow_idx = int(metrics["elbow_idx"])
            c.elbow_value = float(metrics["elbow_value"])

        self.log.debug(f"Steepness output: combined={metrics['combined']}, gap_norm={metrics['gap_norm']}")
        return chunks
