from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from weschatbot.utils.config import config

mysql_config = config["db"]
mysql_engine = None
mysql_session = None

async_engine = None
mysql_async_session = None


def create_engine_parameters():
    return {
        "echo": mysql_config.getboolean("echo", True),
        "pool_size": mysql_config.getint("pool_size", 10),
        "max_overflow": mysql_config.getint("max_overflow", 10),
        "pool_timeout": mysql_config.getint("pool_timeout", 30),
        "pool_recycle": mysql_config.getint("pool_recycle", 3600),
        "pool_pre_ping": mysql_config.getboolean("pool_pre_ping", True),
        "isolation_level": mysql_config.get("isolation_level", "READ COMMITTED"),
    }


def configure_async_sqlalchemy_session():
    global mysql_async_session
    global async_engine

    async_engine = create_async_engine(
        mysql_config["async_sql_alchemy_conn"],
        **create_engine_parameters()
    )

    mysql_async_session = async_sessionmaker(
        autoflush=True,
        expire_on_commit=False,
        bind=async_engine,
        class_=AsyncSession
    )


def configure_sqlalchemy_session():
    from sqlalchemy import create_engine, QueuePool

    global mysql_session
    global mysql_config
    global mysql_engine

    mysql_engine = create_engine(
        url=mysql_config["sql_alchemy_conn"],
        poolclass=QueuePool,
        **create_engine_parameters()
    )

    mysql_session = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=True,
            bind=mysql_engine,
            expire_on_commit=False
        )
    )


def initialize():
    configure_sqlalchemy_session()
    configure_async_sqlalchemy_session()


initialize()
