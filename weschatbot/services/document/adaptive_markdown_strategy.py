import re
from typing import List, Dict, Optional, Tuple
from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter

from base_chunking import BaseChunkingStrategy

class AdaptiveMarkdownStrategy(BaseChunkingStrategy):
    def __init__(
        self,
        chunk_size: int = 2048,
        chunk_overlap: int = 128,
        min_chunk_size: int = 128,
        max_chunk_size: int = 3192,
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
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
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

        self.markdown_parser = MarkdownNodeParser()
        self.sentence_splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def chunk_markdown(self, content: str, metadata: Dict = None) -> List[LlamaDocument]:
        if metadata is None:
            metadata = {}

        content, preprocessing_stats = self._preprocess_content(content)
        if preprocessing_stats:
            metadata['preprocessing_stats'] = preprocessing_stats

        sections = self._parse_content_sections(content)
        merged_sections = self._merge_adjacent_sections(sections)

        chunks = []
        for section in merged_sections:
            if section['type'] == 'table':
                table_chunks = self._chunk_table(section, metadata)
                chunks.extend(table_chunks)
            else:
                text_chunks = self._chunk_text(section, metadata)
                chunks.extend(text_chunks)

        if self.merge_short_chunks:
            chunks = self._merge_short_text_chunks(chunks)

        return self.add_context_to_chunks(chunks)

    def _preprocess_content(self, content: str) -> Tuple[str, Dict]:
        stats = {
            'removed_empty_lines': 0,
            'normalized_tables': 0,
            'removed_duplicate_rows': 0,
            'trimmed_whitespace': 0,
            'fixed_table_formatting': 0,
            'removed_image_references': 0,
            'removed_file_links': 0
        }

        original_content = content
        content = content.replace('\r\n', '\n').replace('\r', '\n')

        if self.remove_image_references:
            content, img_stats = self._remove_image_and_file_references(content)
            stats['removed_image_references'] = img_stats['images']
            stats['removed_file_links'] = img_stats['files']

        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.rstrip()
            if stripped != line:
                stats['trimmed_whitespace'] += 1
            cleaned_lines.append(stripped)

        normalized_lines = []
        empty_count = 0

        for line in cleaned_lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    normalized_lines.append(line)
                else:
                    stats['removed_empty_lines'] += 1
            else:
                empty_count = 0
                normalized_lines.append(line)

        normalized_lines = self._normalize_tables(normalized_lines, stats)
        while normalized_lines and normalized_lines[0].strip() == '':
            normalized_lines.pop(0)
            stats['removed_empty_lines'] += 1

        while normalized_lines and normalized_lines[-1].strip() == '':
            normalized_lines.pop()
            stats['removed_empty_lines'] += 1

        content = '\n'.join(normalized_lines)

        if content != original_content:
            return content, stats
        return content, {}

    def _remove_image_and_file_references(self, content: str) -> Tuple[str, Dict]:
        stats = {'images': 0, 'files': 0}

        image_extensions = r'\.(jpg|jpeg|png|gif|svg|bmp|webp|ico|tiff?)'
        file_extensions = r'\.(pdf|docx?|xlsx?|pptx?|zip|rar|7z|tar|gz)'

        pattern = r'!\[([^\]]*)\]\([^\)]*' + image_extensions + r'[^\)]*\)'
        matches = re.findall(pattern, content, re.IGNORECASE)
        stats['images'] += len(matches)
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        pattern = r'<img[^>]*' + image_extensions + r'[^>]*/?>'
        matches = re.findall(pattern, content, re.IGNORECASE)
        stats['images'] += len(matches)
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        pattern = r'\[([^\]]*)\]\([^\)]*' + file_extensions + r'[^\)]*\)'
        matches = re.findall(pattern, content, re.IGNORECASE)
        stats['files'] += len(matches)

        content = re.sub(pattern, r'\1', content, flags=re.IGNORECASE)


        pattern = r'(?<!\[)\bhttps?://[^\s<>"{}|\\^\[\]`]+' + image_extensions + r'\b'
        matches = re.findall(pattern, content, re.IGNORECASE)
        stats['images'] += len(matches)
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        pattern = r'(?<!\[)\bhttps?://[^\s<>"{}|\\^\[\]`]+' + file_extensions + r'\b'
        matches = re.findall(pattern, content, re.IGNORECASE)
        stats['files'] += len(matches)
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        pattern = r'(?:^|\s)(?:[./\\]?[\w\-./\\]+)?' + image_extensions + r'\b'
        matches = re.findall(pattern, content, re.IGNORECASE)
        stats['images'] += len(matches)
        content = re.sub(pattern, ' ', content, flags=re.IGNORECASE)

        content = re.sub(r' +', ' ', content)
        return content, stats

    def _normalize_tables(self, lines: List[str], stats: Dict) -> List[str]:
        normalized = []
        i = 0

        while i < len(lines):
            line = lines[i]
            if self._is_table_line(line):
                table_lines, i = self._extract_and_normalize_table(lines, i, stats)
                normalized.extend(table_lines)
            else:
                normalized.append(line)
                i += 1

        return normalized

    def _extract_and_normalize_table(self, lines: List[str], start: int, stats: Dict) -> Tuple[List[str], int]:
        table_lines = []
        i = start
        header_line = None
        separator_line = None
        data_rows = []

        while i < len(lines):
            line = lines[i]

            if self._is_table_line(line):
                normalized_line = self._normalize_table_row(line)

                if normalized_line != line:
                    stats['fixed_table_formatting'] += 1

                if header_line is None:
                    header_line = normalized_line
                elif separator_line is None and self._is_table_separator(line):
                    separator_line = self._normalize_table_separator(line)
                    if separator_line != line:
                        stats['fixed_table_formatting'] += 1
                else:
                    data_rows.append(normalized_line)

                i += 1
            elif line.strip() == '' and i + 1 < len(lines) and self._is_table_line(lines[i + 1]):
                i += 1
            else:
                break

        if data_rows:
            unique_rows = []
            seen = set()

            for row in data_rows:
                normalized_for_comparison = re.sub(r'\s+', '', row)
                if normalized_for_comparison not in seen:
                    seen.add(normalized_for_comparison)
                    unique_rows.append(row)
                else:
                    stats['removed_duplicate_rows'] += 1

            data_rows = unique_rows

        if header_line:
            table_lines.append(header_line)

        if separator_line:
            table_lines.append(separator_line)
        elif header_line:
            table_lines.append(self._generate_table_separator(header_line))
            stats['fixed_table_formatting'] += 1

        table_lines.extend(data_rows)

        if table_lines:
            stats['normalized_tables'] += 1

        return table_lines, i

    def _normalize_table_row(self, line: str) -> str:
        parts = line.split('|')
        normalized_parts = []

        for part in parts:
            cleaned = part.strip()
            cleaned = re.sub(r'\s+', ' ', cleaned)

            if cleaned:
                normalized_parts.append(f' {cleaned} ')
            else:
                normalized_parts.append('')

        return '|'.join(normalized_parts)

    def _normalize_table_separator(self, line: str) -> str:
        parts = line.split('|')
        normalized_parts = []

        for part in parts:
            stripped = part.strip()
            if stripped:
                if stripped.startswith(':') and stripped.endswith(':'):
                    normalized_parts.append(':---:')  # Center
                elif stripped.endswith(':'):
                    normalized_parts.append('---:')   # Right
                elif stripped.startswith(':'):
                    normalized_parts.append(':---')   # Left
                else:
                    normalized_parts.append('---')    # Default
            else:
                normalized_parts.append('')

        return '|'.join(normalized_parts)

    def _generate_table_separator(self, header_line: str) -> str:
        num_cols = header_line.count('|') - 1
        if header_line.startswith('|') and header_line.endswith('|'):
            num_cols = header_line.count('|') - 1

        parts = [''] + ['---'] * num_cols + ['']
        return '|'.join(parts)

    def _parse_content_sections(self, content: str) -> List[Dict]:
        sections = []
        lines = content.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            if self._is_table_line(line):
                section, i = self._extract_table_section(lines, i)
                sections.append(section)
            else:
                section, i = self._extract_text_section(lines, i)
                if section['content'].strip():
                    sections.append(section)

        return sections

    def _merge_adjacent_sections(self, sections: List[Dict]) -> List[Dict]:
        if len(sections) <= 1:
            return sections

        merged = []
        i = 0

        while i < len(sections):
            current = sections[i]

            if current['type'] == 'table':
                text_before = merged[-1] if merged and merged[-1]['type'] == 'text' else None
                text_after = sections[i + 1] if i + 1 < len(sections) and sections[i + 1]['type'] == 'text' else None

                table_size = len(current['content'])
                before_size = len(text_before['content']) if text_before else 0
                after_size = len(text_after['content']) if text_after else 0
                total_size = table_size + before_size + after_size + 10  # +10 for newlines

                if total_size <= self.table_max_chunk_size:
                    merged_content_parts = []

                    if text_before:
                        merged_content_parts.append(text_before['content'])
                        merged_content_parts.append('')
                        merged.pop() 

                    merged_content_parts.append(current['content'])

                    if text_after:
                        merged_content_parts.append('')
                        merged_content_parts.append(text_after['content'])
                        i += 1  

                    merged_content = '\n'.join(merged_content_parts)

                    merged.append({
                        'type': 'table',
                        'content': merged_content,
                        'table_only': current['content'],
                        'header': current['header'],
                        'row_count': current['row_count'],
                        'has_merged_context': True,
                        'merged_content_size': len(merged_content),  # Track actual size
                        'context_before': text_before['content'] if text_before else '',
                        'context_after': text_after['content'] if text_after else ''
                    })
                else:
                    merged.append(current)
            else:
                merged.append(current)

            i += 1

        return merged

    def _is_table_line(self, line: str) -> bool:
        return '|' in line and line.count('|') >= 3

    def _extract_table_section(self, lines: List[str], start: int) -> tuple:
        context_before = []
        context_start = max(0, start - self.table_context_lines_before)

        for j in range(context_start, start):
            if lines[j].strip() and not self._is_table_line(lines[j]):
                context_before.append(lines[j])

        table_lines = []
        table_header = None
        i = start

        while i < len(lines):
            line = lines[i]

            if self._is_table_line(line):
                table_lines.append(line)

                if table_header is None and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if self._is_table_separator(next_line):
                        table_header = [line, next_line]

                i += 1
            elif line.strip() == '':
                if i + 1 < len(lines) and self._is_table_line(lines[i + 1]):
                    table_lines.append(line)
                    i += 1
                else:
                    i += 1
                    break
            else:
                break

        context_after = []
        for j in range(i, min(i + self.table_context_lines_after, len(lines))):
            if lines[j].strip() and not self._is_table_line(lines[j]):
                context_after.append(lines[j])

        return {
            'type': 'table',
            'content': '\n'.join(table_lines),
            'table_only': '\n'.join(table_lines),
            'header': table_header,
            'row_count': len([l for l in table_lines if l.strip() and not self._is_table_separator(l)]),
            'context_before': '\n'.join(context_before[-self.table_context_lines_before:]) if context_before else '',
            'context_after': '\n'.join(context_after[:self.table_context_lines_after]) if context_after else ''
        }, i

    def _is_table_separator(self, line: str) -> bool:
        return bool(re.match(r'^\s*\|?[\s\-:|]+\|[\s\-:|]*$', line))

    def _extract_text_section(self, lines: List[str], start: int) -> tuple:
        text_lines = []
        i = start

        while i < len(lines):
            line = lines[i]
            if self._is_table_line(line):
                break

            text_lines.append(line)
            i += 1

        return {
            'type': 'text',
            'content': '\n'.join(text_lines)
        }, i

    def _chunk_table(self, section: Dict, metadata: Dict) -> List[LlamaDocument]:
        chunks = []
        table_content = section['content']
        header = section['header']
        row_count = section['row_count']
        context_before = section.get('context_before', '')
        context_after = section.get('context_after', '')

        lines = table_content.split('\n')
        table_lines = [l for l in lines if l.strip()]

        if not header:
            if len(table_lines) >= 2 and self._is_table_separator(table_lines[1]):
                header = table_lines[:2]
                data_lines = table_lines[2:]
            else:
                header = []
                data_lines = table_lines
        else:
            header_idx = -1
            for idx, line in enumerate(table_lines):
                if header and line == header[0]:
                    header_idx = idx
                    break

            if header_idx >= 0 and header_idx + len(header) < len(table_lines):
                data_lines = table_lines[header_idx + len(header):]
            else:
                data_lines = table_lines

        data_row_count = len(data_lines)

        can_keep_whole = (
            len(table_content) <= self.table_max_chunk_size and
            data_row_count <= self.table_max_rows_threshold
        )

        if can_keep_whole:
            full_content_parts = []

            if self.add_table_summary:
                summary = self._generate_table_summary(section)
                full_content_parts.append(summary)
                full_content_parts.append('')

            if context_before:
                full_content_parts.append(context_before)
                full_content_parts.append('')

            full_content_parts.append('\n'.join(table_lines))
            if context_after:
                full_content_parts.append('')
                full_content_parts.append(context_after)

            chunk_text = '\n'.join(full_content_parts)

            chunks.append(LlamaDocument(
                text=chunk_text,
                metadata={
                    **metadata,
                    'chunk_type': 'table',
                    'row_count': row_count,
                    'is_split': False,
                    'table_strategy': 'keep_whole',
                    'has_context': bool(context_before or context_after),
                    'has_summary': self.add_table_summary,
                    'table_header': header[0] if header else ''
                }
            ))
        else:
            header_size = sum(len(h) + 1 for h in header) if header else 0
            avg_row_size = sum(len(line) for line in data_lines) / max(len(data_lines), 1)
            available_size_per_chunk = self.table_max_chunk_size - header_size - 100
            estimated_rows_per_chunk = max(
                int(available_size_per_chunk / avg_row_size),
                self.table_min_rows_per_chunk
            )

            current_chunk = []
            current_size = 0
            chunk_index = 0

            for row_idx, line in enumerate(data_lines):
                line_size = len(line) + 1 
                projected_chunk_size = current_size + line_size + header_size

                should_split = False

                if len(current_chunk) >= self.table_min_rows_per_chunk:
                    if projected_chunk_size > self.table_max_chunk_size:
                        should_split = True
                    elif len(current_chunk) >= estimated_rows_per_chunk:
                        should_split = True
                elif projected_chunk_size > self.table_max_chunk_size:
                    should_split = True

                if should_split and current_chunk:
                    chunk_lines = []
                    if chunk_index == 0 and self.add_table_summary:
                        summary = self._generate_table_summary(section)
                        chunk_lines.append(summary)
                        chunk_lines.append('')

                    if chunk_index == 0 and context_before:
                        chunk_lines.append(context_before)
                        chunk_lines.append('')

                    if self.preserve_table_headers and header:
                        chunk_lines.extend(header)

                    chunk_lines.extend(current_chunk)
                    chunk_text = '\n'.join(chunk_lines)
                    chunks.append(LlamaDocument(
                        text=chunk_text,
                        metadata={
                            **metadata,
                            'chunk_type': 'table',
                            'is_split': True,
                            'split_index': chunk_index,
                            'row_count': len(current_chunk),
                            'table_strategy': 'row_based_split',
                            'has_context': chunk_index == 0 and bool(context_before),
                            'has_summary': chunk_index == 0 and self.add_table_summary,
                            'table_header': header[0] if header else ''
                        }
                    ))

                    current_chunk = []
                    current_size = 0
                    chunk_index += 1

                current_chunk.append(line)
                current_size += line_size

            if current_chunk:
                chunk_lines = []
                if chunk_index == 0 and self.add_table_summary:
                    summary = self._generate_table_summary(section)
                    chunk_lines.append(summary)
                    chunk_lines.append('')

                if chunk_index == 0 and context_before:
                    chunk_lines.append(context_before)
                    chunk_lines.append('')

                # Add header
                if self.preserve_table_headers and header:
                    chunk_lines.extend(header)

                chunk_lines.extend(current_chunk)

                if context_after:
                    chunk_lines.append('')
                    chunk_lines.append(context_after)

                chunk_text = '\n'.join(chunk_lines)
                chunks.append(LlamaDocument(
                    text=chunk_text,
                    metadata={
                        **metadata,
                        'chunk_type': 'table',
                        'is_split': True,
                        'split_index': chunk_index,
                        'is_last_split': True,
                        'row_count': len(current_chunk),
                        'table_strategy': 'row_based_split',
                        'has_context': (chunk_index == 0 and bool(context_before)) or bool(context_after),
                        'has_summary': chunk_index == 0 and self.add_table_summary,
                        'table_header': header[0] if header else ''
                    }
                ))

        return chunks

    def _chunk_text(self, section: Dict, metadata: Dict) -> List[LlamaDocument]:
        content = section['content']
        temp_doc = LlamaDocument(text=content, metadata=metadata)
        nodes = self.markdown_parser.get_nodes_from_documents([temp_doc])

        chunks = []
        for i, node in enumerate(nodes):
            first_line = node.text.split('\n')[0]
            section_title = first_line if first_line.strip().startswith('#') else None

            chunks.append(LlamaDocument(
                text=node.text,
                metadata={
                    **metadata,
                    'chunk_type': 'markdown_section',
                    'chunk_index': i,
                    'section_title': section_title
                }
            ))

        return chunks


    def _generate_table_summary(self, section: Dict) -> str:
        header = section.get('header', [])
        row_count = section.get('row_count', 0)

        if header and len(header) > 0:
            header_line = header[0]
            cols = [col.strip() for col in header_line.split('|') if col.strip()]

            col_names = ', '.join(cols[:5])
            if len(cols) > 5:
                col_names += f', ... ({len(cols)} columns total)'

            return f'[Table Summary: {row_count} rows with columns: {col_names}]'

        return f'[Table Summary: {row_count} rows]'

    def _count_words(self, text: str) -> int:
        return len(text.split())

    def _merge_short_text_chunks(self, chunks: List[LlamaDocument]) -> List[LlamaDocument]:
        if not chunks:
            return chunks

        max_iterations = 10  
        iteration = 0

        while iteration < max_iterations:
            merged_chunks = self._merge_short_chunks_single_pass(chunks)
            if len(merged_chunks) == len(chunks):
                break

            chunks = merged_chunks
            iteration += 1

        return chunks

    def _merge_short_chunks_single_pass(self, chunks: List[LlamaDocument]) -> List[LlamaDocument]:
        merged_chunks = []
        i = 0

        while i < len(chunks):
            current_chunk = chunks[i]
            current_text = current_chunk.text
            current_word_count = self._count_words(current_text)
            current_type = current_chunk.metadata.get('chunk_type', 'text')

            if current_type == 'table':
                merged_chunks.append(current_chunk)
                i += 1
                continue

            if current_word_count < self.min_words_per_chunk:
                if i + 1 < len(chunks):
                    next_chunk = chunks[i + 1]
                    next_type = next_chunk.metadata.get('chunk_type', 'text')

                    if next_type != 'table':
                        merged_text = current_text + '\n\n' + next_chunk.text
                        merged_word_count = self._count_words(merged_text)

                        if len(merged_text) <= self.max_chunk_size:
                            merged_chunk = LlamaDocument(
                                text=merged_text,
                                metadata={
                                    **next_chunk.metadata,
                                    'word_count': merged_word_count,
                                    'was_merged': True,
                                    'merged_from_short_chunk': True
                                }
                            )
                            merged_chunks.append(merged_chunk)
                            i += 2  
                            continue

                if merged_chunks and merged_chunks[-1].metadata.get('chunk_type') != 'table':
                    prev_chunk = merged_chunks[-1]
                    merged_text = prev_chunk.text + '\n\n' + current_text
                    merged_word_count = self._count_words(merged_text)

                    if len(merged_text) <= self.max_chunk_size:
                        merged_chunks[-1] = LlamaDocument(
                            text=merged_text,
                            metadata={
                                **prev_chunk.metadata,
                                'word_count': merged_word_count,
                                'was_merged': True,
                                'merged_from_short_chunk': True
                            }
                        )
                        i += 1
                        continue

            current_chunk.metadata['word_count'] = current_word_count
            merged_chunks.append(current_chunk)
            i += 1

        return merged_chunks