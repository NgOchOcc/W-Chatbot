import click
import uvicorn

from weschatbot.models.base import Base
from weschatbot.utils import setting


@click.group()
def cli():
    pass


@cli.group("chatbot")
def chatbot():
    pass


@cli.group("management")
def management():
    pass


@cli.group("db")
def db():
    pass


def init_db():
    from weschatbot.models.user import UserStatus  # noqa
    from weschatbot.models.user import Role  # noqa
    from weschatbot.models.user import User  # noqa

    Base.metadata.create_all(setting.mysql_engine)


@db.command("migrate")
def db_migrate():
    init_db()


@chatbot.command("start")
def chatbot_start():
    from weschatbot.www.chatbot_ui.app import app
    uvicorn.run(app, host="0.0.0.0", port=8000)


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
