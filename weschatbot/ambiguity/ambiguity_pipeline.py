import logging
from typing import List

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from weschatbot.ambiguity.base import BaseTask
from weschatbot.ambiguity.chunk import Chunk
from weschatbot.ambiguity.elbow_detection import ElbowDetection
from weschatbot.ambiguity.entropy import SoftmaxEntropy
from weschatbot.ambiguity.logger import BaseLogger, NullLogger
from weschatbot.ambiguity.steepness import Steepness
from weschatbot.utils.config import config

logger = logging.getLogger(__file__)


class CosineFilter(BaseTask):
    def __init__(self, threshold: float = None, relative: float = None):
        self.threshold = threshold
        self.relative = relative

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        self.log.debug(f"CosineFilter input: {chunks}")
        if not chunks:
            return chunks
        scores = [c.score for c in chunks]
        top1 = max(scores)
        filtered = []
        for c in chunks:
            if self.threshold and c.score >= self.threshold:
                filtered.append(c)
            elif self.relative and c.score >= top1 * self.relative:
                filtered.append(c)
        res = filtered if filtered else chunks
        self.log.debug("CosineFilter output:")
        return res


class HybridScoreAnalyzer(BaseTask):
    def __init__(self, discrepancy_threshold: float = 0.3):
        self.discrepancy_threshold = discrepancy_threshold

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        self.log.debug(f"HybridScoreAnalyzer input: {len(chunks)} chunks")
        if not chunks:
            return chunks

        for chunk in chunks:
            vector_score = chunk.vector_score
            text_score = chunk.text_score

            chunk.score_discrepancy = abs(vector_score - text_score)

            max_score = max(vector_score, text_score) if max(vector_score, text_score) > 0 else 1.0
            min_score = min(vector_score, text_score)
            chunk.score_ratio = min_score / max_score if max_score > 0 else 0.0

        if len(chunks) > 0:
            discrepancies = [c.score_discrepancy for c in chunks if c.score_discrepancy is not None]
            ratios = [c.score_ratio for c in chunks if c.score_ratio is not None]

            if discrepancies:
                avg_discrepancy = np.mean(discrepancies)
                max_discrepancy = np.max(discrepancies)
                avg_ratio = np.mean(ratios) if ratios else 1.0

                chunks[0].hybrid_avg_discrepancy = avg_discrepancy
                chunks[0].hybrid_max_discrepancy = max_discrepancy
                chunks[0].hybrid_avg_ratio = avg_ratio

                self.log.debug(
                    f"HybridScoreAnalyzer: avg_discrepancy={avg_discrepancy:.3f}, "
                    f"max_discrepancy={max_discrepancy:.3f}, avg_ratio={avg_ratio:.3f}"
                )

        self.log.debug(f"HybridScoreAnalyzer output: {len(chunks)} chunks")
        return chunks


class Clustering(BaseTask):
    def __init__(self, n_clusters: int = 2):
        self.n_clusters = n_clusters

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        self.log.debug(f"Clustering input: {chunks}")
        if not chunks:
            return chunks

        vectors = np.array([c.vector for c in chunks])
        n_samples = len(chunks)

        if n_samples < self.n_clusters:
            return chunks

        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(vectors)

        for c, label in zip(chunks, labels):
            c.cluster = int(label)

        unique_labels = list(set(labels))
        num_labels = len(unique_labels)

        sizes = {lbl: np.sum(labels == lbl) for lbl in unique_labels}
        has_singleton = any(sz < 2 for sz in sizes.values())

        can_compute_silhouette = (n_samples >= 3 and 2 <= num_labels <= (n_samples - 1) and not has_singleton)

        if can_compute_silhouette:
            sil = silhouette_score(vectors, labels, metric="euclidean")
            for c in chunks:
                c.silhouette = float(sil)
        else:
            for c in chunks:
                c.silhouette = None

        self.log.debug(f"Clustering output: {chunks}")
        return chunks


class ClusterLabeling(BaseTask):
    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        self.log.debug(f"ClusterLabeling input: {chunks}")
        for c in chunks:
            if c.cluster is not None:
                c.cluster_label = f"Cluster-{c.cluster}"
        self.log.debug(f"ClusterLabeling output: {chunks}")
        return chunks


def compute_confidence(
        entropy,
        elbow_index,
        elbow_value,
        steepness,
        k=30,
        w_entropy=0.30,
        w_elbow=0.25,
        w_elbow_cosine=0.25,
        w_steep=0.05,
        w_hybrid=0.15,
        hybrid_avg_ratio=None
):
    entropy_score = 1.0 - entropy

    elbow_index_norm = elbow_index / max(k - 1, 1)
    elbow_index_score = 1.0 - elbow_index_norm
    elbow_cosine_score = 1.0 - elbow_value
    steepness_score = steepness
    hybrid_score = hybrid_avg_ratio if hybrid_avg_ratio is not None else 1.0

    logger.info(f"entropy_score: {entropy_score}")
    logger.info(f"elbow_index_score: {elbow_index_score}")
    logger.info(f"elbow_cosine_score: {elbow_cosine_score}")
    logger.info(f"steepness_score: {steepness_score}")
    logger.info(f"hybrid_score: {hybrid_score}")
    logger.info(f"hybrid_avg_ratio: {hybrid_avg_ratio}")
    logger.info(f"w_entropy: {w_entropy}")
    logger.info(f"w_elbow: {w_elbow}")
    logger.info(f"w_elbow_cosine: {w_elbow_cosine}")
    logger.info(f"w_steep: {w_steep}")
    logger.info(f"w_hybrid: {w_hybrid}")

    confidence = (
            w_entropy * entropy_score +  # noqa
            w_elbow * elbow_index_score +  # noqa
            w_elbow_cosine * elbow_cosine_score +  # noqa
            w_steep * steepness_score +  # noqa
            w_hybrid * hybrid_score
    )

    confidence = float(np.clip(confidence, 0.0, 1.0))

    return confidence


