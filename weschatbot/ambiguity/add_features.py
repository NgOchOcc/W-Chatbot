import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import hdbscan
from weschatbot.ambiguity.features import KMeansFeatures, HDBSCANFeatures


def add_features_and_save(df, features_df, output_path):
    result = df.merge(features_df, on='question_id', how='left')
    result.to_parquet(output_path, index=False)
    return result

def parse_vectors(df):
    if isinstance(df['vector'].iloc[0], str):
        return np.array([json.loads(v) for v in df['vector']])
    return np.vstack(df['vector'].tolist())

def extract_kmeans_features(df, k):
    question_ids = sorted(df['question_id'].unique())
    results = []

    for qid in question_ids:
        q_data = df[df['question_id'] == qid]

        if len(q_data) < 2 or k >= len(q_data):
            continue

        vectors = parse_vectors(q_data)
        scores = q_data['score'].values

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(vectors)

        distances = []
        for i in range(len(vectors)):
            dist = np.linalg.norm(vectors[i] - kmeans.cluster_centers_[labels[i]])
            distances.append(dist)
        distances = np.array(distances)

        features = KMeansFeatures.compute(
            vectors=vectors,
            labels=labels,
            scores=scores,
            distances=distances,
            centers=kmeans.cluster_centers_,
            k=k,
            question_id=qid,
            algorithm='kmeans',
            n_samples=len(q_data)
        )
        results.append(features)

    return pd.DataFrame(results)

def extract_hdbscan_features(df, min_cluster_size, min_samples):
    question_ids = sorted(df['question_id'].unique())
    results = []

    for qid in question_ids:
        q_data = df[df['question_id'] == qid]

        if len(q_data) < 2 or min_cluster_size > len(q_data) // 2:
            continue

        vectors = parse_vectors(q_data)
        scores = q_data['score'].values
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples
        )
        labels = clusterer.fit_predict(vectors)
        features = HDBSCANFeatures.compute(
            vectors=vectors,
            labels=labels,
            scores=scores,
            probabilities=clusterer.probabilities_,
            question_id=qid,
            algorithm='hdbscan',
            params={'min_cluster_size': min_cluster_size, 'min_samples': min_samples}
        )
        results.append(features)

    return pd.DataFrame(results)