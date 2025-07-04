from functools import wraps, reduce

from flask import Flask
from flask_login import LoginManager, login_required
from flask_wtf import CSRFProtect

from weschatbot.models.user import User
from weschatbot.security.flask_jwt_manager import FlaskJWTManager
from weschatbot.services.user_service import UserService
from weschatbot.utils.config import config
from weschatbot.utils.db import provide_session
from weschatbot.www.management.management import Management


class NonAuth:
    def required(self, func):
        @wraps(func)
        def wrap(*args, **kwargs):
            return func(*args, **kwargs)

        return wrap

    def get_user_id(self):
        return None


class JWTAuth(NonAuth):

    def __init__(self, jwt_manager):
        self.jwt_manager = jwt_manager

    def get_user_id(self):
        jwt_data = self.jwt_manager.get_payload()
        user_id = jwt_data.get("user_id")
        return user_id

    def required(self, func):
        @wraps(func)
        def wrap(*args, **kwargs):
            return self.jwt_manager.required()(func)(*args, **kwargs)

        return wrap


def create_jwt_auth():
    jwt_manager = FlaskJWTManager(secret_key=config["jwt"]["secret_key"],
                                  security_algorithm=config["jwt"]["security_algorithm"])
    return JWTAuth(jwt_manager)


class LoginAuth(NonAuth):
    def __init__(self, manager):
        self.manager = manager

    def get_user_id(self):
        from flask_login import current_user
        return current_user.id

    def required(self, func):
        @wraps(func)
        def wrap(*args, **kwargs):
            return login_required(func)(*args, **kwargs)

        return wrap


app = Flask(__name__)
app.secret_key = config["management"]["flask_secret_key"]

csrf = CSRFProtect()
csrf.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "management.login"


@login_manager.user_loader
@provide_session
def load_user(user_id, session=None):
    user = session.query(User).filter(User.id == user_id).one_or_none()
    role = user.role
    permissions = role.permissions
    return user


user_service = UserService()

auth = LoginAuth(login_manager)

bp_management = Management(auth, user_service).register()
app.register_blueprint(bp_management)
