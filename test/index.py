from weschatbot.services.document.process_documents import DocumentProcessor

# Initialize processor
processor = DocumentProcessor(
    collection_name="v768_cosine_5",
    embedding_model="Qwen/Qwen3-Embedding-0.6B",
    embedding_dim=1024,
)

# Process directory
processor.process_directory("data/phase 3/", ['.md', '.pdf', 'xls', 'xlsx'])
