import argparse
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from pathlib import Path
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages


class PDFReportGenerator:
    def __init__(self, algo_dir: str):
        self.algo_dir = Path(algo_dir)
        self.output_path = self.algo_dir / f"{self.algo_dir.name}_report.pdf"
        self.question_dirs = sorted([d for d in self.algo_dir.iterdir()
                                    if d.is_dir() and d.name.startswith('question_')])

    def generate_report(self):
        print(f"PDF: {self.output_path.name}")
        with PdfPages(self.output_path) as pdf:
            self._add_title_page(pdf)

            for q_dir in self.question_dirs:
                qid = q_dir.name.split('_')[1]
                images = self._get_ordered_images(q_dir)

                for img_path in images:
                    fig = plt.figure(figsize=(11, 8.5)) 
                    ax = fig.add_subplot(111)

                    img = mpimg.imread(str(img_path))
                    ax.imshow(img)
                    ax.axis('off')

                    title = f"Question {qid} - {img_path.stem.replace('_', ' ').title()}"
                    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.98)

                    plt.tight_layout(rect=(0, 0, 1, 0.96))
                    pdf.savefig(fig, dpi=150, bbox_inches='tight')
                    plt.close(fig)

            d = pdf.infodict()
            d['Title'] = f'Clustering Report - {self.algo_dir.name}'
            d['CreationDate'] = datetime.now()

        return self.output_path

    def _get_ordered_images(self, q_dir):
        images = sorted(q_dir.glob('*.png'))
        analysis_images = [f for f in images if 'analysis' in f.name]
        if analysis_images:
            return analysis_images

        plot_order = ['tsne', 'distribution', 'silhouette', 'score_distribution',
                     'kmeans_distances', 'hdbscan_probabilities']

        ordered = []
        for plot_type in plot_order:
            matching = [f for f in images if plot_type in f.name]
            if matching:
                ordered.append(matching[0])

        for img in images:
            if img not in ordered:
                ordered.append(img)

        return ordered

    def _add_title_page(self, pdf):
        fig = plt.figure(figsize=(11, 8.5))
        ax = fig.add_subplot(111)
        ax.axis('off')

        ax.text(0.5, 0.7, f'Clustering Visualization Report\n{self.algo_dir.name}',
               ha='center', va='center', fontsize=20, fontweight='bold', transform=ax.transAxes)

        info_text += f'Total Questions: {len(self.question_dirs)}'
        ax.text(0.5, 0.5, info_text, ha='center', va='center', fontsize=12, transform=ax.transAxes)
        pdf.savefig(fig)
        plt.close(fig)

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('algo_dir', help='Algorithm directory with question subdirs')
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    generator = PDFReportGenerator(args.algo_dir)
    generator.generate_report()
