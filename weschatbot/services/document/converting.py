from pathlib import Path

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from markitdown import MarkItDown

from weschatbot.utils.common import SingletonMeta


class MarkerConverter(metaclass=SingletonMeta):
    def __init__(self):
        self.converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )

    def convert(self, document_path: str) -> str:
        rendered = self.converter(str(document_path))

        markdown_text, metadata, images = text_from_rendered(rendered)
        return markdown_text


class MarkitdownConverter(metaclass=SingletonMeta):
    def __init__(self):
        self.converter = MarkItDown()

    def convert(self, document_path: str) -> str:
        rendered = self.converter.convert(document_path)
        return rendered.text_content


class DocumentConverter:
    @staticmethod
    def convert(document_path: str) -> str:
        input_path = Path(document_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {document_path}")

        file_ext = input_path.suffix.lower()

        try:
            if file_ext == '.pdf':
                return MarkerConverter().convert(document_path)
            else:
                return MarkitdownConverter().convert(document_path)
        except Exception as e:
            raise Exception(f"Error converting file {document_path}: {str(e)}")
