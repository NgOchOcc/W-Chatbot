import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import silhouette_score


class ClusteringMetricsComputer:
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self.df = pd.read_csv(csv_path)
        self.algorithm = self.df['algorithm'].iloc[0]
        self.params = json.loads(self.df['params'].iloc[0])
        self.question_ids = sorted(self.df['question_id'].unique())

    def compute_question_metrics(self, question_id: int):
        q_df = self.df[self.df['question_id'] == question_id].copy()
        if len(q_df) < 2:
            return None

        # Parse vectors
        vectors = np.array([json.loads(v) for v in q_df['chunk_vector']])
        labels = q_df['cluster_label'].values
        scores = q_df['score'].values

        unique_clusters = sorted([x for x in set(labels) if x != -1])
        n_clusters = len(unique_clusters)
        n_noise = int((labels == -1).sum())
        n_samples = len(labels)

        metrics = {
            'question_id': int(question_id),
            'n_chunks': n_samples,
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'noise_ratio': n_noise / n_samples if n_samples > 0 else 0,
        }

        non_noise = labels != -1
        if n_clusters >= 2 and non_noise.sum() > 1:
            metrics['silhouette_score'] = float(silhouette_score(vectors[non_noise], labels[non_noise]))
        else:
            metrics['silhouette_score'] = None

        # Score statistics
        metrics['score_mean'] = float(scores.mean())
        metrics['score_std'] = float(scores.std())
        metrics['score_min'] = float(scores.min())
        metrics['score_max'] = float(scores.max())

        if self.algorithm == 'kmeans':
            if 'distance_to_center' in q_df.columns:
                dists = q_df['distance_to_center'].values
                metrics['distance_mean'] = float(dists.mean())
                metrics['distance_std'] = float(dists.std())

        elif self.algorithm == 'hdbscan':
            if 'cluster_probability' in q_df.columns:
                probs = q_df['cluster_probability'].values
                metrics['probability_mean'] = float(probs.mean())
                metrics['probability_std'] = float(probs.std())
                metrics['low_confidence_ratio'] = float((probs < 0.5).sum() / len(probs))

        # Decision
        major_clusters = sum(1 for c in unique_clusters if (labels == c).sum() / n_samples >= 0.25)
        metrics['decision'] = 'ambiguous' if major_clusters >= 2 else 'clear'
        metrics['n_major_clusters'] = major_clusters
        return metrics

    def compute_all_metrics(self):
        all_metrics = []
        for qid in self.question_ids:
            metrics = self.compute_question_metrics(qid)
            if metrics:
                all_metrics.append(metrics)

        return pd.DataFrame(all_metrics)

    def save_metrics(self, output_path: str = None):
        if output_path is None:
            output_path = f"{self.csv_path.parent}/{self.csv_path.stem}_metrics.csv"
        else:
            output_path = Path(output_path)

        metrics_df = self.compute_all_metrics()
        metrics_df.to_csv(output_path, index=False)
        return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file')
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    computer = ClusteringMetricsComputer(args.csv_file)
    computer.save_metrics(args.output)
