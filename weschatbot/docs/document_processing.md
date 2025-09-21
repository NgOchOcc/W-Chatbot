# Document Processing Pipeline

## Overview
End-to-end document processing pipeline: Convert → Chunk → Index into Milvus

## Usage

### 1. Process entire directory
```bash
# Process all .md files in data directory
./weschatbot/services/document/run_pipeline.sh -d data/

# Process with DEBUG log level
./weschatbot/services/document/run_pipeline.sh -d data/ -l DEBUG
```

### 2. Process specific files
```bash
# Process specified files
./weschatbot/services/document/run_pipeline.sh -f data/document_1.md data/document_2.md
```

### 3. Use Python directly
```python
from weschatbot.services.document.process_documents import DocumentProcessor

# Initialize processor
processor = DocumentProcessor(
    collection_name="westaco_documents",
    embedding_model="Qwen/Qwen3-Embedding-0.6B",
    embedding_dim=1024
)

# Process directory
processor.process_directory("data/", ['.md', '.pdf'])

# Process specific files
processor.process_files(["data/document_1.md", "data/document_2.md"])
```

## Chunking Strategy

### 1. Table-heavy documents
- Keep tables in single chunk
- Preserve table headers when splitting is necessary

### 2. Technical reports
- Split by sections (##, ###)
- Maintain report structure

### 3. General documents
- Sentence-based splitting
- Overlap to maintain context

## Configuration

Config file: `config/document_processing.yaml`

```yaml
chunking:
  chunk_size: 1000
  chunk_overlap: 200
  min_chunk_size: 100
  max_chunk_size: 2000
```

## Testing

```bash
# Run tests with sample data
python weschatbot/services/document/test_pipeline.py
```

## Metadata

Each chunk is saved with metadata:
- `doc_type`: Document type (table_heavy, technical_report, general)
- `chunk_type`: Chunk type (table, text, report_section)
- `file_path`: Original file path
- `chunk_position`: Chunk position in document
- `prev_context`/`next_context`: Context from adjacent chunks