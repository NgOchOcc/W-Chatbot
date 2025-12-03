import hashlib
import logging
import random
import string
from typing import Optional

import bcrypt

from weschatbot.exceptions.user_exceptions import InvalidUserError
from weschatbot.models.user import Role, User
from weschatbot.utils.db import provide_session

logger = logging.getLogger(__name__)


class BcryptHash:
    DEFAULT_ROUNDS = 12

    @staticmethod
    def _prepare_password(naked_string: str) -> bytes:
        if naked_string is None:
            naked_string = ""
        return naked_string.encode("utf-8")

    @staticmethod
    def hash_string(naked_string: str, rounds: Optional[int] = None) -> str:
        if rounds is None:
            rounds = BcryptHash.DEFAULT_ROUNDS
        pw_bytes = BcryptHash._prepare_password(naked_string)
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(pw_bytes, salt)
        return hashed.decode("utf-8")

    @staticmethod
    def validate_string(naked_string: str, hashed_string: str) -> bool:
        if not hashed_string:
            return False
        try:
            pw_bytes = BcryptHash._prepare_password(naked_string)
            return bcrypt.checkpw(pw_bytes, hashed_string.encode("utf-8"))
        except (ValueError, TypeError) as e:
            logger.debug(e)
            return False


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


class BaseUserService:
    def update_password(self, user, password, session=None):
        raise NotImplementedError()

    def create_user(self, user_name, password, role_name, is_active=False, session=None):
        raise NotImplementedError()

    def login_user(self, user_name, password, session=None):
        raise NotImplementedError()

    @provide_session
    def get_user(self, user_name, session=None):
        user = session.query(User).filter_by(name=user_name).first()
        if not user:
            raise InvalidUserError("Invalid username")
        return user


class UserService(BaseUserService):

    @provide_session
    def update_password(self, user, password, session=None):
        salt = generate_random_string()
        hashed_password = MD5.hash_string(password, salt)
        user.password = hashed_password
        user.salt = salt

    @provide_session
    def create_user(self, user_name, password, role_name, is_active=False, session=None):
        salt = generate_random_string()
        hashed_password = MD5.hash_string(password, salt)
        role = session.query(Role).filter_by(name=role_name).first()
        user = User(name=user_name, password=hashed_password, salt=salt, role=role, is_active=is_active)
        session.add(user)

    @provide_session
    def login_user(self, user_name, password, session=None):
        user = session.query(User).filter_by(name=user_name).first()
        if not user:
            raise InvalidUserError("Invalid username")
        if not MD5.validate_string(password, user.salt, user.password):
            raise InvalidUserError("Invalid password")
        if not user.is_active:
            raise InvalidUserError("User is not active")
        return user


class BcryptUserService(UserService):
    @provide_session
    def update_password(self, user, password, session=None):
        hashed_password = BcryptHash.hash_string(password)
        user.password = hashed_password

    @provide_session
    def create_user(self, user_name, password, role_name, is_active=False, session=None):
        hashed_password = BcryptHash.hash_string(password)
        role = session.query(Role).filter_by(name=role_name).first()
        user = User(name=user_name, password=hashed_password, role=role, is_active=is_active)
        session.add(user)

    @provide_session
    def login_user(self, user_name, password, session=None):
        user = session.query(User).filter_by(name=user_name).first()
        if not user:
            raise InvalidUserError("Invalid username")
        if not BcryptHash.validate_string(password, user.password):
            raise InvalidUserError("Invalid password")
        if not user.is_active:
            raise InvalidUserError("User is not active")
        return user
