import re
from typing import List, Dict
from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter, SemanticSplitterNodeParser
from llama_index.core.embeddings import BaseEmbedding

from base_chunking import BaseChunkingStrategy


class SentencesplitStrategy:
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
        
    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[LlamaDocument]:
        """Main chunking method for markdown content"""
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
    
    def _chunk_table_document(self, content: str, metadata: Dict) -> List[LlamaDocument]:
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
                            chunks.append(LlamaDocument(
                                text=chunk_text,
                                metadata={**metadata}
                            ))
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
                    chunks.append(LlamaDocument(
                        text=chunk_text,
                        metadata={**metadata}
                    ))
                    current_chunk = []
                    current_size = 0

            current_chunk.append(line)
            current_size += len(line)

            if current_size >= self.chunk_size and not in_table:
                chunk_text = '\n'.join(current_chunk)
                chunks.append(LlamaDocument(
                    text=chunk_text,
                    metadata={**metadata}
                ))
                current_chunk = []
                current_size = 0

                if table_header and in_table:
                    current_chunk.extend(table_header)
                    current_size = sum(len(h) for h in table_header)

        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append(LlamaDocument(
                    text=chunk_text,
                    metadata={**metadata}
                ))

        return chunks
    
    def _chunk_technical_report(self, content: str, metadata: Dict) -> List[LlamaDocument]:
        parser = MarkdownNodeParser()

        temp_doc = LlamaDocument(text=content, metadata=metadata)
        nodes = parser.get_nodes_from_documents([temp_doc])

        chunks = []
        for i, node in enumerate(nodes):
            section_match = re.search(r'^#+\s+(.+)$', node.text.split('\n')[0], re.MULTILINE)

            chunk_metadata = {
                **metadata,
            }

            chunks.append(LlamaDocument(
                text=node.text,
                metadata=chunk_metadata
            ))

        return chunks
    
    def _chunk_general_markdown(self, content: str, metadata: Dict) -> List[LlamaDocument]:
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

            chunks.append(LlamaDocument(
                text=node.text,
                metadata=chunk_metadata
            ))

        return chunks
    
    def add_context_to_chunks(self, chunks: List[LlamaDocument]) -> List[LlamaDocument]:
        enhanced_chunks = []

        for i, chunk in enumerate(chunks):
            enhanced_chunks.append(chunk)
        return enhanced_chunks

