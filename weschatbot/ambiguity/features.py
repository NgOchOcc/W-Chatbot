import numpy as np
from scipy.stats import entropy
from scipy.spatial.distance import cdist


def _safe_div(a, b):
    return float(a / b) if b > 0 else 0.0

def _compute_cluster_sizes(labels):
    return {int(l): int(c) for l, c in zip(*np.unique(labels[labels != -1], return_counts=True))}

def _score_stats(scores):
    mean = scores.mean()
    return {
        'score_mean': float(mean),
        'score_std': float(scores.std()),
        'score_min': float(scores.min()),
        'score_max': float(scores.max()),
        'score_range': float(np.ptp(scores)),
        'score_cv': _safe_div(scores.std(), mean),
    }


class KMeansFeatures:
    @staticmethod
    def compute(vectors, labels, scores, distances, centers, k, question_id, algorithm, n_samples):
        cluster_sizes = _compute_cluster_sizes(labels)
        size_values = list(cluster_sizes.values())
        sorted_sizes = sorted(size_values, reverse=True)
        dist_mean = distances.mean()
        dist_std = distances.std()
        dist_min, dist_max = distances.min(), distances.max()
        cluster_probs = np.array(size_values) / n_samples
        size_mean, size_std = np.mean(size_values), np.std(size_values)
        major_clusters = sum(1 for s in size_values if s / n_samples >= 0.25)
        features = {
            'question_id': int(question_id),
            'algorithm': algorithm,
            'n_clusters': k,
            'n_samples': n_samples,
            'dist_mean': float(dist_mean),
            'dist_std': float(dist_std),
            'dist_min': float(dist_min),
            'dist_max': float(dist_max),
            'dist_range': float(dist_max - dist_min),
            'dist_cv': _safe_div(dist_std, dist_mean),
            'dist_q25': float(np.percentile(distances, 25)),
            'dist_q50': float(np.percentile(distances, 50)),
            'dist_q75': float(np.percentile(distances, 75)),
            'dist_iqr': float(np.ptp(np.percentile(distances, [75, 25]))),
            'cluster_size_mean': float(size_mean),
            'cluster_size_std': float(size_std),
            'cluster_size_min': int(min(size_values)),
            'cluster_size_max': int(max(size_values)),
            'cluster_imbalance': _safe_div(size_std, size_mean),
            'cluster_gini': float((2 * np.sum((np.arange(1, len(size_values) + 1) * np.sort(size_values)))) / (len(size_values) * np.cumsum(np.sort(size_values))[-1]) - (len(size_values) + 1) / len(size_values)),
            'cluster_entropy': float(entropy(cluster_probs)),
            'normalized_entropy': float(entropy(cluster_probs) / np.log(k)) if k > 1 else 0,
            'n_major_clusters': major_clusters,
            'has_multiple_major_clusters': int(major_clusters >= 2),
            'dominant_cluster_ratio': float(sorted_sizes[0] / n_samples),
            'second_largest_ratio': float(sorted_sizes[1] / n_samples) if len(sorted_sizes) > 1 else 0,
            'dominance_gap': float(sorted_sizes[0] / n_samples) - (float(sorted_sizes[1] / n_samples) if len(sorted_sizes) > 1 else 0),
        }

        if len(centers) >= 2:
            inter_dists = cdist(centers, centers)[np.triu_indices(len(centers), k=1)]
            inter_mean = inter_dists.mean()
            features.update({
                'inter_cluster_dist_mean': float(inter_mean),
                'inter_cluster_dist_min': float(inter_dists.min()),
                'inter_cluster_dist_max': float(inter_dists.max()),
                'compactness_ratio': _safe_div(dist_mean, inter_mean),
            })
        else:
            features.update({'inter_cluster_dist_mean': 0.0, 'inter_cluster_dist_min': 0.0, 'inter_cluster_dist_max': 0.0, 'compactness_ratio': 0.0})

        cluster_dist_means = [distances[labels == cid].mean() for cid in cluster_sizes]
        cluster_dist_stds = [distances[labels == cid].std() for cid in cluster_sizes]
        cluster_score_means = [scores[labels == cid].mean() for cid in cluster_sizes]
        cluster_score_stds = [scores[labels == cid].std() for cid in cluster_sizes]
        features.update({
            'within_cluster_dist_mean_avg': float(np.mean(cluster_dist_means)),
            'within_cluster_dist_mean_std': float(np.std(cluster_dist_means)),
            'within_cluster_dist_std_avg': float(np.mean(cluster_dist_stds)),
            'score_mean_across_clusters_std': float(np.std(cluster_score_means)),
            'score_std_across_clusters_mean': float(np.mean(cluster_score_stds)),
            'score_variation_between_clusters': _safe_div(np.std(cluster_score_means), np.mean(cluster_score_means)),
            'distance_score_corr': float(np.corrcoef(distances, scores)[0, 1]) if len(distances) > 1 else 0,
        })
        features.update(_score_stats(scores))
        return features


