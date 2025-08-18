from pymilvus import connections, Collection, utility


def get_collection_info(collection_name: str, host="localhost", port="19530"):
    connections.connect(alias="default", host=host, port=port)
    print(f"🔌 Đã kết nối tới Milvus tại {host}:{port}")

    if not utility.has_collection(collection_name):
        print(f"❌ Collection '{collection_name}' không tồn tại.")
        return

    collection = Collection(collection_name)

    print("📌 Tên:", collection.name)
    print("📄 Mô tả:", collection.description)
    print("📊 Số lượng entities:", collection.num_entities)

    print("📐 Schema:")
    for field in collection.schema.fields:
        print(f" - {field.name}: {field.dtype}, dim={getattr(field, 'dim', 'N/A')}")

    print("🧮 Indexes:")
    if collection.indexes:
        for index in collection.indexes:
            print(f"{index}")
    else:
        print(" - Không có index nào được tạo.")


if __name__ == '__main__':
    get_collection_info("westaco_documents")
