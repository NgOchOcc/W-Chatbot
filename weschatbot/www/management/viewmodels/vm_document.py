import json

from weschatbot.models.user import Document
from weschatbot.services.celery_service import convert_document
from weschatbot.utils.db import provide_session
from weschatbot.www.management.model_vm import ViewModel
from flask import redirect, flash, render_template

from weschatbot.www.management.utils import outside_url_for


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

    actions = {
        "Converted document": outside_url_for(".get_converted_document")
    }

    @provide_session
    def add_item_post(self, session=None):
        return super().add_item_post(callback=convert_document_callback, session=session)

    @provide_session
    def get_converted_document(self, item_id, session=None):
        document = session.query(Document).get(item_id)
        if document is None:
            flash("Item not found", "danger")
            return redirect(self.list_view_model.search_url_func()), 302
        converted_path = document.converted_path
        if converted_path is None:
            flash("Item not found", "danger")
            return redirect(self.list_view_model.search_url_func()), 302
        with open(converted_path, "r") as f:
            converted_content = f.read()
        model = {
            "converted_content": converted_content
        }
        return render_template("management/converted_document.html", model=json.dumps(model, default=str))

    def register(self, flask_app_or_bp):
        super(ViewModelDocument, self).register(flask_app_or_bp)
        self.bp.route("/<int:item_id>/converted_document", methods=["GET"])(self.auth(self.get_converted_document))
