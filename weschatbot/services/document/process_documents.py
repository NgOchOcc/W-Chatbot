#!/usr/bin/env python3
"""
Script to process documents end-to-end:
1. Convert documents to markdown
2. Chunk documents using advanced strategy
3. Index chunks into Milvus vector database
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict
import json

from weschatbot.services.document.index_document_service import DocumentConverter, Pipeline
from weschatbot.services.document.chunking_strategy import AdvancedChunkingStrategy
from weschatbot.utils.config import config
from weschatbot.log.logging_mixin import LoggingMixin


class DocumentProcessor(LoggingMixin):
    """Main processor for document pipeline"""
    
    def __init__(self, 
                 collection_name: str = "westaco_documents",
                 embedding_model: str = "Qwen/Qwen3-Embedding-0.6B",
                 embedding_dim: int = 1024):
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        
        # Initialize components
        self.converter = DocumentConverter()
        self.pipeline = Pipeline(
            collection_name=self.collection_name,
            embedding_model_name=self.embedding_model,
            dim=self.embedding_dim
        )
        
    def process_directory(self, directory_path: str, file_extensions: List[str] = None):
        """Process all documents in a directory"""
        if file_extensions is None:
            file_extensions = ['.md', '.pdf', '.docx', '.txt', '.xls', '.xlsx']
            
        directory = Path(directory_path)
        if not directory.exists():
            raise ValueError(f"Directory not found: {directory_path}")
            
        # Find all matching files
        files_to_process = []
        for ext in file_extensions:
            files_to_process.extend(directory.rglob(f"*{ext}"))
        
        self.log.info(f"Found {len(files_to_process)} files to process")
        
        # Process files in batches
        batch_size = 10
        for i in range(0, len(files_to_process), batch_size):
            batch_files = files_to_process[i:i + batch_size]
            self._process_batch(batch_files)
            
    def process_files(self, file_paths: List[str]):
        """Process specific files"""
        files = [Path(fp) for fp in file_paths]
        
        # Validate all files exist
        for file in files:
            if not file.exists():
                self.log.error(f"File not found: {file}")
                return
                
        self._process_batch(files)
        
    def _process_batch(self, files: List[Path]):
        """Process a batch of files"""
        self.log.info(f"Processing batch of {len(files)} files")
        
        converted_docs = []
        metadata_list = []
        
        for file_path in files:
            try:
                # Convert document
                self.log.info(f"Converting: {file_path}")
                content = self.converter.convert(str(file_path))
                
                # Prepare metadata
                metadata = {
                    "file_path": str(file_path),
                    "file_name": file_path.name,
                    "file_type": file_path.suffix,
                    "parent_dir": file_path.parent.name,
                }
                
                # Check for existing metadata file
                meta_file = file_path.parent / f"{file_path.stem}_meta.json"
                if meta_file.exists():
                    with open(meta_file, 'r') as f:
                        additional_meta = json.load(f)
                        metadata.update(additional_meta)
                
                converted_docs.append(content)
                metadata_list.append(metadata)
                
            except Exception as e:
                self.log.error(f"Error processing {file_path}: {str(e)}")
                continue
        
        if converted_docs:
            # Run pipeline to chunk and index
            self.log.info(f"Indexing {len(converted_docs)} documents")
            self.pipeline.run(converted_docs, metadata_list)
            self.log.info("Batch processing completed")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Process documents for vector database")
    parser.add_argument(
        "--directory", "-d",
        help="Directory containing documents to process",
        type=str
    )
    parser.add_argument(
        "--files", "-f",
        nargs='+',
        help="Specific files to process",
        type=str
    )
    parser.add_argument(
        "--collection",
        default="westaco_documents",
        help="Milvus collection name"
    )
    parser.add_argument(
        "--embedding-model",
        default="Qwen/Qwen3-Embedding-0.6B",
        help="Embedding model name"
    )
    parser.add_argument(
        "--embedding-dim",
        default=1024,
        type=int,
        help="Embedding dimension"
    )
    parser.add_argument(
        "--extensions",
        nargs='+',
        default=['.md', '.pdf', '.docx', '.txt'],
        help="File extensions to process"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create processor
    processor = DocumentProcessor(
        collection_name=args.collection,
        embedding_model=args.embedding_model,
        embedding_dim=args.embedding_dim
    )
    
    # Process based on input
    if args.directory:
        processor.process_directory(args.directory, args.extensions)
    elif args.files:
        processor.process_files(args.files)
    else:
        print("Please specify either --directory or --files")
        parser.print_help()
        sys.exit(1)
        
    print("Processing completed!")


if __name__ == "__main__":
    main()