# Markdown Indexing & Querying with Milvus + LlamaIndex

## 1. Environment Setup

- Requires Python 3.8+ and pip
- Install dependencies:
  ```bash
  pip install llama-index llama-index-vector-stores-milvus llama-index-embeddings-huggingface pymilvus
  pip install torch sentence-transformers
  ```
- Ensure Milvus is running at `localhost:19530` (see `milvus/docker-compose.yml`)

## 2. Prepare Data

- Create `data/` at project root
- Place `.md` files you want to index into this folder

## 3. Index Markdown Files

Run:
```bash
python -m weschatbot.knowledge.index_markdown
```

This script:
- Reads `.md` files in `data/`
- Splits content into chunks
- Embeds with HuggingFace (`all-mpnet-base-v2`)
- Stores vectors and texts into Milvus (`enterprise_kb`)

> To change model (e.g. Qwen3), update `model_name` and `dim`

## 4. Query Markdown Content

Run:
```bash
python -m weschatbot.knowledge.retrieve_markdown
```

This script:
- Connects to Milvus
- Accepts input question
- Returns top-k relevant text chunks

> Use same model and `dim` as indexing

## 5. Common Issues

- **Connection error**: Ensure Milvus is running
- **Dimension mismatch**:
  - Qwen3: `dim=1024`
  - mpnet: `dim=768`
- **NumPy error**: Downgrade with:
  ```bash
  pip install "numpy<2"
  ```

## 6. Config

- Adjust host, port, collection in the scripts
- Or use config from `weschatbot/utils/config.py`

---

### Summary

- Put `.md` files in `data/`
- Run `index_markdown` to index
- Run `retrieve_markdown` to query
- Check logs if errors occur