import json

from flask import render_template, redirect, flash, abort

from weschatbot.models.user import ChatSession
from weschatbot.services.session_service import SessionService
from weschatbot.utils.db import provide_session
from weschatbot.www.management.model_vm import ViewModel, check_permission


class ViewModelChat(ViewModel):
    list_fields = ["id", "uuid", "name", "user", "status"]
    update_fields = ["name"]
    add_fields = []
    detail_fields = ["id", "name", "user", "messages"]
    search_fields = ["name"]

    disabled_view_models = ["add", "update"]

    @provide_session
    @check_permission("list")
    def detail_item(self, item_id, session=None):
        chat = session.query(ChatSession).get(item_id)
        if chat is None:
            flash("Item not found", "danger")
            return abort(404)

        res = chat.to_dict()
        return render_template("management/chat_details.html", title=f"Chat session #{item_id}",
                               model=json.dumps(res, default=str)), 200

    @provide_session
    @check_permission("delete")
    def delete_item_post(self, item, session=None):
        session_service = SessionService()
        res = session_service.delete_chat_session_by_id(item.id)
        if res:
            flash("Item deleted", "success")
        return redirect(self.list_view_model.search_url_func()), 302
