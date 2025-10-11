from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pymilvus import MilvusClient, DataType, FieldSchema, CollectionSchema
from sqlalchemy.orm import joinedload

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.collection import Document, CollectionDocumentStatus, CollectionDocument
from weschatbot.services.document.chunking_strategy import AdvancedChunkingStrategy
from weschatbot.services.vllm_embedding_service import VLLMEmbeddingService
from weschatbot.utils.db import provide_session


class Pipeline:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, documents: List[str], metadata_list: List[dict] = None):
        pass


class PipelineMilvusStore(Pipeline, LoggingMixin):
    def __init__(
            self, collection_name: str,
            dim: int = 1024,
            vllm_base_url: str = "http://westaco-chatbot-vllm-embed:9290",
            vllm_model: str = "Qwen/Qwen3-Embedding-0.6B",
            milvus_host: Optional[str] = None,
            milvus_port: Optional[int] = None,
            metrics: str = "COSINE",
            *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.dim = dim
        self.collection_name = collection_name
        self.vllm_base_url = vllm_base_url
        self.vllm_model = vllm_model

        # Initialize VLLM embedding service
        self.vllm_service = VLLMEmbeddingService(
            base_url=self.vllm_base_url,
            model=self.vllm_model
        )

        self.milvus_host = milvus_host if milvus_host is not None else 'localhost'
        self.milvus_port = milvus_port if milvus_port is not None else 19530
        self.metrics = metrics

        try:
            print(f"Similarity: {self.metrics}")
            # Initialize Milvus client
            self.milvus_client = MilvusClient(
                uri=f"http://{self.milvus_host}:{self.milvus_port}"
            )

            # Create collection if it doesn't exist
            self._create_collection_if_not_exists()

            self.log.info(f"Connected to Milvus collection '{self.collection_name}' with dimension {self.dim}")
        except Exception as e:
            self.log.error(f"Error creating Milvus connection: {str(e)}")
            raise

        self.chunking_strategy = AdvancedChunkingStrategy()

    def _create_collection_if_not_exists(self):
        """Create Milvus collection with proper schema if it doesn't exist"""
        try:
            # Check if collection exists
            if self.milvus_client.has_collection(self.collection_name):
                self.log.info(f"Collection '{self.collection_name}' already exists")
                return

            # Define schema fields
            fields = [
                FieldSchema(name="row_id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="document_id", dtype=DataType.INT64, nullable=True),
                FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=128),
                FieldSchema(name="document_name", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="modified_date", dtype=DataType.VARCHAR, max_length=128, nullable=True),
                FieldSchema(name="text_chunk", dtype=DataType.VARCHAR, max_length=65535, nullable=True),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
                FieldSchema(name="chunk_index", dtype=DataType.INT64, nullable=True),
                FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=128, nullable=True),
            ]

            # Create schema
            schema = CollectionSchema(
                fields=fields,
                description=f"Collection for {self.collection_name}",
                enable_dynamic_field=False
            )

            # Create index parameters
            index_params = self.milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="embedding",
                index_type="AUTOINDEX",
                metric_type=self.metrics
            )

            # Create collection
            self.milvus_client.create_collection(
                collection_name=self.collection_name,
                schema=schema,
                index_params=index_params
            )

            self.log.info(f"Created collection '{self.collection_name}' with schema")
        except Exception as e:
            self.log.error(f"Error creating collection: {str(e)}")
            raise

    def run(self, documents: List[str], metadata_list: List[dict] = None):
        if not documents:
            self.log.warning("No documents provided to index")
            return

        try:
            all_chunks = []
            for i, content in enumerate(documents):
                if content:
                    # Get metadata from metadata_list if provided, otherwise use defaults
                    if metadata_list and i < len(metadata_list):
                        source_metadata = metadata_list[i]
                    else:
                        source_metadata = {"doc_id": f"doc_{i}"}

                    metadata = {
                        'document_id': int(source_metadata.get('doc_id', 0)) if source_metadata.get('doc_id') else None,
                        'doc_id': str(source_metadata.get('doc_id', f'doc_{i}')),
                        'document_name': source_metadata.get('file_name', source_metadata.get('document_name', f'document_{i}')),
                        'file_path': source_metadata.get('file_path', ''),
                        'modified_date': source_metadata.get('modified_date', datetime.now().isoformat()),
                        'created_at': source_metadata.get('created_at', datetime.now().isoformat())
                    }

                    chunks = self.chunking_strategy.chunk_markdown(content, metadata)
                    chunks = self.chunking_strategy.add_context_to_chunks(chunks)

                    all_chunks.extend(chunks)

            if not all_chunks:
                self.log.warning("No valid chunks to index after processing")
                return

            self.log.info(
                f"Indexing {len(all_chunks)} chunks from {len(documents)} documents into collection '{self.collection_name}'")

            # Generate embeddings and prepare entities for Milvus
            entities = []
            batch_size = 100

            for i in range(0, len(all_chunks), batch_size):
                batch_chunks = all_chunks[i:i + batch_size]

                for chunk_index, chunk in enumerate(batch_chunks):
                    text_chunk = chunk.get('text_chunk', '')
                    chunk_metadata = chunk.get('metadata', {})

                    # Generate embedding
                    embedding = self.vllm_service.get_embedding_sync(text_chunk)

                    # Create entity matching Milvus schema
                    entity = {
                        'document_id': chunk_metadata.get('document_id'),
                        'doc_id': str(chunk_metadata.get('doc_id', '')),
                        'document_name': chunk_metadata.get('document_name', ''),
                        'modified_date': chunk_metadata.get('modified_date', ''),
                        'text_chunk': text_chunk,
                        'embedding': embedding,
                        'chunk_index': i + chunk_index,
                        'file_path': chunk_metadata.get('file_path', ''),
                        'created_at': chunk_metadata.get('created_at', '')
                    }

                    entities.append(entity)

                self.log.info(f"Processed {min(i + batch_size, len(all_chunks))}/{len(all_chunks)} chunks")

            # Insert into Milvus
            if entities:
                self.milvus_client.insert(
                    collection_name=self.collection_name,
                    data=entities
                )
                self.log.info(f"Successfully indexed {len(entities)} chunks into Milvus")
            else:
                self.log.warning("No entities to insert")

        except Exception as e:
            self.log.error(f"Error indexing documents: {str(e)}")
            raise


