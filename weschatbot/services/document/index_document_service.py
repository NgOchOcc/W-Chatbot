from typing import List, Optional
from pathlib import Path
from datetime import datetime


from llama_index.core import Document as LlamaDocument, VectorStoreIndex, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.milvus import MilvusVectorStore
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility


from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


from markitdown import MarkItDown
from sqlalchemy.orm import joinedload


from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.user import Document, DocumentStatus
from weschatbot.utils.db import provide_session
from weschatbot.utils.config import config
from weschatbot.services.document.chunking_strategy import AdvancedChunkingStrategy




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
           print(f"Collection '{collection_name}' already exists")
           return False
  
   fields = [
       FieldSchema(name="row_id", dtype=DataType.INT64, is_primary=True, auto_id=True),
       FieldSchema(name="document_name", dtype=DataType.VARCHAR, max_length=512),
       FieldSchema(name="modified_date", dtype=DataType.VARCHAR, max_length=128),
       FieldSchema(name="text_chunk", dtype=DataType.VARCHAR, max_length=65535),
       FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
       FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=128),
       FieldSchema(name="chunk_index", dtype=DataType.INT64),
       FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
       FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=128),
   ]
  
   schema = CollectionSchema(
       fields=fields,
       description=f"Document collection with chunked text and embeddings"
   )
  
   collection = Collection(
       name=collection_name,
       schema=schema
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


       try:
           self.vector_store = MilvusVectorStore(
               uri=f"http://{self.milvus_host}:{self.milvus_port}",
               collection_name=self.collection_name,
               dim=self.dim,
               overwrite=False 
           )
           self.log.info(f"Connected to Milvus collection '{self.collection_name}' with dimension {self.dim}")
       except Exception as e:
           self.log.error(f"Error creating Milvus vector store: {str(e)}")
           raise


       self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
       self.chunking_strategy = AdvancedChunkingStrategy()


   def init_collection(self, collection_name: str = None, dim: int = None, overwrite: bool = False):
       collection_name = collection_name or self.collection_name
       dim = dim or self.dim
       try:
           connections.connect(
               alias="default",
               host=self.milvus_host,
               port=self.milvus_port
           )
          
           if utility.has_collection(collection_name):
               if overwrite:
                   utility.drop_collection(collection_name)
                   self.log.info(f"Dropped existing collection '{collection_name}'")
               else:
                   self.log.info(f"Collection '{collection_name}' already exists")
                   return False
          
           fields = [
               FieldSchema(name="row_id", dtype=DataType.INT64, is_primary=True, auto_id=True),
               FieldSchema(name="document_name", dtype=DataType.VARCHAR, max_length=512),
               FieldSchema(name="modified_date", dtype=DataType.VARCHAR, max_length=128),
               FieldSchema(name="text_chunk", dtype=DataType.VARCHAR, max_length=65535),
               FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
               FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=128),
               FieldSchema(name="chunk_index", dtype=DataType.INT64),
               FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
               FieldSchema(name="created_at", dtype=DataType.VARCHAR, max_length=128),
           ]
          
           schema = CollectionSchema(
               fields=fields,
               description=f"Document collection with chunked text and embeddings"
           )
          
           collection = Collection(
               name=collection_name,
               schema=schema
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
          
           self.log.info(f"Successfully created collection '{collection_name}' with custom schema (dim={dim})")
           return True
          
       except Exception as e:
           self.log.error(f"Error initializing collection '{collection_name}': {str(e)}")
           raise


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


                   metadata['document_name'] = metadata.get('file_name', f'document_{i}')
                   metadata['modified_date'] = datetime.now().isoformat()
                  
                   chunks = self.chunking_strategy.chunk_markdown(content, metadata)
                   chunks = self.chunking_strategy.add_context_to_chunks(chunks)
                  
                   for idx, chunk in enumerate(chunks):
                       if not chunk.metadata:
                           chunk.metadata = {}
                       chunk.metadata['chunk_index'] = idx
                       chunk.metadata['text_chunk'] = chunk.text[:65535]
                       chunk.metadata['document_name'] = metadata['document_name']
                       chunk.metadata['modified_date'] = metadata['modified_date']
                  
                   all_chunks.extend(chunks)


           if not all_chunks:
               self.log.warning("No valid chunks to index after processing")
               return


           self.log.info(
               f"Indexing {len(all_chunks)} chunks from {len(documents)} documents into collection '{self.collection_name}'")
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
   def __init__(self, converter, pipeline, *args, **kwargs):
       self.converter = converter
       self.pipeline = pipeline


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
               converted_content = self.converter.convert(doc.path)
               converted_docs.append(converted_content)


               file_path = Path(doc.path)
               metadata = {
                   "doc_id": str(doc.id),
                   "file_path": doc.path,
                   "file_name": file_path.name,
                   "document_name": file_path.name,
                   "created_at": str(doc.created_at) if hasattr(doc, 'created_at') else None,
                   "modified_date": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else datetime.now().isoformat(),
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
           .options(joinedload(Document.status))
           .join(Document.status)
           .filter(Document.status.has(name="in progress"))
           .limit(10)
           .all()
       )
       if documents:
           return documents
       return None










