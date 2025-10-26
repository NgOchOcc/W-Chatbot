from logging import DEBUG, INFO

import click
import uvicorn

from weschatbot.models.base import Base
from weschatbot.services.document.document_service import DocumentService
from weschatbot.utils import setting


@click.group()
def cli():
    pass


@cli.group("worker")
def worker():
    pass


@cli.group("scheduler")
def scheduler():
    pass


@cli.group("chatbot")
def chatbot():
    pass


@cli.group("management")
def management():
    pass


@cli.group("document")
def document():
    pass


@cli.group("db")
def db():
    pass


@worker.command("start")
def worker_start():
    from weschatbot.worker.celery_worker import worker as celery_worker
    celery_worker().start()


def init_db():
    from weschatbot.models.user import Role  # noqa
    from weschatbot.models.user import User  # noqa
    from weschatbot.models.user import ChatSession  # noqa
    from weschatbot.models.user import ChatMessage  # noqa
    from weschatbot.models.user import ChatStatus  # noqa

    Base.metadata.create_all(setting.mysql_engine)


@db.command("migrate")
def db_migrate():
    init_db()


@scheduler.command("start")
def scheduler_start():
    from weschatbot.worker.scheduler import schedule
    schedule()


@chatbot.command("start")
def chatbot_start():
    from weschatbot.www.chatbot_ui.app import app
    uvicorn.run(app, host="0.0.0.0", port=3000, log_level=INFO)


@cli.command()
def version():
    from weschatbot.version import version
    print(version)


@management.command("start")
@click.argument("gunicorn_args", nargs=-1, type=click.UNPROCESSED)
def management_start(gunicorn_args):
    from weschatbot.www.management.standalone_application import StandaloneApplication
    from weschatbot.www.management.app import app

    options = {}
    for k, v in map(lambda x: x.split("=", 1), gunicorn_args):
        options[k] = v

    StandaloneApplication(app, options).run()


@document.command("convert_all")
def convert_documents():
    print("Converting documents")
    document_service = DocumentService()
    document_service.convert_all_documents()
    print("Done")


@document.command("convert")
@click.option('--id', 'document_id', required=True, type=int, help='Document ID in database (integer)')
def convert_document(document_id):
    print(f"Converting document id: {document_id}")
    document_service = DocumentService()
    try:
        document_service.convert_document(document_id)
    except Exception as e:
        print(e)
        exit(1)
    exit(0)
