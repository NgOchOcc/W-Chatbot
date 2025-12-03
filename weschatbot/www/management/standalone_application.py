import logging.config

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

        log_conf = self.options.get("logConfig")
        if log_conf:
            self.cfg.set("on_starting",
                         lambda server: logging.config.fileConfig(log_conf, disable_existing_loggers=False))
            self.cfg.set("post_fork",
                         lambda server, worker: logging.config.fileConfig(log_conf, disable_existing_loggers=False))

    def load(self):
        return self.application
