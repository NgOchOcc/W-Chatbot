from pydantic_settings import BaseSettings


class CsrfSettings(BaseSettings):
    # TODO move to configuration
    secret_key: str = "xxx-very-secret-key-xXx"


settings = CsrfSettings()
