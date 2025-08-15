from weschatbot.services.document.process_documents import DocumentProcessor

# Initialize processor
processor = DocumentProcessor(
    collection_name="doc_v2",
    embedding_model="Qwen/Qwen3-Embedding-0.6B",
    embedding_dim=1024
)

# Process directory
processor.process_directory("data/", ['.md', '.pdf', 'xls', 'xlsx'])
# processor.process_files([
#     "v2/westaco-chatbot/data/file_1.pdf"
# ])

# from pymilvus import Collection
# from pymilvus import connections

# connections.connect("default", host="localhost", port="19530")

# collection_name = "doc_v2"
# collection = Collection(name=collection_name)

# # Load vào RAM để truy vấn
# collection.load()

# # Xem schema (tên field, kiểu dữ liệu)
# print("Schema:", collection.schema)

# results = collection.query(
#     expr="",
#     output_fields=["id", "embedding"], 
#     limit=10
# )

# print("Total entities:", collection.num_entities)

curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:14b",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
