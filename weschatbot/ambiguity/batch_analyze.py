import argparse
import os
import pandas as pd
import numpy as np
from pathlib import Path
from cluster_analyzer import ClusterAnalyzer
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from datetime import datetime


class BatchAnalyzer:
    def __init__(self, data_path: str, output_dir: str = None,
                 methods: list = None):
        self.data_path = data_path
        self.output_dir = output_dir or "/Users/luungoc/Westaco/Chatbot/weschatbot/ambiguity/results"
        self.methods = methods or ['hdbscan', 'kmeans', 'dbscan']

        # Load data
        print(f"Loading data from: {data_path}")
        self.df = pd.read_parquet(data_path)

        # Get unique questions
        self.questions = self.df.groupby('question_id').agg({
            'question': 'first',
            'content': 'count',
            'score': ['mean', 'min', 'max']
        }).reset_index()

        self.questions.columns = ['question_id', 'question', 'n_chunks',
                                  'avg_score', 'min_score', 'max_score']


        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def analyze_question(self, question_id: int):
        question_dir = Path(self.output_dir) / f"question_{question_id}"
        question_dir.mkdir(parents=True, exist_ok=True)

        question_df = self.df[self.df['question_id'] == question_id].copy()

        if len(question_df) == 0:
            print(f"  ⚠️ No data for question {question_id}")
            return None

        question_text = question_df['question'].iloc[0]
        n_chunks = len(question_df)

        print(f"  Question: {question_text[:100]}...")
        print(f"  Chunks: {n_chunks}")
        # Initialize analyzer
        analyzer = ClusterAnalyzer(
            data_path=self.data_path,
            score_threshold=0.5,  # Lowered from 0.6 to include more chunks
            normalize_vectors=True
        )

        analyzer.df = question_df
        vectors_list = question_df['vector'].tolist()
        analyzer.vectors = np.vstack(vectors_list)
        analyzer.filtered_df = question_df

        question_info_path = question_dir / "question_info.txt"
        with open(question_info_path, 'w', encoding='utf-8') as f:
            f.write(f"Question ID: {question_id}\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Question:\n{question_text}\n\n")
            f.write(f"Number of chunks: {n_chunks}\n")
            f.write(f"Score statistics:\n")
            f.write(f"  Min: {question_df['score'].min():.3f}\n")
            f.write(f"  Max: {question_df['score'].max():.3f}\n")
            f.write(f"  Mean: {question_df['score'].mean():.3f}\n")
            f.write(f"  Median: {question_df['score'].median():.3f}\n")

        results = {
            'question_id': question_id,
            'question': question_text,
            'n_chunks': n_chunks
        }

        for method in self.methods:
            print(f"\n  --- Running {method.upper()} ---")

            try:
                method_result = self._analyze_with_method(
                    analyzer, question_id, method, question_dir
                )

                if method_result:
                    results[f'{method}_decision'] = method_result['decision']
                    results[f'{method}_n_clusters'] = method_result['n_clusters']
                    results[f'{method}_n_major'] = method_result['n_major_clusters']
                    results[f'{method}_silhouette'] = method_result['silhouette']
                    results[f'{method}_noise_ratio'] = method_result['noise_ratio']

                    print(f"  {method.upper()}: {method_result['decision'].upper()}")
                else:
                    print(f"  {method.upper()}: Failed")

            except Exception as e:
                print(f"  {method.upper()} error: {str(e)}")

        self._save_chunk_details(question_df, question_dir)
        return results

    def _analyze_with_method(self, analyzer, question_id, method, output_dir):
        try:
            if method == 'kmeans':
                results = analyzer.apply_kmeans(n_clusters_range=range(2, 6))
                if not results:
                    return None
                best_config = max(results.items(), key=lambda x: x[1]['silhouette'])
                labels = best_config[1]['labels']
                params = {
                    'n_clusters': best_config[0],
                    'silhouette': best_config[1]['silhouette']
                }

            elif method == 'dbscan':
                results = analyzer.apply_dbscan(
                    eps_values=[0.3, 0.5, 0.7, 1.0, 1.5],  # Broader range for better coverage
                    min_samples_values=[2, 3, 5]  # Include smaller min_samples
                )
                valid_results = {k: v for k, v in results.items() if v['silhouette'] > -1}
                if not valid_results:
                    return None
                best_config = max(valid_results.items(), key=lambda x: x[1]['silhouette'])
                labels = best_config[1]['labels']
                params = {
                    'eps': best_config[1]['eps'],
                    'min_samples': best_config[1]['min_samples'],
                    'silhouette': best_config[1]['silhouette']
                }

            elif method == 'hdbscan':
                results = analyzer.apply_hdbscan(
                    min_cluster_sizes=[2, 3, 5, 10],  # Include smaller cluster sizes
                    min_samples_values=[2, 3, 5]  # Include smaller min_samples
                )
                valid_results = {k: v for k, v in results.items() if v['silhouette'] > -1}
                if not valid_results:
                    return None
                best_config = max(valid_results.items(), key=lambda x: x[1]['silhouette'])
                labels = best_config[1]['labels']
                params = {
                    'min_cluster_size': best_config[1]['min_cluster_size'],
                    'min_samples': best_config[1]['min_samples'],
                    'silhouette': best_config[1]['silhouette']
                }
            else:
                return None

            report = analyzer.generate_report(labels, method.upper(), params)
            decision, analysis = analyzer.detect_ambiguity(labels)
            report_path = output_dir / f"{method}_report.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
                f.write(f"\n\n{'='*60}\n")
                f.write(f"DECISION: {decision.upper()}\n")
                f.write(f"{'='*60}\n\n")
                f.write(f"Reason: {analysis['reason']}\n\n")

                if decision == 'ambiguous':
                    f.write(f"Major Clusters:\n")
                    for cluster_id, info in analysis['major_clusters'].items():
                        f.write(f"  - Cluster {cluster_id}: {info['count']} chunks ({info['ratio']:.1%})\n")

            viz_path = output_dir / f"{method}_clusters.jpg"
            analyzer.visualize_clusters_2d(
                labels,
                title=f"{method.upper()} Clustering - Question {question_id}",
                method='pca',
                save_path=str(viz_path),
                figsize=(14, 8)
            )
            plt.close('all') 

            return {
                'decision': decision,
                'n_clusters': analysis['n_total_clusters'],
                'n_major_clusters': analysis['n_major_clusters'],
                'silhouette': analysis['silhouette_score'],
                'noise_ratio': analysis['noise_ratio'],
                'labels': labels
            }

        except Exception as e:
            print(f"    Error in {method}: {str(e)}")
            return None

    def _save_chunk_details(self, question_df, output_dir):
        chunks_path = output_dir / "chunks_list.txt"
        with open(chunks_path, 'w', encoding='utf-8') as f:
            f.write(f"RETRIEVED CHUNKS\n")
            f.write(f"{'='*80}\n\n")

            for idx, row in question_df.iterrows():
                f.write(f"Chunk {idx + 1}:\n")
                f.write(f"  Score: {row['score']:.3f}\n")
                f.write(f"  Content: {row['content']}...\n")
                f.write(f"\n{'-'*80}\n\n")

        csv_path = output_dir / "chunks_data.csv"
        question_df[['question_id', 'question', 'content', 'score']].to_csv(
            csv_path, index=False, encoding='utf-8'
        )

    def run_batch_analysis(self, question_ids: list = None):
        start_time = datetime.now()

        if question_ids is None:
            questions_to_analyze = self.questions['question_id'].tolist()
        else:
            questions_to_analyze = question_ids


        all_results = []
        for i, qid in enumerate(questions_to_analyze, 1):
            print(f"\n[{i}/{len(questions_to_analyze)}] Processing question {qid}...")

            result = self.analyze_question(qid)

            if result:
                all_results.append(result)

        if all_results:
            summary_df = pd.DataFrame(all_results)
            summary_path = Path(self.output_dir) / "analysis_summary.csv"
            summary_df.to_csv(summary_path, index=False, encoding='utf-8')

            for method in self.methods:
                decision_col = f'{method}_decision'
                if decision_col in summary_df.columns:
                    counts = summary_df[decision_col].value_counts()
                    print(f"\n  {method.upper()}:")
                    for decision, count in counts.items():
                        print(f"    {decision}: {count} ({count/len(summary_df):.1%})")

        return all_results


def main():
    parser = argparse.ArgumentParser(
        description='Batch analyze all questions for ambiguity detection'
    )
    parser.add_argument(
        '--data_path',
        type=str,
        default='/Users/luungoc/Westaco/Westaco Data/decision_step.parquet',
        help='Path to the parquet data file'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        default='/Users/luungoc/Westaco/Chatbot/weschatbot/ambiguity/results',
        help='Output directory for results'
    )
    parser.add_argument(
        '--methods',
        type=str,
        default='hdbscan,kmeans,hdbscan',
        help='Comma-separated list of methods (kmeans,dbscan,hdbscan)'
    )
    parser.add_argument(
        '--question_ids',
        type=str,
        default=None,
        help='Optional: comma-separated list of specific question IDs to analyze'
    )

    args = parser.parse_args()
    methods = [m.strip().lower() for m in args.methods.split(',')]
    question_ids = None
    if args.question_ids:
        question_ids = [int(qid.strip()) for qid in args.question_ids.split(',')]

    batch_analyzer = BatchAnalyzer(
        data_path=args.data_path,
        output_dir=args.output_dir,
        methods=methods
    )

    batch_analyzer.run_batch_analysis(question_ids=question_ids)


if __name__ == "__main__":
    main()
