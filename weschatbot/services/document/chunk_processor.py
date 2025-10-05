import csv
import json
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime

from llama_index.core import Document as LlamaDocument

from chunking_strategy import (
    BaseChunkingStrategy,
    SentencesplitStrategy,
    StructureAwareChunkingStrategy,
    TablePreservingStrategy,
)


class ChunkingProcessor:
    """
    Process markdown files and export chunks to CSV format.
    Supports multiple chunking strategies.
    """

    def __init__(
        self,
        strategy: Optional[BaseChunkingStrategy] = None,
        strategy_name: str = 'hybrid'
    ):
        """
        Initialize ChunkingProcessor

        Args:
            strategy: Custom chunking strategy instance. If None, will use strategy_name
            strategy_name: Name of predefined strategy ('hybrid', 'structure_aware',
                          'table_preserving', 'sentence_split'). Default: 'hybrid'
        """
        if strategy is not None:
            self.strategy = strategy
            self.strategy_name = 'custom'
        else:
            self.strategy = self._get_strategy_by_name(strategy_name)
            self.strategy_name = strategy_name

        self.list_columns = ['chunk_id', 'text', 'text_length', 'word_count', 'total_chunks', 'metadata_json']

    def _get_strategy_by_name(self, name: str) -> BaseChunkingStrategy:
        """Get chunking strategy by name"""
        strategies = {
            'structure_aware': StructureAwareChunkingStrategy(),
            'table_preserving': TablePreservingStrategy(),
            'sentence_split': SentencesplitStrategy()
        }

        if name not in strategies:
            raise ValueError(
                f"Unknown strategy '{name}'. Available: {list(strategies.keys())}"
            )

        return strategies[name]

    def process_markdown_file(
        self,
        input_file_path: Union[str, Path],
        output_csv_path: Optional[Union[str, Path]] = None,
        additional_metadata: Optional[Dict] = None,
        include_metadata_columns: Optional[List[str]] = None,
        encoding: str = 'utf-8'
    ) -> str:
        """
        Process a markdown file and export chunks to CSV

        Args:
            input_file_path: Path to input .md file
            output_csv_path: Path to output CSV file. If None, auto-generate based on input filename
            additional_metadata: Additional metadata to add to all chunks
            include_metadata_columns: List of metadata keys to include as separate columns in CSV
            encoding: File encoding (default: utf-8)

        Returns:
            Path to the generated CSV file
        """
        input_path = Path(input_file_path)

        # Validate input file
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file_path}")

        if input_path.suffix.lower() != '.md':
            raise ValueError(f"Input file must be .md format, got: {input_path.suffix}")

        # Generate output path if not provided
        if output_csv_path is None:
            output_csv_path = input_path.parent / f"{input_path.stem}_chunks.csv"
        else:
            output_csv_path = Path(output_csv_path)

        # Read markdown content
        content = input_path.read_text(encoding=encoding)

        # Prepare metadata
        metadata = {
            'source_file': str(input_path.name),
            'source_path': str(input_path.absolute()),
            'processing_date': datetime.now().isoformat(),
            'chunking_strategy': self.strategy_name
        }

        if additional_metadata:
            metadata.update(additional_metadata)

        # Chunk the content
        chunks = self.strategy.chunk_markdown(content, metadata)

        # Export to CSV
        self._export_to_csv(
            chunks,
            output_csv_path,
            include_metadata_columns=include_metadata_columns
        )

        return str(output_csv_path)

    def _export_to_csv(
        self,
        chunks: List[LlamaDocument],
        output_path: Path,
        include_metadata_columns: Optional[List[str]] = None
    ):
        """Export chunks to CSV file"""

        if not chunks:
            raise ValueError("No chunks to export")

        # Determine all metadata keys if not specified
        if include_metadata_columns is None:
            # Collect all unique metadata keys from chunks
            all_metadata_keys = set()
            for chunk in chunks:
                all_metadata_keys.update(chunk.metadata.keys())
            include_metadata_columns = sorted(all_metadata_keys)

        # Define CSV columns
        columns = ['chunk_id', 'text', 'text_length', 'word_count']

        # Add metadata columns
        for meta_key in include_metadata_columns:
            if meta_key not in columns:
                columns.append(meta_key)

        # Add full metadata as JSON column
        columns.append('metadata_json')

        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.list_columns)
            writer.writeheader()
            for i, chunk in enumerate(chunks):
                row = {}
                
                if 'chunk_id' in self.list_columns:
                    row['chunk_id'] = i + 1
                    
                if 'text' in self.list_columns:
                    row['text'] = chunk.text
                    
                if 'text_length' in self.list_columns:
                    row['text_length'] = len(chunk.text)
                    
                if 'word_count' in self.list_columns:
                    row['word_count'] = len(chunk.text.split())
                
                for meta_key in include_metadata_columns:
                    if meta_key in self.list_columns:
                        value = chunk.metadata.get(meta_key, '')
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value, ensure_ascii=False)
                        row[meta_key] = value
                
                if 'metadata_json' in self.list_columns:
                    row['metadata_json'] = json.dumps(chunk.metadata, ensure_ascii=False)
                    
                writer.writerow(row)

    def process_multiple_files(
        self,
        input_files: List[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
        additional_metadata: Optional[Dict] = None,
        include_metadata_columns: Optional[List[str]] = None
    ) -> List[str]:
        """
        Process multiple markdown files

        Args:
            input_files: List of paths to .md files
            output_dir: Directory for output CSV files. If None, use same dir as input files
            additional_metadata: Additional metadata for all files
            include_metadata_columns: Metadata columns to include in CSV

        Returns:
            List of paths to generated CSV files
        """
        output_paths = []

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        for input_file in input_files:
            input_path = Path(input_file)

            if output_dir:
                output_csv = output_dir / f"{input_path.stem}_chunks.csv"
            else:
                output_csv = None

            try:
                output_path = self.process_markdown_file(
                    input_path,
                    output_csv,
                    additional_metadata,
                    include_metadata_columns
                )
                output_paths.append(output_path)
                print(f"✓ Processed: {input_path.name} → {output_path}")
            except Exception as e:
                print(f"✗ Failed to process {input_path.name}: {str(e)}")

        return output_paths

    def get_chunk_statistics(self, chunks: List[LlamaDocument]) -> Dict:
        """Get statistics about chunks"""
        if not chunks:
            return {}

        text_lengths = [len(chunk.text) for chunk in chunks]
        word_counts = [len(chunk.text.split()) for chunk in chunks]

        # Count chunk types
        chunk_types = {}
        for chunk in chunks:
            chunk_type = chunk.metadata.get('chunk_type', 'unknown')
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

        return {
            'total_chunks': len(chunks),
            'avg_text_length': sum(text_lengths) / len(text_lengths),
            'min_text_length': min(text_lengths),
            'max_text_length': max(text_lengths),
            'avg_word_count': sum(word_counts) / len(word_counts),
            'min_word_count': min(word_counts),
            'max_word_count': max(word_counts),
            'chunk_types': chunk_types
        }

    def process_with_statistics(
        self,
        input_file_path: Union[str, Path],
        output_csv_path: Optional[Union[str, Path]] = None,
        print_stats: bool = True
    ) -> Dict:
        """
        Process markdown file and return statistics

        Args:
            input_file_path: Path to input .md file
            output_csv_path: Path to output CSV
            print_stats: Whether to print statistics

        Returns:
            Dictionary with output_path and statistics
        """
        # Read and chunk
        input_path = Path(input_file_path)
        content = input_path.read_text(encoding='utf-8')

        metadata = {
            'source_file': str(input_path.name),
            'chunking_strategy': self.strategy_name
        }

        chunks = self.strategy.chunk_markdown(content, metadata)

        # Get statistics
        stats = self.get_chunk_statistics(chunks)

        # Export to CSV
        if output_csv_path is None:
            output_csv_path = input_path.parent / f"{input_path.stem}_chunks.csv"

        self._export_to_csv(chunks, Path(output_csv_path))

        result = {
            'output_path': str(output_csv_path),
            'statistics': stats
        }

        if print_stats:
            print(f"\n{'='*60}")
            print(f"Chunking Statistics for: {input_path.name}")
            print(f"{'='*60}")
            print(f"Strategy: {self.strategy_name}")
            print(f"Total chunks: {stats['total_chunks']}")
            print(f"\nText Length:")
            print(f"  - Average: {stats['avg_text_length']:.0f} chars")
            print(f"  - Min: {stats['min_text_length']} chars")
            print(f"  - Max: {stats['max_text_length']} chars")
            print(f"\nWord Count:")
            print(f"  - Average: {stats['avg_word_count']:.0f} words")
            print(f"  - Min: {stats['min_word_count']} words")
            print(f"  - Max: {stats['max_word_count']} words")
            print(f"\nChunk Types:")
            for chunk_type, count in stats['chunk_types'].items():
                print(f"  - {chunk_type}: {count}")
            print(f"\nOutput saved to: {output_csv_path}")
            print(f"{'='*60}\n")

        return result


# Convenience function for quick usage
def chunk_markdown_to_csv(
    input_file: Union[str, Path],
    output_file: Optional[Union[str, Path]] = None,
    strategy: str = 'hybrid',
    print_stats: bool = True
) -> str:
    """
    Quick function to chunk a markdown file to CSV

    Args:
        input_file: Path to .md file
        output_file: Path to output CSV (optional)
        strategy: Chunking strategy ('hybrid', 'structure_aware', 'table_preserving', 'sentence_split')
        print_stats: Print statistics

    Returns:
        Path to output CSV file

    Example:
        >>> chunk_markdown_to_csv('document.md', strategy='hybrid')
        >>> chunk_markdown_to_csv('report.md', 'output.csv', strategy='table_preserving')
    """
    processor = ChunkingProcessor(strategy_name=strategy)
    result = processor.process_with_statistics(input_file, output_file, print_stats)
    return result['output_path']
