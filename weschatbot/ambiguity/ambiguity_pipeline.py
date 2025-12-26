from typing import List

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from weschatbot.ambiguity.base import BaseTask
from weschatbot.ambiguity.chunk import Chunk
from weschatbot.ambiguity.elbow_detection import ElbowDetection
from weschatbot.ambiguity.entropy import SoftmaxEntropy
from weschatbot.ambiguity.logger import BaseLogger, CSVLogger
from weschatbot.ambiguity.steepness import Steepness


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

        can_compute_silhouette = (
                n_samples >= 3 and
                2 <= num_labels <= (n_samples - 1) and
                not has_singleton
        )

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


import numpy as np


def compute_confidence(
        entropy,
        elbow_index,
        elbow_value,
        steepness,
        k=30,
        w_entropy=0.35,
        w_elbow=0.30,
        w_elbow_cosine=0.30,
        w_steep=0.05
):
    entropy_score = 1.0 - entropy

    elbow_index_norm = elbow_index / max(k - 1, 1)
    elbow_index_score = 1.0 - elbow_index_norm

    elbow_cosine_score = 1.0 - elbow_value

    steepness_score = steepness

    confidence = (
            w_entropy * entropy_score +
            w_elbow * elbow_index_score +
            w_elbow_cosine * elbow_cosine_score +
            w_steep * steepness_score
    )

    confidence = float(np.clip(confidence, 0.0, 1.0))

    return confidence


class Decision(BaseTask):

    def __init__(self, confidence_threshold=0.35):
        self.confidence_threshold = confidence_threshold

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        if not chunks:
            return chunks

        decision = "answer_direct"

        first_chunk = chunks[0]
        entropy = first_chunk.normalized_entropy
        elbow_index = first_chunk.elbow_idx
        elbow_value = first_chunk.elbow_value
        steepness = first_chunk.steepness_norm
        k = len(chunks)
        confidence = compute_confidence(entropy, elbow_index, elbow_value, steepness, k)

        if confidence < self.confidence_threshold:
            decision = "ask_clarification"
        for c in chunks:
            c.decision = decision
            c.confidence = confidence
        return chunks


class AmbiguityPipeline:
    def __init__(self,
                 filter_task: BaseTask = CosineFilter(threshold=0.4),
                 entropy_task: BaseTask = SoftmaxEntropy(),
                 elbow_task: BaseTask = ElbowDetection(alpha=0.5, min_index=1, sigma_factor=0.4),
                 steepness_task: BaseTask = Steepness(alpha=0.8, sigma_factor=0.25),
                 cluster_task: BaseTask = Clustering(n_clusters=2),
                 labeling_task: BaseTask = ClusterLabeling(),
                 decision_task: BaseTask = Decision(confidence_threshold=0.45),
                 logger: BaseLogger = CSVLogger()):
        self.tasks = [
            ("CosineFilter", filter_task),
            ("EntropyCheck", entropy_task),
            ("ElbowDetection", elbow_task),
            ("Steepness", steepness_task),
            ("Clustering", cluster_task),
            ("ClusterLabeling", labeling_task),
            ("Decision", decision_task),
        ]
        self.logger = logger

    def run(self, chunks: List[Chunk]) -> List[Chunk]:
        for step_name, task in self.tasks:
            chunks = task.process(chunks)
        step_name = "Final"
        self.logger.log_step(step_name, chunks)
        return chunks
