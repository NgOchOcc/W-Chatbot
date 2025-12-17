import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Any
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score, pairwise_distances
from sklearn.preprocessing import normalize
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import warnings

warnings.filterwarnings('ignore')

try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False


class ClusterAnalyzer:
    def __init__(self, data_path: str, score_threshold: float = 0.5,
                 normalize_vectors: bool = True):
        self.data_path = data_path
        self.score_threshold = score_threshold
        self.normalize_vectors = normalize_vectors

        self.df = pd.read_parquet("/Users/luungoc/Westaco/Westaco Data/pipeline_log_1.parquet")
        self.df = self.df[self.df.step == 'Decision'].reset_index()

        print(f"Loaded {len(self.df)} samples")

        required_cols = ['question_id', 'question', 'content', 'vector', 'score']
        missing_cols = set(required_cols) - set(self.df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        self.vectors = None
        self.filtered_df = None

    def prepare_vectors(self, custom_threshold: float = None) -> np.ndarray:
        threshold = custom_threshold if custom_threshold is not None else self.score_threshold

        self.filtered_df = self.df[self.df['score'] >= threshold].copy()
        print(f"After filtering (score >= {threshold}): {len(self.filtered_df)} samples")

        vectors_list = self.filtered_df['vector'].tolist()
        self.vectors = np.vstack(vectors_list)

        if self.normalize_vectors:
            self.vectors = normalize(self.vectors, norm='l2')
            print("Vectors normalized (L2)")

        return self.vectors

    def apply_kmeans(self, n_clusters_range: range = range(2, 6)) -> Dict[int, Dict]:
        if self.vectors is None:
            self.prepare_vectors()

        results = {}
        n_samples = len(self.vectors)

        if n_samples == 1:
            print(f"  Only 1 sample - creating single cluster")
            labels = np.array([0])
            results[1] = {
                'labels': labels,
                'silhouette': 0.0,  
                'cluster_sizes': Counter(labels),
                'centroids': self.vectors,
                'inertia': 0.0
            }
            return results

        max_k = min(max(n_clusters_range), n_samples - 1)
        actual_range = range(max(2, min(n_clusters_range)), max_k + 1)

        for k in actual_range:
            if k >= n_samples:
                print(f"  K={k}: Skipped (K >= n_samples)")
                continue

            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(self.vectors)

            if len(set(labels)) > 1:
                sil_score = silhouette_score(self.vectors, labels)
            else:
                sil_score = -1.0

            cluster_sizes = Counter(labels)

            results[k] = {
                'labels': labels,
                'silhouette': sil_score,
                'cluster_sizes': cluster_sizes,
                'centroids': kmeans.cluster_centers_,
                'inertia': kmeans.inertia_
            }

            print(f"  K={k}: silhouette={sil_score:.3f}, sizes={dict(cluster_sizes)}")

        return results

    def apply_dbscan(self, eps_values: List[float] = [0.3, 0.5, 0.7, 1.0, 1.5],
                     min_samples_values: List[int] = [2, 3, 5]) -> Dict[Tuple, Dict]:
        if self.vectors is None:
            self.prepare_vectors()

        results = {}
        n_samples = len(self.vectors)

        if n_samples == 1:
            print(f"  Only 1 sample - all marked as noise")
            labels = np.array([-1])
            results[(1.0, 2)] = {
                'labels': labels,
                'silhouette': 0.0,
                'n_clusters': 0,
                'n_noise': 1,
                'cluster_sizes': Counter(labels),
                'eps': 1.0,
                'min_samples': 2
            }
            return results

        max_min_samples = max(2, n_samples // 3)
        adjusted_min_samples = [m for m in min_samples_values if m <= max_min_samples]
        if not adjusted_min_samples:
            adjusted_min_samples = [2]

        print(f"\nTrying DBSCAN with eps={eps_values}, min_samples={adjusted_min_samples}")

        for eps in eps_values:
            for min_samples in adjusted_min_samples:
                dbscan = DBSCAN(eps=eps, min_samples=min_samples, metric='euclidean')
                labels = dbscan.fit_predict(self.vectors)

                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                n_noise = list(labels).count(-1)

                if n_clusters > 1 and n_noise < len(labels) - 1:
                    non_noise_mask = labels != -1
                    if sum(non_noise_mask) > 1:
                        sil_score = silhouette_score(
                            self.vectors[non_noise_mask],
                            labels[non_noise_mask]
                        )
                    else:
                        sil_score = -1.0
                else:
                    sil_score = -1.0

                cluster_sizes = Counter(labels)
                results[(eps, min_samples)] = {
                    'labels': labels,
                    'silhouette': sil_score,
                    'n_clusters': n_clusters,
                    'n_noise': n_noise,
                    'cluster_sizes': cluster_sizes,
                    'eps': eps,
                    'min_samples': min_samples
                }

                print(f"  eps={eps}, min_samples={min_samples}: "
                      f"clusters={n_clusters}, noise={n_noise}, silhouette={sil_score:.3f}")

        return results

    def apply_hdbscan(self, min_cluster_sizes: List[int] = [2, 3, 5, 10],
                      min_samples_values: List[int] = [2, 3, 5]) -> Dict[Tuple, Dict]:
        if self.vectors is None:
            self.prepare_vectors()

        results = {}
        n_samples = len(self.vectors)
        if n_samples == 1:
            print(f"  Only 1 sample - all marked as noise")
            labels = np.array([-1])
            results[(2, 2)] = {
                'labels': labels,
                'silhouette': 0.0,
                'n_clusters': 0,
                'n_noise': 1,
                'cluster_sizes': Counter(labels),
                'min_cluster_size': 2,
                'min_samples': 2,
                'probabilities': np.array([0.0])
            }
            return results

        max_cluster_size = max(2, n_samples // 2)
        adjusted_cluster_sizes = [s for s in min_cluster_sizes if s <= max_cluster_size]
        if not adjusted_cluster_sizes:
            adjusted_cluster_sizes = [2]

        max_min_samples = max(2, n_samples // 3)
        adjusted_min_samples = [m for m in min_samples_values if m <= max_min_samples]
        if not adjusted_min_samples:
            adjusted_min_samples = [2]

        for min_cluster_size in adjusted_cluster_sizes:
            for min_samples in adjusted_min_samples:
                clusterer = hdbscan.HDBSCAN(
                    min_cluster_size=min_cluster_size,
                    min_samples=min_samples,
                    metric='euclidean'
                )
                labels = clusterer.fit_predict(self.vectors)

                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                n_noise = list(labels).count(-1)
                if n_clusters > 1 and n_noise < len(labels) - 1:
                    non_noise_mask = labels != -1
                    if sum(non_noise_mask) > 1:
                        sil_score = silhouette_score(
                            self.vectors[non_noise_mask],
                            labels[non_noise_mask]
                        )
                    else:
                        sil_score = -1.0
                else:
                    sil_score = -1.0

                cluster_sizes = Counter(labels)

                results[(min_cluster_size, min_samples)] = {
                    'labels': labels,
                    'silhouette': sil_score,
                    'n_clusters': n_clusters,
                    'n_noise': n_noise,
                    'cluster_sizes': cluster_sizes,
                    'min_cluster_size': min_cluster_size,
                    'min_samples': min_samples,
                    'probabilities': clusterer.probabilities_
                }

                print(f"  min_cluster_size={min_cluster_size}, min_samples={min_samples}: "
                      f"clusters={n_clusters}, noise={n_noise}, silhouette={sil_score:.3f}")

        return results

    def evaluate_clusters(self, labels: np.ndarray) -> Dict[str, Any]:
        if self.vectors is None:
            raise ValueError("Vectors not prepared. Call prepare_vectors() first.")

        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        n_noise = list(labels).count(-1)
        n_samples = len(labels)
        cluster_sizes = Counter(labels)
        cluster_ratios = {
            label: count / n_samples
            for label, count in cluster_sizes.items()
            if label != -1
        }

        if n_clusters > 1 and n_noise < n_samples - 1:
            non_noise_mask = labels != -1
            if sum(non_noise_mask) > 1:
                silhouette = silhouette_score(
                    self.vectors[non_noise_mask],
                    labels[non_noise_mask]
                )
            else:
                silhouette = -1.0
        else:
            silhouette = -1.0

        inter_cluster_distances = {}
        valid_clusters = [c for c in unique_labels if c != -1]

        if len(valid_clusters) > 1:
            centroids = []
            for cluster_id in valid_clusters:
                cluster_mask = labels == cluster_id
                centroid = self.vectors[cluster_mask].mean(axis=0)
                centroids.append(centroid)

            centroids = np.array(centroids)
            distances = pairwise_distances(centroids, metric='cosine')
            for i, c1 in enumerate(valid_clusters):
                for j, c2 in enumerate(valid_clusters):
                    if i < j:
                        inter_cluster_distances[(c1, c2)] = distances[i, j]

        return {
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'n_samples': n_samples,
            'cluster_sizes': cluster_sizes,
            'cluster_ratios': cluster_ratios,
            'silhouette': silhouette,
            'inter_cluster_distances': inter_cluster_distances
        }

    def detect_ambiguity(self, labels: np.ndarray,
                         major_cluster_threshold: float = 0.25,
                         min_inter_distance: float = 0.3) -> Tuple[str, Dict]:
        eval_results = self.evaluate_clusters(labels)

        n_clusters = eval_results['n_clusters']
        n_noise = eval_results['n_noise']
        n_samples = eval_results['n_samples']
        cluster_ratios = eval_results['cluster_ratios']
        inter_distances = eval_results['inter_cluster_distances']

        # Identify major clusters (≥25% of samples)
        major_clusters = {
            cluster_id: {
                'count': eval_results['cluster_sizes'][cluster_id],
                'ratio': ratio
            }
            for cluster_id, ratio in cluster_ratios.items()
            if ratio >= major_cluster_threshold
        }

        n_major_clusters = len(major_clusters)
        noise_ratio = n_noise / n_samples if n_samples > 0 else 0

        avg_inter_distance = None
        if len(major_clusters) > 1 and inter_distances:
            relevant_distances = [
                dist for (c1, c2), dist in inter_distances.items()
                if c1 in major_clusters and c2 in major_clusters
            ]
            if relevant_distances:
                avg_inter_distance = np.mean(relevant_distances)


        decision = None
        reason = ""

        if n_major_clusters >= 2 and avg_inter_distance is not None and avg_inter_distance >= min_inter_distance:
            decision = 'ambiguous'
            reason = (f"Multiple topics detected: {n_major_clusters} major clusters with clear separation "
                     f"(avg distance: {avg_inter_distance:.3f}). Query covers distinct topics.")

        else:
            decision = 'clear'

            if n_major_clusters == 1:
                reason = f"Single topic: One dominant cluster with {list(major_clusters.values())[0]['ratio']:.1%} of chunks."

            elif n_major_clusters >= 2:
                reason = (f"Single topic: {n_major_clusters} clusters found but close together "
                         f"(avg distance: {avg_inter_distance:.3f}), likely sub-topics of same theme.")

            elif noise_ratio > 0.5:
                reason = f"Answerable with top chunks: High noise ratio ({noise_ratio:.1%}), but top-scored chunks can be used."

            elif n_clusters == 0:
                reason = "Answerable: No distinct clusters, all chunks can be used together."

            elif n_clusters > n_samples * 0.5:
                reason = f"Answerable: Many small clusters ({n_clusters}), use highest-scored chunks."

            else:
                reason = "Clear query: Can be answered with retrieved chunks."

        analysis = {
            'decision': decision,
            'reason': reason,
            'n_major_clusters': n_major_clusters,
            'major_clusters': major_clusters,
            'n_total_clusters': n_clusters,
            'noise_ratio': noise_ratio,
            'avg_inter_cluster_distance': avg_inter_distance,
            'silhouette_score': eval_results['silhouette'],
            'all_cluster_ratios': cluster_ratios
        }

        return decision, analysis

    def generate_report(self, labels: np.ndarray, method: str,
                       params: Dict = {}) -> str:
        eval_results = self.evaluate_clusters(labels)

        report = []
        report.append(f"\n{'='*60}")
        report.append(f"CLUSTERING REPORT - {method}")
        report.append(f"{'='*60}")

        if params:
            report.append(f"\nParameters:")
            for key, value in params.items():
                report.append(f"  {key}: {value}")

        report.append(f"\nCluster Statistics:")
        report.append(f"  Total samples: {eval_results['n_samples']}")
        report.append(f"  Number of clusters: {eval_results['n_clusters']}")
        report.append(f"  Noise points: {eval_results['n_noise']} "
                     f"({eval_results['n_noise']/eval_results['n_samples']:.1%})")
        report.append(f"  Silhouette score: {eval_results['silhouette']:.3f}")

        report.append(f"\nCluster Distribution:")
        for cluster_id, count in sorted(eval_results['cluster_sizes'].items()):
            if cluster_id == -1:
                report.append(f"  Noise: {count} samples")
            else:
                ratio = eval_results['cluster_ratios'].get(cluster_id, 0)
                report.append(f"  Cluster {cluster_id}: {count} samples ({ratio:.1%})")

        # Inter-cluster distances
        if eval_results['inter_cluster_distances']:
            report.append(f"\nInter-cluster Distances (Cosine):")
            for (c1, c2), dist in sorted(eval_results['inter_cluster_distances'].items()):
                report.append(f"  Cluster {c1} <-> Cluster {c2}: {dist:.3f}")

        return '\n'.join(report)

    def visualize_clusters_2d(self, labels: np.ndarray, title: str = "Cluster Visualization",
                             method: str = 'pca', save_path: str = None,
                             figsize: Tuple[int, int] = (12, 8)):
        if self.vectors is None:
            raise ValueError("Vectors not prepared. Call prepare_vectors() first.")

        # Handle edge case: too few samples for dimensionality reduction
        n_samples = len(self.vectors)
        if n_samples < 2:
            print(f"  Skipping visualization: only {n_samples} sample(s) - insufficient for 2D projection")
            # Create a simple placeholder figure
            fig, ax = plt.subplots(1, 1, figsize=(8, 6))
            ax.text(0.5, 0.5, f'Insufficient data for visualization\n({n_samples} sample)',
                   ha='center', va='center', fontsize=14)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close('all')
            return None

        n_components = min(2, n_samples - 1)

        if method == 'pca':
            reducer = PCA(n_components=n_components, random_state=42)
            coords_reduced = reducer.fit_transform(self.vectors)
            if n_components == 1:
                coords_2d = np.column_stack([coords_reduced, np.zeros(n_samples)])
                subtitle = f"PCA projection (1D only, {n_samples} samples)"
            else:
                coords_2d = coords_reduced
                explained_var = reducer.explained_variance_ratio_
                subtitle = f"Explained variance: {explained_var[0]:.2%} + {explained_var[1]:.2%} = {sum(explained_var):.2%}"

        else:
            raise ValueError(f"Unknown method: {method}. Use 'pca', 'tsne', or 'umap'")

        fig, axes = plt.subplots(1, 2, figsize=figsize)
        unique_labels = sorted(set(labels))
        colors = sns.color_palette('husl', n_colors=len(unique_labels))

        for i, label in enumerate(unique_labels):
            mask = labels == label
            if label == -1:
                axes[0].scatter(coords_2d[mask, 0], coords_2d[mask, 1],
                              c='gray', marker='x', s=50, alpha=0.5, label='Noise')
            else:
                axes[0].scatter(coords_2d[mask, 0], coords_2d[mask, 1],
                              c=[colors[i]], s=100, alpha=0.7,
                              label=f'Cluster {label} (n={sum(mask)})')

        axes[0].set_title(f'{title}\n{subtitle}')
        axes[0].set_xlabel(f'{method.upper()} Component 1')
        axes[0].set_ylabel(f'{method.upper()} Component 2')
        axes[0].legend(loc='best')
        axes[0].grid(True, alpha=0.3)
        if self.filtered_df is not None:
            scores = np.array(self.filtered_df['score'].tolist())
            scatter = axes[1].scatter(coords_2d[:, 0], coords_2d[:, 1],
                                     c=scores, cmap='viridis', s=100, alpha=0.7)
            axes[1].set_title(f'Cosine Similarity Scores\n(min: {scores.min():.3f}, max: {scores.max():.3f})')
            axes[1].set_xlabel(f'{method.upper()} Component 1')
            axes[1].set_ylabel(f'{method.upper()} Component 2')
            plt.colorbar(scatter, ax=axes[1], label='Cosine Score')
            axes[1].grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Visualization saved to: {save_path}")

        plt.show()
        return coords_2d

