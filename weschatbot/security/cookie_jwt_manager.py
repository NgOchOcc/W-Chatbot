from typing import Optional

from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request
from starlette.responses import RedirectResponse

from weschatbot.exceptions.user_exceptions import InvalidUserError
from weschatbot.security.exceptions import TokenExpiredError, TokenInvalidError
from weschatbot.security.fastapi_jwt_manager import FastAPIJWTManager


class CookieJWTConfig:
    access_token_cookie_name = "jwt_access_token"


class CookieJWT:
    def __init__(self, config: CookieJWTConfig):
        self.config = config
        self.access_token_cookie_name = config.access_token_cookie_name

    def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        token = request.cookies.get(self.config.access_token_cookie_name)
        if not token:
            raise TokenInvalidError("Missing token cookie")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class FastAPICookieJwtManager(FastAPIJWTManager):
    reusable_oauth2 = CookieJWT(CookieJWTConfig())

    def required(self, credential=Depends(reusable_oauth2)):
        try:
            return super().required(credential)
        except TokenInvalidError as e:
            raise e
        except TokenExpiredError as e:
            raise e

    def refresh_required(self, credential=Depends(reusable_oauth2)):
        return super().refresh_required(credential)

    def set_token_cookie(self, token, response):
        response.set_cookie(
            key=self.reusable_oauth2.access_token_cookie_name,
            value=token,
            httponly=True
        )

    def delete_token_cookie(self, response):
        response.delete_cookie(key=self.reusable_oauth2.access_token_cookie_name)
