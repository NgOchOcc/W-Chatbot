import argparse
import pandas as pd

from pathlib import Path
from typing import Optional
from multiprocessing import Pool
from weschatbot.ambiguity.compute_metrics import ClusteringMetricsComputer


def process_single_file(args):
    csv_file, output_dir = args
    computer = ClusteringMetricsComputer(str(csv_file))
    metrics_df = computer.compute_all_metrics()
    metrics_df['params'] = str(computer.params)

    output_file = f"{output_dir}/{csv_file.stem}_metrics.csv"
    metrics_df.to_csv(output_file, index=False)
    return metrics_df, csv_file.name


def batch_compute_metrics(input_dir: str, output_dir: Optional[str] = None, pattern: str = "*.csv", n_workers: int = 8):
    input_path = Path(input_dir)
    csv_files = sorted(input_path.glob(pattern))
    csv_files = [f for f in csv_files if not f.name.endswith('_metrics.csv')]
    if output_dir is None:
        output_dir = f"{input_path}/metrics"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    args_list = [(csv_file, output_path) for csv_file in csv_files]
    all_metrics = []

    with Pool(n_workers) as pool:
        results = pool.map(process_single_file, args_list)

    for metrics_df, filename in results:
        if metrics_df is not None:
            all_metrics.append(metrics_df)

    if all_metrics:
        summary_df = pd.concat(all_metrics, ignore_index=True)
        summary_path = f"{output_path}/all_metrics_summary.csv"
        summary_df.to_csv(summary_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True)
    parser.add_argument('--output_dir', default=None)
    parser.add_argument('--pattern', default='*.csv')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()

    batch_compute_metrics(args.input_dir, args.output_dir, args.pattern, args.workers)
