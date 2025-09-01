import json

from flask import request, redirect, render_template, flash, jsonify

from weschatbot.models.collection import Collection
from weschatbot.services import collection_service
from weschatbot.services.collection_service import CollectionService
from weschatbot.utils.config import config
from weschatbot.utils.db import provide_session
from weschatbot.www.management.model_vm import ViewModel, Pagination


class ViewModelCollection(ViewModel):
    list_fields = ["id", "name", "status"]
    update_fields = ["status"]
    add_fields = ["name", "status"]
    detail_fields = ["name", "status"]
    search_fields = ["name", "status"]

    collection_service = CollectionService(config["milvus"]["host"], config["milvus"]["port"])

    @provide_session
    def add_item_post(self, session=None):
        name = request.form.get("name")
        status_id = request.form.get("status")
        try:
            collection = Collection(name=name, status_id=int(status_id))
            res = CollectionService.create_collection(collection_name=name, milvus_host=config["milvus"]["host"],
                                                      milvus_port=config["milvus"]["port"])
            if res:
                session.add(collection)
            return redirect(self.list_view_model.search_url_func()), 302
        except Exception as e:
            return f"{e}", 500

    @provide_session
    def detail_item(self, item_id, session=None):
        try:
            collection_detail = self.collection_service.get_collection(collection_id=item_id)
            return render_template("management/collection_detail.html",
                                   model=json.dumps(collection_detail.to_dict(), default=str))

        except Exception as e:
            return f"{e}", 500

    @provide_session
    def delete_item_post(self, item, session=None):
        try:
            self.collection_service.delete_collection(collection_id=item.id)
            flash("Successfully deleted the item", "success")
            return redirect(self.list_view_model.search_url_func()), 302
        except Exception as e:
            return f"{e}", 500

    @provide_session
    def all_documents(self, session=None):
        return self.collection_service.all_documents(session=session)

    @provide_session
    def add_document_to_collection(self, session=None):
        try:
            collection_id = int(request.form.get("collection_id"))
            document_id = int(request.form.get("document_id"))

            success = self.collection_service.add_document_to_collection(
                collection_id=collection_id,
                document_id=document_id,
                session=session
            )

            if success:
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"status": "failed", "message": "Document already linked or not found"}), 400

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @provide_session
    def get_documents_by_collection_id(self, session=None):
        collection_id = int(request.args.get("collection_id"))
        res = self.collection_service.get_documents_by_collection_id(collection_id=collection_id, session=session)
        return jsonify(res), 200

    @provide_session
    def remove_document_from_collection(self, session=None):
        collection_id = int(request.form.get("collection_id"))
        document_id = int(request.form.get("document_id"))
        try:
            self.collection_service.remove_document_from_collection(collection_id=collection_id,
                                                                    document_id=document_id,
                                                                    session=session)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @provide_session
    def index_collection(self, session):
        collection_id = int(request.form.get("collection_id"))
        try:
            self.collection_service.index_collection(collection_id=collection_id, session=session)
            return jsonify({"status": "success"}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    @provide_session
    def get_collection(self, session=None):
        collection_id = int(request.args.get("collection_id"))
        res = self.collection_service.get_collection(collection_id=collection_id, session=session)
        return jsonify(res), 200

    @provide_session
    def flush(self, session=None):
        collection_id = int(request.args.get("collection_id"))
        self.collection_service.flush(collection_id=collection_id, session=session)
        return jsonify({"status": "success"}), 200

    def register(self, flask_app_or_bp):
        super(ViewModelCollection, self).register(flask_app_or_bp)
        self.bp.route("/all_documents", methods=["GET"])(self.auth(self.all_documents))
        self.bp.route("/get_collection", methods=["GET"])(self.auth(self.get_collection))
        self.bp.route("/add_document_to_collection", methods=["POST"])(self.auth(self.add_document_to_collection))
        self.bp.route("/remove_document_from_collection", methods=["POST"])(
            self.auth(self.remove_document_from_collection))
        self.bp.route("/get_documents_by_collection_id", methods=["GET"])(
            self.auth(self.get_documents_by_collection_id))
        self.bp.route("/index_collection", methods=["POST"])(self.auth(self.index_collection))
        self.bp.route("/flush_collection", methods=["GET"])(self.auth(self.flush))
