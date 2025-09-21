from functools import wraps, reduce

from flask import Flask, render_template
from flask_login import LoginManager, login_required
from flask_wtf import CSRFProtect
from sqlalchemy.orm import selectinload

from weschatbot.models.user import User
from weschatbot.security.flask_jwt_manager import FlaskJWTManager
from weschatbot.services.user_service import UserService
from weschatbot.utils.config import config
from weschatbot.utils.db import provide_session
from weschatbot.www.management.docs_blueprint import docs_bp
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
    user = session.query(User).options(selectinload(User.role)).filter(User.id == user_id).one_or_none()
    return user


@app.errorhandler(500)
def server_error(error):
    return render_template('management/error.html', code=500, title="Houston, we have a problem!",  # noqa
                           description="The page you are looking for is temporarily unavailable."), 500


@app.errorhandler(401)
def unauthorized_error(error):
    return render_template('management/error.html', code=401, title="Unauthorized Access",  # noqa
                           description="Please login to view this page."), 500


@app.errorhandler(403)
def forbidden_error(error):
    return render_template('management/error.html', code=403, title="Access Denied",  # noqa
                           description="You don’t have permission to access this page."), 403


@app.errorhandler(404)
def notfound_error(error):
    return render_template('management/error.html', code=404, title="Oops! Page not found",  # noqa
                           description="Looks like this page doesn't exist anymore or has been moved."), 404


user_service = UserService()

auth = LoginAuth(login_manager)

bp_management = Management(auth, user_service).register()
bp_management.register_blueprint(docs_bp)
app.register_blueprint(bp_management)
