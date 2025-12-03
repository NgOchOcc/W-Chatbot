from flask import request, jsonify

from weschatbot.security.exceptions import TokenInvalidError, TokenExpiredError
from weschatbot.security.jwt_manager import JWTManager
from weschatbot.utils.config import config


class FlaskJWTManager(JWTManager):

    @staticmethod
    def _extract_bearer(header_value: str) -> str:
        if not header_value:
            raise TokenInvalidError("Bearer token is missing")
        token = header_value.strip()
        if token.lower().startswith("bearer "):
            return token[len("bearer "):].strip()
        return token

    @staticmethod
    def get_bearer_token():
        header = request.headers.get("Authorization")
        return FlaskJWTManager._extract_bearer(header)

    def get_payload(self):
        token = self.get_bearer_token()
        if not token:
            raise TokenInvalidError("Bearer token is missing")
        return self.verify_token(token)

    def required(self, refresh=False):
        def wrap_func(fn):
            def wrapper(*args, **kwargs):
                bearer_token = request.headers.get("Authorization")
                if not bearer_token:
                    raise TokenInvalidError("Bearer token is required")

                try:
                    token = self.get_bearer_token()
                    if refresh:
                        if self.verify_refresh_token(token):
                            return fn(*args, **kwargs)
                    else:
                        if self.verify_access_token(token):
                            return fn(*args, **kwargs)
                    return jsonify({"error": "Invalid token"})
                except TokenExpiredError as e:
                    return jsonify({"error": f"{e}"}), 401
                except TokenInvalidError as e:
                    return jsonify({"error": f"{e}"}), 401

            return wrapper

        return wrap_func


_jwt_manager = FlaskJWTManager(
    secret_key=config["jwt"]["secret_key"],
    security_algorithm=config["jwt"]["security_algorithm"]
)

required = _jwt_manager.required
get_payload = _jwt_manager.get_payload
