from typing import List

import numpy as np

from weschatbot.ambiguity.base import BaseTask
from weschatbot.ambiguity.chunk import Chunk


def discrete_softmax_entropy_cosine(cosines, t=0.05, eps=1e-12):
    s = np.asarray(cosines, dtype=float)
    n = s.size

    if n == 0:
        return {"entropy": 0.0, "normalized_entropy": 0.0, "probs": np.array([])}

    s_scaled = s / t

    s_max = np.max(s_scaled)
    exp_s = np.exp(s_scaled - s_max)
    probs = exp_s / (np.sum(exp_s) + eps)

    probs = np.clip(probs, eps, 1.0)

    entropy = -np.sum(probs * np.log(probs))
    max_entropy = np.log(n)
    normalized_entropy = entropy / max_entropy

    return {
        "entropy": float(entropy),
        "normalized_entropy": float(normalized_entropy),
        "probs": probs
    }


class SoftmaxEntropy(BaseTask):
    def __init__(self, method: str = "softmax"):
        self.method = method

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        self.log.debug(f"EntropyCheck input: {chunks}")
        if not chunks:
            return chunks

        scores = np.array([c.score for c in chunks], dtype=float)
        res = discrete_softmax_entropy_cosine(scores)

        entropy = res["entropy"]
        normalized_entropy = res["normalized_entropy"]
        probs = res["probs"]

        for idx, c in enumerate(chunks):
            c.entropy = float(entropy)
            c.normalized_entropy = float(normalized_entropy)
            c.probs = probs
            try:
                c.prob = float(probs[idx])
            except Exception as e:
                self.log.warning(f"Probability of {idx}: {e}")
                c.prob = None

        self.log.debug(f"EntropyCheck normalized_entropy: {normalized_entropy}")
        self.log.debug(f"EntropyCheck output: {chunks}")
        return chunks
