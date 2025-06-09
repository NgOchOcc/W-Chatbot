import json

from flask import request, redirect, abort, url_for, render_template, jsonify

from weschatbot.models.user import Role, UserStatus, User
from weschatbot.services.user_service import generate_random_string, UserService
from weschatbot.utils.db import provide_session
from weschatbot.www.management.model_vm import ViewModel
from weschatbot.www.management.utils import outside_url_for

user_service = UserService()


class ViewModelUser(ViewModel):
    list_fields = ["id", "name", "role", "status", "modified_date"]
    update_fields = ["name", "role", "status"]
    add_fields = ["name", "role", "status"]
    detail_fields = ["id", "name", "role", "status", "modified_date"]
    search_fields = ["name"]

    actions = {
        "Change password": outside_url_for(".user_change_password")
    }

    @provide_session
    def add_item_post(self, session=None):
        kwargs = {}
        for field in self.add_fields:
            kwargs[field] = request.form.get(field, None)

        user_name = request.form.get("name", None)
        role_id = int(request.form.get("role", None))
        status_id = int(request.form.get("status", None))
        role_name = session.query(Role).get(role_id).name
        status_name = session.query(UserStatus).get(status_id).name
        password = generate_random_string()
        user_service.create_user(user_name, password, role_name, status_name, session=session)
        return redirect(self.list_view_model.search_url_func()), 302

    @provide_session
    def user_change_password(self, item_id, session=None):
        if request.method == "GET":
            user = session.query(User).get(item_id)
            if user is None:
                return abort(404)
            else:
                model = {
                    "user": user.to_dict(),
                    "submit_url": url_for(".user_change_password", item_id=item_id),
                }
                return render_template("management/user_change_password.html", model=json.dumps(model, default=str))
        if request.method == "POST":
            user = session.query(User).get(item_id)
            if user is None:
                return abort(404)
            else:
                password = request.json.get("password", None)
                user_service.update_password(user, password, session=session)
                return jsonify(status="success"), 200
        return abort(405)

    def register(self, flask_app_or_bp):
        super(ViewModelUser, self).register(flask_app_or_bp)
        self.bp.route("/<int:item_id>/user_change_password", methods=["GET", "POST"])(
            self.auth(self.user_change_password))
