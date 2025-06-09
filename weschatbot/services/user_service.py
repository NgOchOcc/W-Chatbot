import hashlib
import random
import string

from weschatbot.exceptions.user_exceptions import InvalidUserError
from weschatbot.models.user import Role, UserStatus, User
from weschatbot.utils.db import provide_session


class MD5:
    @staticmethod
    def hash_string(nake_string, salt_key):
        salted_string = nake_string + salt_key
        return hashlib.md5(salted_string.encode()).hexdigest()

    @staticmethod
    def validate_string(naked_string, salt_key, hashed_string):
        return hashed_string == MD5.hash_string(naked_string, salt_key)


def generate_random_string(length=7):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))


class UserService:

    @provide_session
    def update_password(self, user, password, session=None):
        salt = generate_random_string()
        hashed_password = MD5.hash_string(password, salt)
        user.password = hashed_password
        user.salt = salt

    @provide_session
    def create_user(self, user_name, password, role_name, status_name="new", session=None):
        salt = generate_random_string()
        hashed_password = MD5.hash_string(password, salt)
        role = session.query(Role).filter_by(name=role_name).first()
        status = session.query(UserStatus).filter_by(name=status_name).first()
        user = User(name=user_name, password=hashed_password, salt=salt, role=role, status=status)
        session.add(user)

    @provide_session
    def login_user(self, user_name, password, session=None):
        user = session.query(User).filter_by(name=user_name).first()
        if not user:
            raise InvalidUserError("Invalid username")
        if not MD5.validate_string(password, user.salt, user.password):
            raise InvalidUserError("Invalid password")
        if user.status.name != "active":
            raise InvalidUserError("User is not active")
        return user

    @provide_session
    def get_user(self, user_name, session=None):
        user = session.query(User).filter_by(name=user_name).first()
        if not user:
            raise InvalidUserError("Invalid username")
        return user
