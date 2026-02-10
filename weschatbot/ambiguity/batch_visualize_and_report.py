import argparse

from pathlib import Path
from typing import Optional
from multiprocessing import Pool
from weschatbot.ambiguity.pdf_report import PDFReportGenerator
from weschatbot.ambiguity.visualize import PerQuestionVisualizer


def process_single_visualization(args):
    csv_file, output_path = args
    visualizer = PerQuestionVisualizer(str(csv_file), str(output_path))
    algo_dir = visualizer.generate_all_visualizations()

    generator = PDFReportGenerator(algo_dir)
    pdf_path = generator.generate_report()

    return pdf_path, csv_file.name


def batch_process(input_dir: str, output_dir: Optional[str] = None, pattern: str = "*.csv", n_workers: int = 9):
    input_path = Path(input_dir)
    csv_files = sorted(input_path.glob(pattern))

    if output_dir is None:
        output_dir = f"{input_path}/visualizations"

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    args_list = [(csv_file, output_path) for csv_file in csv_files]
    pdf_files = []
    with Pool(n_workers) as pool:
        results = pool.map(process_single_visualization, args_list)

    for pdf_path, filename in results:
        if pdf_path is not None:
            pdf_files.append(pdf_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', required=True)
    parser.add_argument('--output_dir', default=None)
    parser.add_argument('--pattern', default='*.csv')
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()

    batch_process(args.input_dir, args.output_dir, args.pattern, args.workers)
