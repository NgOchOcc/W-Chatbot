from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

from weschatbot.security.exceptions import TokenExpiredError, TokenInvalidError
from weschatbot.security.fastapi_jwt_manager import FastAPIJWTManager


class FastAPIJWTHeaderManager(FastAPIJWTManager):
    reusable_oauth2 = HTTPBearer(
        scheme_name='Authorization'
    )

    def required(self, credential=Depends(reusable_oauth2)):
        try:
            return super().required(credential)
        except TokenExpiredError as e:
            raise HTTPException(status_code=401, detail=f"{e}")
        except TokenInvalidError as e:
            raise HTTPException(status_code=401, detail=f"{e}")

    def refresh_required(self, credential=Depends(reusable_oauth2)):
        return super().refresh_required(credential)
