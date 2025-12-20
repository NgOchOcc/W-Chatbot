import json
import hdbscan
import argparse
import numpy as np
import pandas as pd

from pathlib import Path
from typing import Optional
from collections import defaultdict
from sklearn.cluster import KMeans, DBSCAN

class ClusteringResultsExporter:
    def __init__(self, data_path: str, output_dir: Optional[str] = None):
        self.output_dir = output_dir or "./clustering_results"
        self.df = pd.read_parquet(data_path)
        self.df = self.df[self.df.step == 'Decision'].reset_index(drop=True)
        self.question_ids = self.df['question_id'].unique()

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        self.results_storage = {
            'kmeans': defaultdict(list),
            'dbscan': defaultdict(list),
            'hdbscan': defaultdict(list)
        }

    def cluster_kmeans(self, question_id: int, k: int):
        question_df = self.df[self.df['question_id'] == question_id].copy()
        vectors = np.vstack(question_df['vector'].tolist())

        if k >= len(vectors):
            return

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(vectors)
        distances = [np.linalg.norm(vectors[i] - kmeans.cluster_centers_[labels[i]])
                     for i in range(len(vectors))]

        for idx in range(len(vectors)):
            self.results_storage['kmeans'][k].append({
                'question_id': question_df['question_id'].iloc[idx],
                'chunk_index': idx,
                'chunk_vector': json.dumps(vectors[idx].tolist()),
                'cluster_label': int(labels[idx]),
                'cluster_center': json.dumps(kmeans.cluster_centers_[labels[idx]].tolist()),
                'distance_to_center': float(distances[idx]),
                'score': float(question_df['score'].iloc[idx]),
                'question': question_df['question'].iloc[idx],
                'content': question_df['content'].iloc[idx],
                'algorithm': 'kmeans',
                'params': json.dumps({'n_clusters': k})
            })

    def cluster_dbscan(self, question_id: int, eps: float, min_samples: int):
        question_df = self.df[self.df['question_id'] == question_id].copy()
        vectors = np.vstack(question_df['vector'].tolist())
        if min_samples > len(vectors):
            return

        labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(vectors)
        for idx in range(len(vectors)):
            self.results_storage['dbscan'][(eps, min_samples)].append({
                'question_id': question_df['question_id'].iloc[idx],
                'chunk_index': idx,
                'chunk_vector': json.dumps(vectors[idx].tolist()),
                'cluster_label': int(labels[idx]),
                'score': float(question_df['score'].iloc[idx]),
                'question': question_df['question'].iloc[idx],
                'content': question_df['content'].iloc[idx],
                'algorithm': 'dbscan',
                'params': json.dumps({'eps': eps, 'min_samples': min_samples})
            })

    def cluster_hdbscan(self, question_id: int, min_cluster_size: int, min_samples: int):
        question_df = self.df[self.df['question_id'] == question_id].copy()
        vectors = np.vstack(question_df['vector'].tolist())
        if min_cluster_size > len(vectors) // 2:
            return

        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=min_samples)
        labels = clusterer.fit_predict(vectors)

        for idx in range(len(vectors)):
            self.results_storage['hdbscan'][(min_cluster_size, min_samples)].append({
                'question_id': question_df['question_id'].iloc[idx],
                'chunk_index': idx,
                'chunk_vector': json.dumps(vectors[idx].tolist()),
                'cluster_label': int(labels[idx]),
                'cluster_probability': float(clusterer.probabilities_[idx]),
                'score': float(question_df['score'].iloc[idx]),
                'question': question_df['question'].iloc[idx],
                'content': question_df['content'].iloc[idx],
                'algorithm': 'hdbscan',
                'params': json.dumps({'min_cluster_size': min_cluster_size, 'min_samples': min_samples})
            })

    def export_all_results(self, question_ids: Optional[list] = None):
        if question_ids is None:
            question_ids = self.question_ids

        for i, qid in enumerate(question_ids, 1):
            question_df = self.df[self.df['question_id'] == qid]
            if len(question_df) < 2:
                continue

            if i % 10 == 0:
                print(f"  [{i}/{len(question_ids)}]")

            for k in range(2, 6):
                self.cluster_kmeans(qid, k)

            for eps in [0.5, 0.7, 1.0]:
                for min_samples in [2, 3, 5]:
                    self.cluster_dbscan(qid, eps, min_samples)

            for min_cluster_size in [2, 3, 5]:
                for min_samples in [2, 3, 5]:
                    self.cluster_hdbscan(qid, min_cluster_size, min_samples)

        # Write to CSV
        total = 0
        for k, records in self.results_storage['kmeans'].items():
            if records:
                pd.DataFrame(records).to_csv(f"{self.output_dir}/kmeans_n_clusters_{k}.csv", index=False)
                total += 1

        for (eps, ms), records in self.results_storage['dbscan'].items():
            if records:
                pd.DataFrame(records).to_csv(f"{self.output_dir}/dbscan_eps_{eps}_min_samples_{ms}.csv", index=False)
                total += 1

        for (mcs, ms), records in self.results_storage['hdbscan'].items():
            if records:
                pd.DataFrame(records).to_csv(f"{self.output_dir}/hdbscan_min_cluster_size_{mcs}_min_samples_{ms}.csv", index=False)
                total += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--data_path', default='/Users/luungoc/Westaco/Westaco Data/decision_step.parquet')
    parser.add_argument('--output_dir', default='./clustering_results')
    parser.add_argument('--question_ids', default=None, help='comma-separated IDs')
    args = parser.parse_args()

    question_ids = None
    if args.question_ids:
        question_ids = [int(x.strip()) for x in args.question_ids.split(',')]

    exporter = ClusteringResultsExporter(args.data_path, args.output_dir)
    exporter.export_all_results(question_ids)
