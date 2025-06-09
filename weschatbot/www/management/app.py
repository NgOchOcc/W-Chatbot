from functools import wraps

from flask import Flask
from flask_wtf import CSRFProtect

from weschatbot.security.flask_jwt_manager import FlaskJWTManager
from weschatbot.utils.config import config
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


app = Flask(__name__)
app.secret_key = config["management"]["flask_secret_key"]

csrf = CSRFProtect()
csrf.init_app(app)

auth = NonAuth()

bp_management = Management(auth).register()
app.register_blueprint(bp_management)
