class Entity:
    def __init__(self, id, content, document_file):
        self.id = id
        self.content = content
        self.document_file = document_file

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "document_file": self.document_file,
        }


class CollectionDesc:

    @staticmethod
    def make_field(field_schema):
        return {
            "name": field_schema.name,
            "type": field_schema.dtype,
            "params": field_schema.params,
        }

    @staticmethod
    def make_index(index):
        return {
            "field_name": index.field_name,
            "index_name": index.index_name,
            "params": {
                "index_type": index.params["index_type"],
                "metric_type": index.params["metric_type"],
            }
        }

    def __init__(self, collection_id, collection_name, description, num_entities, fields, indexes, status):
        self.collection_id = collection_id
        self.collection_name = collection_name
        self.description = description
        self.num_entities = num_entities
        self.fields = [CollectionDesc.make_field(x) for x in fields]
        self.indexes = [CollectionDesc.make_index(x) for x in indexes]
        self.status = status

    def to_dict(self):
        return {
            "collection_id": self.collection_id,
            "collection_name": self.collection_name,
            "description": self.description,
            "num_entities": self.num_entities,
            "fields": self.fields,
            "indexes": self.indexes,
            "status": self.status,
        }
