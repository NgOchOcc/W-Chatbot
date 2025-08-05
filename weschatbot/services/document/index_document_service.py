from typing import List, Optional
from pathlib import Path

from llama_index.core import Document as LlamaDocument, VectorStoreIndex, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

from markitdown import MarkItDown

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.user import Document, DocumentStatus
from weschatbot.utils.db import provide_session
from weschatbot.utils.config import config
from weschatbot.services.document.chunking_strategy import AdvancedChunkingStrategy


class MarkerConverter:
    def __init__(self):
        self.converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )
    
    def convert(self, document_path: str) -> str:
        rendered = self.converter(str(document_path))

        markdown_text, metadata, images = text_from_rendered(rendered)        
        return markdown_text


class MarkitdownConverter:
    def __init__(self):
        self.converter = MarkItDown()
    
    def convert(self, document_path: str) -> str:
        rendered = self.converter.convert((document_path))
        return rendered.text_content
               

class DocumentConverter:
    def __init__(self, *args, **kwargs):
        self.marker_convert = MarkerConverter()
        self.markitdown_convert = MarkitdownConverter()

    def convert(self, document_path: str) -> str:
        input_path = Path(document_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        file_ext = input_path.suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return self.marker_convert.convert(input_path)
            else:
                return self.markitdown_convert.convert(input_path)
        except Exception as e:
            raise Exception(f"Error converting file {input_path}: {str(e)}")
        


class Pipeline:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, documents: List[str], metadata_list: List[dict] = None):
        pass
    
class PipelineMilvusStore(Pipeline, LoggingMixin):
    def __init__(
            self, collection_name: str, 
            dim: int = 1024, 
            embedding_model_name: str = "Qwen/Qwen3-Embedding-0.6B", 
            milvus_host: Optional[str] = None, 
            milvus_port: Optional[int] = None, 
            *args, **kwargs
        ):
        super().__init__(*args, **kwargs)
        self.dim = dim
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name
        self.embed_model = HuggingFaceEmbedding(model_name=self.embedding_model_name)
        
        self.milvus_host = milvus_host if milvus_host is not None else 'localhost'
        self.milvus_port = milvus_port if milvus_port is not None else 19530
        
        self.vector_store = MilvusVectorStore(
            uri=f"http://{self.milvus_host}:{self.milvus_port}",
            collection_name=self.collection_name,
            dim=self.dim,
            overwrite=False  
        )
        
        self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
        self.chunking_strategy = AdvancedChunkingStrategy()

    def run(self, documents: List[str], metadata_list: List[dict] = None):
        if not documents:
            self.log.warning("No documents provided to index")
            return
        
        try:
            all_chunks = []
            for i, content in enumerate(documents):
                if content:
                    if metadata_list and i < len(metadata_list):
                        metadata = metadata_list[i]
                    else:
                        metadata = {"doc_id": f"doc_{i}"}
                    
                    chunks = self.chunking_strategy.chunk_markdown(content, metadata)                    
                    chunks = self.chunking_strategy.add_context_to_chunks(chunks)
                    all_chunks.extend(chunks)
            
            if not all_chunks:
                self.log.warning("No valid chunks to index after processing")
                return
            
            self.log.info(f"Indexing {len(all_chunks)} chunks from {len(documents)} documents into collection '{self.collection_name}'")            
            index = VectorStoreIndex.from_documents(
                all_chunks,
                storage_context=self.storage_context,
                embed_model=self.embed_model,
                show_progress=True
            )
            
            self.log.info(f"Successfully indexed {len(all_chunks)} chunks")
            
        except Exception as e:
            self.log.error(f"Error indexing documents: {str(e)}")
            raise


class IndexDocumentService(LoggingMixin):
    def __init__(self, converter, pipeline, collection_name, *args, **kwargs):
        self.converter = converter
        self.pipeline = pipeline
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
        self.log.info("Start indexing documents...")
        self.mark_in_progress(session)
        doc_entities = self.get_documents(session)
        while doc_entities:
            converted_docs = []
            metadata_list = []
            
            for doc in doc_entities:
                # Convert document
                converted_content = self.converter.convert(doc.path)
                converted_docs.append(converted_content)
                
                # Prepare metadata
                metadata = {
                    "doc_id": doc.id,
                    "file_path": doc.path,
                    "file_name": Path(doc.path).name,
                    "created_at": str(doc.created_at) if hasattr(doc, 'created_at') else None,
                }
                metadata_list.append(metadata)
            
            # Run pipeline with documents and metadata
            self.pipeline.run(converted_docs, metadata_list)
            self.mark_done(doc_entities, session)
            doc_entities = self.get_documents(session)
        self.log.info("Finish indexing documents...")

    @provide_session
    def get_documents(self, session=None):
        documents = session.query(Document).filter(Document.status.name == "in progress").limit(10).all()
        if documents:
            return documents
        return None
