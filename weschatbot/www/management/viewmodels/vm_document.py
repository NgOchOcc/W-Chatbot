from weschatbot.services.celery_service import convert_document
from weschatbot.utils.db import provide_session
from weschatbot.www.management.model_vm import ViewModel


def convert_document_callback(document):
    convert_document.delay(document)


class ViewModelDocument(ViewModel):
    list_fields = ["id", "name", "path", "is_used", "status"]
    update_fields = ["name", "is_used", "status"]
    add_fields = ["name", "path", "status"]
    detail_fields = ["id", "name", "path", "converted_path", "is_used", "status"]
    search_fields = ["name", "path", "status"]

    field_types = {
        "path": "file_upload"
    }

    @provide_session
    def add_item_post(self, session=None):
        return super().add_item_post(callback=convert_document_callback, session=session)
