import argparse
import json
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_samples, silhouette_score

sns.set_style("whitegrid")
plt.rcParams['font.size'] = 9


class PerQuestionVisualizer:
    def __init__(self, csv_path: str, output_dir: Optional[str] = None):
        self.csv_path = Path(csv_path)
        self.output_dir = Path(output_dir) if output_dir else self.csv_path.parent / "visualizations"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.df = pd.read_csv(csv_path)
        self.algorithm = self.df['algorithm'].iloc[0]
        self.params = json.loads(self.df['params'].iloc[0])
        self.question_ids = sorted(self.df['question_id'].unique())

        algo_name = self.csv_path.stem
        self.algo_dir = self.output_dir / algo_name
        self.algo_dir.mkdir(parents=True, exist_ok=True)

    def visualize_question(self, question_id: int):
        q_df = self.df[self.df['question_id'] == question_id].copy()
        if len(q_df) < 2:
            return

        q_dir = self.algo_dir / f"question_{question_id}"
        q_dir.mkdir(parents=True, exist_ok=True)

        vectors = np.array([json.loads(v) for v in q_df['chunk_vector']])
        labels = q_df['cluster_label'].values
        scores = q_df['score'].values

        fig = plt.figure(figsize=(16, 12))

        if self.algorithm == 'kmeans':
            self._plot_kmeans_combined(fig, vectors, labels, scores, question_id, q_df)
        elif self.algorithm == 'dbscan':
            self._plot_dbscan_combined(fig, vectors, labels, scores, question_id)
        elif self.algorithm == 'hdbscan':
            self._plot_hdbscan_combined(fig, vectors, labels, scores, question_id, q_df)

        plt.tight_layout()
        plt.savefig(q_dir / f"question_{question_id}_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()

    def _plot_kmeans_combined(self, fig, vectors, labels, scores, qid, q_df):
        ax1 = fig.add_subplot(2, 2, 1)
        perplexity = min(30, len(vectors) - 1)
        coords = TSNE(n_components=2, perplexity=perplexity, random_state=42, max_iter=1000).fit_transform(vectors)

        for label in sorted(set(labels)):
            mask = labels == label
            ax1.scatter(coords[mask, 0], coords[mask, 1], s=100, alpha=0.7, label=f'C{label} (n={sum(mask)})')

        ax1.set_title(f'Q{qid} - t-SNE Clustering (KMeans)', fontsize=12, fontweight='bold')
        ax1.legend(loc='best', fontsize=8)
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(2, 2, 2)
        unique_labels, counts = np.unique(labels, return_counts=True)
        colors = [f'C{i}' for i in range(len(unique_labels))]

        ax2.bar(range(len(unique_labels)), counts, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_xticks(range(len(unique_labels)))
        ax2.set_xticklabels([f'C{x}' for x in unique_labels])
        ax2.set_ylabel('Number of Chunks')
        ax2.set_title(f'Q{qid} - Cluster Distribution', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        for i, count in enumerate(counts):
            ax2.text(i, count, str(count), ha='center', va='bottom')

        ax3 = fig.add_subplot(2, 2, 3)
        non_noise = labels != -1
        if non_noise.sum() >= 2 and len(set(labels[non_noise])) >= 2:
            sil_samples = silhouette_samples(vectors[non_noise], labels[non_noise])
            sil_avg = silhouette_score(vectors[non_noise], labels[non_noise])

            y_lower = 10
            for i, label in enumerate(sorted(set(labels[non_noise]))):
                cluster_sil = sil_samples[labels[non_noise] == label]
                cluster_sil.sort()

                y_upper = y_lower + len(cluster_sil)
                ax3.fill_betweenx(np.arange(y_lower, y_upper), 0, cluster_sil, facecolor=f'C{i}', alpha=0.7)
                ax3.text(-0.05, y_lower + 0.5 * len(cluster_sil), f'C{label}')
                y_lower = y_upper + 10

            ax3.set_title(f'Q{qid} - Silhouette Plot (Avg: {sil_avg:.3f})', fontsize=12, fontweight='bold')
            ax3.set_xlabel('Silhouette Coefficient')
            ax3.axvline(x=sil_avg, color="red", linestyle="--", linewidth=2)
        else:
            ax3.text(0.5, 0.5, 'Insufficient data for silhouette', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title(f'Q{qid} - Silhouette Plot', fontsize=12, fontweight='bold')

        ax4 = fig.add_subplot(2, 2, 4)
        if 'distance_to_center' in q_df.columns:
            distances = q_df['distance_to_center'].values
            ax4.hist(distances, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
            ax4.axvline(x=distances.mean(), color='red', linestyle='--', linewidth=2,
                        label=f'Mean: {distances.mean():.3f}')
            ax4.set_xlabel('Distance to Centroid')
            ax4.set_ylabel('Frequency')
            ax4.set_title(f'Q{qid} - Distance Distribution', fontsize=12, fontweight='bold')
            ax4.legend()
            ax4.grid(axis='y', alpha=0.3)

    def _plot_dbscan_combined(self, fig, vectors, labels, scores, qid):
        ax1 = fig.add_subplot(2, 2, 1)
        perplexity = min(30, len(vectors) - 1)
        coords = TSNE(n_components=2, perplexity=perplexity, random_state=42, max_iter=1000).fit_transform(vectors)

        for label in sorted(set(labels)):
            mask = labels == label
            if label == -1:
                ax1.scatter(coords[mask, 0], coords[mask, 1], c='gray', marker='x',
                            s=50, alpha=0.5, label=f'Noise (n={sum(mask)})')
            else:
                ax1.scatter(coords[mask, 0], coords[mask, 1], s=100, alpha=0.7,
                            label=f'C{label} (n={sum(mask)})')

        ax1.set_title(f'Q{qid} - t-SNE Clustering (DBSCAN)', fontsize=12, fontweight='bold')
        ax1.legend(loc='best', fontsize=8)
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(2, 2, 2)
        unique_labels, counts = np.unique(labels, return_counts=True)
        colors = ['gray' if l == -1 else f'C{i}' for i, l in enumerate(unique_labels)]
        label_names = ['Noise' if x == -1 else f'C{x}' for x in unique_labels]

        ax2.bar(range(len(unique_labels)), counts, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_xticks(range(len(unique_labels)))
        ax2.set_xticklabels(label_names, rotation=45)
        ax2.set_ylabel('Number of Chunks')
        ax2.set_title(f'Q{qid} - Cluster Distribution', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        for i, count in enumerate(counts):
            ax2.text(i, count, str(count), ha='center', va='bottom')

        ax3 = fig.add_subplot(2, 2, 3)
        non_noise = labels != -1
        if non_noise.sum() >= 2 and len(set(labels[non_noise])) >= 2:
            sil_samples = silhouette_samples(vectors[non_noise], labels[non_noise])
            sil_avg = silhouette_score(vectors[non_noise], labels[non_noise])

            y_lower = 10
            for i, label in enumerate(sorted(set(labels[non_noise]))):
                cluster_sil = sil_samples[labels[non_noise] == label]
                cluster_sil.sort()

                y_upper = y_lower + len(cluster_sil)
                ax3.fill_betweenx(np.arange(y_lower, y_upper), 0, cluster_sil, facecolor=f'C{i}', alpha=0.7)
                ax3.text(-0.05, y_lower + 0.5 * len(cluster_sil), f'C{label}')
                y_lower = y_upper + 10

            ax3.set_title(f'Q{qid} - Silhouette Plot (Avg: {sil_avg:.3f})', fontsize=12, fontweight='bold')
            ax3.set_xlabel('Silhouette Coefficient')
            ax3.axvline(x=sil_avg, color="red", linestyle="--", linewidth=2)
        else:
            ax3.text(0.5, 0.5, 'Insufficient data for silhouette', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title(f'Q{qid} - Silhouette Plot', fontsize=12, fontweight='bold')

        ax4 = fig.add_subplot(2, 2, 4)
        unique_labels_list = sorted(set(labels))
        data = [scores[labels == x] for x in unique_labels_list]
        names = ['Noise' if x == -1 else f'C{x}' for x in unique_labels_list]

        bp = ax4.boxplot(data, tick_labels=names, patch_artist=True)
        for i, box in enumerate(bp['boxes']):
            box.set_facecolor(f'C{i}' if unique_labels_list[i] != -1 else 'gray')
            box.set_alpha(0.7)

        ax4.set_xlabel('Cluster')
        ax4.set_ylabel('Score')
        ax4.set_title(f'Q{qid} - Score Distribution', fontsize=12, fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)

    def _plot_hdbscan_combined(self, fig, vectors, labels, scores, qid, q_df):
        ax1 = fig.add_subplot(2, 2, 1)
        perplexity = min(30, len(vectors) - 1)
        coords = TSNE(n_components=2, perplexity=perplexity, random_state=42, max_iter=1000).fit_transform(vectors)

        for label in sorted(set(labels)):
            mask = labels == label
            if label == -1:
                ax1.scatter(coords[mask, 0], coords[mask, 1], c='gray', marker='x', s=50, alpha=0.5,
                            label=f'Noise (n={sum(mask)})')
            else:
                ax1.scatter(coords[mask, 0], coords[mask, 1], s=100, alpha=0.7, label=f'C{label} (n={sum(mask)})')

        ax1.set_title(f'Q{qid} - t-SNE Clustering (HDBSCAN)', fontsize=12, fontweight='bold')
        ax1.legend(loc='best', fontsize=8)
        ax1.grid(True, alpha=0.3)

        ax2 = fig.add_subplot(2, 2, 2)
        unique_labels, counts = np.unique(labels, return_counts=True)
        colors = ['gray' if l == -1 else f'C{i}' for i, l in enumerate(unique_labels)]
        label_names = ['Noise' if x == -1 else f'C{x}' for x in unique_labels]

        ax2.bar(range(len(unique_labels)), counts, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_xticks(range(len(unique_labels)))
        ax2.set_xticklabels(label_names, rotation=45)
        ax2.set_ylabel('Number of Chunks')
        ax2.set_title(f'Q{qid} - Cluster Distribution', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)

        for i, count in enumerate(counts):
            ax2.text(i, count, str(count), ha='center', va='bottom')

        ax3 = fig.add_subplot(2, 2, 3)
        if 'cluster_probability' in q_df.columns:
            probs = q_df['cluster_probability'].values
            ax3.hist(probs, bins=30, color='steelblue', alpha=0.7, edgecolor='black')
            ax3.axvline(x=probs.mean(), color='red', linestyle='--', linewidth=2,
                        label=f'Mean: {probs.mean():.3f}')
            ax3.set_xlabel('Cluster Probability')
            ax3.set_ylabel('Frequency')
            ax3.set_title(f'Q{qid} - Probability Distribution', fontsize=12, fontweight='bold')
            ax3.legend()
            ax3.grid(axis='y', alpha=0.3)

        ax4 = fig.add_subplot(2, 2, 4)
        unique_labels_list = sorted(set(labels))
        data = [scores[labels == x] for x in unique_labels_list]
        names = ['Noise' if x == -1 else f'C{x}' for x in unique_labels_list]

        bp = ax4.boxplot(data, tick_labels=names, patch_artist=True)
        for i, box in enumerate(bp['boxes']):
            box.set_facecolor(f'C{i}' if unique_labels_list[i] != -1 else 'gray')
            box.set_alpha(0.7)

        ax4.set_xlabel('Cluster')
        ax4.set_ylabel('Score')
        ax4.set_title(f'Q{qid} - Score Distribution', fontsize=12, fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)

    def generate_all_visualizations(self):
        print(f"\nGenerating visualizations: {self.csv_path.name}")
        for i, qid in enumerate(self.question_ids, 1):
            if i % 10 == 0:
                print(f"  [{i}/{len(self.question_ids)}]")
            self.visualize_question(qid)
        print(f"Saved to: {self.algo_dir}")
        return self.algo_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_file')
    parser.add_argument('--output_dir', default=None)
    args = parser.parse_args()

    visualizer = PerQuestionVisualizer(args.csv_file, args.output_dir)
    visualizer.generate_all_visualizations()