class HDBSCANFeatures:
    @staticmethod
    def compute(vectors, labels, scores, probabilities, question_id, algorithm, params):
        noise_mask = labels == -1
        n_noise = int(noise_mask.sum())
        n_samples = len(labels)
        unique_clusters = sorted(set(labels[~noise_mask]))
        n_clusters = len(unique_clusters)
        non_noise = n_samples - n_noise
        low, med, high = 0.5, 0.7, 0.9

        p_q25, p_q75 = np.percentile(probabilities, [25, 75])

        features = {
            'question_id': int(question_id),
            'algorithm': algorithm,
            'min_cluster_size': params['min_cluster_size'],
            'min_samples': params['min_samples'],
            'n_samples': n_samples,
            'n_clusters': n_clusters,
            'n_noise': n_noise,
            'noise_ratio': float(n_noise / n_samples),
            'all_noise': int(n_clusters == 0),
            'prob_mean': float(probabilities.mean()),
            'prob_std': float(probabilities.std()),
            'prob_min': float(probabilities.min()),
            'prob_max': float(probabilities.max()),
            'prob_q25': float(p_q25),
            'prob_q50': float(np.percentile(probabilities, 50)),
            'prob_q75': float(p_q75),
            'prob_iqr': float(p_q75 - p_q25),
            'low_confidence_ratio': float((probabilities < low).sum() / n_samples),
            'medium_confidence_ratio': float(((probabilities >= low) & (probabilities < med)).sum() / n_samples),
            'high_confidence_ratio': float((probabilities >= high).sum() / n_samples),
        }

        if n_clusters == 0:
            features.update({'cluster_size_mean': 0.0, 'cluster_prob_mean_avg': 0.0})
            features.update(_score_stats(scores))
            return features

        cluster_sizes = _compute_cluster_sizes(labels)
        size_values = list(cluster_sizes.values())
        sorted_sizes = sorted(size_values, reverse=True)
        size_mean, size_std = np.mean(size_values), np.std(size_values)

        cluster_probs = np.array(size_values) / non_noise if non_noise > 0 else np.array([])
        major_clusters = sum(1 for s in size_values if s / non_noise >= 0.25) if non_noise > 0 else 0

        features.update({
            'cluster_size_mean': float(size_mean),
            'cluster_size_std': float(size_std),
            'cluster_size_min': int(min(size_values)),
            'cluster_size_max': int(max(size_values)),
            'cluster_entropy': float(entropy(cluster_probs)) if len(cluster_probs) > 0 else 0.0,
            'normalized_entropy': float(entropy(cluster_probs) / np.log(n_clusters)) if len(cluster_probs) > 0 and n_clusters > 1 else 0.0,
            'n_major_clusters': major_clusters,
            'has_multiple_major_clusters': int(major_clusters >= 2),
        })

        if size_values:
            dom_ratio = _safe_div(sorted_sizes[0], non_noise)
            sec_ratio = _safe_div(sorted_sizes[1], non_noise) if len(sorted_sizes) > 1 else 0
            features.update({
                'dominant_cluster_ratio': dom_ratio,
                'second_largest_ratio': sec_ratio,
                'dominance_gap': dom_ratio - sec_ratio,
            })

        cluster_prob_means = [probabilities[labels == cid].mean() for cid in unique_clusters]
        cluster_prob_stds = [probabilities[labels == cid].std() for cid in unique_clusters]
        cluster_prob_mins = [probabilities[labels == cid].min() for cid in unique_clusters]
        cluster_low_ratios = [(probabilities[labels == cid] < low).sum() / (labels == cid).sum() for cid in unique_clusters]
        n_weak = sum(1 for r in cluster_low_ratios if r > 0.3)
        features.update({
            'cluster_prob_mean_avg': float(np.mean(cluster_prob_means)),
            'cluster_prob_mean_std': float(np.std(cluster_prob_means)),
            'cluster_prob_mean_min': float(min(cluster_prob_means)),
            'cluster_prob_std_avg': float(np.mean(cluster_prob_stds)),
            'cluster_prob_min_avg': float(np.mean(cluster_prob_mins)),
            'cluster_low_conf_ratio_avg': float(np.mean(cluster_low_ratios)),
            'cluster_low_conf_ratio_max': float(max(cluster_low_ratios)),
            'cluster_stability_indicator': float(1.0 - np.mean(cluster_prob_stds)),
            'n_weak_clusters': n_weak,
            'weak_cluster_ratio': _safe_div(n_weak, n_clusters),
        })
        cluster_centers = np.array([vectors[labels == cid].mean(axis=0) for cid in unique_clusters])
        if len(cluster_centers) >= 2:
            inter_dists = cdist(cluster_centers, cluster_centers)[np.triu_indices(len(cluster_centers), k=1)]
            features.update({
                'inter_cluster_dist_mean': float(inter_dists.mean()),
                'inter_cluster_dist_min': float(inter_dists.min()),
                'inter_cluster_dist_max': float(inter_dists.max()),
            })
        else:
            features.update({'inter_cluster_dist_mean': 0.0, 'inter_cluster_dist_min': 0.0, 'inter_cluster_dist_max': 0.0})

        compactness = [np.linalg.norm(vectors[labels == cid] - vectors[labels == cid].mean(axis=0), axis=1).mean()
                       for cid in unique_clusters if (labels == cid).sum() >= 2]
        if compactness:
            features.update({
                'cluster_compactness_mean': float(np.mean(compactness)),
                'cluster_compactness_std': float(np.std(compactness)),
            })
        else:
            features.update({'cluster_compactness_mean': 0.0, 'cluster_compactness_std': 0.0})

        if n_noise > 0:
            noise_probs, non_noise_probs = probabilities[noise_mask], probabilities[~noise_mask]
            noise_scores, non_noise_scores = scores[noise_mask], scores[~noise_mask]
            features.update({
                'noise_prob_mean': float(noise_probs.mean()),
                'noise_prob_max': float(noise_probs.max()),
                'noise_score_mean': float(noise_scores.mean()),
                'noise_vs_cluster_prob_diff': float(noise_probs.mean() - non_noise_probs.mean()) if len(non_noise_probs) > 0 else 0,
                'noise_vs_cluster_score_diff': float(noise_scores.mean() - non_noise_scores.mean()) if len(non_noise_scores) > 0 else 0,
            })
        else:
            features.update({k: 0.0 for k in ['noise_prob_mean', 'noise_prob_max', 'noise_score_mean',
                                              'noise_vs_cluster_prob_diff', 'noise_vs_cluster_score_diff']})

        features.update(_score_stats(scores))
        cluster_score_means = [scores[labels == cid].mean() for cid in unique_clusters]
        features['score_variation_between_clusters'] = _safe_div(np.std(cluster_score_means), np.mean(cluster_score_means))
        features['probability_score_corr'] = float(np.corrcoef(probabilities, scores)[0, 1]) if len(probabilities) > 1 else 0
        high_mask = probabilities >= high
        if high_mask.sum() > 0:
            high_unique = len(set(labels[high_mask]) - {-1})
            features['n_clusters_high_confidence'] = high_unique
            features['high_conf_cluster_ratio'] = _safe_div(high_unique, n_clusters)
        else:
            features.update({'n_clusters_high_confidence': 0, 'high_conf_cluster_ratio': 0.0})

        return features
