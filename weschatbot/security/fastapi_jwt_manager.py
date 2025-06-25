from fastapi import HTTPException

from weschatbot.security.exceptions import TokenExpiredError, TokenInvalidError
from weschatbot.security.jwt_manager import JWTManager
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
            raise HTTPException(status_code=401, detail="Invalid token")
        except TokenExpiredError as e:
            raise HTTPException(status_code=401, detail=f"{e}")
        except TokenInvalidError as e:
            raise HTTPException(status_code=401, detail=f"{e}")


_jwt_manager = FastAPIJWTManager(
    secret_key=config["jwt"]["secret_key"],
    security_algorithm=config["jwt"]["security_algorithm"]
)

required = _jwt_manager.required
refresh_required = _jwt_manager.refresh_required
