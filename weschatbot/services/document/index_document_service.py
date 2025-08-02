from typing import List
from pathlib import Path
import tempfile
import subprocess
import sys
import shutil

from llama_index.core import Document as LlamaDocument, VectorStoreIndex, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.user import Document, DocumentStatus
from weschatbot.utils.db import provide_session
from weschatbot.utils.config import config
from weschatbot.services.document.chunking_strategy import AdvancedChunkingStrategy


class DocumentConverter:
    def __init__(self, *args, **kwargs):
        pass

    def convert(self, document_path: str) -> str:
        input_path = Path(document_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        file_ext = input_path.suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return self._convert_pdf(input_path)
            else:
                return self._convert_with_markitdown(input_path)
        except Exception as e:
            raise Exception(f"Error converting file {input_path}: {str(e)}")
    
    def _convert_pdf(self, file_path: Path) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            marker_path = shutil.which("marker_single", path=str(Path(sys.executable).parent))
            if not marker_path:
                raise RuntimeError("Could not find 'marker_single' in current virtual environment.")
            
            command = [marker_path, str(file_path), "--output_dir", str(output_dir)]
            process_result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Marker creates output in a subdirectory with the same name as the file
            output_subdir = output_dir / file_path.stem
            output_md_file = output_subdir / (file_path.stem + ".md")
            
            # If not in subdirectory, check root directory
            if not output_md_file.exists():
                output_md_file = output_dir / (file_path.stem + ".md")
            
            if not output_md_file.exists():
                # Try to find any .md file
                md_files = list(output_dir.rglob("*.md"))
                if md_files:
                    output_md_file = md_files[0]
                else:
                    raise FileNotFoundError(
                        f"Marker did not produce any markdown file in: {output_dir}\n"
                        f"Marker stderr: {process_result.stderr}"
                    )
            
            with open(output_md_file, 'r', encoding='utf-8') as f:
                return f.read()
    
    def _convert_with_markitdown(self, file_path: Path) -> str:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(file_path))
        return result.text_content

class Pipeline(LoggingMixin):
    def __init__(self, collection_name: str, embedding_model_name: str = "Qwen/Qwen3-Embedding-0.6B", dim: int = 1024, *args, **kwargs):
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name
        self.dim = dim
        
        self.embed_model = HuggingFaceEmbedding(model_name=self.embedding_model_name)
        self.milvus_host = 'localhost'
        self.milvus_port = 19530
        
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
