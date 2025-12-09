from typing import List

import pandas as pd

from weschatbot.ambiguity.chunk import Chunk


class BaseLogger:
    def log_step(self, step_name: str, chunks: List[Chunk]):
        raise NotImplementedError


class CSVLogger(BaseLogger):
    def __init__(self, filename="pipeline_log.csv"):
        self.filename = filename
        pd.DataFrame(columns=[
            "question_id", "question", "step", "content", "score", "entropy",
            "cluster", "cluster_label", "silhouette", "decision"
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
            })
        df = pd.DataFrame(data)
        df.to_csv(self.filename, mode="a", header=False, index=False)


class NullLogger(BaseLogger):
    def log_step(self, step_name: str, chunks: List[Chunk]):
        pass
