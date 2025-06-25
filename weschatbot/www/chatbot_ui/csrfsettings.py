from pydantic_settings import BaseSettings


class CsrfSettings(BaseSettings):
    secret_key: str = "xxx-very-secret-key-xXx"

settings = CsrfSettings()
