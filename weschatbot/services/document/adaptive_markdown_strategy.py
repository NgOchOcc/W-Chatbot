import re
from typing import List, Dict

from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import (
    MarkdownNodeParser,
    SentenceSplitter
)

from weschatbot.services.document.base_chunking import BaseChunkingStrategy


class AdaptiveMarkdownStrategy(BaseChunkingStrategy):
    def __init__(
            self,
            chunk_size: int = 2048,
            chunk_overlap: int = 128,
            min_chunk_size: int = 128,
            max_chunk_size: int = 3192,
            min_tokens: int = 256,
            max_tokens: int = 1024,
            table_max_chunk_size: int = 2048,
            table_min_rows_per_chunk: int = 30,
            table_max_rows_threshold: int = 200,
            preserve_table_headers: bool = True,
            add_table_summary: bool = True,
            table_context_lines_before: int = 3,
            table_context_lines_after: int = 2,
            min_words_per_chunk: int = 30,
            remove_image_references: bool = True,
            merge_short_chunks: bool = True
    ):
        super().__init__(chunk_size, chunk_overlap, min_chunk_size, max_chunk_size)
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.table_max_chunk_size = table_max_chunk_size
        self.table_min_rows_per_chunk = table_min_rows_per_chunk
        self.table_max_rows_threshold = table_max_rows_threshold
        self.preserve_table_headers = preserve_table_headers
        self.add_table_summary = add_table_summary
        self.table_context_lines_before = table_context_lines_before
        self.table_context_lines_after = table_context_lines_after
        self.min_words_per_chunk = min_words_per_chunk
        self.remove_image_references = remove_image_references
        self.merge_short_chunks = merge_short_chunks

        # LlamaIndex parsers with token-based sizing
        # Approximate: 1 token ≈ 0.75 words, so adjust chunk_size accordingly
        token_based_chunk_size = int(max_tokens * 0.75)  # ~768 words for 1024 tokens

        self.markdown_parser = MarkdownNodeParser()
        self.sentence_splitter = SentenceSplitter(
            chunk_size=token_based_chunk_size,
            chunk_overlap=int(chunk_overlap * 0.75),
            paragraph_separator="\n\n"
        )

    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[LlamaDocument]:
        metadata = metadata or {}
        if self.remove_image_references:
            content = self._remove_images(content)

        sections = self._split_tables_and_text(content)
        chunks = []
        for section in sections:
            if section['type'] == 'table':
                chunks.extend(self._chunk_table(section, metadata))
            else:
                chunks.extend(self._chunk_text_with_llamaindex(section['content'], metadata))

        if self.merge_short_chunks:
            chunks = self._merge_and_split_chunks(chunks)

        chunks = self._validate_token_limits(chunks)
        return self.add_context_to_chunks(chunks)

    def _estimate_tokens(self, text: str) -> int:
        return len(text) // 4

    def _validate_token_limits(self, chunks: List[LlamaDocument]) -> List[LlamaDocument]:
        validated = []
        i = 0

        while i < len(chunks):
            current = chunks[i]
            token_count = self._estimate_tokens(current.text)

            # Chunk is too small - try to merge with next
            if token_count < self.min_tokens and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                combined_text = f"{current.text}\n\n{next_chunk.text}"
                combined_tokens = self._estimate_tokens(combined_text)

                # If combined is within limits, merge
                if combined_tokens <= self.max_tokens:
                    validated.append(LlamaDocument(
                        text=combined_text,
                        metadata={**next_chunk.metadata}
                    ))
                    i += 2
                    continue
                # If combined is too large, split it
                elif combined_tokens > self.max_tokens:
                    split_chunks = self._split_by_tokens(combined_text, current.metadata)
                    validated.extend(split_chunks)
                    i += 2
                    continue

            # Chunk is too large - split it
            if token_count > self.max_tokens:
                split_chunks = self._split_by_tokens(current.text, current.metadata)
                validated.extend(split_chunks)
                i += 1
                continue

            # Chunk is within limits
            validated.append(current)
            i += 1

        return validated

    def _split_by_tokens(self, text: str, metadata: Dict) -> List[LlamaDocument]:
        doc = LlamaDocument(text=text, metadata=metadata)

        # Use SentenceSplitter to split intelligently
        nodes = self.sentence_splitter.get_nodes_from_documents([doc])

        chunks = []
        for node in nodes:
            node_tokens = self._estimate_tokens(node.text)
            if node_tokens > self.max_tokens:
                sentences = node.text.split('. ')
                current_chunk = []
                current_tokens = 0

                for sentence in sentences:
                    sentence_tokens = self._estimate_tokens(sentence)

                    if current_tokens + sentence_tokens <= self.max_tokens:
                        current_chunk.append(sentence)
                        current_tokens += sentence_tokens
                    else:
                        if current_chunk:
                            chunks.append(LlamaDocument(
                                text='. '.join(current_chunk) + '.',
                                metadata={**metadata}
                            ))
                        current_chunk = [sentence]
                        current_tokens = sentence_tokens

                if current_chunk:
                    chunks.append(LlamaDocument(
                        text='. '.join(current_chunk),
                        metadata={**metadata}
                    ))
            else:
                chunks.append(LlamaDocument(
                    text=node.text,
                    metadata={**metadata}
                ))

        return chunks

    def _remove_images(self, content: str) -> str:
        patterns = [
            r'!\[.*?\]\(.*?\.(jpg|jpeg|png|gif|svg|bmp|webp|ico).*?\)',
            r'<img[^>]*>',
            r'https?://\S+\.(jpg|jpeg|png|gif|svg|bmp|webp|ico)\b'
        ]
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        return content

    def _split_tables_and_text(self, content: str) -> List[Dict]:
        sections = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            if self._is_table_line(lines[i]):
                section, i = self._extract_table_section(lines, i)
            else:
                section, i = self._extract_text_section(lines, i)

            if section['content'].strip():
                sections.append(section)

        return sections

    def _is_table_line(self, line: str) -> bool:
        return '|' in line and line.count('|') >= 3

    def _is_table_separator(self, line: str) -> bool:
        return bool(re.match(r'^\s*\|?[\s\-:|]+\|[\s\-:|]*$', line))

    def _extract_table_section(self, lines: List[str], start: int) -> tuple:
        ctx_before = [
            lines[j] for j in range(max(0, start - self.table_context_lines_before), start)
            if lines[j].strip() and not self._is_table_line(lines[j])
        ]

        table_lines = []
        header = None
        i = start

        while i < len(lines):
            if self._is_table_line(lines[i]):
                table_lines.append(lines[i])
                if not header and i + 1 < len(lines) and self._is_table_separator(lines[i + 1]):
                    header = [lines[i], lines[i + 1]]
                i += 1
            elif not lines[i].strip() and i + 1 < len(lines) and self._is_table_line(lines[i + 1]):
                i += 1
            else:
                i += 1
                break

        ctx_after = [
            lines[j] for j in range(i, min(i + self.table_context_lines_after, len(lines)))
            if lines[j].strip() and not self._is_table_line(lines[j])
        ]

        return {
            'type': 'table',
            'content': '\n'.join(table_lines),
            'header': header,
            'row_count': sum(1 for d in table_lines if d.strip() and not self._is_table_separator(d)),
            'context_before': '\n'.join(ctx_before[-self.table_context_lines_before:]),
            'context_after': '\n'.join(ctx_after[:self.table_context_lines_after])
        }, i

    def _extract_text_section(self, lines: List[str], start: int) -> tuple:
        text_lines = []
        i = start
        while i < len(lines) and not self._is_table_line(lines[i]):
            text_lines.append(lines[i])
            i += 1
        return {'type': 'text', 'content': '\n'.join(text_lines)}, i

    def _chunk_text_with_llamaindex(self, content: str, metadata: Dict) -> List[LlamaDocument]:
        if not content.strip():
            return []

        doc = LlamaDocument(text=content, metadata=metadata)
        nodes = self.markdown_parser.get_nodes_from_documents([doc])
        chunks = []
        for node in nodes:
            chunks.append(LlamaDocument(
                text=node.text,
                metadata={**metadata}
            ))

        return chunks

    def _chunk_table(self, section: Dict, metadata: Dict) -> List[LlamaDocument]:
        content = section['content']
        header = section['header']
        ctx_before = section.get('context_before', '')
        ctx_after = section.get('context_after', '')

        lines = [d for d in content.split('\n') if d.strip()]
        if not header and len(lines) >= 2 and self._is_table_separator(lines[1]):
            header, data = lines[:2], lines[2:]
        elif header:
            header_idx = next((i for i, l in enumerate(lines) if l == header[0]), -1)
            data = lines[header_idx + len(header):] if header_idx >= 0 else lines
        else:
            header, data = [], lines

        if len(content) <= self.table_max_chunk_size and len(data) <= self.table_max_rows_threshold:
            return [self._build_table_chunk(
                lines, header, ctx_before, ctx_after, metadata, section['row_count']
            )]

        return self._split_large_table(data, header, ctx_before, ctx_after, metadata, section['row_count'])

    def _build_table_chunk(self, lines, header, ctx_before, ctx_after, metadata, row_count,
                           split_idx=0, is_last=False) -> LlamaDocument:
        parts = []
        if split_idx == 0 and self.add_table_summary and header:
            cols = [c.strip() for c in header[0].split('|') if c.strip()]
            col_preview = ', '.join(cols[:5])
            if len(cols) > 5:
                col_preview += f', ... ({len(cols)} total)'
            parts.append(f'[Table: {row_count} rows, columns: {col_preview}]\n')

        if split_idx == 0 and ctx_before:
            parts.append(f'{ctx_before}\n')

        parts.append('\n'.join(lines))
        if (split_idx == 0 or is_last) and ctx_after:
            parts.append(f'\n{ctx_after}')

        return LlamaDocument(
            text=''.join(parts),
            metadata={**metadata}
        )

    def _split_large_table(self, data, header, ctx_before, ctx_after, metadata, row_count) -> List[LlamaDocument]:
        header_size = sum(len(h) for h in header) if header else 0
        avg_row_size = sum(len(d) for d in data) / max(len(data), 1)
        rows_per_chunk = max(
            int((self.table_max_chunk_size - header_size - 100) / avg_row_size),
            self.table_min_rows_per_chunk
        )

        chunks = []
        for idx in range(0, len(data), rows_per_chunk):
            chunk_data = data[idx:idx + rows_per_chunk]
            chunk_lines = (header if self.preserve_table_headers and header else []) + chunk_data

            chunks.append(self._build_table_chunk(
                chunk_lines, header,
                ctx_before if idx == 0 else '',
                ctx_after if idx + rows_per_chunk >= len(data) else '',
                metadata, row_count,
                split_idx=idx // rows_per_chunk,
                is_last=(idx + rows_per_chunk >= len(data))
            ))

        return chunks

    def _merge_and_split_chunks(self, chunks: List[LlamaDocument]) -> List[LlamaDocument]:
        if not chunks:
            return chunks

        merged = []
        i = 0

        while i < len(chunks):
            current = chunks[i]
            word_count = len(current.text.split())
            if word_count < self.min_words_per_chunk and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]
                combined_text = f"{current.text}\n\n{next_chunk.text}"

                if len(combined_text) <= self.max_chunk_size:
                    merged.append(LlamaDocument(
                        text=combined_text,
                        metadata={**next_chunk.metadata}
                    ))
                    i += 2
                    continue
                else:
                    # Use SentenceSplitter to split oversized combined chunk
                    doc = LlamaDocument(text=combined_text, metadata=current.metadata)
                    split_nodes = self.sentence_splitter.get_nodes_from_documents([doc])
                    for node in split_nodes:
                        merged.append(LlamaDocument(
                            text=node.text,
                            metadata={**current.metadata}
                        ))
                    i += 2
                    continue

            # Split oversized chunks
            if len(current.text) > self.max_chunk_size:
                doc = LlamaDocument(text=current.text, metadata=current.metadata)
                split_nodes = self.sentence_splitter.get_nodes_from_documents([doc])
                for node in split_nodes:
                    merged.append(LlamaDocument(
                        text=node.text,
                        metadata={**current.metadata}
                    ))
                i += 1
                continue

            merged.append(current)
            i += 1

        return merged
