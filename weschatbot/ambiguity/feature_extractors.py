import json
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Optional
from pathlib import Path
from weschatbot.ambiguity.features import KMeansFeatures, HDBSCANFeatures


class BaseFeatureExtractor(ABC):
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)
        self.algorithm = self.df['algorithm'].iloc[0]
        self.params = json.loads(self.df['params'].iloc[0])
        self.question_ids = sorted(self.df['question_id'].unique())

    @abstractmethod
    def extract_features(self, question_id: int) -> Optional[Dict]:
        pass

    def extract_all_features(self) -> pd.DataFrame:
        return pd.DataFrame([f for qid in self.question_ids if (f := self.extract_features(qid))])

    def _parse_vectors(self, series: pd.Series) -> np.ndarray:
        return np.array([json.loads(v) for v in series])

    def _get_question_data(self, question_id: int) -> Optional[pd.DataFrame]:
        q_df = self.df[self.df['question_id'] == question_id]
        return q_df if len(q_df) >= 2 else None


class KMeansFeatureExtractor(BaseFeatureExtractor):
    def extract_features(self, question_id: int) -> Optional[Dict]:
        if (q_df := self._get_question_data(question_id)) is None:
            return None

        return KMeansFeatures.compute(
            vectors=self._parse_vectors(q_df['chunk_vector']),
            labels=q_df['cluster_label'].values,
            scores=q_df['score'].values,
            distances=q_df['distance_to_center'].values,
            centers=np.unique(self._parse_vectors(q_df['cluster_center']), axis=0),
            k=self.params['n_clusters'],
            question_id=question_id,
            algorithm=self.algorithm,
            n_samples=len(q_df)
        )


class HDBSCANFeatureExtractor(BaseFeatureExtractor):
    def extract_features(self, question_id: int) -> Optional[Dict]:
        if (q_df := self._get_question_data(question_id)) is None:
            return None

        return HDBSCANFeatures.compute(
            vectors=self._parse_vectors(q_df['chunk_vector']),
            labels=q_df['cluster_label'].values,
            scores=q_df['score'].values,
            probabilities=q_df['cluster_probability'].values,
            question_id=question_id,
            algorithm=self.algorithm,
            params=self.params
        )


EXTRACTORS = {
    'kmeans': ('kmeans_*.csv', KMeansFeatureExtractor),
    'hdbscan': ('hdbscan_*.csv', HDBSCANFeatureExtractor)
}


def extract_all_algorithm_features(clustering_results_dir: str, output_dir: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    results_path = Path(clustering_results_dir)
    output_path = Path(output_dir) if output_dir else None
    if output_path:
        output_path.mkdir(parents=True, exist_ok=True)

    result_dfs = {}
    for algo, (pattern, extractor_class) in EXTRACTORS.items():
        print(f"Extracting {algo.upper()} features...")
        features_list = [extractor_class(str(f)).extract_all_features()
                        for f in sorted(results_path.glob(pattern))]
        features_list = [df for df in features_list if not df.empty]

        if features_list:
            combined_df = pd.concat(features_list, ignore_index=True)
            result_dfs[algo] = combined_df
            if output_path:
                output_file = output_path / f"{algo}_features.csv"
                combined_df.to_csv(output_file, index=False)
                print(f"Saved {algo} features to {output_file}")

    return result_dfs


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract features from clustering results for XGBoost training")
    parser.add_argument('--clustering_dir', required=True)
    parser.add_argument('--output_dir', default='./features')
    args = parser.parse_args()

    features = extract_all_algorithm_features(args.clustering_dir, args.output_dir)
    print("\nFeature extraction summary:")
    for algo, df in features.items():
        print(f"{algo}: {len(df)} samples, {len(df.columns)} features")
