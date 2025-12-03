from fastapi import Depends, Response, Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from weschatbot.security.exceptions import TokenExpiredError, TokenInvalidError
from weschatbot.security.fastapi_jwt_manager import FastAPIJWTManager
from weschatbot.utils.config import config

COOKIE_SAMESITE = config["jwt"]["cookie_samesite"]
COOKIE_SECURE = config.getboolean("jwt", "cookie_secure")
COOKIE_ACCESS_TOKEN_MAX_AGE = config.getint("jwt", "access_token_expires_in_seconds")
COOKIE_REFRESH_TOKEN_MAX_AGE = config.getint("jwt", "refresh_token_expires_in_seconds")


class CookieJWTConfig:
    access_token_cookie_name = "jwt_access_token"
    refresh_token_cookie_name = "jwt_refresh_token"


class CookieJWT:
    def __init__(self, config: CookieJWTConfig):
        self.config = config
        self.access_token_cookie_name = config.access_token_cookie_name
        self.refresh_token_cookie_name = config.refresh_token_cookie_name

    def __call__(self, request: Request):
        token = request.cookies.get(self.config.access_token_cookie_name)
        refresh_token = request.cookies.get(self.config.refresh_token_cookie_name)
        if not token:
            raise TokenInvalidError("Missing token cookie")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token), refresh_token


class FastAPICookieJwtManager(FastAPIJWTManager):
    reusable_oauth2 = CookieJWT(CookieJWTConfig())

    async def required(self, response: Response, credential_refresh_token=Depends(reusable_oauth2)):
        refresh_token = None
        try:
            credential, refresh_token = credential_refresh_token
            return super().required(credential)
        except TokenInvalidError as e:
            raise e
        except TokenExpiredError as e:
            self.log.debug(e)
            if not refresh_token:
                raise HTTPException(status_code=401, detail="Access token expired and no refresh token")
            try:
                payload, new_access_token = self.refresh(refresh_token=refresh_token)
                response.set_cookie(
                    key=self.reusable_oauth2.access_token_cookie_name,
                    value=new_access_token,
                    httponly=True,
                    samesite=COOKIE_SAMESITE,
                    secure=COOKIE_SECURE,
                    max_age=COOKIE_ACCESS_TOKEN_MAX_AGE
                )
                return payload
            except TokenExpiredError as e:
                self.log.debug(e)
                raise HTTPException(status_code=401, detail="Refresh token expired")
            except TokenInvalidError:
                self.log.debug(e)
                raise HTTPException(status_code=401, detail="Invalid refresh token")
            except Exception:
                self.log.debug("Unexpected error during token refresh")
                raise HTTPException(status_code=401, detail="Could not refresh token")

    def refresh_required(self, credential=Depends(reusable_oauth2)):
        return super().refresh_required(credential)

    def set_token_cookie(self, token, response, refresh_token):
        response.set_cookie(
            key=self.reusable_oauth2.access_token_cookie_name,
            value=token,
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE,
            max_age=COOKIE_ACCESS_TOKEN_MAX_AGE
        )

        response.set_cookie(
            key=self.reusable_oauth2.refresh_token_cookie_name,
            value=refresh_token,
            httponly=True,
            samesite=COOKIE_SAMESITE,
            secure=COOKIE_SECURE,
            max_age=COOKIE_REFRESH_TOKEN_MAX_AGE
        )

    def delete_token_cookie(self, response):
        response.delete_cookie(key=self.reusable_oauth2.access_token_cookie_name)
        response.delete_cookie(key=self.reusable_oauth2.refresh_token_cookie_name)
