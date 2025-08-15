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
