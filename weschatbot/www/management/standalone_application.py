from gunicorn.app.base import BaseApplication

from weschatbot.log.logging_mixin import LoggingMixin


class StandaloneApplication(BaseApplication, LoggingMixin):
    def __init__(self, application, options=None):
        self.application = application
        self.options = options or {}
        super().__init__()

    def load_config(self):
        config = {key.lower(): value for key, value in self.options.items()}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

