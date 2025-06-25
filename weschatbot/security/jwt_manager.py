from datetime import datetime, timedelta

import jwt

from weschatbot.security.exceptions import TokenExpiredError, TokenInvalidError
from weschatbot.utils.config import config


class JWTManager:
    def __init__(self, secret_key, security_algorithm):
        self.secret_key = secret_key
        self.security_algorithm = security_algorithm

    def create_token(self, exp_in_seconds, payload):
        if exp_in_seconds is not None:
            expire = datetime.now() + timedelta(seconds=exp_in_seconds)
            payload["exp"] = expire

        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.security_algorithm)
        return encoded_jwt

    def decode_token(self, token):
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.security_algorithm])
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Expired token")
        except jwt.InvalidTokenError:
            raise TokenInvalidError("Invalid token")

    def verify_token(self, token, token_type=None):
        try:
            payload = jwt.decode(token, self.secret_key,
                                 algorithms=[self.security_algorithm],
                                 options={"verify_exp": True})
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Expired token")
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError("Invalid token")

        if token_type and payload["type"] != token_type:
            raise TokenInvalidError(f"Invalid {token_type} token")
        return payload

    def create_access_token(self, exp_in_seconds, payload):
        payload["type"] = "access"
        return self.create_token(exp_in_seconds, payload)

    def create_refresh_token(self, exp_in_seconds, payload):
        payload["type"] = "refresh"
        return self.create_token(exp_in_seconds, payload)

    def verify_refresh_token(self, token):
        return self.verify_token(token, "refresh")

    def verify_access_token(self, token):
        return self.verify_token(token, "access")


_jwt_manager = JWTManager(
    secret_key=config["jwt"]["secret_key"],
    security_algorithm=config["jwt"]["security_algorithm"]
)


def create_refresh_token(exp_in_seconds, payload):
    return _jwt_manager.create_refresh_token(exp_in_seconds, payload)


def create_access_token(exp_in_seconds, payload):
    return _jwt_manager.create_access_token(exp_in_seconds, payload)


def decode_token(token):
    return _jwt_manager.decode_token(token)