class StructureAwareChunkingStrategy(BaseChunkingStrategy):
    def __init__(
        self,
        chunk_size: int = 768,
        chunk_overlap: int = 128,
        min_chunk_size: int = 128,
        max_chunk_size: int = 1024,
        preserve_code_blocks: bool = True,
        preserve_tables: bool = True
    ):
        super().__init__(chunk_size, chunk_overlap, min_chunk_size, max_chunk_size)
        self.preserve_code_blocks = preserve_code_blocks
        self.preserve_tables = preserve_tables

    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[LlamaDocument]:
        if metadata is None:
            metadata = {}

        blocks = self._parse_structure(content)
        chunks = self._group_blocks_into_chunks(blocks, metadata)
        return self.add_context_to_chunks(chunks)

    def _parse_structure(self, content: str) -> List[Dict]:
        blocks = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            if line.strip().startswith('```'):
                block, i = self._extract_code_block(lines, i)
                blocks.append(block)
                continue

            if '|' in line and line.count('|') >= 3:
                block, i = self._extract_table(lines, i)
                blocks.append(block)
                continue

            if line.strip().startswith('#'):
                blocks.append({
                    'type': 'header',
                    'level': len(line) - len(line.lstrip('#')),
                    'text': line,
                    'size': len(line)
                })
                i += 1
                continue

            if re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line):
                block, i = self._extract_list(lines, i)
                blocks.append(block)
                continue

            block, i = self._extract_paragraph(lines, i)
            if block['text'].strip():
                blocks.append(block)

        return blocks

    def _extract_code_block(self, lines: List[str], start: int) -> tuple:
        block_lines = [lines[start]]
        i = start + 1

        while i < len(lines):
            block_lines.append(lines[i])
            if lines[i].strip().startswith('```'):
                i += 1
                break
            i += 1

        text = '\n'.join(block_lines)
        language = lines[start].strip()[3:].strip()

        return {
            'type': 'code_block',
            'language': language,
            'text': text,
            'size': len(text),
            'preserve': self.preserve_code_blocks
        }, i

    def _extract_table(self, lines: List[str], start: int) -> tuple:
        block_lines = []
        i = start

        while i < len(lines) and ('|' in lines[i] or lines[i].strip() == ''):
            if lines[i].strip():
                block_lines.append(lines[i])
            else:
                break
            i += 1

        text = '\n'.join(block_lines)

        return {
            'type': 'table',
            'text': text,
            'size': len(text),
            'preserve': self.preserve_tables
        }, i

    def _extract_list(self, lines: List[str], start: int) -> tuple:
        block_lines = []
        i = start

        is_ordered = bool(re.match(r'^\s*\d+\.\s+', lines[start]))
        base_indent = len(lines[start]) - len(lines[start].lstrip())

        while i < len(lines):
            line = lines[i]
            if line.strip() == '':
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if re.match(r'^\s*[-*+]\s+', next_line) or re.match(r'^\s*\d+\.\s+', next_line):
                        block_lines.append(line)
                        i += 1
                        continue
                break

            current_indent = len(line) - len(line.lstrip())
            is_list_item = bool(re.match(r'^\s*[-*+]\s+', line) or re.match(r'^\s*\d+\.\s+', line))
            is_continuation = current_indent > base_indent

            if is_list_item or is_continuation:
                block_lines.append(line)
                i += 1
            else:
                break

        text = '\n'.join(block_lines)
        return {
            'type': 'list',
            'list_type': 'ordered' if is_ordered else 'unordered',
            'text': text,
            'size': len(text)
        }, i

    def _extract_paragraph(self, lines: List[str], start: int) -> tuple:
        block_lines = []
        i = start

        while i < len(lines):
            line = lines[i]
            if line.strip() == '':
                i += 1
                break

            if (line.strip().startswith('#') or
                line.strip().startswith('```') or
                ('|' in line and line.count('|') >= 3) or
                re.match(r'^\s*[-*+]\s+', line) or
                re.match(r'^\s*\d+\.\s+', line)):
                break

            block_lines.append(line)
            i += 1

        text = '\n'.join(block_lines)
        return {
            'type': 'paragraph',
            'text': text,
            'size': len(text)
        }, i

    def _group_blocks_into_chunks(self, blocks: List[Dict], metadata: Dict) -> List[LlamaDocument]:
        chunks = []
        current_chunk = []
        current_size = 0
        current_header_context = ""

        for block in blocks:
            if block['type'] == 'header':
                current_header_context = block['text']

            if block.get('preserve', False):
                if current_chunk:
                    chunk_text = '\n\n'.join(b['text'] for b in current_chunk)
                    if len(chunk_text.strip()) >= self.min_chunk_size:
                        chunks.append(self._create_chunk(chunk_text, current_chunk, metadata, current_header_context))
                    current_chunk = []
                    current_size = 0

                if block['size'] <= self.max_chunk_size:
                    chunks.append(self._create_chunk(block['text'], [block], metadata, current_header_context))
                else:
                    chunks.extend(self._split_large_block(block, metadata, current_header_context))

                continue

            if current_size + block['size'] > self.chunk_size and current_chunk:
                chunk_text = '\n\n'.join(b['text'] for b in current_chunk)
                if len(chunk_text.strip()) >= self.min_chunk_size:
                    chunks.append(self._create_chunk(chunk_text, current_chunk, metadata, current_header_context))

                overlap_blocks = self._get_overlap_blocks(current_chunk)
                current_chunk = overlap_blocks
                current_size = sum(b['size'] for b in overlap_blocks)

            current_chunk.append(block)
            current_size += block['size']

        if current_chunk:
            chunk_text = '\n\n'.join(b['text'] for b in current_chunk)
            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append(self._create_chunk(chunk_text, current_chunk, metadata, current_header_context))
        return chunks


    def _create_chunk(self, text: str, blocks: List[Dict], metadata: Dict, header_context: str) -> LlamaDocument:
        block_types = [b['type'] for b in blocks]

        chunk_metadata = {
            **metadata,
            'chunk_type': 'structure_aware',
            'block_types': list(set(block_types)),
            'block_count': len(blocks),
            'has_code': 'code_block' in block_types,
            'has_table': 'table' in block_types,
            'has_list': 'list' in block_types,
            'section_header': header_context
        }

        return LlamaDocument(text=text, metadata=chunk_metadata)

    def _get_overlap_blocks(self, blocks: List[Dict]) -> List[Dict]:
        if not blocks:
            return []

        overlap_blocks = []
        overlap_size = 0

        for block in reversed(blocks):
            if overlap_size >= self.chunk_overlap:
                break
            overlap_blocks.insert(0, block)
            overlap_size += block['size']

        return overlap_blocks

    def _split_large_block(self, block: Dict, metadata: Dict, header_context: str) -> List[LlamaDocument]:
        chunks = []
        text = block['text']
        lines = text.split('\n')

        current_lines = []
        current_size = 0

        for line in lines:
            if current_size + len(line) > self.chunk_size and current_lines:
                chunk_text = '\n'.join(current_lines)
                chunks.append(self._create_chunk(chunk_text, [block], metadata, header_context))
                current_lines = []
                current_size = 0

            current_lines.append(line)
            current_size += len(line)

        if current_lines:
            chunk_text = '\n'.join(current_lines)
            chunks.append(self._create_chunk(chunk_text, [block], metadata, header_context))

        return chunks


