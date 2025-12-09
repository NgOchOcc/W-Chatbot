from typing import List

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from weschatbot.ambiguity.chunk import Chunk
from weschatbot.ambiguity.logger import BaseLogger, NullLogger, CSVLogger
from weschatbot.log.logging_mixin import LoggingMixin


class BaseTask(LoggingMixin):
    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        return chunks


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


class EntropyCheck(BaseTask):
    def __init__(self, use_softmax: bool = True):
        self.use_softmax = use_softmax

    def compute_entropy(self, scores: List[float]) -> float:
        if self.use_softmax:
            exp_scores = np.exp(scores)
            probs = exp_scores / np.sum(exp_scores)
        else:
            probs = scores / np.sum(scores)
        return -np.sum(probs * np.log(probs + 1e-12))

    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        self.log.debug(f"EntropyCheck input: {chunks}")
        if not chunks:
            return chunks

        scores = np.array([c.score for c in chunks])
        entropy = self.compute_entropy(scores)
        n = len(scores)
        max_entropy = np.log(n) if n > 1 else 1.0
        normalized_entropy = entropy / max_entropy

        for c in chunks:
            c.entropy = normalized_entropy

        self.log.debug(f"normalized_entropy: {normalized_entropy}")
        self.log.debug(f"EntropyCheck output: {chunks}")
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


class Decision(BaseTask):
    def process(self, chunks: List[Chunk]) -> List[Chunk]:
        if not chunks:
            return chunks
        entropy = chunks[0].entropy
        clusters = set(c.cluster for c in chunks if c.cluster is not None)
        decision = "answer_direct"
        if entropy and entropy > 0.7:
            decision = "ask_clarification"
        if len(clusters) > 1:
            decision = "ask_clarification"
        for c in chunks:
            c.decision = decision
        return chunks


class AmbiguityPipeline:
    def __init__(self,
                 filter_task: BaseTask = CosineFilter(threshold=0.7),
                 entropy_task: BaseTask = EntropyCheck(),
                 cluster_task: BaseTask = Clustering(n_clusters=2),
                 labeling_task: BaseTask = ClusterLabeling(),
                 decision_task: BaseTask = Decision(),
                 logger: BaseLogger = CSVLogger()):
        self.tasks = [
            ("CosineFilter", filter_task),
            ("EntropyCheck", entropy_task),
            ("Clustering", cluster_task),
            ("ClusterLabeling", labeling_task),
            ("Decision", decision_task),
        ]
        self.logger = logger

    def run(self, chunks: List[Chunk]) -> List[Chunk]:
        for step_name, task in self.tasks:
            chunks = task.process(chunks)
            self.logger.log_step(step_name, chunks)
        return chunks
