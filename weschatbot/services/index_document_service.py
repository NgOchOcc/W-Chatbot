from functools import reduce

from weschatbot.models.user import Document, DocumentStatus
from weschatbot.utils.db import provide_session


class Embedding:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, documents):
        pass

    def index(self, documents, collection_name):
        pass


class Chunking:
    def __init__(self, *args, **kwargs):
        pass

    def chunk(self, document):
        pass


class DocumentConverter:
    def __init__(self, *args, **kwargs):
        pass

    def convert(self, document_path):
        return ""


class IndexDocumentService:
    def __init__(self, converter, chunking, embedding, collection_name, *args, **kwargs):
        self.converter = converter
        self.chunking = chunking
        self.embedding = embedding
        self.collection_name = collection_name

    @provide_session
    def mark_in_progress(self, session=None):
        documents = session.query(Document).filter(Document.is_used == True).all()
        in_progress_status = session.query(DocumentStatus).filter(DocumentStatus.name == "in progress").one_or_none()
        if in_progress_status is None:
            raise ValueError("'in progress' status not found. Please upgrade the db by command 'alembic upgrade head'.")
        for document in documents:
            document.status = in_progress_status

    @provide_session
    def mark_done(self, documents, session=None):
        done_status = session.query(DocumentStatus).filter(DocumentStatus.name == "done").one_or_none()
        for document in documents:
            document.status = done_status

    @provide_session
    def index(self, session=None):
        self.mark_in_progress(session)
        doc_entities = self.get_documents(session)
        while doc_entities:
            converted_docs = [self.converter.convert(doc.path) for doc in doc_entities]
            chunked_docs = reduce(lambda r, x: r + self.chunking.chunk(x), converted_docs, [])
            self.embedding.index(chunked_docs)
            self.mark_done(doc_entities, session)
            doc_entities = self.get_documents(session)

    @provide_session
    def get_documents(self, session=None):
        documents = session.query(Document).filter(Document.status.name == "in progress").limit(10).all()
        if documents:
            return documents
        return None