class Decision(BaseTask):

    def __init__(self, confidence_threshold=0.35):
        self.confidence_threshold = confidence_threshold
        self.hybrid_w = config.getfloat("ambiguity", "hybrid_w", fallback=0.0) if config.getboolean(
            "ambiguity", "hybrid_enabled", fallback=False) else 0.0
        self.softmax_entropy_w = config.getfloat("ambiguity", "softmax_entropy_w", fallback=0.0) if config.getboolean(
            "ambiguity", "softmax_entropy_enabled", fallback=False) else 0.0
        self.elbow_index_w = config.getfloat("ambiguity", "elbow_index_w", fallback=0.0) if config.getboolean(
            "ambiguity", "elbow_detection_enabled", fallback=False) else 0.0
        self.elbow_cosine_w = config.getfloat("ambiguity", "elbow_cosine_w", fallback=0.0) if config.getboolean(
            "ambiguity", "elbow_detection_enabled", fallback=False) else 0.0
        self.steepness_w = config.getfloat("ambiguity", "steepness_w", fallback=0.0) if config.getboolean(
            "ambiguity", "steepness_enabled", fallback=False) else 0.0

        self.cosine_filter_enabled = config.getboolean("ambiguity", "cosine_filter_enabled", fallback=False)
        self.hybrid_enabled = config.getboolean("ambiguity", "hybrid_enabled", fallback=False)
        self.softmax_entropy_enabled = config.getboolean("ambiguity", "softmax_entropy_enabled", fallback=False)
        self.elbow_detection_enabled = config.getboolean("ambiguity", "elbow_detection_enabled", fallback=False)
        self.steepness_enabled = config.getboolean("ambiguity", "steepness_enabled", fallback=False)

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        if not chunks:
            return chunks

        decision = "answer_direct"

        first_chunk = chunks[0]
        entropy = first_chunk.normalized_entropy
        elbow_index = first_chunk.elbow_idx
        elbow_value = first_chunk.elbow_value
        steepness = first_chunk.steepness_norm
        hybrid_avg_ratio = getattr(first_chunk, 'hybrid_avg_ratio', None)
        k = len(chunks)

        confidence = compute_confidence(
            entropy=entropy,
            elbow_index=elbow_index,
            elbow_value=elbow_value,
            steepness=steepness,
            k=k,
            w_entropy=self.softmax_entropy_w,
            w_elbow=self.elbow_index_w,
            w_elbow_cosine=self.elbow_cosine_w,
            w_steep=self.steepness_w,
            w_hybrid=self.hybrid_w,
            hybrid_avg_ratio=hybrid_avg_ratio
        )

        self.log.debug(f"Confidence: {confidence}")
        self.log.debug(f"self.confidence_threshold: {self.confidence_threshold}")
        if confidence < self.confidence_threshold:
            decision = "ask_clarification"
        for c in chunks:
            c.decision = decision
            c.confidence = confidence
        return chunks


class AmbiguityPipeline:
    def __init__(self,
                 filter_task: BaseTask = CosineFilter(threshold=0.4),
                 hybrid_analyzer_task: BaseTask = HybridScoreAnalyzer(discrepancy_threshold=0.3),
                 entropy_task: BaseTask = SoftmaxEntropy(),
                 elbow_task: BaseTask = ElbowDetection(alpha=0.5, min_index=1, sigma_factor=0.4),
                 steepness_task: BaseTask = Steepness(alpha=0.8, sigma_factor=0.25),
                 cluster_task: BaseTask = Clustering(n_clusters=2),
                 labeling_task: BaseTask = ClusterLabeling(),
                 decision_task: BaseTask = Decision(confidence_threshold=0.5),
                 logger: BaseLogger = NullLogger()):
        self.tasks = [
            (config.getboolean("ambiguity", "cosine_filter_enabled", fallback=False), filter_task),
            (config.getboolean("ambiguity", "hybrid_enabled", fallback=False), hybrid_analyzer_task),
            (config.getboolean("ambiguity", "softmax_entropy_enabled", fallback=False), entropy_task),
            (config.getboolean("ambiguity", "elbow_detection_enabled", fallback=False), elbow_task),
            (config.getboolean("ambiguity", "steepness_enabled", fallback=False), steepness_task),
            (config.getboolean("ambiguity", "clustering_enabled", fallback=False), cluster_task),
            (False, labeling_task),
            (config.getboolean("ambiguity", "decision_enabled", fallback=False), decision_task),
        ]
        self.logger = logger

    def run(self, chunks: List[Chunk]) -> List[Chunk]:
        for step_enabled, task in self.tasks:
            if step_enabled:
                chunks = task.process(chunks)
        step_name = "Final"
        self.logger.log_step(step_name, chunks)
        return chunks
