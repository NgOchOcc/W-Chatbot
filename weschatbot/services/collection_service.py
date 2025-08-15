from pymilvus import connections, list_collections, Collection


class CollectionService:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def connect(self):
        connections.connect(host=self.host, port=self.port)

    def all_collections(self):
        connections.connect(host=self.host, port=self.port)
        collections = list_collections()
        return collections

    def get_entities(self, collection_name, output_fields=None, limit=100):
        self.connect()
        collection = Collection(collection_name)

        collection.load()

        if output_fields is None:
            output_fields = [field.name for field in collection.schema.fields]

        results = collection.query(
            expr="id >= ''",
            output_fields=output_fields,
            limit=limit
        )

        return results