class IndexDocumentService(LoggingMixin):
    def __init__(self, converter, pipeline, collection_name, collection_id, *args, **kwargs):
        self.converter = converter
        self.pipeline = pipeline
        self.collection_name = collection_name
        self.collection_id = collection_id

    @provide_session
    def get_pending_documents_by_collection(self, collection_id: int, session=None):
        links = (
            session.query(CollectionDocument)
            .options(joinedload(CollectionDocument.document), joinedload(CollectionDocument.status))
            .filter(CollectionDocument.collection_id == collection_id)
            .join(CollectionDocumentStatus)
            .filter(CollectionDocumentStatus.name == "new")
            .all()
        )
        return [link.document.to_dict(session=session) for link in links]

    @provide_session
    def mark_in_progress(self, session=None):
        in_progress_status = session.query(CollectionDocumentStatus).filter(
            CollectionDocumentStatus.name == "in progress"
        ).one_or_none()

        if in_progress_status is None:
            raise ValueError("'in progress' status not found. Please upgrade the db by command 'alembic upgrade head'.")

        links = (
            session.query(CollectionDocument)
            .join(CollectionDocumentStatus)
            .filter(CollectionDocument.collection_id == self.collection_id)
            .filter(CollectionDocumentStatus.name == "new")
            .all()
        )

        for link in links:
            link.status = in_progress_status

        session.commit()

    @provide_session
    def mark_done(self, documents, session=None):
        done_status = session.query(CollectionDocumentStatus).filter(
            CollectionDocumentStatus.name == "done"
        ).one_or_none()

        if done_status is None:
            raise ValueError("'done' status not found. Please upgrade the db by command 'alembic upgrade head'.")

        document_ids = [doc.id for doc in documents]

        links = (
            session.query(CollectionDocument)
            .filter(CollectionDocument.collection_id == self.collection_id)
            .filter(CollectionDocument.document_id.in_(document_ids))
            .all()
        )

        for link in links:
            link.status = done_status

        session.commit()

    def convert(self, doc):
        return self.converter.convert(doc.path)

    @provide_session
    def index(self, session=None):
        self.log.info("Start indexing documents...")
        self.mark_in_progress(session)
        doc_entities = self.get_documents(session)
        while doc_entities:
            converted_docs = []
            metadata_list = []

            for doc in doc_entities:
                converted_content = self.convert(doc)
                converted_docs.append(converted_content)

                file_path = Path(doc.path)
                metadata = {
                    "doc_id": str(doc.id),
                    "file_path": doc.path,
                    "file_name": file_path.name,
                    "document_name": file_path.name,
                    "created_at": str(doc.created_at) if hasattr(doc, 'created_at') else "",
                    "modified_date": datetime.fromtimestamp(
                        file_path.stat().st_mtime).isoformat() if file_path.exists() else datetime.now().isoformat(),
                }
                metadata_list.append(metadata)

            self.pipeline.run(converted_docs, metadata_list)
            self.mark_done(doc_entities, session)
            doc_entities = self.get_documents(session)
        self.log.info("Finish indexing documents...")

    @provide_session
    def get_documents(self, session=None):
        documents = (
            session.query(Document)
            .join(CollectionDocument, CollectionDocument.document_id == Document.id)
            .join(CollectionDocumentStatus, CollectionDocument.status_id == CollectionDocumentStatus.id)
            .filter(CollectionDocument.collection_id == self.collection_id)
            .filter(CollectionDocumentStatus.name == "in progress")
            .options(joinedload(Document.status))
            .limit(10)
            .all()
        )

        return documents if documents else None


class IndexDocumentWithoutConverterService(IndexDocumentService):
    def __init__(self, pipeline, collection_name, collection_id, converter=None, *args, **kwargs):
        super().__init__(converter, pipeline, collection_name, collection_id, *args, **kwargs)
        self.pipeline = pipeline
        self.collection_name = collection_name
        self.collection_id = collection_id

    @staticmethod
    def read_converted_file(converted_path):
        with open(converted_path, "r") as f:
            res = f.read()
        return res

    def convert(self, doc):
        return self.read_converted_file(doc.converted_path)



