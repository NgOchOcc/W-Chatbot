import re
from typing import List, Dict

from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core import Document as LlamaDocument


class AdvancedChunkingStrategy:
    def __init__(
        self,
        chunk_size: int = 768,
        chunk_overlap: int = 128,
        min_chunk_size: int = 128,
        max_chunk_size: int = 1024
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        
    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[Dict]:
        """Main chunking method for markdown content - returns list of dicts"""
        if metadata is None:
            metadata = {}

        doc_type = self._detect_document_type(content)
        metadata['doc_type'] = doc_type

        if doc_type == 'table_heavy':
            return self._chunk_table_document(content, metadata)
        elif doc_type == 'technical_report':
            return self._chunk_technical_report(content, metadata)
        else:
            return self._chunk_general_markdown(content, metadata)
    
    def _detect_document_type(self, content: str) -> str:
        """Detect the type of document based on content patterns"""
        lines = content.split('\n')
        table_count = sum(1 for line in lines if '|' in line and line.count('|') >= 3)
        total_lines = len(lines)
        
        if table_count > total_lines * 0.3:
            return 'table_heavy'
        elif any(keyword in content.lower() for keyword in ['raport', 'report', 'anexa', 'inventory']):
            return 'technical_report'
        else:
            return 'general'
    
    def _chunk_table_document(self, content: str, metadata: Dict) -> List[Dict]:
        chunks = []
        current_chunk = []
        current_size = 0
        in_table = False
        table_header = []

        lines = content.split('\n')

        for i, line in enumerate(lines):
            if '|' in line and line.count('|') >= 3:
                if not in_table:
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk)
                        if len(chunk_text.strip()) >= self.min_chunk_size:
                            chunks.append({
                                'text_chunk': chunk_text,
                                'metadata': {**metadata}
                            })
                        current_chunk = []
                        current_size = 0

                    in_table = True
                    table_header = []

                if i < len(lines) - 1 and '---' in lines[i + 1]:
                    table_header = [line, lines[i + 1]]

            elif in_table and line.strip() == '':
                in_table = False
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    chunks.append({
                        'text_chunk': chunk_text,
                        'metadata': {**metadata}
                    })
                    current_chunk = []
                    current_size = 0

            current_chunk.append(line)
            current_size += len(line)

            if current_size >= self.chunk_size and not in_table:
                chunk_text = '\n'.join(current_chunk)
                chunks.append({
                    'text_chunk': chunk_text,
                    'metadata': {**metadata}
                })
                current_chunk = []
                current_size = 0

                if table_header and in_table:
                    current_chunk.extend(table_header)
                    current_size = sum(len(h) for h in table_header)

        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append({
                    'text_chunk': chunk_text,
                    'metadata': {**metadata}
                })

        return chunks
    
    def _chunk_technical_report(self, content: str, metadata: Dict) -> List[Dict]:
        parser = MarkdownNodeParser()

        temp_doc = LlamaDocument(text=content, metadata=metadata)
        nodes = parser.get_nodes_from_documents([temp_doc])

        chunks = []
        for i, node in enumerate(nodes):
            section_match = re.search(r'^#+\s+(.+)$', node.text.split('\n')[0], re.MULTILINE)

            chunk_metadata = {
                **metadata,
            }

            chunks.append({
                'text_chunk': node.text,
                'metadata': chunk_metadata
            })

        return chunks
    
    def _chunk_general_markdown(self, content: str, metadata: Dict) -> List[Dict]:
        splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        temp_doc = LlamaDocument(text=content, metadata=metadata)

        nodes = splitter.get_nodes_from_documents([temp_doc])

        chunks = []
        for i, node in enumerate(nodes):
            chunk_metadata = {
                **metadata,
            }

            chunks.append({
                'text_chunk': node.text,
                'metadata': chunk_metadata
            })

        return chunks
    
    def add_context_to_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Add context to chunks - currently just returns the chunks as-is"""
        enhanced_chunks = []

        for i, chunk in enumerate(chunks):
            enhanced_chunks.append(chunk)
        return enhanced_chunks