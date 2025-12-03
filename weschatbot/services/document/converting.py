import logging
from pathlib import Path

import torch
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from markitdown import MarkItDown

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.utils.common import SingletonMeta

logger = logging.getLogger(__name__)


class Converter:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class MarkerConverter(Converter, metaclass=SingletonMeta):
    def __init__(self):
        self.converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )

    def convert(self, document_path: str) -> str:
        rendered = self.converter(str(document_path))

        markdown_text, metadata, images = text_from_rendered(rendered)
        return markdown_text


class MarkitdownConverter(Converter, metaclass=SingletonMeta):
    def __init__(self):
        self.converter = MarkItDown()

    def convert(self, document_path: str) -> str:
        rendered = self.converter.convert(document_path)
        return rendered.text_content


class DocumentConverter(LoggingMixin):
    @staticmethod
    @torch.no_grad()
    def convert(document_path: str) -> str:
        input_path = Path(document_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {document_path}")

        file_ext = input_path.suffix.lower()

        try:
            if file_ext == '.pdf':
                with MarkerConverter() as converter:
                    res = converter.convert(document_path)
                return res
            else:
                with MarkitdownConverter() as converter:
                    res = converter.convert(document_path)
                return res
        except Exception as e:
            raise Exception(f"Error converting file {document_path}") from e
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("VRAM cache cleared.")
