import os
from typing import List

import pandas as pd

from weschatbot.ambiguity.chunk import Chunk
from weschatbot.log.logging_mixin import LoggingMixin


class BaseLogger(LoggingMixin):
    def log_step(self, step_name: str, chunks: List[Chunk]):
        raise NotImplementedError


class CSVLogger(BaseLogger):
    def __init__(self, filename="pipeline_log.csv"):
        self.filename = filename
        pd.DataFrame(columns=[
            "question_id",
            "question",
            "step",
            "content",
            "score",
            "entropy",
            "cluster",
            "cluster_label",
            "silhouette",
            "decision",
            "elbow_idx",
            "elbow_value",
            "steepness",
            "steepness_norm",
            "steepness_pos_weight",
            "steepness_combined",
            "normalized_entropy",
            "confidence"
        ]).to_csv(self.filename, index=False)

    def log_step(self, step_name: str, chunks: List[Chunk]):
        data = []
        for c in chunks:
            data.append({
                "question_id": c.question_id,
                "question": c.question,
                "step": step_name,
                "content": c.content,
                "score": c.score,
                "entropy": c.entropy,
                "cluster": c.cluster,
                "cluster_label": c.cluster_label,
                "silhouette": c.silhouette,
                "decision": c.decision,
                "elbow_idx": c.elbow_idx,
                "elbow_value": c.elbow_value,
                "steepness": c.steepness,
                "steepness_norm": c.steepness_norm,
                "steepness_pos_weight": c.steepness_pos_weight,
                "steepness_combined": c.steepness_combined,
                "normalized_entropy": c.normalized_entropy,
                "confidence": c.confidence
            })
        df = pd.DataFrame(data)
        df.to_csv(self.filename, mode="a", header=False, index=False)


class NullLogger(BaseLogger):
    def log_step(self, step_name: str, chunks: List[Chunk]):
        pass


class ParquetLogger(BaseLogger):
    def __init__(self, filename="pipeline_log.parquet", engine: str = "pyarrow"):
        self.filename = filename
        self.engine = engine

        if not os.path.exists(self.filename):
            pd.DataFrame(columns=[
                "question_id",
                "question",
                "step",
                "content",
                "score",
                "entropy",
                "cluster",
                "cluster_label",
                "silhouette",
                "decision",
                "vector",
                "elbow_idx",
                "elbow_value",
                "steepness",
                "steepness_norm",
                "steepness_pos_weight",
                "steepness_combined",
                "normalized_entropy",
                "confidence"
            ]).to_parquet(self.filename, engine=self.engine, index=False)

    def log_step(self, step_name: str, chunks: List[Chunk]):
        data = []
        for c in chunks:
            vec = None
            try:
                vec = c.vector.tolist() if c.vector is not None else None
            except Exception as e:
                self.log.debug(e)
                vec = list(c.vector) if c.vector is not None else None

            data.append({
                "question_id": c.question_id,
                "question": c.question,
                "step": step_name,
                "content": c.content,
                "score": c.score,
                "entropy": c.entropy,
                "cluster": c.cluster,
                "cluster_label": c.cluster_label,
                "silhouette": c.silhouette,
                "decision": c.decision,
                "vector": vec,
                "elbow_idx": c.elbow_idx,
                "elbow_value": c.elbow_value,
                "steepness": c.steepness,
                "steepness_norm": c.steepness_norm,
                "steepness_pos_weight": c.steepness_pos_weight,
                "steepness_combined": c.steepness_combined,
                "normalized_entropy": c.normalized_entropy,
                "confidence": c.confidence
            })
        new_df = pd.DataFrame(data)

        if os.path.exists(self.filename):
            try:
                existing = pd.read_parquet(self.filename, engine=self.engine)
                combined = pd.concat([existing, new_df], ignore_index=True)
            except Exception as e:
                self.log.debug(e)
                combined = new_df
        else:
            combined = new_df

        combined.to_parquet(self.filename, engine=self.engine, index=False)
