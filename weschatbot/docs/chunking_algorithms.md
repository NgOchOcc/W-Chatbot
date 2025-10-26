# Adaptive Markdown Chunking Algorithm

```mermaid
flowchart TD
    Start([Input: Markdown Content + Metadata]) --> Preprocess[Preprocess Content]

    Preprocess --> |Remove images if enabled| Split[Split into Sections]

    Split --> Parse{Parse Sections}

    Parse --> |Table Section| TableFlow[Table Chunking Flow]
    Parse --> |Text Section| TextFlow[Text Chunking Flow]

    subgraph TableFlow [Table Processing]
        ExtractTable[Extract Table with Context] --> CheckSize{Check Table Size}
        CheckSize --> |Small Table<br/>≤ 2048 chars<br/>≤ 200 rows| KeepWhole[Keep Whole Table]
        CheckSize --> |Large Table| SplitTable[Split by Rows]

        KeepWhole --> AddContext1[Add Context Before/After]
        SplitTable --> AddContext2[Add Header + Context]

        AddContext1 --> TableChunks[Table Chunks]
        AddContext2 --> TableChunks
    end

    subgraph TextFlow [Text Processing]
        MarkdownParser[LlamaIndex MarkdownNodeParser] --> |Respects headers,<br/>lists, code blocks| TextChunks[Text Chunks]
    end

    TableChunks --> Merge[Merge Short Chunks]
    TextChunks --> Merge

    Merge --> |If enabled| MergeLogic{Check Chunk Size}

    subgraph MergeLogic [Merge & Split Logic]
        CheckWord{Word Count<br/>< min_words?} --> |Yes| TryMerge[Merge with Next]
        CheckWord --> |No| CheckLength{Length > max_size?}

        TryMerge --> |Success| NextChunk[Process Next]
        TryMerge --> |Failed| UseSplitter[Use SentenceSplitter]

        CheckLength --> |Yes| UseSplitter
        CheckLength --> |No| KeepChunk[Keep As-Is]

        UseSplitter --> NextChunk
        KeepChunk --> NextChunk
    end

    MergeLogic --> Validate[Validate Token Limits]

    subgraph Validate [Token Validation: 256-1024 tokens]
        CountTokens[Estimate Tokens<br/>1 token ≈ 4 chars] --> CheckMin{< 256 tokens?}

        CheckMin --> |Yes| MergeSmall[Merge with Next Chunk]
        CheckMin --> |No| CheckMax{> 1024 tokens?}

        CheckMax --> |Yes| SplitLarge[Split Using<br/>SentenceSplitter]
        CheckMax --> |No| ValidChunk[✓ Valid Chunk]

        MergeSmall --> RecountMerged{Check Merged Size}
        RecountMerged --> |≤ 1024| ValidChunk
        RecountMerged --> |> 1024| SplitLarge

        SplitLarge --> |Sentence-aware<br/>splitting| ValidChunk
    end

    Validate --> AddChunkContext[Add Context to Chunks]
    AddChunkContext --> Output([Output: List of Chunks])

    style Start fill:#e1f5e1
    style Output fill:#e1f5e1
    style Validate fill:#fff4e6
    style TableFlow fill:#e3f2fd
    style TextFlow fill:#f3e5f5
    style MergeLogic fill:#fce4ec
```

## Detailed Component Descriptions

### 1. Preprocessing

```mermaid
flowchart LR
    Input[Raw Markdown] --> RemoveImages{remove_image_references?}
    RemoveImages --> |Yes| StripImages[Remove Image Patterns]
    RemoveImages --> |No| Clean[Clean Content]
    StripImages --> Clean
    Clean --> Output[Cleaned Markdown]

    subgraph Image Patterns
        P1["![alt](img.jpg)"]
        P2["&lt;img src='...'&gt;"]
        P3["http://.../img.png"]
    end
```

**Patterns Removed:**
- `![alt](image.jpg)` - Markdown images
- `<img src="...">` - HTML images
- `http://.../image.png` - Direct image URLs

### 2. Section Splitting