class TablePreservingStrategy(BaseChunkingStrategy):
    def __init__(
        self,
        chunk_size: int = 768,
        chunk_overlap: int = 128,
        min_chunk_size: int = 128,
        max_chunk_size: int = 2048,  
        keep_table_headers: bool = True,
        add_table_summary: bool = False
    ):
        super().__init__(chunk_size, chunk_overlap, min_chunk_size, max_chunk_size)
        self.keep_table_headers = keep_table_headers
        self.add_table_summary = add_table_summary

    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[LlamaDocument]:
        if metadata is None:
            metadata = {}

        chunks = []
        sections = self._split_into_sections(content)

        for section in sections:
            if section['type'] == 'table':
                table_chunk = self._process_table_section(section, metadata)
                chunks.append(table_chunk)
            else:
                text_chunks = self._process_text_section(section, metadata)
                chunks.extend(text_chunks)

        return self.add_context_to_chunks(chunks)

    def _split_into_sections(self, content: str) -> List[Dict]:
        sections = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            if '|' in line and line.count('|') >= 3:
                section, i = self._extract_table_section(lines, i)
                sections.append(section)
            else:
                section, i = self._extract_text_section(lines, i)
                if section['content'].strip():
                    sections.append(section)

        return sections

    def _extract_table_section(self, lines: List[str], start: int) -> tuple:
        context_before = []
        context_start = max(0, start - 5)

        for j in range(context_start, start):
            if lines[j].strip() and not ('|' in lines[j] and lines[j].count('|') >= 3):
                context_before.append(lines[j])

        table_lines = []
        i = start
        table_header = []

        while i < len(lines):
            line = lines[i]

            if '|' in line and line.count('|') >= 3:
                table_lines.append(line)
                if not table_header and i + 1 < len(lines) and '---' in lines[i + 1]:
                    table_header = [line, lines[i + 1]]

                i += 1
            elif line.strip() == '':
                i += 1
                if i < len(lines) and '|' in lines[i] and lines[i].count('|') >= 3:
                    table_lines.append('')
                    continue
                else:
                    break
            else:
                break

        context_after = []
        for j in range(i, min(i + 3, len(lines))):
            if lines[j].strip() and not ('|' in lines[j] and lines[j].count('|') >= 3):
                context_after.append(lines[j])

        full_content = []
        if context_before:
            full_content.extend(context_before[-2:])  
            full_content.append('')

        full_content.extend(table_lines)

        if context_after:
            full_content.append('')
            full_content.extend(context_after[:2]) 

        return {
            'type': 'table',
            'content': '\n'.join(full_content),
            'table_only': '\n'.join(table_lines),
            'header': table_header,
            'row_count': len([l for l in table_lines if '|' in l]) - (2 if table_header else 0),
            'context_before': '\n'.join(context_before[-2:]) if context_before else '',
            'context_after': '\n'.join(context_after[:2]) if context_after else ''
        }, i

    def _extract_text_section(self, lines: List[str], start: int) -> tuple:
        text_lines = []
        i = start

        while i < len(lines):
            line = lines[i]
            if '|' in line and line.count('|') >= 3:
                break

            text_lines.append(line)
            i += 1

        return {
            'type': 'text',
            'content': '\n'.join(text_lines)
        }, i

    def _process_table_section(self, section: Dict, metadata: Dict) -> LlamaDocument:
        content = section['content']
        if self.add_table_summary:
            summary = self._generate_table_summary(section)
            content = f"{summary}\n\n{content}"

        chunk_metadata = {
            **metadata,
            'chunk_type': 'table',
            'row_count': section['row_count'],
            'has_context': bool(section.get('context_before') or section.get('context_after')),
            'table_header': section['header'][0] if section.get('header') else ''
        }

        return LlamaDocument(text=content, metadata=chunk_metadata)

    def _process_text_section(self, section: Dict, metadata: Dict) -> List[LlamaDocument]:
        splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        temp_doc = LlamaDocument(text=section['content'], metadata=metadata)
        nodes = splitter.get_nodes_from_documents([temp_doc])

        chunks = []
        for i, node in enumerate(nodes):
            chunk_metadata = {
                **metadata,
                'chunk_type': 'text',
                'chunk_index': i
            }
            chunks.append(LlamaDocument(text=node.text, metadata=chunk_metadata))

        return chunks

    def _generate_table_summary(self, section: Dict) -> str:
        header = section.get('header', [])
        row_count = section.get('row_count', 0)

        if header:
            cols = [col.strip() for col in header[0].split('|') if col.strip()]
            col_names = ', '.join(cols[:5])  # First 5 columns
            if len(cols) > 5:
                col_names += f", ... ({len(cols)} columns total)"

            return f"[Table Summary: {row_count} rows with columns: {col_names}]"

        return f"[Table Summary: {row_count} rows]"

