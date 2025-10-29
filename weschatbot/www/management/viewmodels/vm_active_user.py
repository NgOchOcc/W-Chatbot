import json

from flask import render_template

from weschatbot.services.active_status_service import ActiveStatusService
from weschatbot.utils.redis_config import redis_client
from weschatbot.www.management.model_vm import EmptyViewModel


class ViewModelActiveUser(EmptyViewModel):
    rd_client = redis_client(0)
    active_status_service = ActiveStatusService(rd_client)

    def __init__(self, auth):
        super().__init__(auth)

    def active_users(self):
        model = [x.to_dict() for x in self.active_status_service.get_all_active_user()]
        title = "Active Users"
        return render_template(
            "management/active_users.html",
            model=json.dumps(model, default=str),
            title=title
        )

    def register(self, flask_app_or_bp):
        super().register(flask_app_or_bp)

        self.bp.route("/active_users", methods=["GET"])(self.auth(self.active_users))
