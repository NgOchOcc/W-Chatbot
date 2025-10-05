import re
from typing import List, Dict
from llama_index.core import Document as LlamaDocument

from base_chunking import BaseChunkingStrategy

class RecursiveMarkdownStrategy(BaseChunkingStrategy):
    def __init__(
        self,
        chunk_size: int = 2048,
        chunk_overlap: int = 128,
        min_chunk_size: int = 128,
        max_chunk_size: int = 4096,
        preserve_header_context: bool = True, 
        max_header_depth: int = 3, 
        add_chunk_metadata: bool = True,
        min_words_per_chunk: int = 30,
        remove_image_references: bool = True,
        merge_short_chunks: bool = True
    ):
        super().__init__(chunk_size, chunk_overlap, min_chunk_size, max_chunk_size)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.preserve_header_context = preserve_header_context
        self.max_header_depth = max_header_depth
        self.add_chunk_metadata = add_chunk_metadata
        self.min_words_per_chunk = min_words_per_chunk
        self.remove_image_references = remove_image_references
        self.merge_short_chunks = merge_short_chunks

        self.separators = [
            "\n## ",      # H2 headers
            "\n### ",     # H3 headers
            "\n#### ",    # H4 headers
            "\n##### ",   # H5 headers
            "\n\n",       # Paragraph breaks
            "\n",         # Line breaks
            ". ",         # Sentences
            " ",          # Words
            ""            # Characters (fallback)
        ]

    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[LlamaDocument]:
        if metadata is None:
            metadata = {}

        content = self._preprocess_content(content)
        doc_structure = self._parse_document_structure(content)
        chunks = self._recursive_split(content, doc_structure, metadata)
        if self.merge_short_chunks:
            chunks = self._merge_short_chunks(chunks)

        return self.add_context_to_chunks(chunks)

    def _preprocess_content(self, content: str) -> str:
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        if self.remove_image_references:
            content = self._remove_images_and_files(content)

        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        return content

    def _remove_images_and_files(self, content: str) -> str:
        image_exts = r'\.(jpg|jpeg|png|gif|svg|bmp|webp|ico|tiff?)'
        file_exts = r'\.(pdf|docx?|xlsx?|pptx?|zip|rar|7z|tar|gz)'

        content = re.sub(r'!\[([^\]]*)\]\([^\)]*' + image_exts + r'[^\)]*\)', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<img[^>]*' + image_exts + r'[^>]*/?>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\[([^\]]*)\]\([^\)]*' + file_exts + r'[^\)]*\)', r'\1', content, flags=re.IGNORECASE)
        content = re.sub(r'(?<!\[)\bhttps?://[^\s<>"{}|\\^\[\]`]+(?:' + image_exts + '|' + file_exts + r')\b', '', content, flags=re.IGNORECASE)
        content = re.sub(r' +', ' ', content)

        return content

    def _parse_document_structure(self, content: str) -> Dict:
        lines = content.split('\n')
        structure = {
            'headers': [], 
            'header_stack': []  
        }
        for i, line in enumerate(lines):
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2).strip()
                structure['headers'].append({
                    'line': i,
                    'level': level,
                    'text': text,
                    'full_line': line
                })

        return structure

    def _get_header_context(self, position: int, structure: Dict) -> List[str]:
        if not self.preserve_header_context:
            return []

        header_context = []
        current_level = 7  # Start with max

        for header in reversed(structure['headers']):
            if header['line'] < position:
                if header['level'] < current_level and header['level'] <= self.max_header_depth:
                    header_context.insert(0, header['full_line'])
                    current_level = header['level']
                    if current_level == 1:
                        break

        return header_context

    def _recursive_split(
        self,
        text: str,
        structure: Dict,
        metadata: Dict,
        separator_idx: int = 0
    ) -> List[LlamaDocument]:
        chunks = []
        if len(text) <= self.chunk_size:
            if text.strip():
                return [LlamaDocument(
                    text=text,
                    metadata={**metadata, 'split_method': 'base_case'}
                )]
            return []

        if separator_idx >= len(self.separators):
            return self._split_by_size(text, metadata)

        separator = self.separators[separator_idx]
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        current_chunk = []
        current_size = 0

        for i, split in enumerate(splits):
            if separator and i < len(splits) - 1:
                split_with_sep = split + separator
            else:
                split_with_sep = split

            split_size = len(split_with_sep)
            if current_size + split_size > self.chunk_size and current_chunk:
                chunk_text = ''.join(current_chunk)

                if len(chunk_text) > self.max_chunk_size:
                    sub_chunks = self._recursive_split(
                        chunk_text,
                        structure,
                        metadata,
                        separator_idx + 1
                    )
                    chunks.extend(sub_chunks)
                elif chunk_text.strip():
                    chunks.append(LlamaDocument(
                        text=chunk_text,
                        metadata={
                            **metadata,
                            'separator': separator.replace('\n', '\\n') if separator else 'char'
                        }
                    ))

                overlap_text = self._get_overlap(current_chunk, separator)
                current_chunk = [overlap_text, split_with_sep] if overlap_text else [split_with_sep]
                current_size = len(overlap_text) + split_size
            else:
                current_chunk.append(split_with_sep)
                current_size += split_size

        if current_chunk:
            chunk_text = ''.join(current_chunk)
            if len(chunk_text) > self.max_chunk_size:
                sub_chunks = self._recursive_split(
                    chunk_text,
                    structure,
                    metadata,
                    separator_idx + 1
                )
                chunks.extend(sub_chunks)
            elif chunk_text.strip():
                chunks.append(LlamaDocument(
                    text=chunk_text,
                    metadata={
                        **metadata,
                        'separator': separator.replace('\n', '\\n') if separator else 'char'
                    }
                ))

        return chunks

    def _get_overlap(self, current_chunk: List[str], separator: str) -> str:
        if not current_chunk or self.chunk_overlap == 0:
            return ""

        full_text = ''.join(current_chunk)
        overlap_start = max(0, len(full_text) - self.chunk_overlap)
        return full_text[overlap_start:]

    def _split_by_size(self, text: str, metadata: Dict) -> List[LlamaDocument]:
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            if chunk_text.strip():
                chunks.append(LlamaDocument(
                    text=chunk_text,
                    metadata={**metadata, 'split_method': 'hard_split'}
                ))

            start = end - self.chunk_overlap if self.chunk_overlap > 0 else end

        return chunks

    def _count_words(self, text: str) -> int:
        return len(text.split())

    def _merge_short_chunks(self, chunks: List[LlamaDocument]) -> List[LlamaDocument]:
        if not chunks:
            return chunks

        max_iterations = 10
        iteration = 0

        while iteration < max_iterations:
            merged = self._merge_short_chunks_single_pass(chunks)
            if len(merged) == len(chunks):
                break
            chunks = merged
            iteration += 1

        return chunks

    def _merge_short_chunks_single_pass(self, chunks: List[LlamaDocument]) -> List[LlamaDocument]:
        merged_chunks = []
        i = 0

        while i < len(chunks):
            current = chunks[i]
            word_count = self._count_words(current.text)
            if word_count < self.min_words_per_chunk:
                if i + 1 < len(chunks):
                    next_chunk = chunks[i + 1]
                    merged_text = current.text + '\n\n' + next_chunk.text

                    if len(merged_text) <= self.max_chunk_size:
                        merged_chunks.append(LlamaDocument(
                            text=merged_text,
                            metadata={
                                **next_chunk.metadata,
                                'was_merged': True,
                                'word_count': self._count_words(merged_text)
                            }
                        ))
                        i += 2
                        continue

                if merged_chunks:
                    prev = merged_chunks[-1]
                    merged_text = prev.text + '\n\n' + current.text

                    if len(merged_text) <= self.max_chunk_size:
                        merged_chunks[-1] = LlamaDocument(
                            text=merged_text,
                            metadata={
                                **prev.metadata,
                                'was_merged': True,
                                'word_count': self._count_words(merged_text)
                            }
                        )
                        i += 1
                        continue

            current.metadata['word_count'] = word_count
            merged_chunks.append(current)
            i += 1

        return merged_chunks