```mermaid
flowchart TD
    Start[Markdown Content] --> ParseLine{Parse Line by Line}

    ParseLine --> CheckTable{Is Table Line?<br/>Contains | and count ≥ 3}

    CheckTable --> |Yes| ExtractTable[Extract Complete Table]
    CheckTable --> |No| ExtractText[Extract Text Section]

    ExtractTable --> GetContextBefore[Get Context Before<br/>3 lines]
    GetContextBefore --> CollectRows[Collect All Table Rows]
    CollectRows --> DetectHeader{Detect Header?<br/>Next line is separator}
    DetectHeader --> GetContextAfter[Get Context After<br/>2 lines]
    GetContextAfter --> TableSection[Table Section]

    ExtractText --> TextSection[Text Section]

    TableSection --> Continue{More Lines?}
    TextSection --> Continue
    Continue --> |Yes| ParseLine
    Continue --> |No| Sections[List of Sections]

    style TableSection fill:#e3f2fd
    style TextSection fill:#f3e5f5
```

### 3. Table Chunking Strategy

```mermaid
flowchart TD
    TableSection[Table Section Input] --> ExtractHeaderData[Extract Header & Data]

    ExtractHeaderData --> CheckHeader{Has Separator Line?}
    CheckHeader --> |Yes| SeparateHeader[Header = First 2 lines<br/>Data = Rest]
    CheckHeader --> |No| NoHeader[No Header<br/>All = Data]

    SeparateHeader --> EvaluateSize{Evaluate Size}
    NoHeader --> EvaluateSize

    EvaluateSize --> CheckConditions{Size ≤ 2048 chars<br/>AND<br/>Rows ≤ 200?}

    CheckConditions --> |Yes| BuildWhole[Build Single Chunk]
    CheckConditions --> |No| CalculateRows[Calculate Rows per Chunk]

    subgraph BuildWhole [Keep Whole Table]
        AddSummary1[Add Table Summary<br/>e.g., Table: 50 rows, columns: A, B, C]
        AddSummary1 --> AddCtxBefore1[Add Context Before]
        AddCtxBefore1 --> AddTable1[Add Complete Table]
        AddTable1 --> AddCtxAfter1[Add Context After]
    end

    subgraph CalculateRows [Split Large Table]
        CalcAvgRow[Calculate Average Row Size]
        CalcAvgRow --> CalcPerChunk[Rows per Chunk =<br/>max(calculated, min_rows)]
        CalcPerChunk --> SplitLoop[Split Data by Rows]

        SplitLoop --> FirstChunk{First Chunk?}
        FirstChunk --> |Yes| AddSummary2[Add Summary + Context]
        FirstChunk --> |No| NoSummary[No Summary]

        AddSummary2 --> AddHeader[Add Header if preserve_header]
        NoSummary --> AddHeader
        AddHeader --> AddRows[Add Row Chunk]

        AddRows --> LastChunk{Last Chunk?}
        LastChunk --> |Yes| AddCtxAfter2[Add Context After]
        LastChunk --> |No| NextChunk[Next Chunk]

        AddCtxAfter2 --> NextChunk
        NextChunk --> MoreRows{More Rows?}
        MoreRows --> |Yes| SplitLoop
    end

    BuildWhole --> OutputChunks[Table Chunks]
    CalculateRows --> OutputChunks

    style BuildWhole fill:#c8e6c9
    style CalculateRows fill:#ffccbc
```

### 4. Text Chunking with LlamaIndex

```mermaid
flowchart LR
    TextSection[Text Section] --> CreateDoc[Create LlamaDocument]
    CreateDoc --> MarkdownParser[LlamaIndex<br/>MarkdownNodeParser]

    MarkdownParser --> Analyze{Analyze Structure}

    Analyze --> Headers[Detect Headers<br/># ## ###]
    Analyze --> Lists[Detect Lists<br/>- * 1.]
    Analyze --> CodeBlocks[Detect Code Blocks<br/>``` ```]
    Analyze --> Paragraphs[Detect Paragraphs<br/>\\n\\n]

    Headers --> Split[Smart Split at<br/>Natural Boundaries]
    Lists --> Split
    CodeBlocks --> Split
    Paragraphs --> Split

    Split --> Nodes[Text Nodes]
    Nodes --> ConvertChunks[Convert to Chunks]
    ConvertChunks --> TextChunks[Text Chunks]

    style MarkdownParser fill:#90caf9
```

### 5. Merge & Split Logic

