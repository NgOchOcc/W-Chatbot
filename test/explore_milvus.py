
def main():
    from pymilvus import Collection
    from pymilvus import connections

    connections.connect(
        host="localhost",
        port="19530"
    )

    collection = Collection("doc_v2")
    print(collection.schema)

    entities = collection.query(
        expr="row_id > 0",
        output_fields=["row_id", "doc_id", "text_chunk"],
    )

    for entity in entities:
        print(entity)


if __name__ == '__main__':
    main()
