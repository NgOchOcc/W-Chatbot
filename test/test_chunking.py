from pymilvus import Collection
from pymilvus import connections

connections.connect("default", host="localhost", port="19530")

collection_name = "v768_cosine_5"
collection = Collection(name=collection_name)

# Load vào RAM để truy vấn
collection.load()

# Xem schema (tên field, kiểu dữ liệu)
print("Schema:", collection.schema)

print("Total entities:", collection.num_entities)


# Xem các index đã tạo
indexes = collection.indexes
for index in indexes:
    print("Index info:")
    print("- Field:", index.field_name)
    print("- Index type:", index.params.get("index_type"))
    print("- Metric type:", index.params.get("metric_type"))
