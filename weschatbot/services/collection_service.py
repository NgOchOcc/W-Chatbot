import base64

from pymilvus import connections, FieldSchema, CollectionSchema, DataType, utility, Collection
from pymilvus import list_collections
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from weschatbot.exceptions.collection_exception import CollectionNotFoundException, ExistingCollectionDocumentException, \
    StatusNotFound
from weschatbot.models.collection import Collection as WCollection, Document, CollectionDocument, \
    CollectionDocumentStatus, DocumentStatus
from weschatbot.schemas.collection import CollectionDesc, MilvusNotFoundCollectionDesc
from weschatbot.services.celery_service import index_collection_to_milvus
from weschatbot.utils.db import provide_session


class Base64URL:
    @staticmethod
    def decode(data):
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        return base64.urlsafe_b64decode(data).decode('utf-8')

    @staticmethod
    def encode(data):
        return base64.urlsafe_b64encode(data.encode()).decode().rstrip("=")


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

    def get_entities_by_token(self, token, output_fields=None, **kwargs):
        decoded = Base64URL.decode(token)
        min_row_id, limit, *collection_names = decoded.split(':')
        collection_name = ":".join(collection_names)

        self.connect()
        collection = Collection(collection_name)
        collection.load()

        if output_fields is None:
            output_fields = [field.name for field in collection.schema.fields]

        results = collection.query(limit=int(limit), expr=f"row_id > {min_row_id}", output_fields=output_fields)
        max_row_id = results[-1]["row_id"]
        if len(results) < int(limit):
            return results, None
        next_token = f"{max_row_id}:{limit}:{collection_name}"
        return results, Base64URL.encode(next_token)

    def get_entity_by_row_id(self, collection_name, row_id, output_fields=None, **kwargs):
        self.connect()
        collection = Collection(collection_name)
        collection.load()

        if output_fields is None:
            output_fields = [field.name for field in collection.schema.fields]

        result = collection.query(
            expr=f"row_id == {row_id}",
            out_fields=output_fields
        )
        return result, None

    def get_entities(self, collection_name, output_fields=None, limit=20, **kwargs):
        self.connect()
        collection = Collection(collection_name)

        collection.load()

        if output_fields is None:
            output_fields = [field.name for field in collection.schema.fields]

        results = collection.query(
            expr=f"row_id >= 0",
            output_fields=output_fields,
            limit=limit
        )

        max_row_id = results[-1]["row_id"]
        if len(results) < limit:
            return results, None
        next_token = f"{max_row_id}:{limit}:{collection_name}"
        return results, Base64URL.encode(next_token)

    @provide_session
    def get_collection(self, collection_id, session=None):
        collection = session.query(WCollection).filter(WCollection.id == collection_id).one_or_none()
        if collection:
            self.connect()
            collection_name = collection.name
            if not utility.has_collection(collection_name):
                # raise CollectionNotFoundException(f"Collection {collection_name} is not found")
                return MilvusNotFoundCollectionDesc(collection_id, collection_name)
            res = Collection(collection_name)
            return CollectionDesc(collection_id=collection_id, collection_name=collection_name,
                                  description=res.description,
                                  num_entities=res.num_entities, fields=res.schema.fields, indexes=res.indexes,
                                  status=collection.status.name)

        raise CollectionNotFoundException(f"Collection {collection_id} is not found in DB")

    def delete_milvus_collection(self, collection_name):
        self.connect()
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
            return True
        else:
            raise CollectionNotFoundException(f"Collection {collection_name} is not found")

    @provide_session
    def delete_collection(self, collection_id, session=None):
        collection = session.get(WCollection, collection_id)
        if collection:
            collection_name = collection.name
            self.connect()
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
            try:
                session.query(CollectionDocument) \
                    .filter_by(collection_id=collection_id) \
                    .delete(synchronize_session=False)
                session.delete(collection)
                return True
            except SQLAlchemyError:
                session.rollback()
                raise

    @staticmethod
    def create_collection(
            collection_name: str,
            dim: int = 1024,
            milvus_host: str = 'localhost',
            milvus_port: int = 19530,
            overwrite: bool = False
    ):
        connections.connect(
            alias="default",
            host=milvus_host,
            port=milvus_port
        )

        if utility.has_collection(collection_name):
            if overwrite:
                utility.drop_collection(collection_name)
                print(f"Dropped existing collection '{collection_name}'")
            else:
                print(f"Collection '{collection_name}' already exists, will refer to this collection.")
                return True

        fields = [
            FieldSchema(name="row_id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="document_id", dtype=DataType.INT64, nullable=True),
            FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="document_name", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="modified_date", dtype=DataType.VARCHAR, max_length=128, nullable=True),
            FieldSchema(name="text_chunk", dtype=DataType.VARCHAR, max_length=65535, nullable=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="chunk_index", dtype=DataType.INT64, nullable=True),
            FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
            FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=128, nullable=True),
        ]

        schema = CollectionSchema(
            fields=fields,
            description=f"Document collection with chunked text and embeddings"
        )

        schema.enable_dynamic_field = True

        collection = Collection(
            name=collection_name,
            schema=schema,
        )

        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index(
            field_name="embedding",
            index_params=index_params
        )

        print(f"Successfully created collection '{collection_name}' with custom schema (dim={dim})")
        return True

    @provide_session
    def all_documents(self, session=None):
        res = session.query(Document).all()
        return [x.to_dict(session) for x in res]

    @provide_session
    def converted_documents(self, session=None):
        res = session.query(Document).join(DocumentStatus).filter(DocumentStatus.name == "done").all()
        return [x.to_dict(session) for x in res]

    @provide_session
    def add_document_to_collection(self, collection_id: int, document_id: int, session=None) -> bool:
        collection = session.query(WCollection).filter(WCollection.id == collection_id).one_or_none()
        document = session.query(Document).filter(Document.id == document_id).one_or_none()

        if not collection or not document:
            raise CollectionNotFoundException(f"Collection {collection_id} is not found")

        existing_link = session.query(CollectionDocument).filter_by(
            collection_id=collection_id,
            document_id=document_id
        ).first()

        if existing_link:
            raise ExistingCollectionDocumentException("Document is already in collection")

        status = session.query(CollectionDocumentStatus).filter_by(name="new").first()
        if not status:
            raise StatusNotFound(f"Status new is not found")

        new_link = CollectionDocument(
            collection_id=collection_id,
            document_id=document_id,
            status_id=status.id
        )
        session.add(new_link)

        document.is_used = True

        return True

    @provide_session
    def get_collection_status(self, collection_id, session=None):
        collection = session.query(WCollection).filter(WCollection.id == collection_id).first()
        if collection and collection.status:
            return collection.status.name
        return None

    @provide_session
    def get_documents_by_collection_id(self, collection_id: int, session=None):
        links = (
            session.query(CollectionDocument)
            .join(Document)
            .join(CollectionDocumentStatus)
            .filter(CollectionDocument.collection_id == collection_id)
            .options(
                joinedload(CollectionDocument.document),
                joinedload(CollectionDocument.status)
            )
            .all()
        )
        return [
            {
                **link.document.to_dict(session=session),
                "status": link.status.name
            }
            for link in links
        ]

    @provide_session
    def remove_document_from_collection(self, collection_id: int, document_id: int, session=None):
        link = session.query(CollectionDocument).filter_by(
            collection_id=collection_id,
            document_id=document_id
        ).first()

        if not link:
            raise ExistingCollectionDocumentException("Document is not in collection")

        session.delete(link)

        remaining_links = session.query(CollectionDocument).filter_by(document_id=document_id).count()
        if remaining_links == 0:
            doc = session.get(Document, document_id)
            if doc:
                doc.is_used = False

    @provide_session
    def index_collection(self, collection_id: int, session=None):
        collection = session.query(WCollection).filter(WCollection.id == collection_id).one_or_none()
        if collection:
            collection_name = collection.name
            index_collection_to_milvus.delay(collection_id, collection_name)

    @provide_session
    def flush(self, collection_id, session=None):
        collection = session.get(WCollection, collection_id)
        if collection:
            collection_name = collection.name
            self.connect()
            if utility.has_collection(collection_name):
                collection = Collection(collection_name)
                collection.flush()
            else:
                raise CollectionNotFoundException(f"Collection {collection_name} is not found")
        else:
            raise CollectionNotFoundException(f"Collection {collection_id} is not found")

    @provide_session
    def delete_entities(self, collection_id, row_id, session=None):
        collection = session.get(WCollection, collection_id)
        if collection:
            self.connect()
            collection_name = collection.name
            milvus_collection = Collection(collection_name)
            milvus_collection.delete(expr=f"row_id == {row_id}")
            milvus_collection.flush()
        else:
            raise CollectionNotFoundException(f"Collection {collection_id} is not found")