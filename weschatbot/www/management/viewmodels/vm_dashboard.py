import json

from flask import render_template, jsonify

from weschatbot.services.active_status_service import ActiveStatusService
from weschatbot.services.dashboard_service import DashboardService
from weschatbot.utils.db import provide_session
from weschatbot.utils.redis_config import redis_client
from weschatbot.www.management.model_vm import EmptyViewModel


class ViewModelDashboard(EmptyViewModel):
    active_service = ActiveStatusService(redis_client=redis_client(0))
    dashboard_service = DashboardService(active_status_service=active_service)

    def dashboard(self):
        model = {}
        title = "Dashboard"
        return render_template(
            "management/dashboard.html",
            model=json.dumps(model, default=str),
            title=title
        )

    @provide_session
    def number_of_chat_sessions(self, session=None):
        try:
            result = self.dashboard_service.number_of_chat_sessions(session)
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    @provide_session
    def number_of_messages(self, session=None):
        try:
            result = self.dashboard_service.number_of_messages(session)
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    @provide_session
    def number_of_messages_today(self, session=None):
        try:
            result = self.dashboard_service.number_of_messages_today(session)
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    @provide_session
    def number_of_chat_sessions_today(self, session=None):
        try:
            result = self.dashboard_service.number_of_chat_sessions_today(session)
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    def number_of_active_users(self):
        try:
            result = self.dashboard_service.number_of_active_users()
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    def number_of_distinct_users_with_messages_today(self):
        try:
            result = self.dashboard_service.number_of_distinct_users_with_messages_today()
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    def number_of_messages_daily(self):
        try:
            result = self.dashboard_service.number_of_messages_daily()
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    def number_of_messages_monthly(self):
        try:
            result = self.dashboard_service.number_of_messages_monthly()
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    def number_of_chat_sessions_monthly(self):
        try:
            result = self.dashboard_service.number_of_chat_sessions_monthly()
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    def number_of_chat_sessions_daily(self):
        try:
            result = self.dashboard_service.number_of_chat_sessions_daily()
            return jsonify({"status": "success", "data": result}), 200
        except Exception:  # noqa
            return jsonify({"status": "error", "data": "There is an error"}), 500

    def register(self, flask_app_or_bp):
        super().register(flask_app_or_bp)

        self.bp.route("/dashboard", methods=["GET"])(self.auth(self.dashboard))
        self.bp.route("/number_of_chat_sessions", methods=["GET"])(self.auth(self.number_of_chat_sessions))
        self.bp.route("/number_of_messages", methods=["GET"])(self.auth(self.number_of_messages))
        self.bp.route("/number_of_messages_today", methods=["GET"])(self.auth(self.number_of_messages_today))
        self.bp.route("/number_of_chat_sessions_today", methods=["GET"])(self.auth(self.number_of_chat_sessions_today))
        self.bp.route("/number_of_active_users", methods=["GET"])(self.auth(self.number_of_active_users))
        self.bp.route("/number_of_distinct_users_with_messages_today", methods=["GET"])(
            self.auth(self.number_of_distinct_users_with_messages_today))

        self.bp.route("/number_of_messages_daily", methods=["GET"])(self.auth(self.number_of_messages_daily))
        self.bp.route("/number_of_messages_monthly", methods=["GET"])(self.auth(self.number_of_messages_monthly))
        self.bp.route("/number_of_chat_sessions_daily", methods=["GET"])(self.auth(self.number_of_chat_sessions_daily))
        self.bp.route("/number_of_chat_sessions_monthly", methods=["GET"])(
            self.auth(self.number_of_chat_sessions_monthly))