class SemanticChunkingStrategy(BaseChunkingStrategy):
    def __init__(
        self,
        embed_model: BaseEmbedding,
        chunk_size: int = 768,
        buffer_size: int = 1,
        breakpoint_percentile_threshold: int = 95,
        min_chunk_size: int = 128,
        max_chunk_size: int = 1024
    ):
        super().__init__(chunk_size, 0, min_chunk_size, max_chunk_size)
        self.embed_model = embed_model
        self.buffer_size = buffer_size
        self.breakpoint_percentile_threshold = breakpoint_percentile_threshold

    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[LlamaDocument]:
        if metadata is None:
            metadata = {}

        parser = SemanticSplitterNodeParser(
            buffer_size=self.buffer_size,
            embed_model=self.embed_model,
            breakpoint_percentile_threshold=self.breakpoint_percentile_threshold
        )

        temp_doc = LlamaDocument(text=content, metadata=metadata)
        nodes = parser.get_nodes_from_documents([temp_doc])

        chunks = []
        for i, node in enumerate(nodes):
            if len(node.text) < self.min_chunk_size:
                if chunks and len(chunks[-1].text) + len(node.text) <= self.max_chunk_size:
                    chunks[-1].text += '\n\n' + node.text
                    continue

            chunk_metadata = {
                **metadata,
                'chunk_type': 'semantic',
                'chunk_index': i,
                'semantic_breakpoint': True
            }

            chunks.append(LlamaDocument(text=node.text, metadata=chunk_metadata))

        return self.add_context_to_chunks(chunks)