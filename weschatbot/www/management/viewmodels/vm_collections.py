import json

from flask import render_template, request, jsonify

from weschatbot.schemas.collection import Entity
from weschatbot.services import collection_service
from weschatbot.services.collection_service import CollectionService
from weschatbot.utils.config import config
from weschatbot.www.management.model_vm import ViewModel


class ViewModelCollections(ViewModel):
    milvus_service = CollectionService(host=config["milvus"]["host"], port=config["milvus"]["port"])

    def get_entities(self):
        collection_name = request.args.get('collection_name')
        start_id = request.args.get('start_id')
        limit = request.args.get('limit')

        entity = Entity(1, "abc dax aeadas", "/srv/xx/xxx.pdf")

        return jsonify([entity.to_dict()])

    def list_view(self):
        collections = self.milvus_service.all_collections()
        model = {
            "collections": collections,
        }
        return render_template("management/collections_list.html", model=json.dumps(model, default=str))

    def register(self, flask_app_or_bp):
        super(ViewModelCollections, self).register(flask_app_or_bp)
        self.bp.route("/list_collections", methods=["GET"])(
            self.auth(self.list_view))
        self.bp.route("/entities", methods=["GET"])(
            self.auth(self.get_entities))