```mermaid
flowchart TD
    InputChunks[Input Chunks] --> StartLoop[Process Each Chunk]

    StartLoop --> CountWords[Count Words]
    CountWords --> CheckMin{Words < min_words_per_chunk?}

    CheckMin --> |Yes| HasNext{Has Next Chunk?}
    CheckMin --> |No| CheckMax{Length > max_chunk_size?}

    HasNext --> |Yes| TryCombine[Combine with Next]
    HasNext --> |No| Keep1[Keep As-Is]

    TryCombine --> CheckCombined{Combined Size ≤ max?}
    CheckCombined --> |Yes| MergeSuccess[✓ Merged Chunk]
    CheckCombined --> |No| UseSplitter[Use SentenceSplitter]

    CheckMax --> |Yes| UseSplitter
    CheckMax --> |No| Keep2[Keep As-Is]

    UseSplitter --> SmartSplit[Split at Sentence<br/>Boundaries]
    SmartSplit --> SplitChunks[Multiple Chunks]

    MergeSuccess --> NextChunk[Process Next]
    Keep1 --> NextChunk
    Keep2 --> NextChunk
    SplitChunks --> NextChunk

    NextChunk --> MoreChunks{More Chunks?}
    MoreChunks --> |Yes| StartLoop
    MoreChunks --> |No| OutputMerged[Merged Chunks]

    style MergeSuccess fill:#c8e6c9
    style UseSplitter fill:#ffccbc
```

### 6. Token Validation (256-1024 tokens)

```mermaid
flowchart TD
    InputChunks[Input Chunks] --> ForEach[For Each Chunk]

    ForEach --> EstimateTokens[Estimate Tokens<br/>tokens = length / 4]

    EstimateTokens --> CheckMin{tokens < 256?}

    CheckMin --> |Yes| HasNext{Has Next Chunk?}
    CheckMin --> |No| CheckMax{tokens > 1024?}

    HasNext --> |Yes| MergeNext[Merge with Next]
    HasNext --> |No| TooSmall[Too Small<br/>Keep anyway]

    MergeNext --> CheckMerged{Merged ≤ 1024?}
    CheckMerged --> |Yes| ValidMerge[✓ Valid Merged]
    CheckMerged --> |No| SplitMerged[Split Merged Content]

    CheckMax --> |Yes| SplitLarge[Split Using SentenceSplitter]
    CheckMax --> |No| ValidSize[✓ Valid Size: 256-1024]

    subgraph SplitLarge [Split Large Chunk]
        UseSplitter[Use SentenceSplitter]
        UseSplitter --> CheckNodes{Each Node ≤ 1024?}
        CheckNodes --> |Yes| NodeOK[✓ Nodes Valid]
        CheckNodes --> |No| ForceSplit[Force Split by Sentences]

        ForceSplit --> AccumSentences[Accumulate Sentences<br/>until ≤ 1024 tokens]
        AccumSentences --> NodeOK
    end

    ValidMerge --> NextIter[Next Iteration]
    SplitMerged --> NextIter
    TooSmall --> NextIter
    ValidSize --> NextIter
    NodeOK --> NextIter

    NextIter --> MoreChunks{More Chunks?}
    MoreChunks --> |Yes| ForEach
    MoreChunks --> |No| ValidatedChunks[✓ All Chunks: 256-1024 tokens]

    style ValidMerge fill:#c8e6c9
    style ValidSize fill:#c8e6c9
    style NodeOK fill:#c8e6c9
    style TooSmall fill:#fff9c4
```

## Token Estimation

```mermaid
graph LR
    Text[Input Text] --> CountChars[Count Characters]
    CountChars --> Divide[Divide by 4]
    Divide --> Tokens[Estimated Tokens]

    Info[ℹApproximation:<br/>1 token ≈ 4 characters<br/>1 token ≈ 0.75 words]

    style Info fill:#e1f5fe
```

## Configuration Parameters

```mermaid
mindmap
  root((Adaptive<br/>Markdown<br/>Strategy))
    Token Limits
      min_tokens: 256
      max_tokens: 1024
    Chunk Sizes
      chunk_size: 2048
      chunk_overlap: 128
      min_chunk_size: 128
      max_chunk_size: 3192
    Table Settings
      table_max_chunk_size: 2048
      table_min_rows_per_chunk: 30
      table_max_rows_threshold: 200
      preserve_table_headers: True
      add_table_summary: True
    Context Settings
      table_context_lines_before: 3
      table_context_lines_after: 2
    Merge Settings
      min_words_per_chunk: 30
      merge_short_chunks: True
    Preprocessing
      remove_image_references: True
```
