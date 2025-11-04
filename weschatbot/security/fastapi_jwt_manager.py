from fastapi import HTTPException
from jwt import InvalidTokenError

from weschatbot.security.exceptions import TokenExpiredError, TokenInvalidError
from weschatbot.security.jwt_manager import JWTManager
from weschatbot.services.token_service import TokenService
from weschatbot.utils.config import config


class FastAPIJWTManager(JWTManager):

    def required(self, credential):
        token = credential.credentials
        try:
            payload = self.verify_access_token(token)
            if payload:
                return payload
            raise TokenExpiredError("Invalid access token")
        except TokenInvalidError as e:
            raise e
        except TokenExpiredError as e:
            raise e

    def refresh_required(self, credential):
        token = credential.credentials
        try:
            payload = self.verify_refresh_token(token)
            if payload:
                return payload
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        except TokenExpiredError as e:
            raise HTTPException(status_code=401, detail=f"{e}")
        except TokenInvalidError as e:
            raise HTTPException(status_code=401, detail=f"{e}")

    def refresh(self, refresh_token):
        try:
            in_db_refresh_token = TokenService.get_refresh_token(refresh_token)
            if in_db_refresh_token:
                payload = self.verify_refresh_token(in_db_refresh_token.token)
                if payload:
                    new_access_token = self.create_access_token(
                        int(config["jwt"]["access_token_expires_in_seconds"]),
                        payload)
                    return payload, new_access_token
            raise TokenInvalidError("Invalid refresh token")
        except TokenExpiredError:
            raise
        except TokenInvalidError as e:
            raise


_jwt_manager = FastAPIJWTManager(
    secret_key=config["jwt"]["secret_key"],
    security_algorithm=config["jwt"]["security_algorithm"]
)

required = _jwt_manager.required
refresh_required = _jwt_manager.refresh_required
