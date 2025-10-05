import json
from pathlib import Path
from glob import glob
from chunk_processor import (
    ChunkingProcessor,
    chunk_markdown_to_csv
)
from chunking_strategy import (
    StructureAwareChunkingStrategy,
)
from adaptive_markdown_strategy import AdaptiveMarkdownStrategy
from recursive_markdown_strategy import RecursiveMarkdownStrategy


def basic_processor():
    processor = ChunkingProcessor(strategy_name='hybrid')
    output_path = processor.process_markdown_file(
        input_file_path='/Users/luungoc/Westaco/W-Chatbot/data/_data/OMV_Petrom_Marketing_SRL.20bed50de44db3e33d34967a84b09d66b09d9cf662bb9be5050c8b6fdee5a9a0.pdf.converted.md',
        output_csv_path='/Users/luungoc/Westaco/W-Chatbot/data/chunking_csv/OMV_Petrom_Marketing_SRL.csv'
    )
    print(f"Chunks saved to: {output_path}")


def different_strategies():
    input_file = '/Users/luungoc/Westaco/W-Chatbot/data/_data/OMV_Petrom_Marketing_SRL.20bed50de44db3e33d34967a84b09d66b09d9cf662bb9be5050c8b6fdee5a9a0.pdf.converted.md'
    output_dir = '/Users/luungoc/Westaco/W-Chatbot/data/chunking_csv/'

    processor1 = ChunkingProcessor(strategy_name='structure_aware')
    output1 = processor1.process_markdown_file(
        input_file,
        output_csv_path=output_dir + 'chunks_structure.csv'
    )
    print(f"Structure-aware chunks: {output1}")

    processor2 = ChunkingProcessor(strategy_name='table_preserving')
    output2 = processor2.process_markdown_file(
        input_file,
        output_csv_path=output_dir + 'chunks_table.csv'
    )
    print(f"Table-preserving chunks: {output2}")

    processor3 = ChunkingProcessor(strategy_name='sentence_split')
    output3 = processor3.process_markdown_file(
        input_file,
        output_csv_path=output_dir + 'chunks_sentence.csv'
    )
    print(f"Sentence-split chunks: {output3}")


def adaptive_markdown_strategy():
    adaptive_strategy = AdaptiveMarkdownStrategy(
        chunk_size=1024,
        chunk_overlap=256,
        max_chunk_size=2048,
        preserve_table_headers=True
    )

    list_path = glob('/Users/luungoc/Westaco/W-Chatbot/data/_data/*.md')
    output_dir = '/Users/luungoc/Westaco/W-Chatbot/data/chunking_csv/adaptive_data/'

    for path in list_path:
        name_file = Path(path).name.split('.')[0]
        processor = ChunkingProcessor(strategy=adaptive_strategy)
        output_path = processor.process_markdown_file(
            input_file_path=path,
            output_csv_path=output_dir + f'{name_file}' + '_adaptive_chunks.csv'
        )
        print(f"Chunks saved to: {output_path}")
        print("---"*30)


def recursive_strategy():
    recursive_strategy = RecursiveMarkdownStrategy(
        chunk_size=1500,
        chunk_overlap=300,
        max_chunk_size=3000,
        min_chunk_size=500,
    )

    list_path = glob('/Users/luungoc/Westaco/W-Chatbot/data/_data/*.md')
    output_dir = '/Users/luungoc/Westaco/W-Chatbot/data/chunking_csv/recursive_data/'

    for path in list_path:
        name_file = Path(path).name.split('.')[0]
        processor = ChunkingProcessor(strategy=recursive_strategy)
        output_path = processor.process_markdown_file(
            input_file_path=path,
            output_csv_path=output_dir + f'{name_file}' + '_recursive_chunks.csv'
        )
        print(f"Chunks saved to: {output_path}")
        print("---"*30)

if __name__ == '__main__':
    # basic_processor()
    # different_strategies()
    adaptive_markdown_strategy()
    recursive_strategy()