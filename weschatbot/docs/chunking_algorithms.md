# Adaptive Markdown Chunking Algorithm

## Algorithm Flow

```mermaid
flowchart TD
    Start([Markdown Content]) --> Preprocess[Preprocess:<br/>Remove images if enabled]

    Preprocess --> Split[Split into Sections:<br/>Tables vs Text]

    Split --> Process{Process Each Section}

    Process -->|Table| TableChunk[Table Chunking:<br/>- Keep whole if small<br/>- Split by rows if large<br/>- Add context & summary]

    Process -->|Text| TextChunk[Text Chunking:<br/>LlamaIndex MarkdownNodeParser<br/>Respects structure]

    TableChunk --> Merge[Merge Short Chunks:<br/>Combine if too small<br/>SentenceSplitter if too large]

    TextChunk --> Merge

    Merge --> Validate[Token Validation:<br/>Ensure 256-1024 tokens<br/>- Merge if < 256<br/>- Split if > 1024]

    Validate --> Output([Chunks with<br/>256-1024 tokens])

    style Start fill:#e1f5e1
    style Output fill:#e1f5e1
    style TableChunk fill:#e3f2fd
    style TextChunk fill:#f3e5f5
    style Validate fill:#fff4e6
```

## Key Components

### 1. Preprocessing
- Normalize line endings
- Remove image references (optional)

### 2. Section Splitting
- Detect table lines: `|` with count ≥ 3
- Extract text sections between tables
- Capture context around tables (3 lines before, 2 after)

### 3. Table Chunking
- **Small tables** (≤2048 chars, ≤200 rows): Keep whole
- **Large tables**: Split by rows, preserve headers
- Add table summary and context

### 4. Text Chunking
- Use **LlamaIndex MarkdownNodeParser**
- Respects markdown structure (headers, lists, code blocks)
- Natural boundary detection

### 5. Merge & Split
- Use **LlamaIndex SentenceSplitter**
- Merge short chunks (< min_words)
- Split large chunks (> max_size)

### 6. Token Validation
- Estimate tokens: `length / 4`
- Ensure range: **256-1024 tokens**
- Merge or split as needed


## Output Guarantee

✅ All chunks between **256-1024 tokens**
✅ Tables preserved with headers
✅ Markdown structure respected
✅ Semantic boundaries maintained
