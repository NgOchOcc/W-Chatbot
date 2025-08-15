import os

from flask import Blueprint, render_template, redirect
from flask import request
from flask_login import login_user, logout_user

from weschatbot.exceptions.user_exceptions import InvalidUserError
from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.job import Job
from weschatbot.models.user import User, ChatSession, Role, Permission, Document
from weschatbot.www.management.addition_blueprint import addition_blueprint
from weschatbot.www.management.utils import outside_url_for
from weschatbot.www.management.viewmodels.vm_chat import ViewModelChat
from weschatbot.www.management.viewmodels.vm_collections import ViewModelCollections
from weschatbot.www.management.viewmodels.vm_document import ViewModelDocument
from weschatbot.www.management.viewmodels.vm_job import ViewModelJob
from weschatbot.www.management.viewmodels.vm_permission import ViewModelPermission
from weschatbot.www.management.viewmodels.vm_role import ViewModelRole
from weschatbot.www.management.viewmodels.vm_user import ViewModelUser


class Management(LoggingMixin):
    def __init__(self, auth, user_service):
        self.auth = auth
        self.user_service = user_service

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        static_path = os.path.join(base_dir, 'static/management')
        self.bp = Blueprint('management',
                            import_name="management",
                            url_prefix='/management',
                            template_folder="weschatbot/www/templates",
                            static_folder=static_path, static_url_path='/static')

    @staticmethod
    def index():
        return render_template("management/index.html")  # noqa

    @staticmethod
    def logout():
        logout_user()
        return redirect(outside_url_for(".login")()), 302

    def login(self):
        if request.method == "GET":
            return render_template("management/login.html")  # noqa
        elif request.method == "POST":
            username = request.form.get('username')
            password = request.form.get('password')

            try:
                user = self.user_service.login_user(username, password)
                if user is None:
                    return redirect(outside_url_for(".login")), 302
                login_user(user)
                return redirect(outside_url_for(".index")()), 302
            except InvalidUserError as e:
                return redirect(outside_url_for(".login")()), 302

        else:
            return "Method not supported", 405

    def register(self):
        self.bp.route("/")(self.auth.required(self.index))
        self.bp.route("/login", methods=["GET", "POST"])(self.login)
        self.bp.route("/logout", methods=["GET"])(self.auth.required(self.logout))

        ViewModelUser(User, auth=self.auth.required).register(self.bp)
        ViewModelChat(ChatSession, auth=self.auth.required).register(self.bp)
        ViewModelRole(Role, auth=self.auth.required).register(self.bp)
        ViewModelPermission(Permission, auth=self.auth.required).register(self.bp)
        ViewModelDocument(Document, auth=self.auth.required).register(self.bp)
        ViewModelJob(Job, auth=self.auth.required).register(self.bp)
        ViewModelCollections(None, auth=self.auth.required).register(self.bp)

        self.bp.register_blueprint(addition_blueprint)
        return self.bp
