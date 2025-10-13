import json
from datetime import datetime

from flask import render_template, request, jsonify

from weschatbot.services.query_service import QueryService
from weschatbot.utils.db import provide_session
from weschatbot.www.management.model_vm import ViewModel, Pagination

query_service = QueryService()


class ViewModelQuery(ViewModel):
    list_fields = [
        "id",
        "message_id",
        "document_id",
        "row_id",
        "document_text",
        "cosine_score",
        "collection_id",
        "rank"
    ]

    update_fields = []
    add_fields = []
    detail_fields = [
        "id",
        "message_id",
        "document_id",
        "row_id",
        "document_text",
        "cosine_score",
        "collection_id",
        "rank"
    ]
    search_fields = ["name"]

    disabled_view_models = ["update", "add", "delete"]

    @provide_session
    def list_items(self, session=None):
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        from_date = request.args.get('from_date', datetime.now().strftime("%Y-%m-%d"), type=str)
        to_date = request.args.get('to_date', datetime.now().strftime("%Y-%m-%d"), type=str)
        message_id = request.args.get('message_id', None)

        query_results, page, page_size, total, message_id = query_service.get_query_results_by_date(from_date, to_date,
                                                                                                    page, page_size,
                                                                                                    message_id,
                                                                                                    session)

        model = {
            "pagination": Pagination(page=page, page_size=page_size, total=total).to_dict(),
            "search_params": {
                "from_date": from_date,
                "to_date": to_date,
                "message_id": message_id,
            },
            "query_results": [x for x in query_results]
        }

        return render_template("management/list_query_results.html", model=json.dumps(model, default=str),
                               title="List of Queries")

    @provide_session
    def query_result_summary(self, session=None):
        from_date = request.args.get('from_date', datetime.now().strftime("%Y-%m-%d"), type=str)
        to_date = request.args.get('to_date', datetime.now().strftime("%Y-%m-%d"), type=str)

        result = query_service.summary_query_results(from_date, to_date, session)
        return jsonify({"status": "success", "data": result})

    def register(self, flask_app_or_bp):
        super(ViewModelQuery, self).register(flask_app_or_bp)
        self.bp.route("/query_result_summary", methods=["GET"])(self.auth(self.query_result_summary))
