from weschatbot.exceptions.collection_exception import DocumentNotFoundError
from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.user import Document, DocumentStatus
from weschatbot.services.document.converting import DocumentConverter
from weschatbot.utils.config import config
from weschatbot.utils.db import provide_session


class DocumentService(LoggingMixin):
    converted_file_folder = config["core"]["converted_file_folder"]

    @provide_session
    def convert_document(self, document_id, session=None):
        try:
            std_document_id = int(document_id)
        except ValueError as e:
            raise e
        document = session.query(Document).get(std_document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document ID {std_document_id} not found")

        if document.status.name != "new":
            self.log.info("This document is already converted")
            return

        document_path = document.path
        file_name = document_path.split("/")[-1]
        converted_path = f"{self.converted_file_folder}/{file_name}.converted.md"

        try:
            res = DocumentConverter.convert(document_path)
            with open(converted_path, "w", encoding="utf-8") as f:
                f.write(res)

            done_status = session.query(DocumentStatus).filter(
                DocumentStatus.name == "done"
            ).one_or_none()

            document.status = done_status
            document.converted_path = converted_path

        except DocumentNotFoundError:
            raise

    @provide_session
    def convert_all_documents(self, session=None):
        self.mark_in_progress(session=session)
        documents = session.query(Document).join(DocumentStatus).filter(DocumentStatus.name == "in progress").all()
        for document in documents:
            self.convert_document(document.id, session=session)
            self.mark_done([document], session=session)

    @provide_session
    def mark_in_progress(self, session=None):
        in_progress_status = session.query(DocumentStatus).filter(DocumentStatus.name == "in progress").one_or_none()
        documents = session.query(Document).join(DocumentStatus).filter(DocumentStatus.name == "new").all()
        for document in documents:
            document.status = in_progress_status

        session.commit()

    @provide_session
    def mark_done(self, documents, session=None):
        done_status = session.query(DocumentStatus).filter(DocumentStatus.name == "done").one_or_none()

        document_ids = [doc.id for doc in documents]
        update_documents = session.query(Document).filter(Document.id.in_(document_ids)).all()

        for document in update_documents:
            document.status = done_status

        session.commit()
