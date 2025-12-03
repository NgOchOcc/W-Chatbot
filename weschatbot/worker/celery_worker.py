from celery import Celery
from kombu import Queue
from sqlalchemy.orm import scoped_session

from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.models.job import Job
from weschatbot.utils.common import SingletonMeta
from weschatbot.utils.config import config as app_config
from weschatbot.utils.db import provide_session


@provide_session
def get_all_modules(session: scoped_session = None):
    all_jobs = session.query(Job).all()
    return [".".join(job.class_name.split(".")[:-1]) for job in all_jobs]


class CeleryWorker(LoggingMixin, metaclass=SingletonMeta):

    def __init__(self, config, include):
        self.config = config

        self.celery = Celery(broker=config["celery"]["broker_url"],
                             backend=config["celery"]["backend_url"],
                             include=include)

        self.celery.conf.update(config["celery"])

        if "worker_concurrency" in config["celery"]:
            self.celery.conf.update(
                worker_concurrency=int(config["celery"]["worker_concurrency"])
            )

        if "task_queues" in config["celery"]:
            queues = [Queue(q.strip()) for q in config["celery"]["task_queues"].split(",")]
            self.celery.conf.task_queues = queues

    def get_celery_app(self):
        return self.celery


def celery_app():
    include = get_all_modules() + ["weschatbot.services.celery_service"]
    return CeleryWorker(app_config, include).get_celery_app()

# def worker():
#     return celery_app().Worker()
#
#
# if __name__ == '__main__':
#     worker().start()
