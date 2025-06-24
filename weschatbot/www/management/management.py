import os

from flask import Blueprint, render_template

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.user import User, ChatSession
from weschatbot.www.management.addition_blueprint import addition_blueprint
from weschatbot.www.management.viewmodels.vm_chat import ViewModelChat
from weschatbot.www.management.viewmodels.vm_user import ViewModelUser


class Management(LoggingMixin):
    def __init__(self, auth):
        self.auth = auth

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

    def register(self):
        self.bp.route("/")(self.index)

        ViewModelUser(User, auth=self.auth.required).register(self.bp)
        ViewModelChat(ChatSession, auth=self.auth.required).register(self.bp)

        self.bp.register_blueprint(addition_blueprint)
        return self.bp
